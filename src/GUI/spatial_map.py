from __future__ import annotations

import math
import tkinter as tk
from tkinter import ttk


class SpatialMap:
    """Mapa 2D do corpo de prova.

    O mapa ainda é somente visual: nenhum clique aqui envia comando ao Arduino.
    A origem (0, 0) fica no centro do corpo de prova.
    """

    DEFAULT_SIZE_MM = 35.74

    def __init__(self, parent, colors_getter):
        self.parent = parent
        self.colors_getter = colors_getter
        self.points: list[dict[str, float]] = []
        self.selected_index: int | None = None
        self.shape_var = tk.StringVar(value="Círculo")
        self.size_var = tk.StringVar(value=f"{self.DEFAULT_SIZE_MM:.2f}")
        self.canvas_size = 560
        self.margin = 55

        self.frame = ttk.Frame(parent, padding=18)
        self.frame.pack(fill="both", expand=True)

        header = ttk.Frame(self.frame)
        header.pack(fill="x", pady=(0, 10))
        ttk.Label(header, text="Mapa Espacial", font=("Segoe UI", 18, "bold")).pack(side="left")

        geometry = ttk.LabelFrame(self.frame, text=" Corpo de prova ", padding=8)
        geometry.pack(fill="x", pady=(0, 10))
        ttk.Label(geometry, text="Formato:").pack(side="left", padx=(0, 6))
        shape = ttk.Combobox(
            geometry,
            textvariable=self.shape_var,
            values=("Círculo", "Quadrado"),
            state="readonly",
            width=12,
        )
        shape.pack(side="left")
        shape.bind("<<ComboboxSelected>>", lambda _event: self._geometry_changed())

        ttk.Label(geometry, text="Diâmetro / lado (mm):").pack(side="left", padx=(18, 6))
        size_entry = ttk.Entry(geometry, textvariable=self.size_var, width=12)
        size_entry.pack(side="left")
        size_entry.bind("<Return>", lambda _event: self._geometry_changed())
        ttk.Button(geometry, text="Aplicar", command=self._geometry_changed).pack(side="left", padx=8)

        self.geometry_info = ttk.Label(geometry, text="Centro: X = 0 / Y = 0")
        self.geometry_info.pack(side="left", padx=14)

        body = ttk.Frame(self.frame)
        body.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(
            body,
            width=self.canvas_size,
            height=self.canvas_size,
            highlightthickness=1,
            relief="flat",
        )
        self.canvas.pack(side="left", fill="both", expand=True, padx=(0, 18))
        self.canvas.bind("<Button-1>", self._on_left_click)
        self.canvas.bind("<Button-3>", self._on_right_click)
        self.canvas.bind("<Configure>", lambda _event: self._draw())

        side = ttk.LabelFrame(body, text=" Pontos ", padding=10)
        side.pack(side="right", fill="y")

        self.count_var = tk.StringVar(value="0 pontos")
        ttk.Label(side, textvariable=self.count_var, font=("Segoe UI", 12, "bold")).pack(pady=(0, 8))

        list_frame = ttk.Frame(side)
        list_frame.pack(fill="both", expand=True)
        self.listbox = tk.Listbox(list_frame, width=30, height=10, font=("Consolas", 10), relief="flat")
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scrollbar.set)
        self.listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.listbox.bind("<<ListboxSelect>>", self._select_from_list)

        ttk.Button(side, text="Remover selecionado", command=self.remove_selected).pack(fill="x", pady=(8, 5))
        ttk.Button(side, text="Limpar pontos", command=self.clear).pack(fill="x")

        editor = ttk.LabelFrame(side, text=" Editar ponto ", padding=8)
        editor.pack(fill="x", pady=(12, 0))
        ttk.Label(editor, text="X (mm)").grid(row=0, column=0, sticky="w", pady=3)
        ttk.Label(editor, text="Y (mm)").grid(row=1, column=0, sticky="w", pady=3)
        self.edit_x_var = tk.StringVar()
        self.edit_y_var = tk.StringVar()
        ttk.Entry(editor, textvariable=self.edit_x_var, width=11).grid(row=0, column=1, padx=5)
        ttk.Entry(editor, textvariable=self.edit_y_var, width=11).grid(row=1, column=1, padx=5)
        ttk.Button(editor, text="Salvar ponto", command=self.save_selected).grid(row=2, column=0, columnspan=2, pady=(7, 2), sticky="ew")

        self._geometry_changed()

    @property
    def size_mm(self) -> float:
        try:
            value = float(self.size_var.get().replace(",", "."))
            if value <= 0:
                raise ValueError
            return value
        except ValueError:
            return self.DEFAULT_SIZE_MM

    def _geometry_changed(self):
        value = self.size_mm
        self.size_var.set(f"{value:.3f}")
        self._draw()
        self._refresh_list()

    def _half_size_mm(self):
        return self.size_mm / 2.0

    def _geometry(self):
        width = max(self.canvas.winfo_width(), 400)
        height = max(self.canvas.winfo_height(), 400)
        cx = width / 2
        cy = height / 2
        half = self._half_size_mm()
        radius_px = min(width, height) / 2 - self.margin
        scale = radius_px / half
        return cx, cy, radius_px, scale

    def _mm_to_px(self, x, y):
        cx, cy, _, scale = self._geometry()
        return cx + x * scale, cy - y * scale

    def _px_to_mm(self, px, py):
        cx, cy, _, scale = self._geometry()
        return (px - cx) / scale, (cy - py) / scale

    def _inside_sample(self, x, y):
        half = self._half_size_mm()
        if self.shape_var.get() == "Círculo":
            return math.hypot(x, y) <= half
        return abs(x) <= half and abs(y) <= half

    def _point_at(self, px, py):
        for index, point in reversed(list(enumerate(self.points))):
            point_x, point_y = self._mm_to_px(point["x"], point["y"])
            if math.hypot(px - point_x, py - point_y) <= 10:
                return index
        return None

    def _on_left_click(self, event):
        existing = self._point_at(event.x, event.y)
        if existing is not None:
            self.selected_index = existing
            self._load_selected_editor()
            self._refresh_list()
            self._draw()
            return

        x, y = self._px_to_mm(event.x, event.y)
        if not self._inside_sample(x, y):
            return
        self.points.append({"x": x, "y": y})
        self.selected_index = len(self.points) - 1
        self._refresh_list()
        self._load_selected_editor()
        self._draw()

    def _on_right_click(self, event):
        index = self._point_at(event.x, event.y)
        if index is None:
            index = self.selected_index
        if index is None or not (0 <= index < len(self.points)):
            return
        del self.points[index]
        if not self.points:
            self.selected_index = None
        else:
            self.selected_index = min(index, len(self.points) - 1)
        self._refresh_list()
        self._load_selected_editor()
        self._draw()

    def _select_from_list(self, _event=None):
        selected = self.listbox.curselection()
        if not selected:
            return
        self.selected_index = selected[0]
        self._load_selected_editor()
        self._draw()

    def _load_selected_editor(self):
        if self.selected_index is None or not self.points:
            self.edit_x_var.set("")
            self.edit_y_var.set("")
            return
        point = self.points[self.selected_index]
        self.edit_x_var.set(f"{point['x']:.3f}")
        self.edit_y_var.set(f"{point['y']:.3f}")

    def save_selected(self):
        if self.selected_index is None or not self.points:
            return
        try:
            x = float(self.edit_x_var.get().replace(",", "."))
            y = float(self.edit_y_var.get().replace(",", "."))
        except ValueError:
            return
        if not self._inside_sample(x, y):
            return
        self.points[self.selected_index] = {"x": x, "y": y}
        self._refresh_list()
        self._draw()

    def remove_selected(self):
        if self.selected_index is None:
            selected = self.listbox.curselection()
            if not selected:
                return
            self.selected_index = selected[0]
        if 0 <= self.selected_index < len(self.points):
            del self.points[self.selected_index]
        if not self.points:
            self.selected_index = None
        else:
            self.selected_index = min(self.selected_index, len(self.points) - 1)
        self._refresh_list()
        self._load_selected_editor()
        self._draw()

    def clear(self):
        self.points.clear()
        self.selected_index = None
        self._refresh_list()
        self._load_selected_editor()
        self._draw()

    def _refresh_list(self):
        self.listbox.delete(0, tk.END)
        for i, point in enumerate(self.points, 1):
            marker = "● " if self.selected_index == i - 1 else "  "
            self.listbox.insert(tk.END, f"{marker}{i:02d}  X {point['x']:+8.3f}  Y {point['y']:+8.3f}")
        if self.selected_index is not None and self.points:
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(self.selected_index)
            self.listbox.see(self.selected_index)
        self.count_var.set(f"{len(self.points)} ponto{'s' if len(self.points) != 1 else ''}")

    def _draw(self):
        if not hasattr(self, "canvas"):
            return
        colors = self.colors_getter()
        self.canvas.configure(bg=colors["field"], highlightbackground=colors["border"])
        self.canvas.delete("all")

        cx, cy, radius_px, _ = self._geometry()
        if self.shape_var.get() == "Círculo":
            self.canvas.create_oval(
                cx - radius_px, cy - radius_px,
                cx + radius_px, cy + radius_px,
                fill=colors["panel"], outline=colors["accent"], width=2,
            )
        else:
            self.canvas.create_rectangle(
                cx - radius_px, cy - radius_px,
                cx + radius_px, cy + radius_px,
                fill=colors["panel"], outline=colors["accent"], width=2,
            )

        self.canvas.create_line(self.margin, cy, self.canvas.winfo_width() - self.margin, cy, fill=colors["border"], width=1)
        self.canvas.create_line(cx, self.margin, cx, self.canvas.winfo_height() - self.margin, fill=colors["border"], width=1)
        self.canvas.create_text(self.canvas.winfo_width() - self.margin + 18, cy, text="+X", fill=colors["text"], font=("Segoe UI", 10, "bold"))
        self.canvas.create_text(cx, self.margin - 15, text="+Y", fill=colors["text"], font=("Segoe UI", 10, "bold"))
        self.canvas.create_text(cx + 18, cy + 15, text="0,0", fill=colors["text"], font=("Consolas", 9))

        for i, point in enumerate(self.points, 1):
            px, py = self._mm_to_px(point["x"], point["y"])
            selected = self.selected_index == i - 1
            r = 8 if selected else 6
            self.canvas.create_oval(
                px - r, py - r, px + r, py + r,
                fill=colors["danger"],
                outline=colors["text"] if selected else colors["danger"],
                width=2 if selected else 1,
            )
            self.canvas.create_text(px + 13, py - 13, text=str(i), fill=colors["text"], font=("Segoe UI", 10, "bold"))

    def refresh_theme(self):
        self._draw()

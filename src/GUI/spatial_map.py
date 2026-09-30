from __future__ import annotations

import math
import tkinter as tk
from tkinter import ttk


class SpatialMap:
    """Mapa 2D do corpo de prova. Nenhum clique aqui movimenta a máquina."""

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
        shape = ttk.Combobox(geometry, textvariable=self.shape_var, values=("Círculo", "Quadrado"), state="readonly", width=12)
        shape.pack(side="left")
        shape.bind("<<ComboboxSelected>>", lambda _event: self._geometry_changed())
        ttk.Label(geometry, text="Diâmetro / lado (mm):").pack(side="left", padx=(18, 6))
        ttk.Entry(geometry, textvariable=self.size_var, width=12).pack(side="left")
        ttk.Button(geometry, text="Aplicar", command=self._geometry_changed).pack(side="left", padx=8)
        self.geometry_info = ttk.Label(geometry, text="Centro: X = 0 / Y = 0")
        self.geometry_info.pack(side="left", padx=14)

        body = ttk.Frame(self.frame)
        body.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(body, width=self.canvas_size, height=self.canvas_size, highlightthickness=1, relief="flat")
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
        self.points_canvas = tk.Canvas(list_frame, width=350, height=330, highlightthickness=0)
        points_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.points_canvas.yview)
        self.points_rows = ttk.Frame(self.points_canvas)
        self.points_window = self.points_canvas.create_window((0, 0), window=self.points_rows, anchor="nw")
        self.points_canvas.configure(yscrollcommand=points_scroll.set)
        self.points_canvas.pack(side="left", fill="both", expand=True)
        points_scroll.pack(side="right", fill="y")
        self.points_rows.bind("<Configure>", lambda _e: self.points_canvas.configure(scrollregion=self.points_canvas.bbox("all")))
        self.points_canvas.bind("<Configure>", lambda e: self.points_canvas.itemconfigure(self.points_window, width=e.width))
        self.points_canvas.bind("<MouseWheel>", self._scroll_points)

        buttons = ttk.Frame(side)
        buttons.pack(fill="x", pady=(8, 0))
        ttk.Button(buttons, text="Limpar pontos", command=self.clear).pack(fill="x")
        ttk.Label(side, text="Clique esquerdo: adicionar / selecionar\nClique direito: apagar selecionado", font=("Segoe UI", 9)).pack(pady=(8, 0))

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
        self.geometry_info.configure(text=f"Centro: X = 0 / Y = 0  |  Tamanho: {value:.3f} mm")
        self._refresh_rows()
        self._draw()

    def _half_size_mm(self):
        return self.size_mm / 2.0

    def _geometry(self):
        width = max(self.canvas.winfo_width(), 400)
        height = max(self.canvas.winfo_height(), 400)
        cx, cy = width / 2, height / 2
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
            self._refresh_rows()
            self._draw()
            return
        x, y = self._px_to_mm(event.x, event.y)
        if not self._inside_sample(x, y):
            return
        self.points.append({"x": x, "y": y})
        self.selected_index = len(self.points) - 1
        self._refresh_rows()
        self._draw()

    def _on_right_click(self, event):
        index = self._point_at(event.x, event.y)
        if index is None:
            index = self.selected_index
        if index is None or not (0 <= index < len(self.points)):
            return
        self._delete_index(index)

    def _delete_index(self, index):
        del self.points[index]
        if not self.points:
            self.selected_index = None
        else:
            self.selected_index = min(index, len(self.points) - 1)
        self._refresh_rows()
        self._draw()

    def _select(self, index):
        self.selected_index = index
        self._refresh_rows()
        self._draw()

    def _save_row(self, index, x_var, y_var):
        try:
            x = float(x_var.get().replace(",", "."))
            y = float(y_var.get().replace(",", "."))
        except ValueError:
            self._refresh_rows()
            return
        if not self._inside_sample(x, y):
            self._refresh_rows()
            return
        self.points[index] = {"x": x, "y": y}
        self.selected_index = index
        self._refresh_rows()
        self._draw()

    def _refresh_rows(self):
        if not hasattr(self, "points_rows"):
            return
        for child in self.points_rows.winfo_children():
            child.destroy()
        for index, point in enumerate(self.points):
            row = tk.Frame(self.points_rows, bd=1, relief="solid")
            row.pack(fill="x", pady=2)
            row.bind("<Button-1>", lambda _e, i=index: self._select(i))
            marker = "●" if self.selected_index == index else "○"
            tk.Button(row, text=marker, width=2, relief="flat", command=lambda i=index: self._select(i)).pack(side="left")
            tk.Label(row, text=f"P{index + 1}", width=4, anchor="w").pack(side="left")
            x_var = tk.StringVar(value=f"{point['x']:.3f}")
            y_var = tk.StringVar(value=f"{point['y']:.3f}")
            tk.Entry(row, textvariable=x_var, width=8, justify="center").pack(side="left", padx=2)
            tk.Entry(row, textvariable=y_var, width=8, justify="center").pack(side="left", padx=2)
            tk.Button(row, text="✓", width=3, relief="flat", command=lambda i=index, xv=x_var, yv=y_var: self._save_row(i, xv, yv)).pack(side="left", padx=2)
            tk.Button(row, text="🗑", width=3, relief="flat", command=lambda i=index: self._delete_index(i)).pack(side="left", padx=2)
        self.count_var.set(f"{len(self.points)} ponto{'s' if len(self.points) != 1 else ''}")
        if self.selected_index is not None and self.points:
            self.points_canvas.after_idle(lambda: self.points_canvas.yview_moveto(min(1.0, self.selected_index / max(1, len(self.points)))))

    def _scroll_points(self, event):
        self.points_canvas.yview_scroll(int(-event.delta / 120), "units")

    def clear(self):
        self.points.clear()
        self.selected_index = None
        self._refresh_rows()
        self._draw()

    def _draw(self):
        if not hasattr(self, "canvas"):
            return
        colors = self.colors_getter()
        self.canvas.configure(bg=colors["field"], highlightbackground=colors["border"])
        self.canvas.delete("all")
        cx, cy, radius_px, _ = self._geometry()
        if self.shape_var.get() == "Círculo":
            self.canvas.create_oval(cx - radius_px, cy - radius_px, cx + radius_px, cy + radius_px, fill=colors["panel"], outline=colors["accent"], width=2)
        else:
            self.canvas.create_rectangle(cx - radius_px, cy - radius_px, cx + radius_px, cy + radius_px, fill=colors["panel"], outline=colors["accent"], width=2)
        self.canvas.create_line(self.margin, cy, self.canvas.winfo_width() - self.margin, cy, fill=colors["border"], width=1)
        self.canvas.create_line(cx, self.margin, cx, self.canvas.winfo_height() - self.margin, fill=colors["border"], width=1)
        self.canvas.create_text(self.canvas.winfo_width() - self.margin + 18, cy, text="+X", fill=colors["text"], font=("Segoe UI", 10, "bold"))
        self.canvas.create_text(cx, self.margin - 15, text="+Y", fill=colors["text"], font=("Segoe UI", 10, "bold"))
        self.canvas.create_text(cx + 18, cy + 15, text="0,0", fill=colors["text"], font=("Consolas", 9))
        for i, point in enumerate(self.points, 1):
            px, py = self._mm_to_px(point["x"], point["y"])
            selected = self.selected_index == i - 1
            r = 8 if selected else 6
            self.canvas.create_oval(px - r, py - r, px + r, py + r, fill=colors["danger"], outline=colors["text"] if selected else colors["danger"], width=2 if selected else 1)
            self.canvas.create_text(px + 13, py - 13, text=str(i), fill=colors["text"], font=("Segoe UI", 10, "bold"))

    def refresh_theme(self):
        self._draw()

from __future__ import annotations

import math
import tkinter as tk
from tkinter import ttk


class SpatialMap:
    """Mapa 2D do corpo de prova circular.

    Esta primeira versão é apenas visual: clique no círculo para criar pontos
    X/Y. Nenhum comando é enviado ao Arduino.
    """

    DIAMETER_MM = 35.74

    def __init__(self, parent, colors_getter):
        self.parent = parent
        self.colors_getter = colors_getter
        self.points: list[tuple[float, float]] = []
        self.radius_mm = self.DIAMETER_MM / 2.0
        self.canvas_size = 560
        self.margin = 55

        self.frame = ttk.Frame(parent, padding=18)
        self.frame.pack(fill="both", expand=True)

        header = ttk.Frame(self.frame)
        header.pack(fill="x", pady=(0, 12))
        ttk.Label(header, text="Mapa Espacial", font=("Segoe UI", 18, "bold")).pack(side="left")
        ttk.Label(header, text="Clique no corpo de prova para adicionar pontos X/Y.", font=("Segoe UI", 10)).pack(side="left", padx=18)

        body = ttk.Frame(self.frame)
        body.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(body, width=self.canvas_size, height=self.canvas_size,
                                highlightthickness=1, relief="flat")
        self.canvas.pack(side="left", fill="both", expand=True, padx=(0, 18))
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<Configure>", lambda _event: self._draw())

        side = ttk.LabelFrame(body, text=" Pontos ", padding=12)
        side.pack(side="right", fill="y")
        self.count_var = tk.StringVar(value="0 pontos")
        ttk.Label(side, textvariable=self.count_var, font=("Segoe UI", 12, "bold")).pack(pady=(0, 10))

        self.listbox = tk.Listbox(side, width=27, height=18, font=("Consolas", 10), relief="flat")
        self.listbox.pack(fill="both", expand=True)

        ttk.Button(side, text="Remover selecionado", command=self.remove_selected).pack(fill="x", pady=(10, 5))
        ttk.Button(side, text="Limpar pontos", command=self.clear).pack(fill="x")

        info = ttk.LabelFrame(side, text=" Corpo de prova ", padding=8)
        info.pack(fill="x", pady=(18, 0))
        ttk.Label(info, text=f"Diâmetro: {self.DIAMETER_MM:.2f} mm").pack(anchor="w")
        ttk.Label(info, text="Centro: X = 0 / Y = 0").pack(anchor="w")

        self._draw()

    def _geometry(self):
        width = max(self.canvas.winfo_width(), 400)
        height = max(self.canvas.winfo_height(), 400)
        cx = width / 2
        cy = height / 2
        radius_px = min(width, height) / 2 - self.margin
        scale = radius_px / self.radius_mm
        return cx, cy, radius_px, scale

    def _mm_to_px(self, x, y):
        cx, cy, _, scale = self._geometry()
        return cx + x * scale, cy - y * scale

    def _px_to_mm(self, px, py):
        cx, cy, _, scale = self._geometry()
        return (px - cx) / scale, (cy - py) / scale

    def _on_click(self, event):
        x, y = self._px_to_mm(event.x, event.y)
        if math.hypot(x, y) > self.radius_mm:
            return
        self.points.append((x, y))
        self._refresh_list()
        self._draw()

    def remove_selected(self):
        selected = self.listbox.curselection()
        if not selected:
            return
        del self.points[selected[0]]
        self._refresh_list()
        self._draw()

    def clear(self):
        self.points.clear()
        self._refresh_list()
        self._draw()

    def _refresh_list(self):
        self.listbox.delete(0, tk.END)
        for i, (x, y) in enumerate(self.points, 1):
            self.listbox.insert(tk.END, f"{i:02d}    X {x:+8.3f}    Y {y:+8.3f}")
        self.count_var.set(f"{len(self.points)} ponto{'s' if len(self.points) != 1 else ''}")

    def _draw(self):
        if not hasattr(self, "canvas"):
            return
        colors = self.colors_getter()
        self.canvas.configure(bg=colors["field"], highlightbackground=colors["border"])
        self.canvas.delete("all")

        cx, cy, radius_px, _ = self._geometry()
        self.canvas.create_oval(cx - radius_px, cy - radius_px, cx + radius_px, cy + radius_px,
                                fill=colors["panel"], outline=colors["accent"], width=2)

        # Eixos do mapa.
        self.canvas.create_line(self.margin, cy, self.canvas.winfo_width() - self.margin, cy,
                                fill=colors["border"], width=1)
        self.canvas.create_line(cx, self.margin, cx, self.canvas.winfo_height() - self.margin,
                                fill=colors["border"], width=1)
        self.canvas.create_text(self.canvas.winfo_width() - self.margin + 18, cy,
                                text="+X", fill=colors["text"], font=("Segoe UI", 10, "bold"))
        self.canvas.create_text(cx, self.margin - 15, text="+Y",
                                fill=colors["text"], font=("Segoe UI", 10, "bold"))
        self.canvas.create_text(cx + 18, cy + 15, text="0,0",
                                fill=colors["text"], font=("Consolas", 9))

        for i, (x, y) in enumerate(self.points, 1):
            px, py = self._mm_to_px(x, y)
            r = 6
            self.canvas.create_oval(px-r, py-r, px+r, py+r,
                                    fill=colors["danger"], outline=colors["danger"])
            self.canvas.create_text(px + 12, py - 12, text=str(i),
                                    fill=colors["text"], font=("Segoe UI", 10, "bold"))

    def refresh_theme(self):
        self._draw()

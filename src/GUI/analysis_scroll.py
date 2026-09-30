from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk


def install_analysis_scroll(MainWindow):
    """Substitui apenas a montagem da aba Análise.

    A lógica de execução existente permanece na MainWindow. Esta extensão
    apenas cria uma área rolável para que dezenas de pontos possam ser vistos
    e editados sem alterar o controlador ou o Arduino.
    """

    def _analysis(self, p):
        ttk.Label(p, text="Análise por pontos", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        setup = ttk.LabelFrame(p, text=" Pontos ", padding=8)
        setup.pack(fill="x", pady=13)
        ttk.Label(setup, text="Quantidade:", font=("Segoe UI", 10)).pack(side="left", padx=12)
        ttk.Spinbox(setup, from_=1, to=100, width=8, textvariable=self.point_count_var).pack(side="left")
        ttk.Button(setup, text="Criar", command=self.create_point_fields).pack(side="left", padx=10)
        ttk.Button(setup, text="Limpar", command=self.clear_points).pack(side="left")

        self.point_table = ttk.LabelFrame(p, text=" Posições X ", padding=6)
        self.point_table.pack(fill="both", expand=True)

        viewport = ttk.Frame(self.point_table)
        viewport.pack(fill="both", expand=True)
        self.point_canvas = tk.Canvas(viewport, highlightthickness=0)
        scrollbar = ttk.Scrollbar(viewport, orient="vertical", command=self.point_canvas.yview)
        self.point_scroll_frame = ttk.Frame(self.point_canvas)
        self.point_canvas_window = self.point_canvas.create_window((0, 0), window=self.point_scroll_frame, anchor="nw")
        self.point_canvas.configure(yscrollcommand=scrollbar.set)
        self.point_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.point_scroll_frame.bind("<Configure>", lambda _e: self.point_canvas.configure(scrollregion=self.point_canvas.bbox("all")))
        self.point_canvas.bind("<Configure>", lambda e: self.point_canvas.itemconfigure(self.point_canvas_window, width=e.width))
        self.point_canvas.bind("<MouseWheel>", lambda e: self.point_canvas.yview_scroll(int(-e.delta / 120), "units"))

        header = ttk.Frame(self.point_scroll_frame)
        header.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        ttk.Label(header, text="Ponto", font=("Segoe UI", 10, "bold"), width=12).grid(row=0, column=0)
        ttk.Label(header, text="X (mm)", font=("Segoe UI", 10, "bold"), width=16).grid(row=0, column=1)
        self.point_scroll_frame.columnconfigure(0, weight=1)

        footer = ttk.Frame(p)
        footer.pack(fill="x", pady=11)
        ttk.Label(footer, textvariable=self.sequence_status_var, font=("Segoe UI", 10)).pack(side="left")
        self.execute_button = ttk.Button(footer, text="EXECUTAR", command=self.execute_analysis, state="disabled")
        self.execute_button.pack(side="right")

    def create_point_fields(self):
        try:
            n = int(self.point_count_var.get())
            if not 1 <= n <= 100:
                raise ValueError
        except ValueError:
            messagebox.showerror("Pontos", "Quantidade inválida.")
            return

        for widget in self.point_scroll_frame.winfo_children():
            if widget.grid_info().get("row") != "0":
                widget.destroy()

        self.point_entries = []
        for row in range(1, n + 1):
            ttk.Label(self.point_scroll_frame, text=f"Ponto {row}", width=12).grid(row=row, column=0, pady=5, padx=5)
            entry = tk.Entry(self.point_scroll_frame, width=16, justify="center", font=("Segoe UI", 10))
            entry.grid(row=row, column=1, pady=5, padx=5)
            self.point_entries.append(entry)

        if self.point_entries:
            self.point_entries[0].focus_set()
        self.sequence_status_var.set(f"{n} pontos.")
        self.execute_button.configure(state="normal")

    MainWindow._analysis = _analysis
    MainWindow.create_point_fields = create_point_fields
    return MainWindow

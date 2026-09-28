from __future__ import annotations

import json
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

from src.controller.arduino import ArduinoController
from src.controller.axis import Axis
from src.controller.machine import Machine
from src.controller.point_sequence import PointSequence

CONFIG_FILE = Path("calibration.json")

# Tema claro original / tema escuro inspirado na interface escura do ChatGPT.
LIGHT = {"bg": "#f0f0f0", "panel": "#ffffff", "field": "#ffffff", "fg": "#202124", "muted": "#5f6368", "border": "#d0d3d8", "accent": "#5865f2", "danger": "#d93025"}
DARK = {"bg": "#212121", "panel": "#2f2f2f", "field": "#424242", "fg": "#ececec", "muted": "#b4b4b4", "border": "#4b4b4b", "accent": "#8ab4f8", "danger": "#f28b82"}


class MainWindow:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("IC Máquina — Controle de 3 Eixos")
        self.root.geometry("900x680")
        self.root.minsize(820, 620)
        self.dark_mode = False
        self.arduino: ArduinoController | None = None
        self.sequence = PointSequence()
        self.recovery_mm = 5.0
        self.up_direction = 1

        self.machine = Machine(
            x=Axis(200, 16, 8, calibrated_steps_per_mm=400.0),
            y=Axis(200, 16, 8, calibrated_steps_per_mm=400.0),
            z=Axis(200, 16, 8, calibrated_steps_per_mm=400.0),
        )
        self._load_calibration()

        self.port_var = tk.StringVar(value="COM3")
        self.status_var = tk.StringVar(value="Modo virtual — Arduino desconectado")
        self.log_var = tk.StringVar(value="Pronto.")
        self.step_var = tk.StringVar(value="100")
        self.target_axis_var = tk.StringVar(value="X")
        self.target_var = tk.StringVar()
        self.recovery_var = tk.StringVar(value=str(self.recovery_mm))
        self.point_x_var = tk.StringVar()
        self.point_label_var = tk.StringVar()
        self.calibration_vars = {a: tk.StringVar(value=f"{self.machine.get_axis(a).microsteps_per_mm:.6f}") for a in "XYZ"}
        self.position_vars = {a: tk.StringVar(value="0.000 mm") for a in "XYZ"}
        self.sequence_status_var = tk.StringVar(value="Nenhum ponto programado.")

        self.style = ttk.Style(self.root)
        self.style.theme_use("clam")
        self._build()
        self._apply_theme()
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def _build(self) -> None:
        self.header = tk.Frame(self.root)
        self.header.pack(fill="x", padx=20, pady=(15, 8))
        self.title_label = tk.Label(self.header, text="IC Máquina", font=("Segoe UI", 19, "bold"))
        self.title_label.pack(side="left")
        self.subtitle_label = tk.Label(self.header, text="Controle de 3 eixos", font=("Segoe UI", 10))
        self.subtitle_label.pack(side="left", padx=12, pady=(7, 0))
        ttk.Button(self.header, text="Modo escuro", command=self.toggle_dark_mode).pack(side="right")

        self.connection = ttk.LabelFrame(self.root, text="  Comunicação  ", padding=10)
        self.connection.pack(fill="x", padx=20, pady=5)
        ttk.Label(self.connection, text="Porta COM:").grid(row=0, column=0, padx=5)
        ttk.Entry(self.connection, textvariable=self.port_var, width=9).grid(row=0, column=1, padx=5)
        ttk.Button(self.connection, text="Conectar", command=self.connect).grid(row=0, column=2, padx=5)
        ttk.Button(self.connection, text="Desconectar", command=self.disconnect).grid(row=0, column=3, padx=5)
        self.status_label = tk.Label(self.connection, textvariable=self.status_var, font=("Segoe UI", 9, "bold"))
        self.status_label.grid(row=0, column=4, padx=15, sticky="w")
        self.connection.columnconfigure(4, weight=1)

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=20, pady=8)
        operation = ttk.Frame(notebook, padding=16)
        points = ttk.Frame(notebook, padding=16)
        calibration = ttk.Frame(notebook, padding=16)
        notebook.add(operation, text="Operação")
        notebook.add(points, text="Pontos")
        notebook.add(calibration, text="Calibração")
        self._build_operation(operation)
        self._build_points(points)
        self._build_calibration(calibration)

        self.footer = tk.Frame(self.root)
        self.footer.pack(fill="x", padx=20, pady=(2, 15))
        self.log_title = tk.Label(self.footer, text="LOG:", font=("Segoe UI", 8, "bold"))
        self.log_title.pack(side="left", padx=8, pady=7)
        self.log_label = tk.Label(self.footer, textvariable=self.log_var, anchor="w", font=("Segoe UI", 9))
        self.log_label.pack(side="left", fill="x", expand=True)

    def _build_operation(self, parent: ttk.Frame) -> None:
        positions = ttk.LabelFrame(parent, text="  Posição estimada  ")
        positions.pack(fill="x", pady=(0, 12))
        for col, axis in enumerate("XYZ"):
            card = tk.Frame(positions, highlightthickness=1)
            card.grid(row=0, column=col, padx=7, pady=10, sticky="nsew")
            tk.Label(card, text=axis, font=("Segoe UI", 12, "bold")).pack(padx=55, pady=(9, 2))
            tk.Label(card, textvariable=self.position_vars[axis], font=("Consolas", 14, "bold")).pack(padx=35, pady=(0, 9))
            positions.columnconfigure(col, weight=1)

        manual = ttk.LabelFrame(parent, text="  Movimento incremental  ")
        manual.pack(fill="x", pady=5)
        ttk.Label(manual, text="Passos:").grid(row=0, column=0, padx=8, pady=8)
        ttk.Entry(manual, textvariable=self.step_var, width=10).grid(row=0, column=1)
        for row, axis in enumerate("XYZ", start=1):
            ttk.Label(manual, text=axis, font=("Segoe UI", 10, "bold")).grid(row=row, column=0, padx=8, pady=4)
            minus = ttk.Button(manual, text=f"{axis} −", width=12)
            plus = ttk.Button(manual, text=f"{axis} +", width=12)
            minus.grid(row=row, column=1, padx=5, pady=3)
            plus.grid(row=row, column=2, padx=5, pady=3)
            minus.bind("<ButtonPress-1>", lambda _e, a=axis: self.jog_start(a, -1))
            minus.bind("<ButtonRelease-1>", lambda _e: self.jog_stop())
            plus.bind("<ButtonPress-1>", lambda _e, a=axis: self.jog_start(a, 1))
            plus.bind("<ButtonRelease-1>", lambda _e: self.jog_stop())
        tk.Button(parent, text="PARAR", command=self.stop, relief="flat", bd=0, font=("Segoe UI", 10, "bold")).pack(fill="x", pady=10, ipady=7)

        target = ttk.LabelFrame(parent, text="  Ir para posição teórica  ")
        target.pack(fill="x", pady=5)
        ttk.Label(target, text="Eixo:").grid(row=0, column=0, padx=5, pady=10)
        ttk.Combobox(target, values=("X", "Y", "Z"), state="readonly", width=5, textvariable=self.target_axis_var).grid(row=0, column=1)
        ttk.Label(target, text="Posição (mm):").grid(row=0, column=2, padx=5)
        ttk.Entry(target, textvariable=self.target_var, width=12).grid(row=0, column=3)
        ttk.Button(target, text="Mover", command=self.move_to).grid(row=0, column=4, padx=8)
        ttk.Button(parent, text="Zerar posição estimada", command=self.zero).pack(pady=6)

    def _build_points(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="Pontos de análise", font=("Segoe UI", 14, "bold")).pack(anchor="w")
        ttk.Label(parent, text="Para cada ponto: X → descer Z até o limite → subir Z → próximo ponto.").pack(anchor="w", pady=(3, 10))
        add = ttk.Frame(parent)
        add.pack(fill="x")
        ttk.Label(add, text="X (mm):").pack(side="left")
        ttk.Entry(add, textvariable=self.point_x_var, width=12).pack(side="left", padx=5)
        ttk.Label(add, text="Nome:").pack(side="left")
        ttk.Entry(add, textvariable=self.point_label_var, width=20).pack(side="left", padx=5)
        ttk.Button(add, text="Adicionar", command=self.add_point).pack(side="left", padx=5)
        ttk.Button(add, text="Remover", command=self.remove_point).pack(side="left")
        self.point_list = tk.Listbox(parent, height=12, relief="flat", font=("Consolas", 10))
        self.point_list.pack(fill="both", expand=True, pady=10)
        options = ttk.LabelFrame(parent, text="  Subida após o toque  ")
        options.pack(fill="x")
        ttk.Label(options, text="Distância (mm):").grid(row=0, column=0, padx=7, pady=9)
        ttk.Entry(options, textvariable=self.recovery_var, width=10).grid(row=0, column=1)
        ttk.Button(parent, text="Iniciar sequência", command=self.start_sequence).pack(fill="x", pady=9, ipady=5)
        ttk.Label(parent, textvariable=self.sequence_status_var).pack(anchor="w")

    def _build_calibration(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="Calibração", font=("Segoe UI", 14, "bold")).pack(anchor="w")
        ttk.Label(parent, text="Altere os valores experimentais de passos/mm usados nos cálculos.").pack(anchor="w", pady=(3, 12))
        table = ttk.LabelFrame(parent, text="  Passos por mm  ")
        table.pack(fill="x")
        for col, text in enumerate(("Eixo", "Passos/mm")):
            ttk.Label(table, text=text, font=("Segoe UI", 9, "bold")).grid(row=0, column=col, padx=30, pady=8)
        for row, axis in enumerate("XYZ", start=1):
            ttk.Label(table, text=axis, font=("Segoe UI", 10, "bold")).grid(row=row, column=0, pady=7)
            ttk.Entry(table, textvariable=self.calibration_vars[axis], width=18).grid(row=row, column=1)
        ttk.Button(parent, text="Aplicar calibração", command=self.apply_calibration).pack(anchor="w", pady=10)
        ttk.Button(parent, text="Salvar calibração", command=self.save_calibration).pack(anchor="w")

    def connect(self) -> None:
        try:
            controller = ArduinoController(self.port_var.get().strip())
            controller.connect()
            self.arduino = controller
            self.status_var.set(f"Arduino conectado — {controller.port}")
            self.status_label.configure(fg="#23a559")
            self.log_var.set("Conexão serial estabelecida.")
        except Exception as exc:
            self.status_var.set("Falha na conexão")
            messagebox.showerror("Arduino", str(exc))

    def disconnect(self) -> None:
        if self.arduino is not None:
            self.arduino.disconnect()
            self.arduino = None
        self.status_var.set("Modo virtual — Arduino desconectado")
        self.status_label.configure(fg=DARK["muted"] if self.dark_mode else LIGHT["muted"])
        self.log_var.set("Arduino desconectado.")

    def _send_move(self, axis: str, direction: int, steps: int) -> None:
        if self.arduino is None:
            self.log_var.set(f"Modo virtual: {axis} {'+' if direction > 0 else '-'} {steps} passos.")
            return
        response = self.arduino.send(f"MOVE {axis} {direction} {steps}")
        self.log_var.set(f"> MOVE {axis} {direction} {steps}    < {response}")

    def jog_start(self, axis: str, direction: int) -> None:
        if self.arduino is None:
            self.log_var.set(f"Modo virtual: JOG {axis} {'+' if direction > 0 else '-'}")
            return
        try:
            self.arduino.jog(axis, direction)
            self.log_var.set(f"> JOG {axis} {direction}")
        except Exception as exc:
            messagebox.showerror("JOG", str(exc))

    def jog_stop(self) -> None:
        self.stop(update_log=True)

    def stop(self, update_log: bool = True) -> None:
        if self.arduino is not None:
            try:
                self.arduino.stop()
            except Exception:
                pass
        if update_log:
            self.log_var.set("STOP enviado.")

    def move_to(self) -> None:
        try:
            target = float(self.target_var.get())
        except ValueError:
            messagebox.showerror("Movimento", "Informe uma posição em mm.")
            return
        axis = self.target_axis_var.get()
        item = self.machine.get_axis(axis)
        movement = item.calculate_move(target)
        if movement["direction"] == 0:
            self.log_var.set(f"{axis} já está em {target:.3f} mm.")
            return
        self._send_move(axis, movement["direction"], movement["microsteps"])
        item.move_to(target)
        self.refresh_positions()

    def zero(self) -> None:
        self.machine.zero()
        self.refresh_positions()
        self.log_var.set("Zero lógico definido.")

    def add_point(self) -> None:
        try:
            x = float(self.point_x_var.get())
        except ValueError:
            messagebox.showerror("Ponto", "X deve ser um número em mm.")
            return
        self.sequence.add(x, self.point_label_var.get().strip())
        self.point_x_var.set("")
        self.point_label_var.set("")
        self.refresh_point_list()

    def remove_point(self) -> None:
        selection = self.point_list.curselection()
        if selection:
            self.sequence.remove(selection[0])
            self.refresh_point_list()

    def refresh_point_list(self) -> None:
        self.point_list.delete(0, tk.END)
        for index, point in enumerate(self.sequence.points, start=1):
            label = f" — {point.label}" if point.label else ""
            self.point_list.insert(tk.END, f"{index:02d} | X = {point.x_mm:.3f} mm{label}")

    def start_sequence(self) -> None:
        try:
            self.recovery_mm = float(self.recovery_var.get())
            if self.recovery_mm <= 0:
                raise ValueError
            self.sequence.start()
        except ValueError:
            messagebox.showerror("Sequência", "A subida deve ser maior que zero.")
            return
        self.sequence_status_var.set("Sequência iniciada.")
        self.root.after(50, self._run_next_point)

    def _run_next_point(self) -> None:
        point = self.sequence.current()
        if point is None:
            self.sequence_status_var.set("Sequência concluída.")
            return
        try:
            x_axis = self.machine.get_axis("X")
            movement = x_axis.calculate_move(point.x_mm)
            if movement["direction"]:
                self._send_move("X", movement["direction"], movement["microsteps"])
                x_axis.move_to(point.x_mm)
                self.refresh_positions()
            self.sequence_status_var.set(f"Ponto {self.sequence.index + 1}/{len(self.sequence.points)}: descendo Z.")
            if self.arduino is None:
                self.log_var.set("Modo virtual: SEEK_Z_DOWN → limite → subida.")
            else:
                response = self.arduino.send("SEEK_Z_DOWN")
                self.log_var.set(f"> SEEK_Z_DOWN    < {response}")
            z_axis = self.machine.get_axis("Z")
            steps = round(self.recovery_mm * z_axis.microsteps_per_mm)
            self._send_move("Z", self.up_direction, steps)
            z_axis.move_to(z_axis.current_position_mm + self.recovery_mm)
            self.refresh_positions()
            if self.sequence.advance():
                self.root.after(100, self._run_next_point)
            else:
                self.sequence_status_var.set("Sequência concluída.")
        except Exception as exc:
            self.stop(update_log=False)
            self.sequence_status_var.set("Sequência interrompida por erro.")
            messagebox.showerror("Sequência", str(exc))

    def apply_calibration(self) -> None:
        try:
            for axis in "XYZ":
                self.machine.get_axis(axis).set_calibration(float(self.calibration_vars[axis].get()))
            self.log_var.set("Calibração aplicada.")
        except ValueError:
            messagebox.showerror("Calibração", "Os valores devem ser números positivos.")

    def save_calibration(self) -> None:
        self.apply_calibration()
        data = {axis: self.machine.get_axis(axis).microsteps_per_mm for axis in "XYZ"}
        data["recovery_mm"] = self.recovery_mm
        CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        self.log_var.set(f"Calibração salva em {CONFIG_FILE}.")

    def _load_calibration(self) -> None:
        if not CONFIG_FILE.exists():
            return
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            for axis in "XYZ":
                if axis in data:
                    self.machine.get_axis(axis).set_calibration(float(data[axis]))
            if "recovery_mm" in data:
                self.recovery_mm = float(data["recovery_mm"])
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            pass

    def refresh_positions(self) -> None:
        for axis, value in self.machine.positions().items():
            self.position_vars[axis].set(f"{value:.3f} mm")

    def toggle_dark_mode(self) -> None:
        self.dark_mode = not self.dark_mode
        self._apply_theme()

    def _apply_theme(self) -> None:
        theme = DARK if self.dark_mode else LIGHT
        self.root.configure(bg=theme["bg"])
        for widget in (self.header, self.footer):
            widget.configure(bg=theme["bg"])
        for widget in (self.title_label, self.subtitle_label, self.log_title, self.log_label):
            widget.configure(bg=theme["bg"], fg=theme["fg"] if widget is self.title_label else theme["muted"])
        self.style.configure(".", background=theme["panel"], foreground=theme["fg"], fieldbackground=theme["field"])
        self.style.configure("TFrame", background=theme["panel"])
        self.style.configure("TLabel", background=theme["panel"], foreground=theme["fg"])
        self.style.configure("TLabelframe", background=theme["panel"], foreground=theme["muted"])
        self.style.configure("TLabelframe.Label", background=theme["panel"], foreground=theme["muted"])
        self.style.configure("TEntry", fieldbackground=theme["field"], foreground=theme["fg"])
        self.style.configure("TCombobox", fieldbackground=theme["field"], foreground=theme["fg"])
        self.style.configure("TNotebook", background=theme["bg"])
        self.style.configure("TNotebook.Tab", background=theme["panel"], foreground=theme["muted"], padding=(14, 7))
        self.style.map("TNotebook.Tab", background=[("selected", theme["accent"])], foreground=[("selected", "white")])
        self.style.configure("TButton", background=theme["panel"], foreground=theme["fg"], padding=(9, 5))
        self.style.map("TButton", background=[("active", theme["field"])])
        self.status_label.configure(bg=theme["panel"], fg=theme["muted"])
        self.connection.configure(style="TLabelframe")

    def close(self) -> None:
        self.stop(update_log=False)
        self.disconnect()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    MainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()

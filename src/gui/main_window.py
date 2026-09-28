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

# Paleta inspirada no Discord: escura, neutra e com um único destaque.
BG = "#313338"
PANEL = "#2b2d31"
PANEL_2 = "#1e1f22"
INPUT = "#1e1f22"
TEXT = "#f2f3f5"
MUTED = "#b5bac1"
ACCENT = "#5865f2"
ACCENT_HOVER = "#4752c4"
SUCCESS = "#23a559"
DANGER = "#da373c"
BORDER = "#3f4147"


class MainWindow:
    """Interface principal da máquina."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("IC Máquina — Controle de 3 Eixos")
        self.root.geometry("1000x720")
        self.root.minsize(920, 650)
        self.dark_mode = True
        self.arduino: ArduinoController | None = None
        self.sequence = PointSequence()
        self.recovery_mm = 5.0
        self.down_direction = -1
        self.up_direction = 1

        self.machine = Machine(
            x=Axis(200, 16, 8, calibrated_steps_per_mm=400.0),
            y=Axis(200, 16, 8, calibrated_steps_per_mm=400.0),
            z=Axis(200, 16, 8, calibrated_steps_per_mm=400.0),
        )
        self._load_calibration()

        self.port_var = tk.StringVar(value="COM3")
        self.status_var = tk.StringVar(value="MODO VIRTUAL  •  Arduino desconectado")
        self.log_var = tk.StringVar(value="Pronto. Nenhum motor será acionado sem conectar o Arduino.")
        self.step_var = tk.StringVar(value="100")
        self.target_axis_var = tk.StringVar(value="X")
        self.target_var = tk.StringVar(value="")
        self.recovery_var = tk.StringVar(value=str(self.recovery_mm))
        self.point_x_var = tk.StringVar(value="")
        self.point_label_var = tk.StringVar(value="")
        self.calibration_vars = {
            axis: tk.StringVar(value=f"{self.machine.get_axis(axis).microsteps_per_mm:.6f}")
            for axis in ("X", "Y", "Z")
        }
        self.position_vars = {axis: tk.StringVar(value="0.000 mm") for axis in ("X", "Y", "Z")}
        self.sequence_status_var = tk.StringVar(value="Nenhum ponto programado.")

        self.style = ttk.Style(self.root)
        self.style.theme_use("clam")
        self._apply_theme()
        self._build()
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def _build(self) -> None:
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill="x", padx=20, pady=(18, 10))
        tk.Label(header, text="IC Máquina", bg=BG, fg=TEXT, font=("Segoe UI", 20, "bold")).pack(side="left")
        tk.Label(header, text="CONTROLE • 3 EIXOS", bg=BG, fg=MUTED, font=("Segoe UI", 9, "bold")).pack(side="left", padx=12, pady=(8, 0))
        ttk.Button(header, text="Alternar tema", command=self.toggle_dark_mode).pack(side="right")

        connection = tk.Frame(self.root, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        connection.pack(fill="x", padx=20, pady=(0, 10))
        tk.Label(connection, text="CONEXÃO", bg=PANEL, fg=MUTED, font=("Segoe UI", 9, "bold")).grid(row=0, column=0, padx=14, pady=9, sticky="w")
        ttk.Label(connection, text="Porta").grid(row=0, column=1, padx=(8, 4))
        ttk.Entry(connection, textvariable=self.port_var, width=9).grid(row=0, column=2, padx=4)
        ttk.Button(connection, text="Conectar", command=self.connect).grid(row=0, column=3, padx=5)
        ttk.Button(connection, text="Desconectar", command=self.disconnect).grid(row=0, column=4, padx=5)
        self.status_label = tk.Label(connection, textvariable=self.status_var, bg=PANEL, fg=MUTED, font=("Segoe UI", 9, "bold"))
        self.status_label.grid(row=0, column=5, padx=15, sticky="w")
        connection.columnconfigure(5, weight=1)

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=20, pady=5)
        operation = ttk.Frame(notebook, padding=18)
        points = ttk.Frame(notebook, padding=18)
        calibration = ttk.Frame(notebook, padding=18)
        notebook.add(operation, text="  Operação  ")
        notebook.add(points, text="  Pontos  ")
        notebook.add(calibration, text="  Calibração  ")
        self._build_operation_tab(operation)
        self._build_points_tab(points)
        self._build_calibration_tab(calibration)

        footer = tk.Frame(self.root, bg=PANEL_2)
        footer.pack(fill="x", padx=20, pady=(5, 15))
        tk.Label(footer, text="LOG", bg=PANEL_2, fg=MUTED, font=("Segoe UI", 8, "bold")).pack(side="left", padx=12, pady=8)
        tk.Label(footer, textvariable=self.log_var, bg=PANEL_2, fg=TEXT, anchor="w", font=("Segoe UI", 9)).pack(side="left", fill="x", expand=True, padx=4)

    def _build_operation_tab(self, parent: ttk.Frame) -> None:
        positions = ttk.LabelFrame(parent, text="  POSIÇÃO ESTIMADA  ")
        positions.pack(fill="x", pady=(0, 12))
        for column, axis in enumerate(("X", "Y", "Z")):
            card = tk.Frame(positions, bg=PANEL_2, highlightbackground=BORDER, highlightthickness=1)
            card.grid(row=0, column=column, padx=7, pady=10, sticky="nsew")
            tk.Label(card, text=axis, bg=PANEL_2, fg=ACCENT, font=("Segoe UI", 12, "bold")).pack(padx=55, pady=(10, 2))
            tk.Label(card, textvariable=self.position_vars[axis], bg=PANEL_2, fg=TEXT, font=("Consolas", 15, "bold")).pack(padx=35, pady=(0, 10))
            positions.columnconfigure(column, weight=1)

        manual = ttk.LabelFrame(parent, text="  CONTROLE MANUAL  ")
        manual.pack(fill="x", pady=8)
        ttk.Label(manual, text="Passos por comando:").grid(row=0, column=0, padx=7, pady=10)
        ttk.Entry(manual, textvariable=self.step_var, width=10).grid(row=0, column=1)
        ttk.Label(manual, text="Segure o botão para JOG; solte para STOP.").grid(row=0, column=2, columnspan=3, padx=15)
        for row, axis in enumerate(("X", "Y", "Z"), start=1):
            ttk.Label(manual, text=f"Eixo {axis}", font=("Segoe UI", 10, "bold")).grid(row=row, column=0, padx=7, pady=6)
            minus = ttk.Button(manual, text=f"{axis}  −", width=13)
            plus = ttk.Button(manual, text=f"{axis}  +", width=13)
            minus.grid(row=row, column=1, padx=5, pady=3)
            plus.grid(row=row, column=2, padx=5, pady=3)
            minus.bind("<ButtonPress-1>", lambda _e, a=axis: self.jog_start(a, -1))
            minus.bind("<ButtonRelease-1>", lambda _e: self.jog_stop())
            plus.bind("<ButtonPress-1>", lambda _e, a=axis: self.jog_start(a, 1))
            plus.bind("<ButtonRelease-1>", lambda _e: self.jog_stop())

        stop = tk.Button(parent, text="PARAR MOVIMENTO", command=self.stop, bg=DANGER, fg="white", activebackground="#a12d31", activeforeground="white", relief="flat", bd=0, font=("Segoe UI", 10, "bold"), cursor="hand2")
        stop.pack(fill="x", pady=12, ipady=8)

        target = ttk.LabelFrame(parent, text="  IR PARA POSIÇÃO TEÓRICA  ")
        target.pack(fill="x", pady=8)
        ttk.Label(target, text="Eixo:").grid(row=0, column=0, padx=7, pady=10)
        ttk.Combobox(target, values=("X", "Y", "Z"), state="readonly", width=5, textvariable=self.target_axis_var).grid(row=0, column=1, padx=5)
        ttk.Label(target, text="Posição (mm):").grid(row=0, column=2, padx=7)
        ttk.Entry(target, textvariable=self.target_var, width=12).grid(row=0, column=3)
        ttk.Button(target, text="Calcular / mover", command=self.move_to).grid(row=0, column=4, padx=8)
        ttk.Button(parent, text="Zerar posição estimada", command=self.zero).pack(pady=7)

    def _build_points_tab(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="Programa de análise", font=("Segoe UI", 15, "bold")).pack(anchor="w")
        ttk.Label(parent, text="Cada ponto é X. A máquina irá: posicionar X → descer Z até o limite → subir Z → próximo X.", wraplength=850).pack(anchor="w", pady=(3, 12))
        add = ttk.Frame(parent)
        add.pack(fill="x")
        ttk.Label(add, text="X (mm):").pack(side="left")
        ttk.Entry(add, textvariable=self.point_x_var, width=12).pack(side="left", padx=6)
        ttk.Label(add, text="Nome:").pack(side="left")
        ttk.Entry(add, textvariable=self.point_label_var, width=20).pack(side="left", padx=6)
        ttk.Button(add, text="Adicionar", command=self.add_point).pack(side="left", padx=6)
        ttk.Button(add, text="Remover", command=self.remove_point).pack(side="left")
        self.point_list = tk.Listbox(parent, height=12, bg=INPUT, fg=TEXT, selectbackground=ACCENT, selectforeground="white", relief="flat", highlightbackground=BORDER, highlightthickness=1, font=("Consolas", 10))
        self.point_list.pack(fill="both", expand=True, pady=12)
        options = ttk.LabelFrame(parent, text="  COMPORTAMENTO Z  ")
        options.pack(fill="x", pady=5)
        ttk.Label(options, text="Subida após tocar o botão (mm):").grid(row=0, column=0, padx=7, pady=10)
        ttk.Entry(options, textvariable=self.recovery_var, width=10).grid(row=0, column=1)
        ttk.Label(options, text="Descida: Z −    •    Subida: Z +").grid(row=0, column=2, padx=18)
        run = tk.Button(parent, text="INICIAR SEQUÊNCIA", command=self.start_sequence, bg=ACCENT, fg="white", activebackground=ACCENT_HOVER, activeforeground="white", relief="flat", bd=0, font=("Segoe UI", 10, "bold"), cursor="hand2")
        run.pack(fill="x", pady=10, ipady=7)
        ttk.Label(parent, textvariable=self.sequence_status_var).pack(anchor="w")

    def _build_calibration_tab(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="Calibração dos eixos", font=("Segoe UI", 15, "bold")).pack(anchor="w")
        ttk.Label(parent, text="Edite os valores experimentais de passos/mm. Eles substituem o valor teórico para os movimentos.", wraplength=850).pack(anchor="w", pady=(3, 12))
        table = ttk.LabelFrame(parent, text="  PARÂMETROS  ")
        table.pack(fill="x", pady=5)
        for col, text in enumerate(("Eixo", "Passos/mm", "Observação")):
            ttk.Label(table, text=text, font=("Segoe UI", 9, "bold")).grid(row=0, column=col, padx=25, pady=9)
        for row, axis in enumerate(("X", "Y", "Z"), start=1):
            ttk.Label(table, text=axis, font=("Segoe UI", 11, "bold")).grid(row=row, column=0, pady=8)
            ttk.Entry(table, textvariable=self.calibration_vars[axis], width=18).grid(row=row, column=1)
            ttk.Label(table, text="valor experimental").grid(row=row, column=2, padx=15)
        ttk.Button(parent, text="Aplicar calibração", command=self.apply_calibration).pack(anchor="w", pady=10)
        ttk.Button(parent, text="Salvar calibração", command=self.save_calibration).pack(anchor="w")
        ttk.Separator(parent).pack(fill="x", pady=15)
        ttk.Label(parent, text="Modelo inicial: 200 passos/rev × 16 microsteps ÷ 8 mm/rev = 400 passos/mm.").pack(anchor="w")
        ttk.Label(parent, text="Os 400 são apenas ponto de partida; os valores experimentais devem prevalecer.").pack(anchor="w", pady=3)

    def connect(self) -> None:
        try:
            controller = ArduinoController(self.port_var.get().strip())
            controller.connect()
            self.arduino = controller
            self.status_var.set(f"CONECTADO  •  {controller.port}")
            self.status_label.configure(fg=SUCCESS)
            self.log_var.set("Arduino conectado. Ainda recomendamos testar comunicação sem motores.")
        except Exception as exc:
            self.status_var.set("FALHA NA CONEXÃO")
            self.status_label.configure(fg=DANGER)
            messagebox.showerror("Arduino", str(exc))

    def disconnect(self) -> None:
        if self.arduino is not None:
            self.arduino.disconnect()
            self.arduino = None
        self.status_var.set("MODO VIRTUAL  •  Arduino desconectado")
        self.status_label.configure(fg=MUTED)
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
            self.log_var.set(f"> JOG {axis} {direction} — solte para STOP")
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
            self.log_var.set("STOP enviado. Movimento interrompido.")

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
        self.log_var.set("Zero lógico definido nas posições atuais.")

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
            messagebox.showerror("Sequência", "A subida após o botão deve ser maior que zero.")
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
            self.sequence_status_var.set(f"Ponto {self.sequence.index + 1}/{len(self.sequence.points)}: X posicionado; descendo Z.")
            if self.arduino is None:
                self.log_var.set("Modo virtual: SEEK_Z_DOWN (simulado) → limite → subida.")
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
                self.sequence_status_var.set("Sequência concluída com todos os pontos executados.")
        except Exception as exc:
            self.stop(update_log=False)
            self.sequence_status_var.set("Sequência interrompida por erro.")
            messagebox.showerror("Sequência", str(exc))

    def apply_calibration(self) -> None:
        try:
            for axis in ("X", "Y", "Z"):
                value = float(self.calibration_vars[axis].get())
                self.machine.get_axis(axis).set_calibration(value)
            self.log_var.set("Calibração aplicada à máquina virtual.")
        except ValueError:
            messagebox.showerror("Calibração", "Todos os valores devem ser números positivos.")

    def save_calibration(self) -> None:
        self.apply_calibration()
        data = {axis: self.machine.get_axis(axis).microsteps_per_mm for axis in ("X", "Y", "Z")}
        data["recovery_mm"] = self.recovery_mm
        CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        self.log_var.set(f"Calibração salva em {CONFIG_FILE}.")

    def _load_calibration(self) -> None:
        if not CONFIG_FILE.exists():
            return
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            for axis in ("X", "Y", "Z"):
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
        dark = self.dark_mode
        bg = BG if dark else "#f2f3f5"
        panel = PANEL if dark else "#ffffff"
        field = INPUT if dark else "#ffffff"
        fg = TEXT if dark else "#232428"
        muted = MUTED if dark else "#5c5f66"
        self.root.configure(bg=bg)
        self.style.configure(".", background=panel, foreground=fg, fieldbackground=field, font=("Segoe UI", 9))
        self.style.configure("TFrame", background=panel)
        self.style.configure("TLabel", background=panel, foreground=fg)
        self.style.configure("TLabelframe", background=panel, foreground=muted, bordercolor=BORDER)
        self.style.configure("TLabelframe.Label", background=panel, foreground=muted)
        self.style.configure("TEntry", fieldbackground=field, foreground=fg, insertcolor=fg)
        self.style.configure("TCombobox", fieldbackground=field, foreground=fg)
        self.style.configure("TButton", background=panel_ if (panel_ := panel) else panel, foreground=fg, padding=(10, 6), borderwidth=0)
        self.style.map("TButton", background=[("active", "#3f4147" if dark else "#e3e5e8")])
        self.style.configure("TNotebook", background=bg, borderwidth=0)
        self.style.configure("TNotebook.Tab", background=PANEL_2 if dark else "#e3e5e8", foreground=muted, padding=(16, 8))
        self.style.map("TNotebook.Tab", background=[("selected", ACCENT)], foreground=[("selected", "white")])

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

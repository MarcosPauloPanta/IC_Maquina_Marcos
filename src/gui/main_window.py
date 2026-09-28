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


class MainWindow:
    """Interface principal da máquina.

    A aplicação possui três camadas visíveis para o usuário:
    operação, sequência de pontos e calibração. O modo virtual permite
    aprender/testar a lógica sem energizar motores.
    """

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("IC Máquina — Controle de 3 Eixos")
        self.root.geometry("980x700")
        self.root.minsize(900, 620)

        self.dark_mode = False
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
        self.status_var = tk.StringVar(value="Modo virtual — Arduino desconectado")
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
        self.position_vars = {
            axis: tk.StringVar(value="0.000 mm") for axis in ("X", "Y", "Z")
        }
        self.sequence_status_var = tk.StringVar(value="Nenhum ponto programado.")

        self.style = ttk.Style(self.root)
        self.style.theme_use("clam")
        self._apply_theme()
        self._build()
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    # ---------- Interface ----------

    def _build(self) -> None:
        top = ttk.Frame(self.root)
        top.pack(fill="x", padx=12, pady=10)
        ttk.Label(top, text="IC Máquina", font=("", 18, "bold")).pack(side="left")
        ttk.Button(top, text="☾ Modo escuro", command=self.toggle_dark_mode).pack(side="right")

        connection = ttk.LabelFrame(self.root, text="Comunicação")
        connection.pack(fill="x", padx=12, pady=5)
        ttk.Label(connection, text="Porta:").grid(row=0, column=0, padx=6, pady=8)
        ttk.Entry(connection, textvariable=self.port_var, width=10).grid(row=0, column=1)
        ttk.Button(connection, text="Conectar", command=self.connect).grid(row=0, column=2, padx=6)
        ttk.Button(connection, text="Desconectar", command=self.disconnect).grid(row=0, column=3, padx=6)
        ttk.Label(connection, textvariable=self.status_var).grid(row=0, column=4, padx=12)

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=12, pady=5)

        operation = ttk.Frame(notebook, padding=12)
        points = ttk.Frame(notebook, padding=12)
        calibration = ttk.Frame(notebook, padding=12)
        notebook.add(operation, text="Operação")
        notebook.add(points, text="Pontos")
        notebook.add(calibration, text="Calibração")

        self._build_operation_tab(operation)
        self._build_points_tab(points)
        self._build_calibration_tab(calibration)

        ttk.Label(self.root, textvariable=self.log_var, relief="sunken", anchor="w").pack(
            fill="x", padx=12, pady=(5, 10)
        )

    def _build_operation_tab(self, parent: ttk.Frame) -> None:
        positions = ttk.LabelFrame(parent, text="Posição estimada")
        positions.pack(fill="x", pady=5)
        for column, axis in enumerate(("X", "Y", "Z")):
            ttk.Label(positions, text=axis, font=("", 13, "bold")).grid(
                row=0, column=column, padx=70, pady=(10, 2)
            )
            ttk.Label(positions, textvariable=self.position_vars[axis]).grid(
                row=1, column=column, padx=70, pady=(0, 10)
            )

        manual = ttk.LabelFrame(parent, text="Controle manual — segure o botão para movimentar")
        manual.pack(fill="x", pady=8)
        ttk.Label(manual, text="Passos por comando:").grid(row=0, column=0, padx=6, pady=8)
        ttk.Entry(manual, textvariable=self.step_var, width=10).grid(row=0, column=1)
        ttk.Label(manual, text="(o firmware poderá interpretar o jog continuamente)").grid(
            row=0, column=2, columnspan=3, padx=10
        )

        for row, axis in enumerate(("X", "Y", "Z"), start=1):
            ttk.Label(manual, text=f"Eixo {axis}").grid(row=row, column=0, padx=6, pady=6)
            minus = ttk.Button(manual, text=f"{axis} −", width=12)
            plus = ttk.Button(manual, text=f"{axis} +", width=12)
            minus.grid(row=row, column=1, padx=5)
            plus.grid(row=row, column=2, padx=5)
            minus.bind("<ButtonPress-1>", lambda _e, a=axis: self.jog_start(a, -1))
            minus.bind("<ButtonRelease-1>", lambda _e: self.jog_stop())
            plus.bind("<ButtonPress-1>", lambda _e, a=axis: self.jog_start(a, 1))
            plus.bind("<ButtonRelease-1>", lambda _e: self.jog_stop())

        emergency = ttk.Button(parent, text="PARAR MOVIMENTO", command=self.stop)
        emergency.pack(fill="x", pady=8, ipady=8)

        target = ttk.LabelFrame(parent, text="Ir para posição teórica")
        target.pack(fill="x", pady=8)
        ttk.Label(target, text="Eixo:").grid(row=0, column=0, padx=6, pady=8)
        ttk.Combobox(
            target, values=("X", "Y", "Z"), state="readonly", width=5,
            textvariable=self.target_axis_var,
        ).grid(row=0, column=1, padx=6)
        ttk.Label(target, text="Posição (mm):").grid(row=0, column=2, padx=6)
        ttk.Entry(target, textvariable=self.target_var, width=12).grid(row=0, column=3)
        ttk.Button(target, text="Calcular / mover", command=self.move_to).grid(row=0, column=4, padx=6)
        ttk.Button(parent, text="Zerar posição estimada", command=self.zero).pack(pady=5)

    def _build_points_tab(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="Programa de análise", font=("", 14, "bold")).pack(anchor="w")
        ttk.Label(
            parent,
            text="Cada ponto é uma coordenada X. A sequência será: ir ao X → descer Z até o limite → subir Z → próximo X.",
            wraplength=850,
        ).pack(anchor="w", pady=(2, 10))

        add = ttk.Frame(parent)
        add.pack(fill="x")
        ttk.Label(add, text="X (mm):").pack(side="left")
        ttk.Entry(add, textvariable=self.point_x_var, width=12).pack(side="left", padx=6)
        ttk.Label(add, text="Nome opcional:").pack(side="left")
        ttk.Entry(add, textvariable=self.point_label_var, width=20).pack(side="left", padx=6)
        ttk.Button(add, text="Adicionar ponto", command=self.add_point).pack(side="left", padx=6)
        ttk.Button(add, text="Remover selecionado", command=self.remove_point).pack(side="left")

        self.point_list = tk.Listbox(parent, height=12)
        self.point_list.pack(fill="both", expand=True, pady=10)

        options = ttk.LabelFrame(parent, text="Comportamento Z")
        options.pack(fill="x", pady=5)
        ttk.Label(options, text="Subida após tocar o botão (mm):").grid(row=0, column=0, padx=6, pady=8)
        ttk.Entry(options, textvariable=self.recovery_var, width=10).grid(row=0, column=1)
        ttk.Label(options, text="Descida: Z −    Subida: Z +").grid(row=0, column=2, padx=15)

        ttk.Button(parent, text="INICIAR SEQUÊNCIA", command=self.start_sequence).pack(fill="x", pady=8, ipady=6)
        ttk.Label(parent, textvariable=self.sequence_status_var).pack(anchor="w")

    def _build_calibration_tab(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="Calibração dos eixos", font=("", 14, "bold")).pack(anchor="w")
        ttk.Label(
            parent,
            text="Altere aqui os valores experimentais de passos/mm. Eles substituem o cálculo teórico usado pela GUI.",
            wraplength=850,
        ).pack(anchor="w", pady=(2, 12))

        table = ttk.LabelFrame(parent, text="Parâmetros usados nos movimentos")
        table.pack(fill="x", pady=5)
        ttk.Label(table, text="Eixo").grid(row=0, column=0, padx=30, pady=8)
        ttk.Label(table, text="Passos/mm").grid(row=0, column=1, padx=30)
        ttk.Label(table, text="Observação").grid(row=0, column=2, padx=30)
        for row, axis in enumerate(("X", "Y", "Z"), start=1):
            ttk.Label(table, text=axis, font=("", 11, "bold")).grid(row=row, column=0, pady=8)
            ttk.Entry(table, textvariable=self.calibration_vars[axis], width=18).grid(row=row, column=1)
            ttk.Label(table, text="valor experimental; revise após nova calibração").grid(row=row, column=2, padx=10)

        ttk.Button(parent, text="Aplicar calibração", command=self.apply_calibration).pack(anchor="w", pady=10)
        ttk.Button(parent, text="Salvar calibração", command=self.save_calibration).pack(anchor="w")

        ttk.Separator(parent).pack(fill="x", pady=15)
        ttk.Label(parent, text="Modelo teórico atual: 200 passos/rev × 16 microsteps / 8 mm/rev = 400 passos/mm.").pack(anchor="w")
        ttk.Label(parent, text="Os 400 são apenas o ponto de partida; a calibração experimental deve prevalecer.").pack(anchor="w")

    # ---------- Comunicação ----------

    def connect(self) -> None:
        try:
            controller = ArduinoController(self.port_var.get().strip())
            controller.connect()
            self.arduino = controller
            self.status_var.set(f"Conectado em {controller.port}")
            self.log_var.set("Arduino conectado. Movimentos reais estão liberados pela interface.")
        except Exception as exc:
            self.status_var.set("Falha na conexão")
            messagebox.showerror("Arduino", str(exc))

    def disconnect(self) -> None:
        if self.arduino is not None:
            self.arduino.disconnect()
            self.arduino = None
        self.status_var.set("Modo virtual — Arduino desconectado")
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
            self.log_var.set(f"> JOG {axis} {direction} — soltando o botão envia STOP")
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

    # ---------- Movimento ----------

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

    # ---------- Pontos ----------

    def add_point(self) -> None:
        try:
            x = float(self.point_x_var.get())
        except ValueError:
            messagebox.showerror("Ponto", "X deve ser um número em mm.")
            return
        label = self.point_label_var.get().strip()
        self.sequence.add(x, label)
        self.point_x_var.set("")
        self.point_label_var.set("")
        self.refresh_point_list()

    def remove_point(self) -> None:
        selection = self.point_list.curselection()
        if not selection:
            return
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
        except ValueError as exc:
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
            # 1) posiciona X no ponto.
            x_axis = self.machine.get_axis("X")
            movement = x_axis.calculate_move(point.x_mm)
            if movement["direction"]:
                self._send_move("X", movement["direction"], movement["microsteps"])
                x_axis.move_to(point.x_mm)
                self.refresh_positions()

            self.sequence_status_var.set(
                f"Ponto {self.sequence.index + 1}/{len(self.sequence.points)}: X posicionado; descendo Z."
            )

            # 2) O firmware deve parar quando o botão de limite Z for acionado.
            if self.arduino is None:
                self.log_var.set("Modo virtual: SEEK_Z_DOWN (simulado) → limite → subida.")
            else:
                response = self.arduino.send("SEEK_Z_DOWN")
                self.log_var.set(f"> SEEK_Z_DOWN    < {response}")

            # 3) Sobe uma distância configurada após o toque.
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

    # ---------- Calibração ----------

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
        data = {
            axis: self.machine.get_axis(axis).microsteps_per_mm
            for axis in ("X", "Y", "Z")
        }
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
            # Um arquivo de calibração inválido não deve impedir a GUI de abrir.
            pass

    def refresh_positions(self) -> None:
        for axis, value in self.machine.positions().items():
            self.position_vars[axis].set(f"{value:.3f} mm")

    # ---------- Tema / encerramento ----------

    def toggle_dark_mode(self) -> None:
        self.dark_mode = not self.dark_mode
        self._apply_theme()

    def _apply_theme(self) -> None:
        if not hasattr(self, "style"):
            return
        if self.dark_mode:
            bg, fg, field = "#202124", "#f1f3f4", "#303134"
            self.style.configure(".", background=bg, foreground=fg, fieldbackground=field)
            self.style.configure("TEntry", foreground=fg, fieldbackground=field)
            self.style.configure("TCombobox", foreground=fg, fieldbackground=field)
            self.style.configure("TNotebook", background=bg)
            self.style.configure("TNotebook.Tab", background=field, foreground=fg)
            self.root.configure(bg=bg)
        else:
            self.style.configure(".", background="#f0f0f0", foreground="#000000", fieldbackground="#ffffff")
            self.style.configure("TEntry", foreground="#000000", fieldbackground="#ffffff")
            self.style.configure("TCombobox", foreground="#000000", fieldbackground="#ffffff")
            self.root.configure(bg="#f0f0f0")

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

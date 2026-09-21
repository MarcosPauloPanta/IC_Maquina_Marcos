from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from src.controller.arduino import ArduinoController
from src.controller.axis import Axis
from src.controller.machine import Machine


class MainWindow:
    """Interface inicial para testes da máquina.

    A GUI começa em modo virtual. A comunicação serial só é usada quando
    o operador conecta explicitamente o Arduino.
    """

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("IC Máquina — Controle de 3 Eixos")
        self.root.geometry("760x520")

        self.machine = Machine(
            x=Axis(200, 16, 8),
            y=Axis(200, 16, 8),
            z=Axis(200, 16, 8),
        )
        self.arduino: ArduinoController | None = None

        self.port_var = tk.StringVar(value="COM3")
        self.status_var = tk.StringVar(value="Modo virtual — Arduino desconectado")
        self.log_var = tk.StringVar(value="Pronto.")
        self.step_var = tk.StringVar(value="100")
        self.target_var = tk.StringVar(value="")

        self.position_vars = {
            axis: tk.StringVar(value="0.000 mm") for axis in ("X", "Y", "Z")
        }
        self._build()

    def _build(self) -> None:
        connection = ttk.LabelFrame(self.root, text="Comunicação")
        connection.pack(fill="x", padx=12, pady=10)

        ttk.Label(connection, text="Porta:").grid(row=0, column=0, padx=6, pady=8)
        ttk.Entry(connection, textvariable=self.port_var, width=10).grid(row=0, column=1)
        ttk.Button(connection, text="Conectar", command=self.connect).grid(row=0, column=2, padx=6)
        ttk.Button(connection, text="Desconectar", command=self.disconnect).grid(row=0, column=3, padx=6)
        ttk.Label(connection, textvariable=self.status_var).grid(row=0, column=4, padx=12)

        positions = ttk.LabelFrame(self.root, text="Posição estimada")
        positions.pack(fill="x", padx=12, pady=8)

        for column, axis in enumerate(("X", "Y", "Z")):
            ttk.Label(positions, text=axis, font=("", 12, "bold")).grid(
                row=0, column=column, padx=45, pady=(8, 2)
            )
            ttk.Label(positions, textvariable=self.position_vars[axis]).grid(
                row=1, column=column, padx=45, pady=(0, 8)
            )

        controls = ttk.LabelFrame(self.root, text="Movimento incremental")
        controls.pack(fill="x", padx=12, pady=8)

        ttk.Label(controls, text="Passos:").grid(row=0, column=0, padx=6, pady=8)
        ttk.Entry(controls, textvariable=self.step_var, width=10).grid(row=0, column=1)

        column = 2
        for axis in ("X", "Y", "Z"):
            ttk.Button(
                controls, text=f"{axis} −", width=9,
                command=lambda a=axis: self.jog(a, -1)
            ).grid(row=0, column=column, padx=4)
            ttk.Button(
                controls, text=f"{axis} +", width=9,
                command=lambda a=axis: self.jog(a, 1)
            ).grid(row=0, column=column + 1, padx=4)
            column += 2

        target = ttk.LabelFrame(self.root, text="Ir para posição teórica")
        target.pack(fill="x", padx=12, pady=8)

        ttk.Label(target, text="Eixo:").grid(row=0, column=0, padx=6, pady=8)
        self.target_axis = ttk.Combobox(
            target, values=("X", "Y", "Z"), state="readonly", width=5
        )
        self.target_axis.current(0)
        self.target_axis.grid(row=0, column=1, padx=6)

        ttk.Label(target, text="Posição (mm):").grid(row=0, column=2, padx=6)
        ttk.Entry(target, textvariable=self.target_var, width=12).grid(row=0, column=3)
        ttk.Button(target, text="Calcular / mover", command=self.move_to).grid(
            row=0, column=4, padx=6
        )

        ttk.Button(self.root, text="Zerar posição estimada", command=self.zero).pack(pady=10)
        ttk.Label(self.root, textvariable=self.log_var, relief="sunken", anchor="w").pack(
            fill="x", padx=12, pady=8
        )

    def connect(self) -> None:
        try:
            controller = ArduinoController(self.port_var.get().strip())
            controller.connect()
            self.arduino = controller
            self.status_var.set(f"Conectado em {controller.port}")
            self.log_var.set("Arduino conectado.")
        except Exception as exc:
            self.status_var.set("Falha na conexão")
            messagebox.showerror("Arduino", str(exc))

    def disconnect(self) -> None:
        if self.arduino is not None:
            self.arduino.disconnect()
            self.arduino = None
        self.status_var.set("Modo virtual — Arduino desconectado")
        self.log_var.set("Arduino desconectado.")

    def jog(self, axis: str, direction: int) -> None:
        try:
            steps = int(self.step_var.get())
            if steps <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Movimento", "Passos deve ser um inteiro positivo.")
            return

        item = self.machine.get_axis(axis)
        distance = direction * steps / item.microsteps_per_mm
        target = item.current_position_mm + distance

        self._send_move(axis, direction, steps)
        item.move_to(target)
        self.refresh_positions()

    def move_to(self) -> None:
        try:
            target = float(self.target_var.get())
        except ValueError:
            messagebox.showerror("Movimento", "Informe uma posição em mm.")
            return

        axis = self.target_axis.get()
        item = self.machine.get_axis(axis)
        movement = item.calculate_move(target)

        if movement["direction"] == 0:
            self.log_var.set(f"{axis} já está em {target:.3f} mm.")
            return

        self._send_move(axis, movement["direction"], movement["microsteps"])
        item.move_to(target)
        self.refresh_positions()

    def _send_move(self, axis: str, direction: int, steps: int) -> None:
        if self.arduino is None:
            self.log_var.set(
                f"Modo virtual: {axis} {'+' if direction > 0 else '-'} {steps} passos."
            )
            return

        command = f"MOVE {axis} {direction} {steps}"
        response = self.arduino.send(command)
        self.log_var.set(f"> {command}    < {response}")

    def refresh_positions(self) -> None:
        for axis, value in self.machine.positions().items():
            self.position_vars[axis].set(f"{value:.3f} mm")

    def zero(self) -> None:
        self.machine.zero()
        self.refresh_positions()
        self.log_var.set("Zero lógico definido nas posições atuais.")


def main() -> None:
    root = tk.Tk()
    MainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()

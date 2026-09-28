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

LIGHT = {
    "bg": "#ffffff", "panel": "#ffffff", "field": "#f7f7f8",
    "fg": "#2d2d2d", "muted": "#6e6e80", "border": "#e5e5e5",
    "accent": "#10a37f", "danger": "#ef4444",
}
DARK = {
    "bg": "#212121", "panel": "#2f2f2f", "field": "#424242",
    "fg": "#ececec", "muted": "#b4b4b4", "border": "#4b4b4b",
    "accent": "#10a37f", "danger": "#f28b82",
}


class MainWindow:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("IC Máquina — Controle de 3 Eixos")
        self.root.geometry("980x760")
        self.root.minsize(900, 680)

        self.dark_mode = False
        self.arduino: ArduinoController | None = None
        self.sequence = PointSequence()
        self.recovery_mm = 5.0
        self.jog_after_id: str | None = None
        self.JOG_PULSE_MS = 350

        self.machine = Machine(
            x=Axis(200, 16, 8, calibrated_steps_per_mm=400.0),
            y=Axis(200, 16, 8, calibrated_steps_per_mm=400.0),
            z=Axis(200, 16, 8, calibrated_steps_per_mm=400.0),
        )
        self._load_calibration()

        self.port_var = tk.StringVar(value="COM3")
        self.status_var = tk.StringVar(value="Arduino desconectado")
        self.log_var = tk.StringVar(value="Pronto.")
        self.step_var = tk.StringVar(value="100")
        self.target_axis_var = tk.StringVar(value="X")
        self.target_var = tk.StringVar()
        self.point_x_var = tk.StringVar()
        self.point_label_var = tk.StringVar()
        self.terminal_command_var = tk.StringVar()
        self.sequence_status_var = tk.StringVar(value="Nenhum ponto programado.")
        self.calibration_vars = {
            a: tk.StringVar(value=f"{self.machine.get_axis(a).microsteps_per_mm:.6f}")
            for a in "XYZ"
        }
        self.position_vars = {a: tk.StringVar(value="0.000 mm") for a in "XYZ"}

        self.style = ttk.Style(self.root)
        self.style.theme_use("clam")
        self._build()
        self._apply_theme()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(100, self._poll_serial)

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
        terminal = ttk.Frame(notebook, padding=16)
        points = ttk.Frame(notebook, padding=16)
        calibration = ttk.Frame(notebook, padding=16)
        notebook.add(operation, text="Operação")
        notebook.add(terminal, text="Terminal")
        notebook.add(points, text="Pontos")
        notebook.add(calibration, text="Calibração")
        self._build_operation(operation)
        self._build_terminal(terminal)
        self._build_points(points)
        self._build_calibration(calibration)

        self.footer = tk.Frame(self.root)
        self.footer.pack(fill="x", padx=20, pady=(2, 15))
        self.log_title = tk.Label(self.footer, text="LOG:", font=("Segoe UI", 8, "bold"))
        self.log_title.pack(side="left", padx=8, pady=7)
        self.log_label = tk.Label(self.footer, textvariable=self.log_var, anchor="w", font=("Segoe UI", 9))
        self.log_label.pack(side="left", fill="x", expand=True)

    def _build_operation(self, parent) -> None:
        positions = ttk.LabelFrame(parent, text="  Posição estimada  ")
        positions.pack(fill="x", pady=(0, 12))
        for col, axis in enumerate("XYZ"):
            card = tk.Frame(positions, highlightthickness=1)
            card.grid(row=0, column=col, padx=7, pady=10, sticky="nsew")
            tk.Label(card, text=axis, font=("Segoe UI", 12, "bold")).pack(padx=55, pady=(9, 2))
            tk.Label(card, textvariable=self.position_vars[axis], font=("Consolas", 14, "bold")).pack(padx=35, pady=(0, 9))
            positions.columnconfigure(col, weight=1)

        manual = ttk.LabelFrame(parent, text="  JOG — clique para um pulso seguro  ")
        manual.pack(fill="x", pady=5)
        ttk.Label(manual, text="Passos/pulso:").grid(row=0, column=0, padx=8, pady=8)
        ttk.Entry(manual, textvariable=self.step_var, width=10).grid(row=0, column=1)
        ttk.Label(manual, text="Máximo 350 ms; STOP automático.").grid(row=0, column=2, columnspan=2, padx=10, sticky="w")
        for row, axis in enumerate("XYZ", start=1):
            ttk.Label(manual, text=axis, font=("Segoe UI", 10, "bold")).grid(row=row, column=0, padx=8, pady=4)
            ttk.Button(manual, text=f"{axis} −", width=12, command=lambda a=axis: self.jog_click(a, -1)).grid(row=row, column=1, padx=5, pady=3)
            ttk.Button(manual, text=f"{axis} +", width=12, command=lambda a=axis: self.jog_click(a, 1)).grid(row=row, column=2, padx=5, pady=3)
        tk.Button(parent, text="PARAR", command=self.stop, relief="flat", bd=0, font=("Segoe UI", 10, "bold")).pack(fill="x", pady=10, ipady=7)

        target = ttk.LabelFrame(parent, text="  Ir para posição teórica — próxima etapa  ")
        target.pack(fill="x", pady=5)
        ttk.Label(target, text="Eixo:").grid(row=0, column=0, padx=5, pady=10)
        ttk.Combobox(target, values=("X", "Y", "Z"), state="readonly", width=5, textvariable=self.target_axis_var).grid(row=0, column=1)
        ttk.Label(target, text="Posição (mm):").grid(row=0, column=2, padx=5)
        ttk.Entry(target, textvariable=self.target_var, width=12).grid(row=0, column=3)
        ttk.Button(target, text="Mover", command=self.move_to).grid(row=0, column=4, padx=8)
        ttk.Button(parent, text="Zerar posição estimada", command=self.zero).pack(pady=6)

    def _build_terminal(self, parent) -> None:
        ttk.Label(parent, text="Terminal Arduino", font=("Segoe UI", 14, "bold")).pack(anchor="w")
        ttk.Label(parent, text="Comandos diretos para diagnóstico e testes. A proteção física continua no Arduino.").pack(anchor="w", pady=(3, 8))
        frame = tk.Frame(parent, bd=0, highlightthickness=1)
        frame.pack(fill="both", expand=True)
        self.terminal_history = tk.Text(frame, height=20, wrap="none", font=("Consolas", 10), bd=0, padx=12, pady=10)
        self.terminal_history.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(frame, orient="vertical", command=self.terminal_history.yview)
        scroll.pack(side="right", fill="y")
        self.terminal_history.configure(yscrollcommand=scroll.set)

        entry = ttk.Frame(parent)
        entry.pack(fill="x", pady=(8, 0))
        command_entry = ttk.Entry(entry, textvariable=self.terminal_command_var)
        command_entry.pack(side="left", fill="x", expand=True)
        command_entry.bind("<Return>", lambda _event: self.send_terminal_command())
        command_entry.focus_set()
        ttk.Button(entry, text="Enviar", command=self.send_terminal_command).pack(side="left", padx=(8, 0))
        ttk.Button(entry, text="Limpar", command=self.clear_terminal).pack(side="left", padx=5)

    def _build_points(self, parent) -> None:
        ttk.Label(parent, text="Pontos de análise", font=("Segoe UI", 14, "bold")).pack(anchor="w")
        ttk.Label(parent, text="Reservado para a próxima etapa, depois de JOG e MOVE.").pack(anchor="w", pady=(3, 10))
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
        ttk.Label(parent, textvariable=self.sequence_status_var).pack(anchor="w")

    def _build_calibration(self, parent) -> None:
        ttk.Label(parent, text="Calibração", font=("Segoe UI", 14, "bold")).pack(anchor="w")
        ttk.Label(parent, text="Valores experimentais de passos/mm usados pelos cálculos.").pack(anchor="w", pady=(3, 12))
        table = ttk.LabelFrame(parent, text="  Passos por mm  ")
        table.pack(fill="x")
        ttk.Label(table, text="Eixo", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, padx=30, pady=8)
        ttk.Label(table, text="Passos/mm", font=("Segoe UI", 9, "bold")).grid(row=0, column=1, padx=30, pady=8)
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
            self.status_label.configure(fg=LIGHT["accent"] if not self.dark_mode else DARK["accent"])
            self.log_var.set("Serial conectada; PING/PONG confirmado.")
            self._terminal_write("[SYSTEM] conectado; PING/PONG OK")
        except Exception as exc:
            self.status_var.set("Falha na conexão")
            self._terminal_write(f"[ERROR] {exc}")
            messagebox.showerror("Arduino", str(exc))

    def disconnect(self) -> None:
        self._cancel_jog()
        if self.arduino is not None:
            self.arduino.disconnect()
            self.arduino = None
        self.status_var.set("Arduino desconectado")
        self.status_label.configure(fg=DARK["muted"] if self.dark_mode else LIGHT["muted"])
        self.log_var.set("Arduino desconectado.")

    def _terminal_write(self, text: str) -> None:
        self.terminal_history.insert(tk.END, text + "\n")
        self.terminal_history.see(tk.END)

    def clear_terminal(self) -> None:
        self.terminal_history.delete("1.0", tk.END)

    def send_terminal_command(self) -> None:
        command = self.terminal_command_var.get().strip()
        if not command:
            return
        self.terminal_command_var.set("")
        self._terminal_write(f"> {command}")
        if self.arduino is None:
            self._terminal_write("< ERROR Arduino não conectado")
            return
        try:
            upper = command.upper()
            # JOG e STOP podem produzir respostas de forma assíncrona; não
            # bloqueamos a GUI esperando uma única linha nesses comandos.
            if upper.startswith("JOG ") or upper == "STOP":
                self.arduino.send_nowait(command)
                self._terminal_write("< comando enviado; aguardando resposta...")
            else:
                self._terminal_write(f"< {self.arduino.send(command)}")
        except Exception as exc:
            self._terminal_write(f"< ERROR {exc}")

    def _poll_serial(self) -> None:
        if self.arduino is not None:
            try:
                for line in self.arduino.read_available():
                    self._terminal_write(f"< {line}")
            except Exception as exc:
                self._terminal_write(f"< SERIAL ERROR {exc}")
        self.root.after(100, self._poll_serial)

    def jog_click(self, axis: str, direction: int) -> None:
        self._cancel_jog()
        try:
            steps = int(self.step_var.get())
            if steps <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("JOG", "Passos/pulso deve ser um inteiro positivo.")
            return
        if self.arduino is None:
            self.log_var.set("Arduino desconectado — JOG não executado.")
            return
        try:
            # O firmware atual define o JOG por tempo/renovação, não por
            # quantidade de passos. O campo acima permanece visível apenas
            # como placeholder até o protocolo MOVE ser integrado.
            self.arduino.jog(axis, direction)
            self._terminal_write(f"> JOG {axis} {direction}")
            self.log_var.set(f"JOG {axis} {'+' if direction > 0 else '-'} — pulso iniciado.")
            self.jog_after_id = self.root.after(self.JOG_PULSE_MS, self._finish_jog_pulse)
        except Exception as exc:
            messagebox.showerror("JOG", str(exc))

    def _finish_jog_pulse(self) -> None:
        self.jog_after_id = None
        self.stop(update_log=True)

    def _cancel_jog(self) -> None:
        if self.jog_after_id is not None:
            try:
                self.root.after_cancel(self.jog_after_id)
            except Exception:
                pass
            self.jog_after_id = None
        if self.arduino is not None:
            try:
                self.arduino.stop()
            except Exception:
                pass

    def stop(self, update_log: bool = True) -> None:
        self._cancel_jog()
        if update_log:
            self.log_var.set("STOP enviado.")
            self._terminal_write("> STOP")

    def move_to(self) -> None:
        messagebox.showinfo("Próxima etapa", "MOVE pela interface será habilitado depois da validação do JOG.")

    def zero(self) -> None:
        if self.arduino is None:
            messagebox.showwarning("ZERO", "Conecte o Arduino antes de zerar.")
            return
        try:
            response = self.arduino.send("ZERO")
            self.machine.zero()
            self.refresh_positions()
            self._terminal_write(f"> ZERO\n< {response}")
            self.log_var.set("ZERO confirmado pelo Arduino.")
        except Exception as exc:
            messagebox.showerror("ZERO", str(exc))

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
            self.point_list.insert(0 + tk.END, f"{index:02d} | X = {point.x_mm:.3f} mm{label}")

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
        self.style.configure("TNotebook", background=theme["bg"])
        self.style.configure("TNotebook.Tab", background=theme["panel"], foreground=theme["muted"], padding=(14, 7))
        self.style.map("TNotebook.Tab", background=[("selected", theme["accent"])], foreground=[("selected", "white")])
        self.style.configure("TButton", background=theme["panel"], foreground=theme["fg"], padding=(9, 5))
        self.style.map("TButton", background=[("active", theme["field"])])
        self.status_label.configure(bg=theme["panel"], fg=theme["muted"])
        self.terminal_history.configure(bg=theme["field"], fg=theme["fg"], insertbackground=theme["fg"])

    def close(self) -> None:
        self._cancel_jog()
        self.disconnect()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    MainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()

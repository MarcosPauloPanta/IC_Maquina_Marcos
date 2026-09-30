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

    A GUI fica responsável pela operação e pela apresentação.
    A proteção física dos limites continua no Arduino.
    """

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("IC Máquina — Controle")
        self.root.geometry("1000x760")
        self.root.minsize(900, 650)

        self.arduino: ArduinoController | None = None
        self.machine = Machine(
            x=Axis(200, 16, 8, calibrated_steps_per_mm=400.0),
            y=Axis(200, 16, 8, calibrated_steps_per_mm=400.0),
            z=Axis(200, 16, 8, calibrated_steps_per_mm=400.0),
        )
        self.sequence = PointSequence()

        self.dark_mode = False
        self.jog_axis: str | None = None
        self.jog_direction = 0
        self.jog_refresh_id: str | None = None
        self.point_entries: list[tk.Entry] = []

        self.port_var = tk.StringVar(value="COM3")
        self.status_var = tk.StringVar(value="Desconectado")
        self.log_var = tk.StringVar(value="Pronto.")
        self.jog_speed_var = tk.StringVar(value="500")
        self.point_count_var = tk.StringVar(value="3")
        self.sequence_status_var = tk.StringVar(value="Defina a quantidade de pontos.")
        self.position_vars = {a: tk.StringVar(value="0.000 mm") for a in "XYZ"}
        self.calibration_vars = {a: tk.StringVar() for a in "XYZ"}

        self._load_calibration()

        self.style = ttk.Style(root)
        self.style.theme_use("clam")

        self._build()
        self._apply_theme()

        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(100, self._poll_serial)

    # ============================================================
    # INTERFACE
    # ============================================================

    def _build(self) -> None:
        header = tk.Frame(self.root)
        header.pack(fill="x", padx=20, pady=(15, 8))
        self.header = header

        self.title_label = tk.Label(
            header,
            text="IC Máquina",
            font=("Segoe UI", 20, "bold"),
        )
        self.title_label.pack(side="left")

        tk.Label(
            header,
            text="Controle de 3 eixos",
            font=("Segoe UI", 10),
        ).pack(side="left", padx=12, pady=(8, 0))

        ttk.Button(
            header,
            text="Tema",
            command=self.toggle_dark_mode,
        ).pack(side="right")

        connection = ttk.LabelFrame(self.root, text=" Comunicação ", padding=9)
        connection.pack(fill="x", padx=20, pady=4)
        self.connection = connection

        ttk.Label(connection, text="Porta:").grid(row=0, column=0, padx=5)
        ttk.Entry(connection, textvariable=self.port_var, width=8).grid(row=0, column=1)

        self.connect_button = ttk.Button(connection, text="Conectar", command=self.connect)
        self.connect_button.grid(row=0, column=2, padx=5)

        ttk.Button(connection, text="Desconectar", command=self.disconnect).grid(row=0, column=3)

        self.status_label = tk.Label(
            connection,
            textvariable=self.status_var,
            font=("Segoe UI", 9, "bold"),
        )
        self.status_label.grid(row=0, column=4, padx=15, sticky="w")

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=20, pady=8)

        operation = ttk.Frame(notebook, padding=16)
        points = ttk.Frame(notebook, padding=16)
        terminal = ttk.Frame(notebook, padding=16)
        calibration = ttk.Frame(notebook, padding=16)

        notebook.add(operation, text="Operação")
        notebook.add(points, text="Análise")
        notebook.add(terminal, text="Terminal")
        notebook.add(calibration, text="Calibração")

        self._build_operation(operation)
        self._build_points(points)
        self._build_terminal(terminal)
        self._build_calibration(calibration)

        footer = tk.Frame(self.root)
        footer.pack(fill="x", padx=20, pady=(0, 12))
        self.footer = footer

        tk.Label(
            footer,
            text="STATUS",
            font=("Segoe UI", 8, "bold"),
        ).pack(side="left", padx=8)
        tk.Label(
            footer,
            textvariable=self.log_var,
            anchor="w",
        ).pack(side="left", fill="x", expand=True)

    def _build_operation(self, parent) -> None:
        positions = ttk.LabelFrame(parent, text=" Posição estimada ")
        positions.pack(fill="x", pady=(0, 15))

        for col, axis in enumerate("XYZ"):
            card = ttk.Frame(positions, padding=10)
            card.grid(row=0, column=col, padx=8, pady=8, sticky="nsew")
            ttk.Label(card, text=axis, font=("Segoe UI", 12, "bold")).pack()
            ttk.Label(
                card,
                textvariable=self.position_vars[axis],
                font=("Consolas", 15, "bold"),
            ).pack(pady=(3, 0))
            positions.columnconfigure(col, weight=1)

        # --------------------------------------------------------
        # JOG
        # --------------------------------------------------------
        jog = ttk.LabelFrame(parent, text=" JOG — segure o botão para mover ")
        jog.pack(fill="x", pady=5)

        ttk.Label(jog, text="Velocidade (passos/s):").grid(
            row=0, column=0, columnspan=2, padx=8, pady=10, sticky="e"
        )
        ttk.Entry(jog, textvariable=self.jog_speed_var, width=10).grid(
            row=0, column=2, padx=5, pady=10, sticky="w"
        )
        ttk.Label(
            jog,
            text="Clique e mantenha pressionado. Solte para parar.",
        ).grid(row=0, column=3, columnspan=2, padx=10, sticky="w")

        for row, axis in enumerate("XYZ", start=1):
            ttk.Label(jog, text=axis, font=("Segoe UI", 11, "bold")).grid(
                row=row, column=1, padx=8, pady=5
            )

            minus = tk.Button(
                jog,
                text=f"{axis} −",
                width=12,
                relief="raised",
                font=("Segoe UI", 10, "bold"),
            )
            minus.grid(row=row, column=2, padx=5, pady=4)
            minus.bind("<ButtonPress-1>", lambda _e, a=axis: self._jog_press(a, -1))
            minus.bind("<ButtonRelease-1>", lambda _e: self._jog_release())

            plus = tk.Button(
                jog,
                text=f"{axis} +",
                width=12,
                relief="raised",
                font=("Segoe UI", 10, "bold"),
            )
            plus.grid(row=row, column=3, padx=5, pady=4)
            plus.bind("<ButtonPress-1>", lambda _e, a=axis: self._jog_press(a, 1))
            plus.bind("<ButtonRelease-1>", lambda _e: self._jog_release())

        stop_button = tk.Button(
            parent,
            text="PARAR",
            command=self.stop,
            font=("Segoe UI", 11, "bold"),
            relief="flat",
            pady=8,
        )
        stop_button.pack(fill="x", pady=12)

        ttk.Button(
            parent,
            text="Zerar posição estimada",
            command=self.zero,
        ).pack()

    # ============================================================
    # ANÁLISE / PONTOS
    # ============================================================

    def _build_points(self, parent) -> None:
        ttk.Label(
            parent,
            text="Sequência de análise",
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            parent,
            text="A máquina muda somente X entre os pontos. Y permanece parado.",
        ).pack(anchor="w", pady=(3, 15))

        setup = ttk.LabelFrame(parent, text=" 1. Quantos pontos? ")
        setup.pack(fill="x")

        ttk.Label(setup, text="Quantidade:").pack(side="left", padx=(12, 5), pady=12)
        ttk.Spinbox(
            setup,
            from_=1,
            to=100,
            width=7,
            textvariable=self.point_count_var,
        ).pack(side="left")

        ttk.Button(
            setup,
            text="Criar pontos",
            command=self.create_point_fields,
        ).pack(side="left", padx=10)

        ttk.Button(
            setup,
            text="Limpar",
            command=self.clear_points,
        ).pack(side="left")

        table = ttk.LabelFrame(parent, text=" 2. Informe X de cada ponto ")
        table.pack(fill="both", expand=True, pady=12)
        self.point_table = table

        ttk.Label(
            table,
            text="Ponto",
            font=("Segoe UI", 9, "bold"),
        ).grid(row=0, column=0, padx=35, pady=8)
        ttk.Label(
            table,
            text="X (mm)",
            font=("Segoe UI", 9, "bold"),
        ).grid(row=0, column=1, padx=35, pady=8)

        action = ttk.Frame(parent)
        action.pack(fill="x")

        self.sequence_status_label = ttk.Label(
            action,
            textvariable=self.sequence_status_var,
        )
        self.sequence_status_label.pack(side="left")

        self.execute_button = ttk.Button(
            action,
            text="EXECUTAR ANÁLISE",
            command=self.prepare_analysis,
            state="disabled",
        )
        self.execute_button.pack(side="right")

        ttk.Label(
            parent,
            text="Z: profundidade de contato ainda será definida. A execução automática ficará bloqueada até essa definição.",
            wraplength=850,
        ).pack(anchor="w", pady=(10, 0))

    def create_point_fields(self) -> None:
        try:
            count = int(self.point_count_var.get())
            if not 1 <= count <= 100:
                raise ValueError
        except ValueError:
            messagebox.showerror("Pontos", "Escolha uma quantidade entre 1 e 100.")
            return

        for widget in self.point_table.winfo_children():
            info = widget.grid_info()
            if int(info.get("row", 0)) > 0:
                widget.destroy()

        self.point_entries.clear()

        for row in range(1, count + 1):
            ttk.Label(self.point_table, text=f"Ponto {row}").grid(
                row=row, column=0, padx=25, pady=5
            )
            entry = tk.Entry(self.point_table, width=14, justify="center")
            entry.grid(row=row, column=1, padx=25, pady=5)
            self.point_entries.append(entry)

        if self.point_entries:
            self.point_entries[0].focus_set()

        self.sequence_status_var.set(f"{count} pontos criados. Agora informe as posições X.")
        self.execute_button.configure(state="normal")

    def clear_points(self) -> None:
        for entry in self.point_entries:
            entry.destroy()
        self.point_entries.clear()
        self.sequence.clear()
        self.sequence_status_var.set("Nenhum ponto definido.")
        self.execute_button.configure(state="disabled")

    def prepare_analysis(self) -> None:
        positions: list[float] = []

        try:
            for entry in self.point_entries:
                value = float(entry.get().replace(",", "."))
                positions.append(value)
        except ValueError:
            messagebox.showerror("Pontos", "Todos os campos X precisam conter números.")
            return

        if not positions:
            return

        self.sequence.set_points(positions)
        resumo = " → ".join(f"{x:g}" for x in positions)
        self.sequence_status_var.set(f"Sequência pronta: X = {resumo} mm")
        self.log_var.set("Sequência de X salva. A execução aguarda a definição do Z.")

        # Ainda não enviamos movimento: a profundidade de contato do Z
        # deliberadamente não foi definida pelo usuário.
        messagebox.showinfo(
            "Sequência pronta",
            "Os pontos foram registrados.\n\n"
            "Próximo passo: definir a descida do Z e o recuo após o contato."
        )

    # ============================================================
    # TERMINAL
    # ============================================================

    def _build_terminal(self, parent) -> None:
        ttk.Label(
            parent,
            text="Terminal Arduino",
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            parent,
            text="Use para diagnóstico. Ex.: PING, STATUS, POS, LIMITS, HELP.",
        ).pack(anchor="w", pady=(3, 8))

        terminal_box = tk.Frame(parent, bd=0, highlightthickness=1)
        terminal_box.pack(fill="both", expand=True)

        self.terminal_history = tk.Text(
            terminal_box,
            height=20,
            wrap="none",
            font=("Consolas", 10),
            bd=0,
            padx=12,
            pady=10,
        )
        self.terminal_history.pack(side="left", fill="both", expand=True)

        scroll = ttk.Scrollbar(
            terminal_box,
            orient="vertical",
            command=self.terminal_history.yview,
        )
        scroll.pack(side="right", fill="y")
        self.terminal_history.configure(yscrollcommand=scroll.set)

        command_line = tk.Frame(parent, bd=0)
        command_line.pack(fill="x", pady=(8, 0))

        tk.Label(
            command_line,
            text="»",
            font=("Consolas", 13, "bold"),
        ).pack(side="left", padx=(8, 4))

        self.terminal_command = tk.Entry(
            command_line,
            font=("Consolas", 11),
            relief="flat",
        )
        self.terminal_command.pack(side="left", fill="x", expand=True, ipady=5)
        self.terminal_command.bind("<Return>", self._terminal_enter)

        ttk.Button(
            command_line,
            text="Enviar",
            command=self.send_terminal_command,
        ).pack(side="left", padx=7)

        ttk.Button(
            command_line,
            text="Limpar",
            command=self.clear_terminal,
        ).pack(side="left")

        self._terminal_write("IC Máquina — terminal pronto")
        self._terminal_write("Digite um comando abaixo do » e pressione ENTER.")

    def _terminal_enter(self, _event=None):
        self.send_terminal_command()
        return "break"

    def _terminal_write(self, text: str) -> None:
        self.terminal_history.insert(tk.END, text + "\n")
        self.terminal_history.see(tk.END)

    def clear_terminal(self) -> None:
        self.terminal_history.delete("1.0", tk.END)
        self._terminal_write("Terminal limpo.")

    def send_terminal_command(self) -> None:
        command = self.terminal_command.get().strip()
        if not command:
            return

        self.terminal_command.delete(0, tk.END)
        self._terminal_write(f"» {command}")

        if self.arduino is None or not self.arduino.is_connected:
            self._terminal_write("Arduino não conectado.")
            return

        try:
            response = self.arduino.send(command)
            self._terminal_write(response)
        except Exception as exc:
            self._terminal_write(f"ERRO: {exc}")

    def _poll_serial(self) -> None:
        if self.arduino is not None and self.arduino.is_connected:
            try:
                for line in self.arduino.read_available():
                    self._terminal_write(line)
            except Exception as exc:
                self._terminal_write(f"SERIAL ERROR: {exc}")
        self.root.after(100, self._poll_serial)

    # ============================================================
    # JOG CONTÍNUO
    # ============================================================

    def _jog_press(self, axis: str, direction: int) -> None:
        """Começa a mover imediatamente e mantém o comando renovado."""

        if self.arduino is None or not self.arduino.is_connected:
            self.log_var.set("Conecte o Arduino antes de usar o JOG.")
            return

        try:
            speed = int(self.jog_speed_var.get())
            if not 1 <= speed <= 10000:
                raise ValueError
        except ValueError:
            messagebox.showerror("JOG", "Velocidade: use um inteiro entre 1 e 10000 passos/s.")
            return

        # Se outro eixo estiver sendo segurado, primeiro o paramos.
        if self.jog_axis is not None:
            self._send_jog_stop()

        self.jog_axis = axis
        self.jog_direction = direction

        try:
            self.arduino.jog_start(axis, direction, speed)
            self.log_var.set(f"JOG {axis}{'+' if direction > 0 else '-'} — {speed} passos/s")
            self._schedule_jog_refresh()
        except Exception as exc:
            self.jog_axis = None
            messagebox.showerror("JOG", str(exc))

    def _schedule_jog_refresh(self) -> None:
        if self.jog_axis is None:
            return
        self.jog_refresh_id = self.root.after(100, self._refresh_jog)

    def _refresh_jog(self) -> None:
        self.jog_refresh_id = None

        if self.jog_axis is None or self.arduino is None or not self.arduino.is_connected:
            return

        try:
            speed = int(self.jog_speed_var.get())
            self.arduino.jog_start(self.jog_axis, self.jog_direction, speed)
            self._schedule_jog_refresh()
        except Exception as exc:
            self._send_jog_stop()
            self.log_var.set(f"JOG interrompido: {exc}")

    def _jog_release(self) -> None:
        self._send_jog_stop()
        self.log_var.set("JOG parado.")

    def _send_jog_stop(self) -> None:
        if self.jog_refresh_id is not None:
            try:
                self.root.after_cancel(self.jog_refresh_id)
            except Exception:
                pass
            self.jog_refresh_id = None

        if self.arduino is not None and self.arduino.is_connected:
            try:
                self.arduino.jog_stop()
            except Exception:
                pass

        self.jog_axis = None
        self.jog_direction = 0

    def stop(self) -> None:
        self._send_jog_stop()
        if self.arduino is not None and self.arduino.is_connected:
            try:
                self.arduino.stop()
            except Exception:
                pass
        self.log_var.set("STOP enviado.")

    # ============================================================
    # CONEXÃO
    # ============================================================

    def connect(self) -> None:
        if self.arduino is not None and self.arduino.is_connected:
            return

        try:
            controller = ArduinoController(self.port_var.get().strip())
            controller.connect()
            self.arduino = controller
            self.status_var.set(f"Conectado — {controller.port}")
            self.status_label.configure(fg="#10a37f")
            self.connect_button.configure(state="disabled")
            self.log_var.set("Conectado. PING/PONG confirmado.")
            self._terminal_write("[SYSTEM] PONG — Arduino conectado")
        except Exception as exc:
            self.status_var.set("Falha na conexão")
            messagebox.showerror("Arduino", str(exc))

    def disconnect(self) -> None:
        self._send_jog_stop()
        if self.arduino is not None:
            try:
                self.arduino.disconnect()
            except Exception:
                pass
            self.arduino = None

        self.status_var.set("Desconectado")
        self.status_label.configure(fg="#777777")
        self.connect_button.configure(state="normal")
        self.log_var.set("Arduino desconectado.")

    # ============================================================
    # ZERO / CALIBRAÇÃO
    # ============================================================

    def zero(self) -> None:
        if self.arduino is None or not self.arduino.is_connected:
            messagebox.showwarning("ZERO", "Conecte o Arduino primeiro.")
            return

        try:
            response = self.arduino.send("ZERO")
            self.machine.zero()
            self.refresh_positions()
            self._terminal_write(f"ZERO → {response}")
            self.log_var.set("Posição zerada.")
        except Exception as exc:
            messagebox.showerror("ZERO", str(exc))

    def _build_calibration(self, parent) -> None:
        ttk.Label(parent, text="Calibração", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        ttk.Label(parent, text="Passos efetivos por milímetro usados pelo modelo Python.").pack(anchor="w", pady=(3, 12))

        table = ttk.LabelFrame(parent, text=" Passos/mm ")
        table.pack(fill="x")

        for col, text in enumerate(("Eixo", "Passos/mm")):
            ttk.Label(table, text=text, font=("Segoe UI", 9, "bold")).grid(
                row=0, column=col, padx=35, pady=8
            )

        for row, axis in enumerate("XYZ", start=1):
            ttk.Label(table, text=axis).grid(row=row, column=0, pady=6)
            ttk.Entry(table, textvariable=self.calibration_vars[axis], width=18).grid(
                row=row, column=1
            )

        ttk.Button(parent, text="Aplicar", command=self.apply_calibration).pack(anchor="w", pady=10)
        ttk.Button(parent, text="Salvar", command=self.save_calibration).pack(anchor="w")

    def apply_calibration(self) -> None:
        try:
            for axis in "XYZ":
                self.machine.get_axis(axis).set_calibration(
                    float(self.calibration_vars[axis].get().replace(",", "."))
                )
            self.log_var.set("Calibração aplicada.")
        except ValueError:
            messagebox.showerror("Calibração", "Use valores numéricos positivos.")

    def save_calibration(self) -> None:
        self.apply_calibration()
        data = {
            axis: self.machine.get_axis(axis).microsteps_per_mm
            for axis in "XYZ"
        }
        CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        self.log_var.set("Calibração salva.")

    def _load_calibration(self) -> None:
        if not CONFIG_FILE.exists():
            for axis in "XYZ":
                self.calibration_vars[axis].set(
                    f"{self.machine.get_axis(axis).microsteps_per_mm:.6f}"
                )
            return

        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            for axis in "XYZ":
                if axis in data:
                    self.machine.get_axis(axis).set_calibration(float(data[axis]))
                self.calibration_vars[axis].set(
                    f"{self.machine.get_axis(axis).microsteps_per_mm:.6f}"
                )
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            for axis in "XYZ":
                self.calibration_vars[axis].set(
                    f"{self.machine.get_axis(axis).microsteps_per_mm:.6f}"
                )

    def refresh_positions(self) -> None:
        for axis, value in self.machine.positions().items():
            self.position_vars[axis].set(f"{value:.3f} mm")

    # ============================================================
    # TEMA / FECHAMENTO
    # ============================================================

    def toggle_dark_mode(self) -> None:
        self.dark_mode = not self.dark_mode
        self._apply_theme()

    def _apply_theme(self) -> None:
        bg = "#212121" if self.dark_mode else "#ffffff"
        fg = "#ececec" if self.dark_mode else "#2d2d2d"
        field = "#424242" if self.dark_mode else "#f7f7f8"
        panel = "#2f2f2f" if self.dark_mode else "#ffffff"

        self.root.configure(bg=bg)
        self.header.configure(bg=bg)
        self.footer.configure(bg=bg)
        self.title_label.configure(bg=bg, fg=fg)

        self.style.configure(".", background=panel, foreground=fg, fieldbackground=field)
        self.style.configure("TFrame", background=panel)
        self.style.configure("TLabel", background=panel, foreground=fg)
        self.style.configure("TLabelframe", background=panel, foreground=fg)
        self.style.configure("TLabelframe.Label", background=panel, foreground=fg)
        self.style.configure("TButton", background=panel, foreground=fg)
        self.style.configure("TEntry", fieldbackground=field, foreground=fg)
        self.style.configure("TNotebook", background=bg)
        self.style.configure("TNotebook.Tab", background=panel, foreground=fg, padding=(14, 7))

        self.terminal_history.configure(
            bg=field,
            fg=fg,
            insertbackground=fg,
        )
        self.terminal_command.configure(
            bg=field,
            fg=fg,
            insertbackground=fg,
        )

    def close(self) -> None:
        self._send_jog_stop()
        self.disconnect()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    MainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()

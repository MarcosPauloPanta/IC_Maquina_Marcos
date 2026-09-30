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
    """Interface principal da máquina de análise.

    A GUI organiza operação, calibração, pontos e terminal.
    A proteção física dos limites permanece no Arduino.
    """

    # Identidade visual inspirada em instrumentação de laboratório:
    # claro = aço/branco + bronze; escuro = grafite + vermelho.
    LIGHT = {"bg": "#F4F4F2", "panel": "#FFFFFF", "field": "#ECEDEB", "text": "#252525", "accent": "#8A5A32", "border": "#B8B8B2", "danger": "#A51D2D"}
    DARK = {"bg": "#17191B", "panel": "#24272A", "field": "#303438", "text": "#E8E8E6", "accent": "#B32632", "border": "#45494D", "danger": "#E04B58"}

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("IC Máquina — Laboratório de Corrosão")
        self.root.geometry("1050x780")
        self.root.minsize(920, 680)

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

        # Calibração dos três eixos.
        self.calibration_vars = {a: tk.StringVar() for a in "XYZ"}
        # Parâmetros de aproximação do Z; ficam editáveis e salváveis.
        self.z_down_mm_var = tk.StringVar(value="1.000")
        self.z_speed_var = tk.StringVar(value="200")
        self.z_retract_mm_var = tk.StringVar(value="1.000")

        self.style = ttk.Style(root)
        self.style.theme_use("clam")
        self._load_calibration()
        self._build()
        self._apply_theme()

        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(100, self._poll_serial)

    # ============================================================
    # CONSTRUÇÃO DA INTERFACE
    # ============================================================

    def _build(self) -> None:
        header = tk.Frame(self.root)
        header.pack(fill="x", padx=20, pady=(14, 8))
        self.header = header

        title_box = tk.Frame(header)
        title_box.pack(side="left")
        self.title_box = title_box

        self.title_label = tk.Label(title_box, text="IC Máquina", font=("Segoe UI", 21, "bold"))
        self.title_label.pack(anchor="w")
        self.subtitle_label = tk.Label(title_box, text="Instrumentação — Laboratório de Corrosão", font=("Segoe UI", 9))
        self.subtitle_label.pack(anchor="w")

        ttk.Button(header, text="Tema claro / escuro", command=self.toggle_dark_mode).pack(side="right", pady=5)

        connection = ttk.LabelFrame(self.root, text=" Comunicação ", padding=9)
        connection.pack(fill="x", padx=20, pady=4)
        self.connection = connection

        ttk.Label(connection, text="Porta:").grid(row=0, column=0, padx=5)
        ttk.Entry(connection, textvariable=self.port_var, width=9).grid(row=0, column=1)
        self.connect_button = ttk.Button(connection, text="Conectar", command=self.connect)
        self.connect_button.grid(row=0, column=2, padx=5)
        ttk.Button(connection, text="Desconectar", command=self.disconnect).grid(row=0, column=3)
        self.status_label = tk.Label(connection, textvariable=self.status_var, font=("Segoe UI", 9, "bold"))
        self.status_label.grid(row=0, column=4, padx=15, sticky="w")

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=20, pady=8)

        operation = ttk.Frame(notebook, padding=16)
        analysis = ttk.Frame(notebook, padding=16)
        terminal = ttk.Frame(notebook, padding=16)
        calibration = ttk.Frame(notebook, padding=16)

        notebook.add(operation, text="Operação")
        notebook.add(analysis, text="Análise")
        notebook.add(terminal, text="Terminal")
        notebook.add(calibration, text="Calibração")

        self._build_operation(operation)
        self._build_analysis(analysis)
        self._build_terminal(terminal)
        self._build_calibration(calibration)

        footer = tk.Frame(self.root)
        footer.pack(fill="x", padx=20, pady=(0, 10))
        self.footer = footer
        self.footer_label = tk.Label(footer, text="STATUS", font=("Segoe UI", 8, "bold"))
        self.footer_label.pack(side="left", padx=8)
        self.footer_message = tk.Label(footer, textvariable=self.log_var, anchor="w")
        self.footer_message.pack(side="left", fill="x", expand=True)

    def _build_operation(self, parent) -> None:
        positions = ttk.LabelFrame(parent, text=" Posição estimada ")
        positions.pack(fill="x", pady=(0, 14))

        for col, axis in enumerate("XYZ"):
            card = ttk.Frame(positions, padding=10)
            card.grid(row=0, column=col, padx=8, pady=8, sticky="nsew")
            ttk.Label(card, text=axis, font=("Segoe UI", 12, "bold")).pack()
            ttk.Label(card, textvariable=self.position_vars[axis], font=("Consolas", 15, "bold")).pack(pady=(3, 0))
            positions.columnconfigure(col, weight=1)

        jog = ttk.LabelFrame(parent, text=" JOG — pressione e segure para mover ")
        jog.pack(fill="x", pady=5)
        ttk.Label(jog, text="Velocidade (passos/s):").grid(row=0, column=0, padx=8, pady=10, sticky="e")
        ttk.Entry(jog, textvariable=self.jog_speed_var, width=10).grid(row=0, column=1, padx=4, pady=10, sticky="w")
        ttk.Label(jog, text="Solte o botão para parar.").grid(row=0, column=2, columnspan=2, padx=12, sticky="w")

        for row, axis in enumerate("XYZ", start=1):
            ttk.Label(jog, text=axis, font=("Segoe UI", 11, "bold")).grid(row=row, column=0, padx=8, pady=5)
            minus = tk.Button(jog, text=f"{axis} −", width=14, font=("Segoe UI", 10, "bold"))
            plus = tk.Button(jog, text=f"{axis} +", width=14, font=("Segoe UI", 10, "bold"))
            minus.grid(row=row, column=1, padx=5, pady=4)
            plus.grid(row=row, column=2, padx=5, pady=4)
            minus.bind("<ButtonPress-1>", lambda _e, a=axis: self._jog_press(a, -1))
            minus.bind("<ButtonRelease-1>", lambda _e: self._jog_release())
            plus.bind("<ButtonPress-1>", lambda _e, a=axis: self._jog_press(a, 1))
            plus.bind("<ButtonRelease-1>", lambda _e: self._jog_release())

        self.stop_button = tk.Button(parent, text="PARAR", command=self.stop, font=("Segoe UI", 11, "bold"), relief="flat", pady=8)
        self.stop_button.pack(fill="x", pady=12)
        ttk.Button(parent, text="Zerar posição estimada", command=self.zero).pack()

    # ============================================================
    # ANÁLISE
    # ============================================================

    def _build_analysis(self, parent) -> None:
        ttk.Label(parent, text="Análise por pontos", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        ttk.Label(parent, text="Defina apenas as posições X. Y permanece parado durante a sequência.").pack(anchor="w", pady=(3, 14))

        setup = ttk.LabelFrame(parent, text=" 1. Quantidade de pontos ")
        setup.pack(fill="x")
        ttk.Label(setup, text="Pontos:").pack(side="left", padx=(12, 5), pady=12)
        ttk.Spinbox(setup, from_=1, to=100, width=7, textvariable=self.point_count_var).pack(side="left")
        ttk.Button(setup, text="Criar pontos", command=self.create_point_fields).pack(side="left", padx=10)
        ttk.Button(setup, text="Limpar", command=self.clear_points).pack(side="left")

        table = ttk.LabelFrame(parent, text=" 2. Posições X ")
        table.pack(fill="both", expand=True, pady=12)
        self.point_table = table
        ttk.Label(table, text="Ponto", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, padx=45, pady=8)
        ttk.Label(table, text="X (mm)", font=("Segoe UI", 9, "bold")).grid(row=0, column=1, padx=45, pady=8)

        action = ttk.Frame(parent)
        action.pack(fill="x")
        ttk.Label(action, textvariable=self.sequence_status_var).pack(side="left")
        self.execute_button = ttk.Button(action, text="EXECUTAR ANÁLISE", command=self.prepare_analysis, state="disabled")
        self.execute_button.pack(side="right")

        ttk.Label(
            parent,
            text="A execução automática do ciclo X → Z ↓ → contato → Z ↑ ficará disponível depois que os parâmetros do Z forem definidos e testados.",
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
            if int(widget.grid_info().get("row", 0)) > 0:
                widget.destroy()
        self.point_entries.clear()

        for row in range(1, count + 1):
            ttk.Label(self.point_table, text=f"Ponto {row}").grid(row=row, column=0, padx=35, pady=5)
            entry = tk.Entry(self.point_table, width=14, justify="center")
            entry.grid(row=row, column=1, padx=35, pady=5)
            self.point_entries.append(entry)
        if self.point_entries:
            self.point_entries[0].focus_set()
        self.sequence_status_var.set(f"{count} pontos criados. Informe as posições X.")
        self.execute_button.configure(state="normal")

    def clear_points(self) -> None:
        for entry in self.point_entries:
            entry.destroy()
        self.point_entries.clear()
        self.sequence.clear()
        self.sequence_status_var.set("Nenhum ponto definido.")
        self.execute_button.configure(state="disabled")

    def prepare_analysis(self) -> None:
        try:
            positions = [float(entry.get().replace(",", ".")) for entry in self.point_entries]
        except ValueError:
            messagebox.showerror("Pontos", "Todos os campos X precisam conter números.")
            return
        if not positions:
            return
        self.sequence.set_points(positions)
        resumo = " → ".join(f"{x:g}" for x in positions)
        self.sequence_status_var.set(f"Sequência pronta: X = {resumo} mm")
        self.log_var.set("Pontos salvos. O ciclo automático do Z aguarda validação dos parâmetros.")
        messagebox.showinfo("Sequência pronta", "Os pontos foram registrados.\n\nO ciclo automático ainda aguarda a calibração/teste do Z.")

    # ============================================================
    # CALIBRAÇÃO
    # ============================================================

    def _build_calibration(self, parent) -> None:
        ttk.Label(parent, text="Calibração da máquina", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        ttk.Label(parent, text="Os valores abaixo ficam salvos no arquivo calibration.json.").pack(anchor="w", pady=(3, 12))

        axes = ttk.LabelFrame(parent, text=" Passos efetivos por milímetro ")
        axes.pack(fill="x", pady=(0, 12))
        ttk.Label(axes, text="Eixo", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, padx=45, pady=8)
        ttk.Label(axes, text="Passos/mm", font=("Segoe UI", 9, "bold")).grid(row=0, column=1, padx=45, pady=8)
        for row, axis in enumerate("XYZ", start=1):
            ttk.Label(axes, text=axis, font=("Segoe UI", 10, "bold")).grid(row=row, column=0, pady=6)
            ttk.Entry(axes, textvariable=self.calibration_vars[axis], width=18).grid(row=row, column=1, pady=6)

        zbox = ttk.LabelFrame(parent, text=" Parâmetros de aproximação do Z — editáveis ")
        zbox.pack(fill="x", pady=4)

        fields = [
            ("Descida máxima / curso de contato (mm)", self.z_down_mm_var),
            ("Velocidade de descida (passos/s)", self.z_speed_var),
            ("Recuo após contato (mm)", self.z_retract_mm_var),
        ]
        for row, (label, variable) in enumerate(fields):
            ttk.Label(zbox, text=label).grid(row=row, column=0, padx=12, pady=8, sticky="w")
            ttk.Entry(zbox, textvariable=variable, width=18).grid(row=row, column=1, padx=12, pady=8, sticky="w")

        ttk.Label(
            zbox,
            text="Ainda não estamos assumindo valores corretos para o Z. Eles serão ajustados quando você trouxer os dados de calibração.",
            wraplength=700,
        ).grid(row=3, column=0, columnspan=2, padx=12, pady=(5, 12), sticky="w")

        buttons = ttk.Frame(parent)
        buttons.pack(fill="x", pady=12)
        ttk.Button(buttons, text="Aplicar", command=self.apply_calibration).pack(side="left")
        ttk.Button(buttons, text="Salvar calibração", command=self.save_calibration).pack(side="left", padx=8)
        ttk.Button(buttons, text="Recarregar salva", command=self._reload_calibration).pack(side="left")

    def apply_calibration(self) -> None:
        try:
            for axis in "XYZ":
                self.machine.get_axis(axis).set_calibration(float(self.calibration_vars[axis].get().replace(",", ".")))
            down = float(self.z_down_mm_var.get().replace(",", "."))
            speed = int(self.z_speed_var.get())
            retract = float(self.z_retract_mm_var.get().replace(",", "."))
            if down <= 0 or speed <= 0 or retract <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Calibração", "Confira os valores: passos/mm, Z e velocidade devem ser positivos.")
            return False
        self.log_var.set("Calibração aplicada ao modelo da máquina.")
        return True

    def save_calibration(self) -> None:
        if not self.apply_calibration():
            return
        data = {
            "axes_steps_per_mm": {axis: self.machine.get_axis(axis).microsteps_per_mm for axis in "XYZ"},
            "z_approach": {
                "down_mm": float(self.z_down_mm_var.get().replace(",", ".")),
                "speed_steps_s": int(self.z_speed_var.get()),
                "retract_mm": float(self.z_retract_mm_var.get().replace(",", ".")),
            },
        }
        CONFIG_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        self.log_var.set(f"Calibração salva em {CONFIG_FILE}.")

    def _load_calibration(self) -> None:
        defaults = {axis: self.machine.get_axis(axis).microsteps_per_mm for axis in "XYZ"}
        for axis in "XYZ":
            self.calibration_vars[axis].set(f"{defaults[axis]:.6f}")
        if not CONFIG_FILE.exists():
            return
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            axes = data.get("axes_steps_per_mm", data)
            for axis in "XYZ":
                if axis in axes:
                    self.machine.get_axis(axis).set_calibration(float(axes[axis]))
                    self.calibration_vars[axis].set(f"{float(axes[axis]):.6f}")
            z = data.get("z_approach", {})
            if "down_mm" in z:
                self.z_down_mm_var.set(str(z["down_mm"]))
            if "speed_steps_s" in z:
                self.z_speed_var.set(str(z["speed_steps_s"]))
            if "retract_mm" in z:
                self.z_retract_mm_var.set(str(z["retract_mm"]))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            pass

    def _reload_calibration(self) -> None:
        self._load_calibration()
        self.log_var.set("Valores salvos recarregados.")

    # ============================================================
    # TERMINAL
    # ============================================================

    def _build_terminal(self, parent) -> None:
        ttk.Label(parent, text="Terminal Arduino", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        ttk.Label(parent, text="Diagnóstico direto da comunicação serial.").pack(anchor="w", pady=(3, 8))

        box = tk.Frame(parent, bd=0, highlightthickness=1)
        box.pack(fill="both", expand=True)
        self.terminal_history = tk.Text(box, height=20, wrap="none", font=("Consolas", 10), bd=0, padx=12, pady=10)
        self.terminal_history.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(box, orient="vertical", command=self.terminal_history.yview)
        scroll.pack(side="right", fill="y")
        self.terminal_history.configure(yscrollcommand=scroll.set)

        command_line = tk.Frame(parent, bd=0)
        command_line.pack(fill="x", pady=(8, 0))
        self.terminal_prompt = tk.Label(command_line, text="»", font=("Consolas", 13, "bold"))
        self.terminal_prompt.pack(side="left", padx=(8, 4))
        self.terminal_command = tk.Entry(command_line, font=("Consolas", 11), relief="flat")
        self.terminal_command.pack(side="left", fill="x", expand=True, ipady=5)
        self.terminal_command.bind("<Return>", self._terminal_enter)
        ttk.Button(command_line, text="Enviar", command=self.send_terminal_command).pack(side="left", padx=7)
        ttk.Button(command_line, text="Limpar", command=self.clear_terminal).pack(side="left")
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
    # JOG
    # ============================================================

    def _jog_press(self, axis: str, direction: int) -> None:
        if self.arduino is None or not self.arduino.is_connected:
            self.log_var.set("Conecte o Arduino antes de usar o JOG.")
            return
        try:
            speed = int(self.jog_speed_var.get())
            if not 1 <= speed <= 10000:
                raise ValueError
        except ValueError:
            messagebox.showerror("JOG", "Use uma velocidade inteira entre 1 e 10000 passos/s.")
            return
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
        if self.jog_axis is not None:
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
    # CONEXÃO / POSIÇÃO
    # ============================================================

    def connect(self) -> None:
        if self.arduino is not None and self.arduino.is_connected:
            return
        try:
            controller = ArduinoController(self.port_var.get().strip())
            controller.connect()
            self.arduino = controller
            self.status_var.set(f"Conectado — {controller.port}")
            self.status_label.configure(fg=self._colors()["accent"])
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
        self.status_label.configure(fg=self._colors()["text"])
        self.connect_button.configure(state="normal")
        self.log_var.set("Arduino desconectado.")

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

    def refresh_positions(self) -> None:
        for axis, value in self.machine.positions().items():
            self.position_vars[axis].set(f"{value:.3f} mm")

    # ============================================================
    # TEMA
    # ============================================================

    def _colors(self) -> dict[str, str]:
        return self.DARK if self.dark_mode else self.LIGHT

    def toggle_dark_mode(self) -> None:
        self.dark_mode = not self.dark_mode
        self._apply_theme()

    def _apply_theme(self) -> None:
        c = self._colors()
        self.root.configure(bg=c["bg"])
        self.header.configure(bg=c["bg"])
        self.title_box.configure(bg=c["bg"])
        self.title_label.configure(bg=c["bg"], fg=c["text"])
        self.subtitle_label.configure(bg=c["bg"], fg=c["accent"])
        self.footer.configure(bg=c["bg"])
        self.footer_label.configure(bg=c["bg"], fg=c["accent"])
        self.footer_message.configure(bg=c["bg"], fg=c["text"])
        self.stop_button.configure(bg=c["danger"], fg="#FFFFFF", activebackground=c["danger"], activeforeground="#FFFFFF")
        self.terminal_prompt.configure(bg=c["panel"], fg=c["accent"])
        self.terminal_history.configure(bg=c["field"], fg=c["text"], insertbackground=c["text"])
        self.terminal_command.configure(bg=c["field"], fg=c["text"], insertbackground=c["text"])
        self.style.configure(".", background=c["panel"], foreground=c["text"], fieldbackground=c["field"])
        self.style.configure("TFrame", background=c["panel"])
        self.style.configure("TLabel", background=c["panel"], foreground=c["text"])
        self.style.configure("TLabelframe", background=c["panel"], foreground=c["text"], bordercolor=c["border"])
        self.style.configure("TLabelframe.Label", background=c["panel"], foreground=c["accent"])
        self.style.configure("TButton", background=c["panel"], foreground=c["text"])
        self.style.configure("TEntry", fieldbackground=c["field"], foreground=c["text"])
        self.style.configure("TSpinbox", fieldbackground=c["field"], foreground=c["text"])
        self.style.configure("TNotebook", background=c["bg"])
        self.style.configure("TNotebook.Tab", background=c["panel"], foreground=c["text"], padding=(15, 7))

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

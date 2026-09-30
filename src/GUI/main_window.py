from __future__ import annotations

import json
import threading
import time
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

from src.controller.arduino import ArduinoController
from src.controller.axis import Axis
from src.controller.machine import Machine
from src.controller.point_sequence import PointSequence

CONFIG_FILE = Path("calibration.json")


class MainWindow:
    LIGHT = {"bg": "#F4F4F1", "panel": "#FFFFFF", "field": "#E4E4DF", "text": "#181818", "accent": "#74451F", "border": "#A9A9A2", "danger": "#A51D2D"}
    DARK = {"bg": "#141516", "panel": "#1D1F21", "field": "#25282B", "text": "#F5F5F2", "accent": "#E24A55", "border": "#464A4F", "danger": "#E04450"}

    def __init__(self, root):
        self.root = root
        self.root.title("Máquina de Análise")
        self.root.geometry("1120x820")
        self.root.minsize(980, 720)
        self.arduino = None
        self.machine = Machine(
            Axis(200, 16, 8, calibrated_steps_per_mm=400),
            Axis(200, 16, 8, calibrated_steps_per_mm=400),
            Axis(200, 16, 8, calibrated_steps_per_mm=400),
        )
        self.sequence = PointSequence()
        self.dark_mode = False
        self.analysis_running = False
        self.jog_axis = None
        self.jog_direction = 0
        self.jog_refresh_id = None
        self.last_pos_request = 0
        self.port_var = tk.StringVar(value="COM3")
        self.status_var = tk.StringVar(value="Desconectado")
        self.log_var = tk.StringVar(value="Pronto.")
        self.jog_speed_var = tk.StringVar(value="500")
        self.point_count_var = tk.StringVar(value="3")
        self.sequence_status_var = tk.StringVar(value="Nenhum ponto definido.")
        self.position_vars = {a: tk.StringVar(value="0.000 mm") for a in "XYZ"}
        self.calibration_vars = {a: tk.StringVar() for a in "XYZ"}
        self.point_entries = []
        self.z_down_mm_var = tk.StringVar(value="1.000")
        self.z_speed_var = tk.StringVar(value="200")
        self.z_retract_mm_var = tk.StringVar(value="1.000")
        self.z_dwell_s_var = tk.StringVar(value="1.000")
        self.style = ttk.Style(root)
        self.style.theme_use("clam")
        self._load_calibration()
        self._build()
        self._apply_theme()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(100, self._poll_serial)

    def _build(self):
        self.header = tk.Frame(self.root)
        self.header.pack(fill="x", padx=20, pady=12)
        ttk.Button(self.header, text="Claro / Escuro", command=self.toggle_dark_mode).pack(side="right")

        c = ttk.LabelFrame(self.root, text=" Comunicação ", padding=11)
        c.pack(fill="x", padx=20, pady=4)
        self.connection = c
        ttk.Label(c, text="Porta:").grid(row=0, column=0, padx=6)
        ttk.Entry(c, textvariable=self.port_var, width=10).grid(row=0, column=1)
        self.connect_button = ttk.Button(c, text="Conectar", command=self.connect)
        self.connect_button.grid(row=0, column=2, padx=6)
        ttk.Button(c, text="Desconectar", command=self.disconnect).grid(row=0, column=3)
        self.status_label = tk.Label(c, textvariable=self.status_var, font=("Segoe UI", 10, "bold"))
        self.status_label.grid(row=0, column=4, padx=16)

        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True, padx=20, pady=8)
        op = ttk.Frame(nb, padding=18)
        an = ttk.Frame(nb, padding=18)
        te = ttk.Frame(nb, padding=18)
        ca = ttk.Frame(nb, padding=18)
        nb.add(op, text="Operação")
        nb.add(an, text="Análise")
        nb.add(te, text="Terminal")
        nb.add(ca, text="Calibração")
        self._operation(op)
        self._analysis(an)
        self._terminal(te)
        self._calibration(ca)

        self.footer = tk.Frame(self.root)
        self.footer.pack(fill="x", padx=20, pady=8)
        self.footer_label = tk.Label(self.footer, text="STATUS", font=("Segoe UI", 9, "bold"))
        self.footer_label.pack(side="left", padx=8)
        self.footer_message = tk.Label(self.footer, textvariable=self.log_var, anchor="w", font=("Segoe UI", 10))
        self.footer_message.pack(side="left", fill="x", expand=True)

    def _operation(self, p):
        pos = ttk.LabelFrame(p, text=" Posição estimada ")
        pos.pack(fill="x", pady=(0, 16))
        for col, a in enumerate("XYZ"):
            card = ttk.Frame(pos, padding=12)
            card.grid(row=0, column=col, padx=9, pady=9, sticky="nsew")
            ttk.Label(card, text=a, font=("Segoe UI", 14, "bold")).pack()
            ttk.Label(card, textvariable=self.position_vars[a], font=("Consolas", 17, "bold")).pack()
            pos.columnconfigure(col, weight=1)

        jog = ttk.LabelFrame(p, text=" JOG ")
        jog.pack(fill="x")
        ttk.Label(jog, text="Velocidade (passos/s):", font=("Segoe UI", 10)).grid(row=0, column=0, padx=8, pady=12)
        ttk.Entry(jog, textvariable=self.jog_speed_var, width=11, font=("Segoe UI", 10)).grid(row=0, column=1)
        ttk.Label(jog, text="Recomendado: 500 passos/s", font=("Segoe UI", 10, "bold")).grid(row=0, column=2, padx=14)
        for r, a in enumerate("XYZ", 2):
            ttk.Label(jog, text=a, font=("Segoe UI", 11, "bold")).grid(row=r, column=0, padx=8, pady=6)
            m = tk.Button(jog, text=f"{a} −", width=15, font=("Segoe UI", 10, "bold"), relief="flat", pady=5)
            q = tk.Button(jog, text=f"{a} +", width=15, font=("Segoe UI", 10, "bold"), relief="flat", pady=5)
            m.grid(row=r, column=1, padx=5, pady=5)
            q.grid(row=r, column=2, padx=5, pady=5)
            m.bind("<ButtonPress-1>", lambda e, x=a: self._jog_press(x, -1))
            m.bind("<ButtonRelease-1>", self._jog_release)
            q.bind("<ButtonPress-1>", lambda e, x=a: self._jog_press(x, 1))
            q.bind("<ButtonRelease-1>", self._jog_release)

        self.stop_button = tk.Button(p, text="PARAR", command=self.stop, font=("Segoe UI", 12, "bold"), relief="flat", pady=10)
        self.stop_button.pack(fill="x", pady=14)
        ttk.Button(p, text="Zerar posição", command=self.zero).pack()

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
        ttk.Label(self.point_table, text="Ponto", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, padx=45, pady=9)
        ttk.Label(self.point_table, text="X (mm)", font=("Segoe UI", 10, "bold")).grid(row=0, column=1, padx=45, pady=9)
        self.point_table.columnconfigure(0, weight=1)
        self.point_table.columnconfigure(1, weight=1)
        a = ttk.Frame(p)
        a.pack(fill="x", pady=11)
        ttk.Label(a, textvariable=self.sequence_status_var, font=("Segoe UI", 10)).pack(side="left")
        self.execute_button = ttk.Button(a, text="EXECUTAR", command=self.execute_analysis, state="disabled")
        self.execute_button.pack(side="right")

    def create_point_fields(self):
        try:
            n = int(self.point_count_var.get())
            assert 1 <= n <= 100
        except (ValueError, AssertionError):
            messagebox.showerror("Pontos", "Quantidade inválida.")
            return
        for w in self.point_table.winfo_children():
            if int(w.grid_info().get("row", 0)) > 0:
                w.destroy()
        self.point_entries = []
        for r in range(1, n + 1):
            ttk.Label(self.point_table, text=str(r), font=("Segoe UI", 10)).grid(row=r, column=0, pady=6)
            e = tk.Entry(self.point_table, width=16, justify="center", font=("Segoe UI", 10))
            e.grid(row=r, column=1, pady=6)
            self.point_entries.append(e)
        if self.point_entries:
            self.point_entries[0].focus_set()
        self.sequence_status_var.set(f"{n} pontos.")
        self.execute_button.configure(state="normal")

    def clear_points(self):
        for e in self.point_entries:
            e.destroy()
        self.point_entries = []
        self.sequence.clear()
        self.sequence_status_var.set("Nenhum ponto definido.")
        self.execute_button.configure(state="disabled")

    def execute_analysis(self):
        try:
            points = [float(e.get().replace(",", ".")) for e in self.point_entries]
            assert points
        except (ValueError, AssertionError):
            messagebox.showerror("Pontos", "Todos os X precisam conter números.")
            return
        if not self.arduino or not self.arduino.is_connected:
            messagebox.showwarning("Análise", "Conecte o Arduino.")
            return
        if not self._apply_z_values(True):
            return
        self.sequence.set_points(points)
        self.analysis_running = True
        self.execute_button.configure(state="disabled")
        threading.Thread(target=self._analysis_worker, args=(points,), daemon=True).start()

    def _analysis_worker(self, points):
        try:
            current = self.machine.x.current_position_mm
            down = round(float(self.z_down_mm_var.get().replace(",", ".")) * self.machine.z.microsteps_per_mm)
            retract = round(float(self.z_retract_mm_var.get().replace(",", ".")) * self.machine.z.microsteps_per_mm)
            speed = int(self.z_speed_var.get())
            dwell = float(self.z_dwell_s_var.get().replace(",", "."))
            for i, target in enumerate(points, 1):
                # Coordenada de análise: os pontos são percorridos no sentido -X.
                steps = -round((target - current) * self.machine.x.microsteps_per_mm)
                if steps:
                    self.arduino.move_steps("X", steps, 500)
                # Convenção solicitada: Z+ desce, depois Z- sobe.
                self.arduino.z_approach(down, speed, retract)
                time.sleep(dwell)
                self.arduino.z_retract(retract, speed)
                self._apply_position_line(self.arduino.position())
                current = target
                self.root.after(0, lambda i=i, n=len(points): self._progress(i, n))
            self.root.after(0, lambda: self._finished(True, None))
        except Exception as e:
            try:
                self.arduino.stop()
            except Exception:
                pass
            self.root.after(0, lambda: self._finished(False, str(e)))

    def _progress(self, i, n):
        self.sequence_status_var.set(f"Ponto {i}/{n}")
        self.log_var.set(f"Ponto {i}/{n} concluído.")
        self.refresh_positions()

    def _finished(self, ok, error):
        self.analysis_running = False
        self.execute_button.configure(state="normal")
        self.sequence_status_var.set("Análise concluída." if ok else "Análise interrompida.")
        self.log_var.set("Análise executada." if ok else "Análise interrompida.")
        if not ok:
            messagebox.showerror("Análise", error or "Erro")

    def _calibration(self, p):
        ttk.Label(p, text="Calibração", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        a = ttk.LabelFrame(p, text=" Passos por milímetro ", padding=8)
        a.pack(fill="x", pady=12)
        for r, x in enumerate("XYZ"):
            ttk.Label(a, text=x, font=("Segoe UI", 10, "bold")).grid(row=r, column=0, padx=30, pady=7)
            ttk.Entry(a, textvariable=self.calibration_vars[x], width=19, font=("Segoe UI", 10)).grid(row=r, column=1, pady=7)
        z = ttk.LabelFrame(p, text=" Parâmetros do Z ", padding=8)
        z.pack(fill="x")
        fields = [
            ("Descida máxima (mm)", self.z_down_mm_var),
            ("Velocidade de descida (passos/s)", self.z_speed_var),
            ("Recuo após contato (mm)", self.z_retract_mm_var),
            ("Tempo de permanência embaixo (s)", self.z_dwell_s_var),
        ]
        for r, (label, var) in enumerate(fields):
            ttk.Label(z, text=label, font=("Segoe UI", 10)).grid(row=r, column=0, padx=12, pady=9, sticky="w")
            ttk.Entry(z, textvariable=var, width=19, font=("Segoe UI", 10)).grid(row=r, column=1, padx=12, pady=9)
        b = ttk.Frame(p)
        b.pack(pady=13)
        ttk.Button(b, text="Aplicar", command=self.apply_calibration).pack(side="left")
        ttk.Button(b, text="Salvar", command=self.save_calibration).pack(side="left", padx=8)
        ttk.Button(b, text="Recarregar", command=self._reload_calibration).pack(side="left")

    def _apply_z_values(self, show=False):
        try:
            d = float(self.z_down_mm_var.get().replace(",", "."))
            s = int(self.z_speed_var.get())
            r = float(self.z_retract_mm_var.get().replace(",", "."))
            t = float(self.z_dwell_s_var.get().replace(",", "."))
            assert d > 0 and s > 0 and r > 0 and t >= 0
            return True
        except (ValueError, AssertionError):
            if show:
                messagebox.showerror("Calibração", "Parâmetros do Z inválidos.")
            return False

    def apply_calibration(self):
        try:
            for a in "XYZ":
                v = float(self.calibration_vars[a].get().replace(",", "."))
                assert v > 0
                self.machine.get_axis(a).set_calibration(v)
            return self._apply_z_values(True)
        except (ValueError, AssertionError):
            messagebox.showerror("Calibração", "Passos/mm inválidos.")
            return False

    def save_calibration(self):
        if not self.apply_calibration():
            return
        d = {
            "axes_steps_per_mm": {a: self.machine.get_axis(a).microsteps_per_mm for a in "XYZ"},
            "z_approach": {
                "down_mm": float(self.z_down_mm_var.get().replace(",", ".")),
                "speed_steps_s": int(self.z_speed_var.get()),
                "retract_mm": float(self.z_retract_mm_var.get().replace(",", ".")),
                "dwell_s": float(self.z_dwell_s_var.get().replace(",", ".")),
            },
        }
        CONFIG_FILE.write_text(json.dumps(d, indent=2), encoding="utf-8")
        self.log_var.set("Calibração salva.")

    def _load_calibration(self):
        for a in "XYZ":
            self.calibration_vars[a].set(f"{self.machine.get_axis(a).microsteps_per_mm:.6f}")
        if not CONFIG_FILE.exists():
            return
        try:
            d = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            axes = d.get("axes_steps_per_mm", {})
            z = d.get("z_approach", {})
            for a in "XYZ":
                if a in axes:
                    self.machine.get_axis(a).set_calibration(float(axes[a]))
                    self.calibration_vars[a].set(str(axes[a]))
            if "down_mm" in z: self.z_down_mm_var.set(str(z["down_mm"]))
            if "speed_steps_s" in z: self.z_speed_var.set(str(z["speed_steps_s"]))
            if "retract_mm" in z: self.z_retract_mm_var.set(str(z["retract_mm"]))
            if "dwell_s" in z: self.z_dwell_s_var.set(str(z["dwell_s"]))
        except Exception:
            pass

    def _reload_calibration(self):
        self._load_calibration()
        self.log_var.set("Calibração recarregada.")

    def _terminal(self, p):
        ttk.Label(p, text="Terminal", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        self.terminal_history = tk.Text(p, font=("Consolas", 11), relief="flat")
        self.terminal_history.pack(fill="both", expand=True)
        line = tk.Frame(p)
        line.pack(fill="x", pady=9)
        self.terminal_prompt = tk.Label(line, text="»", font=("Consolas", 15, "bold"))
        self.terminal_prompt.pack(side="left")
        self.terminal_command = tk.Entry(line, font=("Consolas", 12))
        self.terminal_command.pack(side="left", fill="x", expand=True, ipady=6)
        self.terminal_command.bind("<Return>", lambda e: (self.send_terminal_command(), "break")[1])
        ttk.Button(line, text="Enviar", command=self.send_terminal_command).pack(side="left", padx=7)
        ttk.Button(line, text="Limpar", command=lambda: self.terminal_history.delete("1.0", tk.END)).pack(side="left")
        self._terminal_write("Terminal pronto.")

    def _terminal_write(self, text):
        self.terminal_history.insert(tk.END, text + "\n")
        self.terminal_history.see(tk.END)

    def send_terminal_command(self):
        command = self.terminal_command.get().strip()
        if not command:
            return
        self.terminal_command.delete(0, tk.END)
        self._terminal_write("» " + command)
        if not self.arduino or not self.arduino.is_connected:
            self._terminal_write("Arduino não conectado.")
            return
        try:
            self._terminal_write(self.arduino.send(command))
        except Exception as e:
            self._terminal_write("ERRO: " + str(e))

    def _poll_serial(self):
        if self.arduino and self.arduino.is_connected and not self.analysis_running:
            try:
                if time.monotonic() - self.last_pos_request > .25:
                    self.arduino.request_position()
                    self.last_pos_request = time.monotonic()
                for line in self.arduino.read_available():
                    if line.startswith("POS "):
                        self._apply_position_line(line)
                    else:
                        self._terminal_write(line)
            except Exception as e:
                self._terminal_write("SERIAL ERROR: " + str(e))
        self.root.after(100, self._poll_serial)

    def _apply_position_line(self, line):
        try:
            for token in line.split()[1:]:
                axis, raw = token.split("=")
                if axis in self.machine.axes:
                    self.machine.get_axis(axis).current_position_mm = int(raw) / self.machine.get_axis(axis).microsteps_per_mm
            self.refresh_positions()
        except (ValueError, IndexError):
            pass

    def refresh_positions(self):
        for a, value in self.machine.positions().items():
            self.position_vars[a].set(f"{value:.3f} mm")

    def _jog_press(self, axis, direction):
        if self.analysis_running:
            return
        if not self.arduino or not self.arduino.is_connected:
            self.log_var.set("Conecte o Arduino.")
            return
        try:
            speed = int(self.jog_speed_var.get())
            assert 1 <= speed <= 10000
        except (ValueError, AssertionError):
            messagebox.showerror("JOG", "Velocidade entre 1 e 10000 passos/s.")
            return
        self._send_jog_stop()
        self.jog_axis = axis
        self.jog_direction = direction
        self.arduino.jog_start(axis, direction, speed)
        self._schedule_jog_refresh()

    def _schedule_jog_refresh(self):
        if self.jog_axis is not None:
            self.jog_refresh_id = self.root.after(100, self._refresh_jog)

    def _refresh_jog(self):
        self.jog_refresh_id = None
        if self.jog_axis is None or not self.arduino or not self.arduino.is_connected:
            return
        try:
            self.arduino.jog_start(self.jog_axis, self.jog_direction, int(self.jog_speed_var.get()))
            self._schedule_jog_refresh()
        except Exception:
            self._send_jog_stop()

    def _jog_release(self, event=None):
        self._send_jog_stop()

    def _send_jog_stop(self):
        if self.jog_refresh_id:
            try: self.root.after_cancel(self.jog_refresh_id)
            except Exception: pass
            self.jog_refresh_id = None
        if self.arduino and self.arduino.is_connected:
            try: self.arduino.jog_stop()
            except Exception: pass
        self.jog_axis = None
        self.jog_direction = 0

    def stop(self):
        self._send_jog_stop()
        if self.arduino and self.arduino.is_connected:
            self.arduino.stop()
        self.log_var.set("STOP enviado.")

    def connect(self):
        if self.arduino and self.arduino.is_connected:
            return
        try:
            self.arduino = ArduinoController(self.port_var.get().strip())
            self.arduino.connect()
            self.status_var.set("Conectado — " + self.arduino.port)
            self.connect_button.configure(state="disabled")
        except Exception as e:
            self.status_var.set("Falha na conexão")
            messagebox.showerror("Arduino", str(e))

    def disconnect(self):
        self._send_jog_stop()
        if self.arduino:
            try: self.arduino.disconnect()
            except Exception: pass
        self.arduino = None
        self.status_var.set("Desconectado")
        self.connect_button.configure(state="normal")

    def zero(self):
        if not self.arduino or not self.arduino.is_connected:
            messagebox.showwarning("ZERO", "Conecte o Arduino primeiro.")
            return
        try:
            self.arduino.send("ZERO")
            self.machine.zero()
            self.refresh_positions()
        except Exception as e:
            messagebox.showerror("ZERO", str(e))

    def _colors(self):
        return self.DARK if self.dark_mode else self.LIGHT

    def toggle_dark_mode(self):
        self.dark_mode = not self.dark_mode
        self._apply_theme()

    def _apply_theme(self):
        c = self._colors()
        self.root.configure(bg=c["bg"])
        self.header.configure(bg=c["bg"])
        self.footer.configure(bg=c["bg"])
        self.footer_label.configure(bg=c["bg"], fg=c["accent"])
        self.footer_message.configure(bg=c["bg"], fg=c["text"])
        self.status_label.configure(bg=c["panel"], fg=c["accent"])
        self.stop_button.configure(bg=c["danger"], fg="white", activebackground=c["danger"], activeforeground="white")
        self.terminal_prompt.configure(bg=c["panel"], fg=c["accent"])
        self.terminal_history.configure(bg=c["field"], fg=c["text"], insertbackground=c["text"])
        self.terminal_command.configure(bg=c["field"], fg=c["text"], insertbackground=c["text"])
        self.style.configure(".", background=c["panel"], foreground=c["text"], fieldbackground=c["field"], font=("Segoe UI", 10))
        self.style.configure("TFrame", background=c["panel"])
        self.style.configure("TLabel", background=c["panel"], foreground=c["text"], font=("Segoe UI", 10))
        self.style.configure("TLabelframe", background=c["panel"], foreground=c["text"], bordercolor=c["border"])
        self.style.configure("TLabelframe.Label", background=c["panel"], foreground=c["text"], font=("Segoe UI", 10, "bold"))
        self.style.configure("TButton", background=c["panel"], foreground=c["text"], font=("Segoe UI", 10, "bold"), padding=(10, 6))
        self.style.map("TButton", background=[("active", c["field"])], foreground=[("active", c["text"])])
        self.style.configure("TNotebook", background=c["bg"], borderwidth=0)
        self.style.configure("TNotebook.Tab", background=c["field"], foreground=c["text"], padding=(14, 8), font=("Segoe UI", 10, "bold"))
        self.style.map("TNotebook.Tab", background=[("selected", c["panel"])], foreground=[("selected", c["text"])])

    def close(self):
        self._send_jog_stop()
        self.disconnect()
        self.root.destroy()


def main():
    root = tk.Tk()
    MainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()

from __future__ import annotations

import queue
import threading
import time
from typing import Optional


class ArduinoController:
    """Comunicação serial entre a GUI e o firmware do Arduino."""

    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 0.25):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self._serial: Optional[object] = None
        self._rx_queue: queue.Queue[str] = queue.Queue()
        self._reader_thread: threading.Thread | None = None
        self._reader_stop = threading.Event()

    @property
    def is_connected(self) -> bool:
        return bool(self._serial is not None and self._serial.is_open)

    def connect(self) -> None:
        try:
            import serial
        except ImportError as exc:
            raise RuntimeError("PySerial não está instalado. Execute: pip install -r requirements.txt") from exc
        if self.is_connected:
            return

        self._serial = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
        time.sleep(2.0)
        self._serial.reset_input_buffer()
        self._serial.reset_output_buffer()

        self._serial.write(b"PING\n")
        self._serial.flush()
        response = self._serial.readline().decode("ascii", errors="replace").strip()
        if response != "PONG":
            self._serial.close()
            self._serial = None
            raise RuntimeError(f"Arduino respondeu algo inesperado ao PING: {response!r}")

        self._reader_stop.clear()
        self._reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._reader_thread.start()

    def disconnect(self) -> None:
        if self._serial is None:
            return
        try:
            if self.is_connected:
                try:
                    self.send_nowait("JOG_STOP")
                    self.send_nowait("STOP")
                except Exception:
                    pass
                time.sleep(0.02)
        finally:
            self._reader_stop.set()
            if self._reader_thread is not None and self._reader_thread.is_alive():
                self._reader_thread.join(timeout=0.5)
            self._reader_thread = None
            try:
                if self._serial.is_open:
                    self._serial.close()
            finally:
                self._serial = None
            self._clear_rx_queue()

    def _clear_rx_queue(self) -> None:
        while True:
            try:
                self._rx_queue.get_nowait()
            except queue.Empty:
                return

    def _reader_loop(self) -> None:
        while not self._reader_stop.is_set():
            serial_port = self._serial
            if serial_port is None or not serial_port.is_open:
                return
            try:
                line = serial_port.readline()
            except Exception:
                return
            if line:
                text = line.decode("ascii", errors="replace").strip()
                if text:
                    self._rx_queue.put(text)

    def _write_line(self, command: str) -> None:
        command = command.strip()
        if not command:
            raise ValueError("Comando vazio.")
        if not self.is_connected:
            raise RuntimeError("Arduino não conectado.")
        self._serial.write((command + "\n").encode("ascii"))
        self._serial.flush()

    def send_nowait(self, command: str) -> None:
        self._write_line(command)

    def send(self, command: str) -> str:
        self._clear_rx_queue()
        self._write_line(command)
        deadline = time.monotonic() + max(self.timeout, 0.5)
        while time.monotonic() < deadline:
            try:
                return self._rx_queue.get(timeout=0.05)
            except queue.Empty:
                continue
        raise TimeoutError(f"Arduino não respondeu: {command.strip()}")

    def read_available(self) -> list[str]:
        lines: list[str] = []
        while True:
            try:
                lines.append(self._rx_queue.get_nowait())
            except queue.Empty:
                return lines

    def wait_for_motion(self, timeout_s: float = 120.0, ready_prefix: str | None = None) -> str:
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            try:
                line = self._rx_queue.get(timeout=0.05)
            except queue.Empty:
                continue
            if line.startswith("ERR"):
                raise RuntimeError(line)
            if line.startswith("LIMIT") or line.startswith("Z_DOWN_LIMIT") or line.startswith("Z_UP_LIMIT"):
                return line
            if ready_prefix and line.startswith(ready_prefix):
                return line
            if line.startswith("DONE"):
                return line
        raise TimeoutError("Arduino não concluiu o movimento dentro do tempo esperado.")

    def jog_start(self, axis: str, direction: int, speed_steps_s: int) -> None:
        axis = axis.upper()
        if axis not in {"X", "Y", "Z"}:
            raise ValueError("Eixo inválido. Use X, Y ou Z.")
        if speed_steps_s <= 0:
            raise ValueError("A velocidade deve ser positiva.")
        self.send_nowait(f"JOG_START {axis} {1 if direction > 0 else -1} {int(speed_steps_s)}")

    def jog_stop(self) -> None:
        if self.is_connected:
            self.send_nowait("JOG_STOP")

    def jog(self, axis: str, direction: int) -> None:
        self.jog_start(axis, direction, 200)

    def stop(self) -> None:
        if self.is_connected:
            self.send_nowait("JOG_STOP")
            self.send_nowait("STOP")

    def move_steps(self, axis: str, steps: int, speed_steps_s: int) -> None:
        axis = axis.upper()
        if axis not in {"X", "Y", "Z"}:
            raise ValueError("Eixo inválido. Use X, Y ou Z.")
        if speed_steps_s <= 0:
            raise ValueError("A velocidade deve ser positiva.")
        self._clear_rx_queue()
        self.send_nowait(f"MOVE {axis} {int(steps)} {int(speed_steps_s)}")
        result = self.wait_for_motion()
        if result.startswith(("LIMIT", "Z_DOWN_LIMIT", "Z_UP_LIMIT")):
            raise RuntimeError(result)

    def z_approach(self, steps: int, speed_steps_s: int, retract_steps: int, dwell_ms: int = 0) -> None:
        """Desce o Z usando o comando aceito pelo firmware atual.

        O firmware responde com Z_APPROACH_READY quando chega ao limite
        superior ou quando atinge o máximo de passos configurado.
        """
        if steps <= 0 or speed_steps_s <= 0 or retract_steps <= 0:
            raise ValueError("Parâmetros do Z inválidos.")
        self._clear_rx_queue()
        self.send_nowait(f"Z_APPROACH {int(steps)} {int(speed_steps_s)} {int(retract_steps)}")
        result = self.wait_for_motion(ready_prefix="Z_APPROACH_READY")
        if not result.startswith("Z_APPROACH_READY"):
            raise RuntimeError(result)

    def z_retract(self, steps: int, speed_steps_s: int) -> None:
        """Sobe o Z usando o comando aceito pelo firmware atual."""
        if steps <= 0 or speed_steps_s <= 0:
            raise ValueError("Parâmetros do Z inválidos.")
        self._clear_rx_queue()
        self.send_nowait(f"Z_RETRACT {int(steps)} {int(speed_steps_s)}")
        result = self.wait_for_motion()
        if result.startswith(("LIMIT", "Z_DOWN_LIMIT", "Z_UP_LIMIT")):
            raise RuntimeError(result)
        if not result.startswith("DONE"):
            raise RuntimeError(result)

    def request_position(self) -> None:
        if self.is_connected:
            self.send_nowait("POS")

    def ping(self) -> str:
        return self.send("PING")

    def status(self) -> str:
        return self.send("STATUS")

    def limits(self) -> str:
        return self.send("LIMITS")

    def position(self) -> str:
        return self.send("POS")

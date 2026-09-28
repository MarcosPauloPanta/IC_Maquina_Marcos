from __future__ import annotations

import queue
import threading
import time
from typing import Optional


class ArduinoController:
    """Camada de comunicação serial entre a GUI e o firmware do Arduino.

    A porta é aberta uma única vez. Um thread dedicado somente lê a serial
    e coloca as linhas recebidas em uma fila; a GUI apenas consulta essa fila.
    Isso evita que a leitura serial bloqueie o Tkinter e torna o Terminal
    adequado para respostas assíncronas do Arduino.
    """

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
            raise RuntimeError(
                "PySerial não está instalado. Execute: pip install -r requirements.txt"
            ) from exc

        if self.is_connected:
            return

        self._serial = serial.Serial(self.port, self.baudrate, timeout=self.timeout)

        # Abrir uma porta USB-serial com Arduino Uno normalmente reinicia a placa.
        # Esperamos o boot terminar e descartamos mensagens antigas antes do PING.
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
        self._reader_thread = threading.Thread(
            target=self._reader_loop,
            name="arduino-serial-reader",
            daemon=True,
        )
        self._reader_thread.start()

    def disconnect(self) -> None:
        if self._serial is None:
            return

        try:
            if self.is_connected:
                try:
                    self.send_nowait("STOP")
                    time.sleep(0.02)
                except Exception:
                    pass
        finally:
            self._reader_stop.set()
            thread = self._reader_thread
            self._reader_thread = None

            if thread is not None and thread.is_alive():
                thread.join(timeout=0.5)

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

            if not line:
                continue

            text = line.decode("ascii", errors="replace").strip()
            if text:
                self._rx_queue.put(text)

    def _write_line(self, command: str) -> str:
        line = command.strip()
        if not line:
            raise ValueError("Comando vazio.")
        if not self.is_connected:
            raise RuntimeError("Arduino não conectado.")
        self._serial.write((line + "\n").encode("ascii"))
        self._serial.flush()
        return line

    def send(self, command: str) -> str:
        """Envia um comando e espera a próxima resposta recebida."""
        self._clear_rx_queue()
        self._write_line(command)
        deadline = time.monotonic() + max(self.timeout, 0.5)

        while time.monotonic() < deadline:
            try:
                return self._rx_queue.get(timeout=0.05)
            except queue.Empty:
                continue

        raise TimeoutError(f"Arduino não respondeu ao comando: {command.strip()}")

    def send_nowait(self, command: str) -> None:
        """Envia o comando sem esperar resposta; o leitor captura a resposta."""
        self._write_line(command)

    def read_available(self) -> list[str]:
        """Retorna todas as linhas recebidas desde a última consulta da GUI."""
        lines: list[str] = []
        while True:
            try:
                lines.append(self._rx_queue.get_nowait())
            except queue.Empty:
                return lines

    def jog(self, axis: str, direction: int) -> None:
        axis = axis.upper()
        if axis not in {"X", "Y", "Z"}:
            raise ValueError("Eixo inválido. Use X, Y ou Z.")
        self.send_nowait(f"JOG {axis} {1 if direction > 0 else -1}")

    def stop(self) -> None:
        if self.is_connected:
            self.send_nowait("STOP")

    def ping(self) -> str:
        return self.send("PING")

    def status(self) -> str:
        return self.send("STATUS")

    def limits(self) -> str:
        return self.send("LIMITS")

    def position(self) -> str:
        return self.send("POS")

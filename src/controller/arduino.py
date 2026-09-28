from __future__ import annotations

import time
from typing import Optional


class ArduinoController:
    """Camada fina de comunicação serial com o Arduino.

    O protocolo é textual de propósito: fica fácil observar no monitor serial
    exatamente o que a GUI está pedindo ao firmware.
    """

    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 2.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self._serial: Optional[object] = None

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

    def disconnect(self) -> None:
        if self.is_connected:
            self.stop()
            self._serial.close()

    def send(self, command: str) -> str:
        if not self.is_connected:
            raise RuntimeError("Arduino não conectado.")
        line = command.strip()
        if not line:
            raise ValueError("Comando vazio.")
        self._serial.write((line + "\n").encode("ascii"))
        response = self._serial.readline().decode("ascii", errors="replace").strip()
        if not response:
            raise TimeoutError("Arduino não respondeu dentro do tempo limite.")
        return response

    def send_nowait(self, command: str) -> None:
        """Envia sem esperar resposta; usado para jog/STOP."""
        if not self.is_connected:
            raise RuntimeError("Arduino não conectado.")
        line = command.strip()
        self._serial.write((line + "\n").encode("ascii"))

    def jog(self, axis: str, direction: int) -> None:
        self.send_nowait(f"JOG {axis.upper()} {1 if direction > 0 else -1}")

    def stop(self) -> None:
        if self.is_connected:
            self.send_nowait("STOP")

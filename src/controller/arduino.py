from __future__ import annotations

import time
from typing import Optional


class ArduinoController:
    """Comunicação serial com o Arduino.

    Esta classe não conhece detalhes de X/Y/Z. Ela apenas envia comandos
    e recebe respostas. O protocolo exato pode ser adaptado ao firmware.
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
            raise RuntimeError(
                "PySerial não está instalado. Execute: pip install pyserial"
            ) from exc

        if self.is_connected:
            return

        self._serial = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            timeout=self.timeout,
        )
        time.sleep(2.0)

    def disconnect(self) -> None:
        if self._serial is not None and self._serial.is_open:
            self._serial.close()

    def send(self, command: str) -> str:
        """Envia uma linha e retorna a primeira resposta do Arduino."""
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

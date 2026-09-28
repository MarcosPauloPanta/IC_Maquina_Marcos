from __future__ import annotations

import time
from typing import Optional


class ArduinoController:
    """Camada de comunicação serial entre a GUI e o firmware do Arduino.

    O protocolo continua textual para facilitar testes e auditoria no terminal.
    Movimentos programados e JOG usam o protocolo já existente no firmware.
    """

    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 0.25):
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
                "PySerial não está instalado. Execute: pip install -r requirements.txt"
            ) from exc

        if self.is_connected:
            return

        self._serial = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
        # O Uno normalmente reinicia ao abrir a porta. Esperamos o boot e
        # descartamos mensagens antigas antes do primeiro comando.
        time.sleep(2.0)
        self._serial.reset_input_buffer()

        response = self.send("PING")
        if response != "PONG":
            self.disconnect()
            raise RuntimeError(f"Arduino respondeu algo inesperado ao PING: {response!r}")

    def disconnect(self) -> None:
        if self.is_connected:
            try:
                self.stop()
            except Exception:
                pass
            self._serial.close()
            self._serial = None

    def _write_line(self, command: str) -> str:
        line = command.strip()
        if not line:
            raise ValueError("Comando vazio.")
        self._serial.write((line + "\n").encode("ascii"))
        return line

    def send(self, command: str) -> str:
        """Envia um comando e espera uma resposta textual.

        Deve ser usado para comandos que possuem uma resposta única, como PING,
        STATUS, LIMITS, ZERO e comandos de diagnóstico.
        """
        if not self.is_connected:
            raise RuntimeError("Arduino não conectado.")

        line = self._write_line(command)
        response = self._serial.readline().decode("ascii", errors="replace").strip()
        if not response:
            raise TimeoutError(f"Arduino não respondeu ao comando: {line}")
        return response

    def send_nowait(self, command: str) -> None:
        """Envia sem bloquear esperando resposta.

        Usado principalmente por JOG e STOP, pois o firmware pode responder
        assincronamente enquanto a máquina está em movimento.
        """
        if not self.is_connected:
            raise RuntimeError("Arduino não conectado.")
        self._write_line(command)

    def read_available(self) -> list[str]:
        """Lê todas as linhas que já chegaram sem bloquear a GUI."""
        if not self.is_connected:
            return []

        lines: list[str] = []
        while self._serial.in_waiting:
            raw = self._serial.readline()
            if not raw:
                break
            text = raw.decode("ascii", errors="replace").strip()
            if text:
                lines.append(text)
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

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MeasurementPoint:
    """Um ponto de análise definido pela coordenada X."""

    x_mm: float
    label: str = ""


class PointSequence:
    """Planeja a sequência X -> descer Z -> tocar limite -> subir.

    A detecção física do botão Z é responsabilidade do firmware. A GUI apenas
    envia as etapas do protocolo e acompanha o estado da sequência.
    """

    def __init__(self) -> None:
        self.points: list[MeasurementPoint] = []
        self.index = -1

    def add(self, x_mm: float, label: str = "") -> None:
        self.points.append(MeasurementPoint(float(x_mm), label))

    def remove(self, index: int) -> None:
        del self.points[index]

    def clear(self) -> None:
        self.points.clear()
        self.index = -1

    def start(self) -> None:
        if not self.points:
            raise ValueError("Adicione pelo menos um ponto.")
        self.index = 0

    def current(self) -> MeasurementPoint | None:
        if 0 <= self.index < len(self.points):
            return self.points[self.index]
        return None

    def advance(self) -> bool:
        self.index += 1
        return self.index < len(self.points)

    @property
    def finished(self) -> bool:
        return self.index >= len(self.points) and bool(self.points)

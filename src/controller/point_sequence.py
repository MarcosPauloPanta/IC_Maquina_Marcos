from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MeasurementPoint:
    """Um ponto da análise. Somente X varia entre pontos; Y fica fixo."""

    x_mm: float


class PointSequence:
    """Sequência simples e ordenada de posições X."""

    def __init__(self) -> None:
        self.points: list[MeasurementPoint] = []
        self.index = -1

    def add(self, x_mm: float) -> None:
        self.points.append(MeasurementPoint(float(x_mm)))

    def set_points(self, positions_mm: list[float]) -> None:
        self.points = [MeasurementPoint(float(x)) for x in positions_mm]
        self.index = -1

    def remove(self, index: int) -> None:
        del self.points[index]
        if self.points and self.index >= len(self.points):
            self.index = len(self.points) - 1
        elif not self.points:
            self.index = -1

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
        return bool(self.points) and self.index >= len(self.points)

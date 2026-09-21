from __future__ import annotations

from dataclasses import dataclass, field

from src.controller.axis import Axis


@dataclass
class Machine:
    """Coordena os três eixos no modelo virtual."""

    x: Axis
    y: Axis
    z: Axis
    axes: dict[str, Axis] = field(init=False)

    def __post_init__(self) -> None:
        self.axes = {"X": self.x, "Y": self.y, "Z": self.z}

    def get_axis(self, name: str) -> Axis:
        key = name.upper()
        if key not in self.axes:
            raise ValueError(f"Eixo inválido: {name}. Use X, Y ou Z.")
        return self.axes[key]

    def move_to(self, axis: str, target_mm: float) -> dict:
        return self.get_axis(axis).move_to(target_mm)

    def zero(self, axis: str | None = None) -> None:
        if axis is None:
            for item in self.axes.values():
                item.current_position_mm = 0.0
            return
        self.get_axis(axis).current_position_mm = 0.0

    def positions(self) -> dict[str, float]:
        return {
            name: item.current_position_mm
            for name, item in self.axes.items()
        }

"""Modelo lógico da máquina. Agrupa os eixos X, Y e Z; não faz homing nem comprova posição física."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.controller.axis import Axis


@dataclass
## O QUE FAZ: Agrupa os eixos e permite consultar ou alterar suas posições lógicas.
class Machine:
    """Coordena os três eixos no modelo virtual."""

    x: Axis
    y: Axis
    z: Axis
    axes: dict[str, Axis] = field(init=False)

    ## O QUE FAZ: Cria o dicionário para encontrar cada eixo pelo nome.
    def __post_init__(self) -> None:
        self.axes = {"X": self.x, "Y": self.y, "Z": self.z}

    ## O QUE FAZ: Retorna um eixo válido pelo nome informado.
    def get_axis(self, name: str) -> Axis:
        key = name.upper()
        if key not in self.axes:
            raise ValueError(f"Eixo inválido: {name}. Use X, Y ou Z.")
        return self.axes[key]

    def move_to(self, axis: str, target_mm: float) -> dict:
        return self.get_axis(axis).move_to(target_mm)

    ## O QUE FAZ: Zera a posição lógica de um eixo ou de todos.
    def zero(self, axis: str | None = None) -> None:
        if axis is None:
            for item in self.axes.values():
                item.current_position_mm = 0.0
            return
        self.get_axis(axis).current_position_mm = 0.0

    ## O QUE FAZ: Devolve as posições lógicas atuais dos eixos.
    def positions(self) -> dict[str, float]:
        return {
            name: item.current_position_mm
            for name, item in self.axes.items()
        }

"""Testes automatizados da classe Machine. Eles verificam o modelo lógico, não o hardware."""

from src.controller.axis import Axis
from src.controller.machine import Machine


## O QUE FAZ: Cria uma máquina de teste com três eixos independentes.
def criar_maquina():
    return Machine(
        x=Axis(200, 16, 8),
        y=Axis(200, 16, 8),
        z=Axis(200, 16, 8),
    )


## O QUE FAZ: Confere que a máquina disponibiliza X, Y e Z pelo nome.
def test_maquina_expoe_tres_eixos():
    machine = criar_maquina()

    assert set(machine.axes) == {"X", "Y", "Z"}


## O QUE FAZ: Confere o encaminhamento de um movimento ao eixo solicitado.
def test_maquina_move_eixo():
    machine = criar_maquina()

    resultado = machine.move_to("X", 10)

    assert resultado["microsteps"] == 4000
    assert machine.positions()["X"] == 10


## O QUE FAZ: Confere que zerar um eixo não altera as posições lógicas dos demais.
def test_zero_de_um_eixo_nao_altera_os_outros():
    machine = criar_maquina()
    machine.move_to("X", 10)
    machine.move_to("Y", 5)

    machine.zero("X")

    assert machine.positions() == {"X": 0.0, "Y": 5, "Z": 0.0}

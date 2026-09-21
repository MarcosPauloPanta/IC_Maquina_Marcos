from src.controller.axis import Axis
from src.controller.machine import Machine


def criar_maquina():
    return Machine(
        x=Axis(200, 16, 8),
        y=Axis(200, 16, 8),
        z=Axis(200, 16, 8),
    )


def test_maquina_expoe_tres_eixos():
    machine = criar_maquina()

    assert set(machine.axes) == {"X", "Y", "Z"}


def test_maquina_move_eixo():
    machine = criar_maquina()

    resultado = machine.move_to("X", 10)

    assert resultado["microsteps"] == 4000
    assert machine.positions()["X"] == 10


def test_zero_de_um_eixo_nao_altera_os_outros():
    machine = criar_maquina()
    machine.move_to("X", 10)
    machine.move_to("Y", 5)

    machine.zero("X")

    assert machine.positions() == {"X": 0.0, "Y": 5, "Z": 0.0}

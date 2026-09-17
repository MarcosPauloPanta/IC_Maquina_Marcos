from src.controller.axis import Axis


def criar_eixo():
    return Axis(
        steps_per_revolution=200,
        microstepping=16,
        mm_per_revolution=8
    )


def test_movimento_positivo():
    axis = criar_eixo()

    resultado = axis.calculate_move(10)

    assert resultado["distance_mm"] == 10
    assert resultado["direction"] == 1
    assert resultado["microsteps"] == 4000
    assert resultado["theoretical_position_mm"] == 10


def test_movimento_negativo():
    axis = criar_eixo()
    axis.current_position_mm = 10

    resultado = axis.calculate_move(5)

    assert resultado["distance_mm"] == -5
    assert resultado["direction"] == -1
    assert resultado["microsteps"] == 2000
    assert resultado["theoretical_position_mm"] == 5


def test_eixo_parado():
    axis = criar_eixo()
    axis.current_position_mm = 10

    resultado = axis.calculate_move(10)

    assert resultado["distance_mm"] == 0
    assert resultado["direction"] == 0
    assert resultado["microsteps"] == 0
    assert resultado["theoretical_position_mm"] == 10


def test_movimento_para_posicao_negativa():
    axis = criar_eixo()

    resultado = axis.calculate_move(-5)

    assert resultado["distance_mm"] == -5
    assert resultado["direction"] == -1
    assert resultado["microsteps"] == 2000
    assert resultado["theoretical_position_mm"] == -5


def test_movimento_atualiza_posicao():
    axis = criar_eixo()

    resultado = axis.move_to(10)

    assert resultado["microsteps"] == 4000
    assert axis.current_position_mm == 10


def test_sequencia_de_movimentos():
    axis = criar_eixo()

    axis.move_to(10)

    assert axis.current_position_mm == 10

    resultado = axis.move_to(5)

    assert resultado["distance_mm"] == -5
    assert resultado["direction"] == -1
    assert resultado["microsteps"] == 2000
    assert axis.current_position_mm == 5
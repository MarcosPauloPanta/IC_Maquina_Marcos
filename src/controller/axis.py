from dataclasses import dataclass


@dataclass
class Axis:
    """
    Modelo matemático de um eixo da máquina.

    Não controla hardware.
    Não gera GPIO.
    Não movimenta motores.
    """

    steps_per_revolution: int
    microstepping: int
    mm_per_revolution: float
    current_position_mm: float = 0.0

    @property
    def microsteps_per_revolution(self) -> int:
        """
        Quantidade de microsteps necessários para uma
        revolução completa do motor.
        """
        return self.steps_per_revolution * self.microstepping

    @property
    def microsteps_per_mm(self) -> float:
        """
        Quantidade de microsteps necessária para deslocar
        o eixo em 1 mm.
        """
        return (
            self.microsteps_per_revolution
            / self.mm_per_revolution
        )

    def calculate_move(self, target_position_mm: float) -> dict:
        """
        Calcula o movimento necessário para alcançar
        uma posição desejada.

        Retorna apenas informações matemáticas.
        """

        distance_mm = (
            target_position_mm - self.current_position_mm
        )

        if distance_mm > 0:
            direction = 1
        elif distance_mm < 0:
            direction = -1
        else:
            direction = 0

        microsteps = round(
            abs(distance_mm) * self.microsteps_per_mm
        )

        theoretical_position_mm = (
            self.current_position_mm
            + direction
            * microsteps
            / self.microsteps_per_mm
        )

        return {
            "distance_mm": distance_mm,
            "direction": direction,
            "microsteps": microsteps,
            "theoretical_position_mm": theoretical_position_mm,
        }

    def move_to(self, target_position_mm: float) -> dict:

        """
        Calcula e executa, no modelo virtual, um movimento
        até a posição desejada.

        Não controla hardware.
        """

        movement = self.calculate_move(target_position_mm)

        self.current_position_mm = movement["theoretical_position_mm"]

        return movement
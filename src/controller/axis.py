from dataclasses import dataclass


@dataclass
class Axis:
    """Modelo matemático de um eixo.

    A classe converte distância em mm para microsteps. Ela não conhece
    Arduino, serial ou motores; isso mantém a matemática separada do hardware.
    """

    steps_per_revolution: int
    microstepping: int
    mm_per_revolution: float
    current_position_mm: float = 0.0
    calibrated_steps_per_mm: float | None = None

    @property
    def microsteps_per_revolution(self) -> int:
        return self.steps_per_revolution * self.microstepping

    @property
    def microsteps_per_mm(self) -> float:
        """Passos efetivos por mm; usa calibração quando fornecida."""
        if self.calibrated_steps_per_mm is not None:
            return self.calibrated_steps_per_mm
        return self.microsteps_per_revolution / self.mm_per_revolution

    def set_calibration(self, steps_per_mm: float) -> None:
        if steps_per_mm <= 0:
            raise ValueError("steps/mm deve ser maior que zero.")
        self.calibrated_steps_per_mm = float(steps_per_mm)

    def calculate_move(self, target_position_mm: float) -> dict:
        distance_mm = target_position_mm - self.current_position_mm
        direction = 1 if distance_mm > 0 else -1 if distance_mm < 0 else 0
        microsteps = round(abs(distance_mm) * self.microsteps_per_mm)
        theoretical_position_mm = (
            self.current_position_mm
            + direction * microsteps / self.microsteps_per_mm
        )
        return {
            "distance_mm": distance_mm,
            "direction": direction,
            "microsteps": microsteps,
            "theoretical_position_mm": theoretical_position_mm,
        }

    def move_to(self, target_position_mm: float) -> dict:
        movement = self.calculate_move(target_position_mm)
        self.current_position_mm = movement["theoretical_position_mm"]
        return movement

// ============================================================
// CONTROLADOR DE MOTORES - CNC SHIELD V3 + A4988 + Arduino Uno
// CONFIGURACAO ATUAL DO HARDWARE
// ============================================================
// Eixos fisicos:
//   X -> slot X
//   Y -> slot Y
//   Z -> slot Z
//
// PINAGEM CNC SHIELD V3:
//   X STEP = D2 | X DIR = D5
//   Y STEP = D3 | Y DIR = D6
//   Z STEP = D4 | Z DIR = D7
//   ENABLE = D8
//
// LIMITES FISICOS DO Z:
//   A1  = BOTAO DE CIMA
//   D11 = BOTAO DE BAIXO (HOLD)
//   BOTAO PRESSIONADO = HIGH
//
// CONVENCAO LOGICA DO PROJETO:
//   Z+ = DESCIDA
//   Z- = SUBIDA
//
// SEGURANCA:
//   1. Somente UM eixo pode se mover por vez.
//   2. STOP interrompe movimento.
//   3. JOG possui timeout (dead-man).
//   4. Limites do Z sao verificados antes de cada passo.
//   5. Drivers sao desligados apos periodo parado para reduzir aquecimento.
//
// PROTOCOLO:
//   PING
//   STATUS
//   LIMITS
//   POS
//   ZERO [X|Y|Z]
//   MOVE X|Y|Z +/-steps speed
//   JOG_START X|Y|Z +/-1 speed
//   JOG_STOP
//   STOP
//   Z_APPROACH down_steps speed retract_steps
//   Z_RETRACT steps speed
// ============================================================

const unsigned long BAUD_RATE = 115200;

const uint8_t X_STEP = 2;
const uint8_t X_DIR  = 5;
const uint8_t Y_STEP = 3;
const uint8_t Y_DIR  = 6;
const uint8_t Z_STEP = 4;
const uint8_t Z_DIR  = 7;
const uint8_t ENABLE_PIN = 8;

const uint8_t Z_TOP_BUTTON = A1;
const uint8_t Z_BOTTOM_BUTTON = 11;
const uint8_t LIMIT_ACTIVE_LEVEL = HIGH;

const unsigned int STEP_PULSE_US = 5;
const unsigned long JOG_TIMEOUT_MS = 300;
const unsigned long IDLE_DISABLE_MS = 2000;
const unsigned int ENABLE_SETTLE_MS = 2;

const long X_MIN_STEPS = -10000;
const long X_MAX_STEPS = 10000;
const long Y_MIN_STEPS = -10000;
const long Y_MAX_STEPS = 10000;

enum MotionMode {
  IDLE,
  NORMAL_MOVE,
  CONTINUOUS_JOG,
  Z_APPROACH_DOWN,
  Z_RETRACT
};

MotionMode mode = IDLE;
char moving_axis = 'X';
int moving_direction = 1;
long remaining_steps = 0;
unsigned long moving_speed_sps = 500;
unsigned long last_jog_ms = 0;
unsigned long last_activity_ms = 0;
long position_steps[3] = {0, 0, 0};
bool drivers_enabled = false;
String input_line;

uint8_t stepPin(char axis) {
  if (axis == 'X') return X_STEP;
  if (axis == 'Y') return Y_STEP;
  return Z_STEP;
}

uint8_t dirPin(char axis) {
  if (axis == 'X') return X_DIR;
  if (axis == 'Y') return Y_DIR;
  return Z_DIR;
}

uint8_t axisIndex(char axis) {
  if (axis == 'X') return 0;
  if (axis == 'Y') return 1;
  return 2;
}

bool validAxis(char axis) {
  return axis == 'X' || axis == 'Y' || axis == 'Z';
}

bool zTopPressed() {
  return digitalRead(Z_TOP_BUTTON) == LIMIT_ACTIVE_LEVEL;
}

bool zBottomPressed() {
  return digitalRead(Z_BOTTOM_BUTTON) == LIMIT_ACTIVE_LEVEL;
}

bool validSpeed(long speed) {
  return speed >= 1 && speed <= 10000;
}

unsigned long intervalUs(unsigned long speed) {
  unsigned long value = 1000000UL / max(1UL, speed);
  if (value < STEP_PULSE_US + 2) value = STEP_PULSE_US + 2;
  return value;
}

void enableDrivers() {
  last_activity_ms = millis();
  if (drivers_enabled) return;
  digitalWrite(ENABLE_PIN, LOW);
  drivers_enabled = true;
  delay(ENABLE_SETTLE_MS);
}

void disableDrivers() {
  digitalWrite(ENABLE_PIN, HIGH);
  drivers_enabled = false;
}

void pulseStep(char axis, unsigned long speed) {
  unsigned long interval = intervalUs(speed);
  digitalWrite(stepPin(axis), HIGH);
  delayMicroseconds(STEP_PULSE_US);
  digitalWrite(stepPin(axis), LOW);
  unsigned long rest = interval - STEP_PULSE_US;
  if (rest > 0) delayMicroseconds(rest);
}

bool softLimitBlocks(char axis, int direction) {
  if (axis != 'X' && axis != 'Y') return false;
  long pos = position_steps[axisIndex(axis)];
  long minimum = axis == 'X' ? X_MIN_STEPS : Y_MIN_STEPS;
  long maximum = axis == 'X' ? X_MAX_STEPS : Y_MAX_STEPS;
  return (direction < 0 && pos <= minimum) ||
         (direction > 0 && pos >= maximum);
}

// Z+ = DESCIDA / Z- = SUBIDA.
// Se o sentido mecanico do motor estiver invertido, altere SOMENTE
// os dois niveis abaixo. Os botoes nao devem ser trocados por isso.
void setDirection(char axis, int direction) {
  digitalWrite(dirPin(axis), direction > 0 ? HIGH : LOW);
  delayMicroseconds(10);
}

bool zLimitBlocks(int direction) {
  // Z+ = descida: botao de cima limita essa direcao.
  if (direction > 0) return zTopPressed();

  // Z- = subida: botao de baixo limita essa direcao.
  return zBottomPressed();
}

void stopMotion() {
  mode = IDLE;
  remaining_steps = 0;
  last_activity_ms = millis();
}

void printPosition() {
  Serial.print(F("POS X=")); Serial.print(position_steps[0]);
  Serial.print(F(" Y=")); Serial.print(position_steps[1]);
  Serial.print(F(" Z=")); Serial.println(position_steps[2]);
}

void printLimits() {
  Serial.print(F("LIMITS TOP="));
  Serial.print(zTopPressed() ? F("PRESSED") : F("FREE"));
  Serial.print(F(" BOTTOM="));
  Serial.print(zBottomPressed() ? F("PRESSED") : F("FREE"));
  Serial.print(F(" RAW_TOP=")); Serial.print(digitalRead(Z_TOP_BUTTON));
  Serial.print(F(" RAW_BOTTOM=")); Serial.println(digitalRead(Z_BOTTOM_BUTTON));
}

void startMove(char axis, long signedSteps, unsigned long speed) {
  if (!validAxis(axis) || signedSteps == 0 || !validSpeed((long)speed)) {
    Serial.println(F("ERR BAD_MOVE")); return;
  }
  if (mode != IDLE) { Serial.println(F("ERR BUSY")); return; }

  int direction = signedSteps > 0 ? 1 : -1;
  long steps = signedSteps > 0 ? signedSteps : -signedSteps;

  if ((axis == 'Z' && zLimitBlocks(direction)) ||
      softLimitBlocks(axis, direction)) {
    Serial.println(F("LIMIT")); return;
  }

  enableDrivers();
  setDirection(axis, direction);
  moving_axis = axis;
  moving_direction = direction;
  remaining_steps = steps;
  moving_speed_sps = speed;
  mode = NORMAL_MOVE;
  Serial.println(F("ACK MOVE"));
}

void startJog(char axis, int direction, unsigned long speed) {
  if (!validAxis(axis) || !validSpeed((long)speed) ||
      (direction != 1 && direction != -1)) {
    Serial.println(F("ERR BAD_JOG")); return;
  }

  if (mode != IDLE) {
    if (mode == CONTINUOUS_JOG && axis == moving_axis &&
        direction == moving_direction) {
      moving_speed_sps = speed;
      last_jog_ms = millis();
      return;
    }
    Serial.println(F("ERR BUSY")); return;
  }

  if ((axis == 'Z' && zLimitBlocks(direction)) ||
      softLimitBlocks(axis, direction)) {
    Serial.println(F("LIMIT")); return;
  }

  enableDrivers();
  setDirection(axis, direction);
  moving_axis = axis;
  moving_direction = direction;
  moving_speed_sps = speed;
  last_jog_ms = millis();
  mode = CONTINUOUS_JOG;
  Serial.println(F("ACK JOG"));
}

void startZApproach(long downSteps, unsigned long speed, long retractSteps) {
  if (downSteps <= 0 || retractSteps <= 0 || !validSpeed((long)speed)) {
    Serial.println(F("ERR BAD_Z_APPROACH")); return;
  }
  if (mode != IDLE) { Serial.println(F("ERR BUSY")); return; }

  if (zTopPressed()) {
    Serial.println(F("Z_APPROACH_READY LIMIT_TOP")); return;
  }

  enableDrivers();
  moving_axis = 'Z';
  moving_direction = 1;
  moving_speed_sps = speed;
  remaining_steps = downSteps;
  setDirection('Z', 1);
  mode = Z_APPROACH_DOWN;
  Serial.println(F("ACK Z_APPROACH"));
}

void startZRetract(long steps, unsigned long speed) {
  if (steps <= 0 || !validSpeed((long)speed)) {
    Serial.println(F("ERR BAD_Z_RETRACT")); return;
  }
  if (mode != IDLE) { Serial.println(F("ERR BUSY")); return; }
  if (zBottomPressed()) { Serial.println(F("LIMIT Z_BOTTOM")); return; }

  enableDrivers();
  moving_axis = 'Z';
  moving_direction = -1;
  moving_speed_sps = speed;
  remaining_steps = steps;
  setDirection('Z', -1);
  mode = Z_RETRACT;
  Serial.println(F("ACK Z_RETRACT"));
}

void executeMotion() {
  if (mode == IDLE) return;

  if (mode == CONTINUOUS_JOG) {
    if (millis() - last_jog_ms > JOG_TIMEOUT_MS) {
      stopMotion();
      Serial.println(F("JOG_TIMEOUT"));
      return;
    }

    if ((moving_axis == 'Z' && zLimitBlocks(moving_direction)) ||
        softLimitBlocks(moving_axis, moving_direction)) {
      stopMotion();
      Serial.println(F("LIMIT"));
      return;
    }

    pulseStep(moving_axis, moving_speed_sps);
    position_steps[axisIndex(moving_axis)] += moving_direction;
    return;
  }

  if ((moving_axis == 'Z' && zLimitBlocks(moving_direction)) ||
      softLimitBlocks(moving_axis, moving_direction)) {
    stopMotion();
    Serial.println(mode == Z_APPROACH_DOWN ? F("Z_APPROACH_READY LIMIT") : F("LIMIT"));
    return;
  }

  pulseStep(moving_axis, moving_speed_sps);
  position_steps[axisIndex(moving_axis)] += moving_direction;
  remaining_steps--;

  if (remaining_steps <= 0) {
    if (mode == Z_APPROACH_DOWN) {
      stopMotion();
      Serial.println(F("Z_APPROACH_READY MAX_STEPS"));
    } else if (mode == Z_RETRACT) {
      stopMotion();
      Serial.println(F("DONE Z_RETRACT"));
    } else {
      stopMotion();
      Serial.println(F("DONE"));
    }
  }
}

void zeroAxis(char axis) {
  if (axis == 'X') position_steps[0] = 0;
  else if (axis == 'Y') position_steps[1] = 0;
  else if (axis == 'Z') position_steps[2] = 0;
}

void handleCommand(String line) {
  line.trim();
  if (!line.length()) return;

  char buffer[100];
  line.toCharArray(buffer, sizeof(buffer));
  char* cmd = strtok(buffer, " \t");
  if (!cmd) return;

  if (!strcmp(cmd, "PING")) { Serial.println(F("PONG")); return; }

  if (!strcmp(cmd, "STATUS")) {
    Serial.print(F("STATUS MODE=")); Serial.println((int)mode); return;
  }

  if (!strcmp(cmd, "LIMITS")) { printLimits(); return; }
  if (!strcmp(cmd, "POS")) { printPosition(); return; }

  if (!strcmp(cmd, "ZERO")) {
    char* a = strtok(NULL, " \t");
    if (a && validAxis(a[0])) zeroAxis(a[0]);
    else if (!a) {
      position_steps[0] = 0;
      position_steps[1] = 0;
      position_steps[2] = 0;
    } else {
      Serial.println(F("ERR BAD_AXIS")); return;
    }
    Serial.println(F("OK ZERO")); return;
  }

  if (!strcmp(cmd, "MOVE")) {
    char* a = strtok(NULL, " \t");
    char* d = strtok(NULL, " \t");
    char* v = strtok(NULL, " \t");
    if (!a || !d || !v || !validAxis(a[0])) {
      Serial.println(F("ERR BAD_MOVE")); return;
    }
    startMove(a[0], atol(d), atol(v));
    return;
  }

  if (!strcmp(cmd, "JOG_START")) {
    char* a = strtok(NULL, " \t");
    char* d = strtok(NULL, " \t");
    char* v = strtok(NULL, " \t");
    if (!a || !d || !v || !validAxis(a[0])) {
      Serial.println(F("ERR BAD_JOG")); return;
    }
    long dValue = atol(d);
    if (dValue != 1 && dValue != -1) {
      Serial.println(F("ERR BAD_JOG_DIRECTION")); return;
    }
    startJog(a[0], (int)dValue, atol(v));
    return;
  }

  if (!strcmp(cmd, "JOG_STOP")) {
    if (mode == CONTINUOUS_JOG) stopMotion();
    Serial.println(F("OK JOG_STOP")); return;
  }

  if (!strcmp(cmd, "STOP")) {
    stopMotion();
    Serial.println(F("OK STOP")); return;
  }

  if (!strcmp(cmd, "Z_APPROACH")) {
    char* d = strtok(NULL, " \t");
    char* v = strtok(NULL, " \t");
    char* r = strtok(NULL, " \t");
    if (!d || !v || !r) {
      Serial.println(F("ERR BAD_Z_APPROACH")); return;
    }
    startZApproach(atol(d), atol(v), atol(r));
    return;
  }

  if (!strcmp(cmd, "Z_RETRACT")) {
    char* s = strtok(NULL, " \t");
    char* v = strtok(NULL, " \t");
    if (!s || !v) {
      Serial.println(F("ERR BAD_Z_RETRACT")); return;
    }
    startZRetract(atol(s), atol(v));
    return;
  }

  Serial.println(F("ERR UNKNOWN_COMMAND"));
}

void readSerial() {
  while (Serial.available() > 0) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      if (input_line.length() > 0) {
        handleCommand(input_line);
        input_line = "";
      }
    } else if (input_line.length() < 95) {
      input_line += c;
    } else {
      input_line = "";
      Serial.println(F("ERR LINE_TOO_LONG"));
    }
  }
}

void setup() {
  pinMode(X_STEP, OUTPUT);
  pinMode(X_DIR, OUTPUT);
  pinMode(Y_STEP, OUTPUT);
  pinMode(Y_DIR, OUTPUT);
  pinMode(Z_STEP, OUTPUT);
  pinMode(Z_DIR, OUTPUT);
  pinMode(ENABLE_PIN, OUTPUT);

  // Os botoes fornecem HIGH quando pressionados.
  pinMode(Z_TOP_BUTTON, INPUT);
  pinMode(Z_BOTTOM_BUTTON, INPUT);

  digitalWrite(X_STEP, LOW);
  digitalWrite(Y_STEP, LOW);
  digitalWrite(Z_STEP, LOW);
  digitalWrite(X_DIR, LOW);
  digitalWrite(Y_DIR, LOW);
  digitalWrite(Z_DIR, LOW);

  // Drivers inicialmente habilitados para compatibilidade com testes.
  digitalWrite(ENABLE_PIN, LOW);
  drivers_enabled = true;
  last_activity_ms = millis();

  Serial.begin(BAUD_RATE);
  Serial.println(F("Arduino pronto."));
  Serial.println(F("Z fisico = SLOT Z (D4/D7)."));
  Serial.println(F("TOP=A1 | BOTTOM=D11 | PRESSED=HIGH"));
  Serial.println(F("Z+ = DESCIDA | Z- = SUBIDA"));
  Serial.println(F("Comandos: PING, STATUS, LIMITS, POS, MOVE, JOG_START, JOG_STOP, STOP, Z_APPROACH, Z_RETRACT"));
}

void loop() {
  readSerial();
  executeMotion();

  if (mode == IDLE && drivers_enabled &&
      millis() - last_activity_ms >= IDLE_DISABLE_MS) {
    disableDrivers();
  }
}

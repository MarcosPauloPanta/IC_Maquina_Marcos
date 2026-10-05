// ============================================================
// CONTROLADOR DE MOTORES — CNC Shield V3 + A4988 + Arduino Uno
// VERSÃO: EIXO Z FÍSICO USANDO O SLOT A
// ============================================================
// Regras de segurança:
//   1. Somente UM eixo pode estar em movimento por vez.
//   2. STOP interrompe qualquer movimento.
//   3. JOG possui timeout (dead-man): sem renovação, para sozinho.
//   4. Os dois botões continuam sendo limites físicos do eixo Z.
//   5. Os drivers são desabilitados após período parado para reduzir calor.
//
// PINAGEM CNC SHIELD V3:
//   X STEP = D2 | X DIR = D5
//   Y STEP = D3 | Y DIR = D6
//   A STEP = D12| A DIR = D13   <-- MOTOR Z FÍSICO
//   ENABLE = D8
//
// BOTÕES:
//   A1  = botão de CIMA
//   D11 = botão de BAIXO
//   LIMIT_ACTIVE_LEVEL = HIGH
//
// IMPORTANTE:
//   O motor que antes estava no slot Z deve ser conectado ao SLOT A.
//   O driver correspondente também deve estar no SLOT A.
//
// A GUI continua trabalhando com o nome lógico Z.
// O Arduino traduz Z -> slot A internamente.
// ============================================================

const unsigned long BAUD_RATE = 115200;

// -------------------------
// X / Y
// -------------------------
const uint8_t X_STEP = 2;
const uint8_t X_DIR  = 5;

const uint8_t Y_STEP = 3;
const uint8_t Y_DIR  = 6;

// -------------------------
// Z lógico -> SLOT A físico
// -------------------------
const uint8_t Z_STEP = 12;   // A STEP
const uint8_t Z_DIR  = 13;   // A DIR

const uint8_t ENABLE_PIN = 8;

// -------------------------
// Limites físicos do Z
// -------------------------
const uint8_t Z_TOP_BUTTON    = A1;
const uint8_t Z_BOTTOM_BUTTON = 11;

// Botão pressionado = HIGH.
const uint8_t LIMIT_ACTIVE_LEVEL = HIGH;

// -------------------------
// Temporização
// -------------------------
const unsigned int STEP_PULSE_US = 5;
const unsigned long JOG_TIMEOUT_MS = 300;
const unsigned long IDLE_DISABLE_MS = 2000;
const unsigned int ENABLE_SETTLE_MS = 2;

// -------------------------
// Limites de software X/Y
// -------------------------
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

// Posição lógica continua sendo X/Y/Z.
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
  return (direction < 0 && pos <= minimum) || (direction > 0 && pos >= maximum);
}

// Convenção lógica do projeto:
//   Z+ = DESCIDA
//   Z- = SUBIDA
//
// O sentido elétrico do slot A pode ser invertido sem alterar os botões.
// Neste primeiro teste usamos a mesma convenção lógica do código anterior:
//   Z+ -> DIR HIGH
//   Z- -> DIR LOW
//
// Se o teste físico no slot A mostrar o sentido mecânico invertido,
// basta inverter os dois níveis nesta função — não mexer nos botões.
void setDirection(char axis, int direction) {
  digitalWrite(dirPin(axis), direction > 0 ? HIGH : LOW);
  delayMicroseconds(10);
}

bool zLimitBlocks(int direction) {
  // Z+ = descida -> botão de cima interrompe
  if (direction > 0) return zTopPressed();

  // Z- = subida -> botão de baixo interrompe
  return zBottomPressed();
}

void stopMotion() {
  mode = IDLE;
  remaining_steps = 0;
  last_activity_ms = millis();
}

void printPosition() {
  Serial.print(F("POS X="));
  Serial.print(position_steps[0]);
  Serial.print(F(" Y="));
  Serial.print(position_steps[1]);
  Serial.print(F(" Z="));
  Serial.println(position_steps[2]);
}

void printLimits() {
  Serial.print(F("LIMITS TOP="));
  Serial.print(zTopPressed() ? F("PRESSED") : F("FREE"));
  Serial.print(F(" BOTTOM="));
  Serial.print(zBottomPressed() ? F("PRESSED") : F("FREE"));
  Serial.print(F(" RAW_TOP="));
  Serial.print(digitalRead(Z_TOP_BUTTON));
  Serial.print(F(" RAW_BOTTOM="));
  Serial.println(digitalRead(Z_BOTTOM_BUTTON));
}

void startMove(char axis, long signedSteps, unsigned long speed) {
  if (!validAxis(axis) || signedSteps == 0 || !validSpeed((long)speed)) {
    Serial.println(F("ERR BAD_MOVE"));
    return;
  }

  if (mode != IDLE) {
    Serial.println(F("ERR BUSY"));
    return;
  }

  int direction = signedSteps > 0 ? 1 : -1;
  long steps = signedSteps > 0 ? signedSteps : -signedSteps;

  if (axis == 'Z' && zLimitBlocks(direction)) {
    Serial.println(F("LIMIT"));
    return;
  }

  if (softLimitBlocks(axis, direction)) {
    Serial.println(F("LIMIT_SOFT"));
    return;
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
  if (!validAxis(axis) || !validSpeed((long)speed) || (direction != 1 && direction != -1)) {
    Serial.println(F("ERR BAD_JOG"));
    return;
  }

  if (mode != IDLE) {
    if (mode == CONTINUOUS_JOG && axis == moving_axis && direction == moving_direction) {
      moving_speed_sps = speed;
      last_jog_ms = millis();
      return;
    }
    Serial.println(F("ERR BUSY"));
    return;
  }

  if ((axis == 'Z' && zLimitBlocks(direction)) || softLimitBlocks(axis, direction)) {
    Serial.println(F("LIMIT"));
    return;
  }

  enableDrivers();
  setDirection(axis, direction);

  moving_axis = axis;
  moving_direction = direction;
  moving_speed_sps = speed;
  last_jog_ms = millis();
  mode = CONTINUOUS_JOG;
}

void startZApproach(long downSteps, unsigned long speed, long retractSteps) {
  if (downSteps <= 0 || retractSteps <= 0 || !validSpeed((long)speed)) {
    Serial.println(F("ERR BAD_Z_APPROACH"));
    return;
  }

  if (mode != IDLE) {
    Serial.println(F("ERR BUSY"));
    return;
  }

  enableDrivers();
  moving_axis = 'Z';
  moving_direction = 1; // Z+ = descida
  moving_speed_sps = speed;
  remaining_steps = downSteps;
  (void)retractSteps;

  setDirection('Z', +1);

  if (zTopPressed()) {
    remaining_steps = 0;
    stopMotion();
    Serial.println(F("Z_APPROACH_READY LIMIT_TOP"));
    return;
  }

  mode = Z_APPROACH_DOWN;
  Serial.println(F("ACK Z_APPROACH"));
}

void startZRetract(long steps, unsigned long speed) {
  if (steps <= 0 || !validSpeed((long)speed)) {
    Serial.println(F("ERR BAD_Z_RETRACT"));
    return;
  }

  if (mode != IDLE) {
    Serial.println(F("ERR BUSY"));
    return;
  }

  if (zBottomPressed()) {
    Serial.println(F("LIMIT Z_BOTTOM"));
    return;
  }

  enableDrivers();
  moving_axis = 'Z';
  moving_direction = -1; // Z- = subida
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
    if (mode == Z_APPROACH_DOWN) {
      stopMotion();
      Serial.println(F("Z_APPROACH_READY LIMIT"));
    } else {
      stopMotion();
      Serial.println(F("LIMIT"));
    }
    return;
  }

  pulseStep(moving_axis, moving_speed_sps);
  position_steps[axisIndex(moving_axis)] += moving_direction;
  remaining_steps--;

  if (remaining_steps <= 0) {
    if (mode == Z_APPROACH_DOWN) {
      stopMotion();
      Serial.println(F("Z_APPROACH_READY MAX_STEPS"));
      return;
    }

    if (mode == Z_RETRACT) {
      stopMotion();
      Serial.println(F("DONE Z_RETRACT"));
      return;
    }

    stopMotion();
    Serial.println(F("DONE"));
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

  if (!strcmp(cmd, "PING")) {
    Serial.println(F("PONG"));
    return;
  }

  if (!strcmp(cmd, "STATUS")) {
    Serial.print(F("STATUS MODE="));
    Serial.println((int)mode);
    return;
  }

  if (!strcmp(cmd, "LIMITS")) {
    printLimits();
    return;
  }

  if (!strcmp(cmd, "POS")) {
    printPosition();
    return;
  }

  if (!strcmp(cmd, "ZERO")) {
    char* a = strtok(NULL, " \t");
    if (a && validAxis(a[0])) {
      zeroAxis(a[0]);
    } else if (!a) {
      position_steps[0] = 0;
      position_steps[1] = 0;
      position_steps[2] = 0;
    } else {
      Serial.println(F("ERR BAD_AXIS"));
      return;
    }
    Serial.println(F("OK ZERO"));
    return;
  }

  // MOVE Z 1 1000 = Z+ (descida)
  // MOVE Z -1 1000 = Z- (subida)
  if (!strcmp(cmd, "MOVE")) {
    char* a = strtok(NULL, " \t");
    char* d = strtok(NULL, " \t");
    char* v = strtok(NULL, " \t");

    if (!a || !d || !v || !validAxis(a[0])) {
      Serial.println(F("ERR BAD_MOVE"));
      return;
    }

    startMove(a[0], atol(d) * 1L, atol(v));
    return;
  }

  if (!strcmp(cmd, "JOG_START")) {
    char* a = strtok(NULL, " \t");
    char* d = strtok(NULL, " \t");
    char* v = strtok(NULL, " \t");

    if (!a || !d || !v || !validAxis(a[0])) {
      Serial.println(F("ERR BAD_JOG"));
      return;
    }

    startJog(a[0], atol(d) >= 0 ? 1 : -1, atol(v));
    return;
  }

  if (!strcmp(cmd, "JOG_STOP")) {
    if (mode == CONTINUOUS_JOG) stopMotion();
    Serial.println(F("OK JOG_STOP"));
    return;
  }

  if (!strcmp(cmd, "STOP")) {
    stopMotion();
    Serial.println(F("OK STOP"));
    return;
  }

  if (!strcmp(cmd, "Z_APPROACH")) {
    char* d = strtok(NULL, " \t");
    char* v = strtok(NULL, " \t");
    char* r = strtok(NULL, " \t");

    if (!d || !v || !r) {
      Serial.println(F("ERR BAD_Z_APPROACH"));
      return;
    }

    startZApproach(atol(d), atol(v), atol(r));
    return;
  }

  if (!strcmp(cmd, "Z_RETRACT")) {
    char* s = strtok(NULL, " \t");
    char* v = strtok(NULL, " \t");

    if (!s || !v) {
      Serial.println(F("ERR BAD_Z_RETRACT"));
      return;
    }

    startZRetract(atol(s), atol(v));
    return;
  }

  if (!strcmp(cmd, "HELP")) {
    Serial.println(F("PING STATUS LIMITS POS ZERO MOVE JOG_START JOG_STOP STOP Z_APPROACH Z_RETRACT"));
    return;
  }

  Serial.println(F("ERR UNKNOWN_COMMAND"));
}

void setup() {
  // Começa com os drivers DESABILITADOS.
  digitalWrite(ENABLE_PIN, HIGH);
  pinMode(ENABLE_PIN, OUTPUT);
  digitalWrite(ENABLE_PIN, HIGH);

  pinMode(X_STEP, OUTPUT);
  pinMode(X_DIR, OUTPUT);
  pinMode(Y_STEP, OUTPUT);
  pinMode(Y_DIR, OUTPUT);
  pinMode(Z_STEP, OUTPUT);
  pinMode(Z_DIR, OUTPUT);

  pinMode(Z_TOP_BUTTON, INPUT);
  pinMode(Z_BOTTOM_BUTTON, INPUT);

  digitalWrite(X_STEP, LOW);
  digitalWrite(Y_STEP, LOW);
  digitalWrite(Z_STEP, LOW);

  digitalWrite(X_DIR, LOW);
  digitalWrite(Y_DIR, LOW);
  digitalWrite(Z_DIR, LOW);

  Serial.begin(BAUD_RATE);
  input_line.reserve(96);
  Serial.println(F("READY"));
  Serial.println(F("Z LOGICO -> SLOT A: STEP=D12 DIR=D13"));
  Serial.println(F("BOTAO CIMA=A1 | BOTAO BAIXO=D11 | ATIVO=HIGH"));
}

void loop() {
  while (Serial.available()) {
    char c = Serial.read();

    if (c == '\n' || c == '\r') {
      if (input_line.length()) {
        handleCommand(input_line);
        input_line = "";
      }
    } else if (input_line.length() < 95) {
      input_line += c;
    }
  }

  executeMotion();

  if (mode == IDLE && drivers_enabled &&
      millis() - last_activity_ms >= IDLE_DISABLE_MS) {
    disableDrivers();
  }
}

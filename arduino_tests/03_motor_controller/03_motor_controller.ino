// TESTE 03 — CONTROLADOR REAL DOS MOTORES
// CNC Shield V3 + A4988
//
// Pinos padrão da CNC Shield V3:
// X: STEP D2 / DIR D5
// Y: STEP D3 / DIR D6
// Z: STEP D4 / DIR D7
// ENABLE: D8 (LOW = habilitado)
//
// Botões de proteção usados no projeto:
// BOTÃO DE CIMA    = A1
// BOTÃO DE BAIXO   = D11
// Ambos são tratados como INPUT_PULLUP: pressionado = LOW.
//
// Protocolo serial em 115200 baud:
// PING
// STATUS
// MOVE X 1 1000
// JOG Z -1
// STOP
// SEEK_Z_DOWN
//
// IMPORTANTE: testar primeiro com o conjunto mecânico livre e velocidade baixa.

const long BAUD_RATE = 115200;

const uint8_t X_STEP = 2;
const uint8_t X_DIR = 5;
const uint8_t Y_STEP = 3;
const uint8_t Y_DIR = 6;
const uint8_t Z_STEP = 4;
const uint8_t Z_DIR = 7;
const uint8_t ENABLE_PIN = 8;

const uint8_t TOP_BUTTON = A1;
const uint8_t BOTTOM_BUTTON = 11;

// Velocidade inicial conservadora. Menor = mais rápido.
const unsigned int STEP_INTERVAL_US = 1500;
const unsigned int STEP_PULSE_US = 5;

bool moving = false;
char moving_axis = 'X';
int moving_direction = 1;
long remaining_steps = 0;

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

bool validAxis(char axis) {
  return axis == 'X' || axis == 'Y' || axis == 'Z';
}

bool limitPressed(char axis, int direction) {
  if (axis != 'Z') return false;
  if (direction < 0 && digitalRead(BOTTOM_BUTTON) == LOW) return true;
  if (direction > 0 && digitalRead(TOP_BUTTON) == LOW) return true;
  return false;
}

void pulseStep(char axis) {
  digitalWrite(stepPin(axis), HIGH);
  delayMicroseconds(STEP_PULSE_US);
  digitalWrite(stepPin(axis), LOW);
  delayMicroseconds(STEP_INTERVAL_US);
}

void stopMotion() {
  moving = false;
  remaining_steps = 0;
}

void startMove(char axis, int direction, long steps) {
  if (!validAxis(axis) || steps <= 0) {
    Serial.println("ERR BAD_MOVE");
    return;
  }

  if (limitPressed(axis, direction)) {
    Serial.println("LIMIT");
    return;
  }

  digitalWrite(dirPin(axis), direction > 0 ? HIGH : LOW);
  moving_axis = axis;
  moving_direction = direction > 0 ? 1 : -1;
  remaining_steps = steps;
  moving = true;
  Serial.println("ACK MOVE");
}

void executeMotion() {
  if (!moving) return;

  if (limitPressed(moving_axis, moving_direction)) {
    stopMotion();
    Serial.println("LIMIT");
    return;
  }

  pulseStep(moving_axis);
  remaining_steps--;

  if (remaining_steps <= 0) {
    stopMotion();
    Serial.println("DONE");
  }
}

void seekZDown() {
  if (digitalRead(BOTTOM_BUTTON) == LOW) {
    Serial.println("LIMIT Z_BOTTOM_ALREADY");
    return;
  }

  digitalWrite(Z_DIR, LOW);
  Serial.println("ACK SEEK_Z_DOWN");

  // Busca o limite inferior. O botão físico é a referência de segurança.
  while (digitalRead(BOTTOM_BUTTON) != LOW) {
    pulseStep('Z');
  }

  stopMotion();
  Serial.println("LIMIT Z_BOTTOM");
}

void handleCommand(String command) {
  command.trim();
  command.toUpperCase();

  if (command == "PING") {
    Serial.println("PONG");
    return;
  }

  if (command == "STATUS") {
    Serial.println(moving ? "BUSY" : "IDLE");
    return;
  }

  if (command == "STOP") {
    stopMotion();
    Serial.println("ACK STOP");
    return;
  }

  if (command == "SEEK_Z_DOWN") {
    if (moving) {
      Serial.println("ERR BUSY");
      return;
    }
    seekZDown();
    return;
  }

  char axis;
  int direction;
  long steps;

  if (sscanf(command.c_str(), "MOVE %c %d %ld", &axis, &direction, &steps) == 3) {
    startMove(axis, direction, steps);
    return;
  }

  if (sscanf(command.c_str(), "JOG %c %d", &axis, &direction) == 2) {
    startMove(axis, direction, 2147483647L);
    return;
  }

  if (command.length() > 0) {
    Serial.println("ERR UNKNOWN_COMMAND");
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

  pinMode(TOP_BUTTON, INPUT_PULLUP);
  pinMode(BOTTOM_BUTTON, INPUT_PULLUP);

  digitalWrite(ENABLE_PIN, LOW);
  digitalWrite(X_STEP, LOW);
  digitalWrite(Y_STEP, LOW);
  digitalWrite(Z_STEP, LOW);

  Serial.begin(BAUD_RATE);
  Serial.println("READY MOTOR_CONTROLLER");
}

void loop() {
  // Sempre verifica os comandos seriais, inclusive STOP durante JOG.
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    handleCommand(command);
  }

  executeMotion();
}

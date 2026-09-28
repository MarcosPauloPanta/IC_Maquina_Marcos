// TESTE 02 — PROTOCOLO DA MÁQUINA, SEM MOTOR
// Objetivo: testar os comandos que o Python/GUI enviará ao Arduino.
// NENHUM pino de STEP/DIR é acionado neste teste.
//
// Comandos:
//   PING
//   STATUS
//   MOVE X 1 100
//   JOG Z -1
//   STOP
//   SEEK_Z_DOWN
//
// Todos os comandos apenas são reconhecidos e respondidos.
// Nenhum motor pode se mover com este sketch.

const long BAUD_RATE = 115200;

void setup() {
  Serial.begin(BAUD_RATE);
  while (!Serial) {
    ;
  }
  Serial.println("READY TEST_NO_MOTOR");
}

void loop() {
  if (!Serial.available()) {
    return;
  }

  String command = Serial.readStringUntil('\n');
  command.trim();
  command.toUpperCase();

  if (command == "PING") {
    Serial.println("PONG");
    return;
  }

  if (command == "STATUS") {
    Serial.println("READY TEST_NO_MOTOR");
    return;
  }

  if (command == "STOP") {
    Serial.println("ACK STOP");
    return;
  }

  if (command == "SEEK_Z_DOWN") {
    Serial.println("ACK SEEK_Z_DOWN NO_MOTOR");
    return;
  }

  if (command.startsWith("MOVE ")) {
    Serial.print("ACK ");
    Serial.println(command);
    return;
  }

  if (command.startsWith("JOG ")) {
    Serial.print("ACK ");
    Serial.println(command);
    return;
  }

  if (command.length() > 0) {
    Serial.println("ERR UNKNOWN_COMMAND");
  }
}

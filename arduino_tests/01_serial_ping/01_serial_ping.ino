/* CÓPIA COMENTADA PARA ESTUDO — v0.1.0.
 * Foram acrescentados comentários; não altere os comandos executáveis sem testar.
 */
// TESTE 01 — COMUNICAÇÃO SERIAL
// Objetivo: provar que PC <-> Arduino estão se comunicando.
// NÃO usa motor, A4988 ou STEP/DIR.
//
// Envie pela Serial Monitor:
//   PING
//   STATUS
//   HELP
//
// Respostas esperadas:
//   PONG
//   READY
//   COMMANDS: PING STATUS HELP

const long BAUD_RATE = 115200;

// ESTUDO: setup roda uma vez quando o Arduino inicia; configura a serial e informa que está pronto.
void setup() {
  Serial.begin(BAUD_RATE);
  while (!Serial) {
    ;
  }

  Serial.println("READY");
}

// ESTUDO: loop roda continuamente; verifica se chegou um comando e responde sem controlar motores.
void loop() {
  if (!Serial.available()) {
    return;
  }

  String command = Serial.readStringUntil('\n');
  command.trim();
  command.toUpperCase();

  if (command == "PING") {
    Serial.println("PONG");
  } else if (command == "STATUS") {
    Serial.println("READY");
  } else if (command == "HELP") {
    Serial.println("COMMANDS: PING STATUS HELP");
  } else if (command.length() > 0) {
    Serial.println("ERR UNKNOWN_COMMAND");
  }
}

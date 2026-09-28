// ============================================================
// TESTE 03 — CONTROLADOR DE MOTORES DA MÁQUINA
// CNC Shield V3 + A4988 + Arduino Uno
// ============================================================
//
// OBJETIVO DESTE TESTE
// --------------------
// Este firmware é a ponte entre o computador e os motores.
// Ele permite testar, nesta ordem:
//
//   1) PING / STATUS  -> comunicação
//   2) JOG             -> movimento manual de UM eixo
//   3) MOVE            -> movimento de uma quantidade definida de passos
//   4) SEEK_Z_DOWN     -> Z desce até o botão inferior
//   5) STOP            -> parada imediata solicitada pelo computador
//
// REGRA FUNDAMENTAL DO PROJETO
// ----------------------------
// SOMENTE UM EIXO PODE SE MOVIMENTAR POR VEZ.
//
// O Arduino possui uma trava: se X estiver em movimento, um comando para
// Y ou Z será rejeitado. A mesma regra vale para qualquer combinação.
//
// ============================================================
// PINAGEM — CNC SHIELD V3
// ============================================================
//
//        STEP     DIR
// X      D2       D5
// Y      D3       D6
// Z      D4       D7
//
// ENABLE = D8
//
// IMPORTANTE: no CNC Shield V3, ENABLE normalmente é ativo em LOW.
// Portanto LOW = drivers habilitados.
//
// BOTÕES DO PROJETO
// -----------------
// Botão de cima  = A1
// Botão de baixo = D11
//
// Usamos INPUT_PULLUP:
//   solto     -> HIGH
//   pressionado -> LOW
//
// ============================================================
// COMANDOS SERIAIS
// ============================================================
//
// PING
// STATUS
// MOVE X 1 1000
// MOVE X -1 1000
// JOG X 1
// JOG X -1
// STOP
// SEEK_Z_DOWN
//
// Para JOG, a GUI envia JOG ao apertar e STOP ao soltar.
// Assim, o motor não continua andando depois que o botão é solto.
//
// ============================================================

const long BAUD_RATE = 115200;

// -------------------------
// Pinos dos motores
// -------------------------
const uint8_t X_STEP = 2;
const uint8_t X_DIR  = 5;

const uint8_t Y_STEP = 3;
const uint8_t Y_DIR  = 6;

const uint8_t Z_STEP = 4;
const uint8_t Z_DIR  = 7;

const uint8_t ENABLE_PIN = 8;

// -------------------------
// Pinos dos limites físicos
// -------------------------
const uint8_t TOP_BUTTON    = A1;
const uint8_t BOTTOM_BUTTON = 11;

// -------------------------
// Temporização do motor
// -------------------------
// Quanto maior STEP_INTERVAL_US, mais devagar o motor gira.
// Começamos propositalmente devagar para o primeiro teste.
const unsigned int STEP_INTERVAL_US = 1500;
const unsigned int STEP_PULSE_US    = 5;

// ============================================================
// ESTADO DO CONTROLADOR
// ============================================================

// moving = true significa que existe UM movimento em andamento.
bool moving = false;

// Qual eixo está sendo movimentado neste momento.
char moving_axis = 'X';

// +1 ou -1.
int moving_direction = 1;

// Quantos passos ainda faltam no comando MOVE.
long remaining_steps = 0;

// ============================================================
// FUNÇÕES AUXILIARES
// ============================================================

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

// ------------------------------------------------------------
// Verifica se um limite físico impede a direção solicitada.
// ------------------------------------------------------------
// No Z:
//   direção -1 -> descendo -> botão inferior
//   direção +1 -> subindo  -> botão superior
//
// X e Y ainda não possuem limites configurados neste teste.
// ------------------------------------------------------------
bool limitPressed(char axis, int direction) {
  if (axis != 'Z') {
    return false;
  }

  if (direction < 0 && digitalRead(BOTTOM_BUTTON) == LOW) {
    return true;
  }

  if (direction > 0 && digitalRead(TOP_BUTTON) == LOW) {
    return true;
  }

  return false;
}

// ------------------------------------------------------------
// Gera UM pulso STEP.
// ------------------------------------------------------------
// Um pulso é o que o A4988 interpreta como um passo/microstep.
// A quantidade física por passo depende da configuração de
// microstepping do driver e da mecânica.
// ------------------------------------------------------------
void pulseStep(char axis) {
  digitalWrite(stepPin(axis), HIGH);
  delayMicroseconds(STEP_PULSE_US);
  digitalWrite(stepPin(axis), LOW);
  delayMicroseconds(STEP_INTERVAL_US);
}

// ------------------------------------------------------------
// Para qualquer movimento em andamento.
// ------------------------------------------------------------
void stopMotion() {
  moving = false;
  remaining_steps = 0;
}

// ============================================================
// MOVIMENTO NORMAL — MOVE
// ============================================================

void startMove(char axis, int direction, long steps) {
  // Validação básica do comando.
  if (!validAxis(axis) || steps <= 0 || (direction != 1 && direction != -1)) {
    Serial.println("ERR BAD_MOVE");
    return;
  }

  // REGRA DE SEGURANÇA MAIS IMPORTANTE:
  // se qualquer eixo já estiver se movimentando, rejeitamos
  // qualquer novo movimento.
  if (moving) {
    Serial.println("ERR BUSY");
    return;
  }

  // Não permitimos começar um movimento se o limite correspondente
  // já estiver pressionado.
  if (limitPressed(axis, direction)) {
    Serial.println("LIMIT");
    return;
  }

  // Define a direção elétrica do driver.
  digitalWrite(dirPin(axis), direction > 0 ? HIGH : LOW);

  moving_axis = axis;
  moving_direction = direction;
  remaining_steps = steps;
  moving = true;

  Serial.println("ACK MOVE");
}

// ------------------------------------------------------------
// Executa o movimento sem bloquear o loop inteiro.
// ------------------------------------------------------------
void executeMotion() {
  if (!moving) {
    return;
  }

  // Verificamos o limite ANTES de cada passo.
  if (limitPressed(moving_axis, moving_direction)) {
    stopMotion();
    Serial.println("LIMIT");
    return;
  }

  pulseStep(moving_axis);
  remaining_steps--;

  // Terminou a quantidade solicitada.
  if (remaining_steps <= 0) {
    stopMotion();
    Serial.println("DONE");
  }
}

// ============================================================
// JOG
// ============================================================
//
// JOG é movimento manual.
//
// A GUI faz:
//
//   botão pressionado -> JOG X 1
//   botão solto       -> STOP
//
// O Arduino transforma JOG em um movimento muito longo, mas
// continua verificando STOP, limites e novos comandos.
//
// O número 2147483647 é o maior valor positivo de um long de
// 32 bits assinado. Na prática, o movimento termina quando o
// usuário mandar STOP ou um limite for atingido.
// ============================================================

void startJog(char axis, int direction) {
  if (!validAxis(axis) || (direction != 1 && direction != -1)) {
    Serial.println("ERR BAD_JOG");
    return;
  }

  if (moving) {
    Serial.println("ERR BUSY");
    return;
  }

  if (limitPressed(axis, direction)) {
    Serial.println("LIMIT");
    return;
  }

  digitalWrite(dirPin(axis), direction > 0 ? HIGH : LOW);

  moving_axis = axis;
  moving_direction = direction;
  remaining_steps = 2147483647L;
  moving = true;

  // Não enviamos ACK aqui.
  // Isso evita deixar uma resposta de JOG presa no buffer serial
  // quando a GUI mandar STOP ao soltar o botão.
}

// ============================================================
// BUSCA DO LIMITE INFERIOR DO Z
// ============================================================
//
// SEEK_Z_DOWN não pode ser um while cego.
// Precisamos continuar lendo a serial para que STOP funcione.
//
// Portanto, enquanto o Z procura o botão:
//   - gera um passo;
//   - verifica o botão;
//   - verifica se chegou STOP;
//
// Ao tocar o botão, retorna:
//   LIMIT Z_BOTTOM
//
// Se receber STOP antes disso:
//   ACK STOP
// ============================================================

void seekZDown() {
  if (moving) {
    Serial.println("ERR BUSY");
    return;
  }

  // Se já começou com o botão pressionado, não movimentamos o Z.
  if (digitalRead(BOTTOM_BUTTON) == LOW) {
    Serial.println("LIMIT Z_BOTTOM_ALREADY");
    return;
  }

  digitalWrite(Z_DIR, LOW); // direção definida como "descer"
  moving_axis = 'Z';
  moving_direction = -1;
  moving = true;

  Serial.println("ACK SEEK_Z_DOWN");

  while (moving) {
    // ----------------------------------------------------------
    // PRIMEIRO: segurança física.
    // ----------------------------------------------------------
    if (digitalRead(BOTTOM_BUTTON) == LOW) {
      stopMotion();
      Serial.println("LIMIT Z_BOTTOM");
      return;
    }

    // ----------------------------------------------------------
    // SEGUNDO: permite STOP vindo do computador.
    // ----------------------------------------------------------
    if (Serial.available()) {
      String command = Serial.readStringUntil('\n');
      command.trim();
      command.toUpperCase();

      if (command == "STOP") {
        stopMotion();
        Serial.println("ACK STOP");
        return;
      }

      // Durante a busca do Z não aceitamos outro movimento.
      Serial.println("ERR BUSY");
    }

    // ----------------------------------------------------------
    // TERCEIRO: gera um passo.
    // ----------------------------------------------------------
    pulseStep('Z');
  }
}

// ============================================================
// INTERPRETADOR DE COMANDOS
// ============================================================

void handleCommand(String command) {
  command.trim();
  command.toUpperCase();

  if (command.length() == 0) {
    return;
  }

  // ----------------------------------------------------------
  // Teste simples de comunicação.
  // ----------------------------------------------------------
  if (command == "PING") {
    Serial.println("PONG");
    return;
  }

  // ----------------------------------------------------------
  // Estado atual do Arduino.
  // ----------------------------------------------------------
  if (command == "STATUS") {
    if (moving) {
      Serial.print("BUSY ");
      Serial.println(moving_axis);
    } else {
      Serial.println("IDLE");
    }
    return;
  }

  // ----------------------------------------------------------
  // Parada geral.
  // ----------------------------------------------------------
  if (command == "STOP") {
    stopMotion();
    Serial.println("ACK STOP");
    return;
  }

  // ----------------------------------------------------------
  // Busca do botão inferior do Z.
  // ----------------------------------------------------------
  if (command == "SEEK_Z_DOWN") {
    seekZDown();
    return;
  }

  // ----------------------------------------------------------
  // MOVE EIXO DIREÇÃO PASSOS
  // Exemplo: MOVE X 1 1000
  // ----------------------------------------------------------
  char axis;
  int direction;
  long steps;

  if (sscanf(command.c_str(), "MOVE %c %d %ld", &axis, &direction, &steps) == 3) {
    startMove(axis, direction, steps);
    return;
  }

  // ----------------------------------------------------------
  // JOG EIXO DIREÇÃO
  // Exemplo: JOG Z -1
  // ----------------------------------------------------------
  if (sscanf(command.c_str(), "JOG %c %d", &axis, &direction) == 2) {
    startJog(axis, direction);
    return;
  }

  Serial.println("ERR UNKNOWN_COMMAND");
}

// ============================================================
// SETUP
// ============================================================

void setup() {
  // Pinos dos motores como saída.
  pinMode(X_STEP, OUTPUT);
  pinMode(X_DIR, OUTPUT);
  pinMode(Y_STEP, OUTPUT);
  pinMode(Y_DIR, OUTPUT);
  pinMode(Z_STEP, OUTPUT);
  pinMode(Z_DIR, OUTPUT);

  // Habilita os drivers.
  pinMode(ENABLE_PIN, OUTPUT);
  digitalWrite(ENABLE_PIN, LOW);

  // Pinos dos botões com resistor pull-up interno.
  pinMode(TOP_BUTTON, INPUT_PULLUP);
  pinMode(BOTTOM_BUTTON, INPUT_PULLUP);

  // Estado inicial seguro dos sinais STEP.
  digitalWrite(X_STEP, LOW);
  digitalWrite(Y_STEP, LOW);
  digitalWrite(Z_STEP, LOW);

  // Inicializa comunicação USB/serial.
  Serial.begin(BAUD_RATE);

  // Timeout curto para leitura de comandos.
  // Isso é especialmente importante porque o firmware precisa
  // continuar responsivo ao STOP.
  Serial.setTimeout(50);

  Serial.println("READY MOTOR_CONTROLLER");
}

// ============================================================
// LOOP PRINCIPAL
// ============================================================

void loop() {
  // Primeiro verificamos se o computador enviou um comando.
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    handleCommand(command);
  }

  // Depois executamos UM passo do movimento atual.
  // Nunca existe X + Y + Z ao mesmo tempo.
  executeMotion();
}

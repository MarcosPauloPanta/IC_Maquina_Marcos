# Protocolo serial e firmware — v0.1.0

## 1. Escopo

Este documento descreve `firmware/controller.ino`, firmware de teste incluído no repositório para Arduino Uno, CNC Shield V3 e drivers A4988. Ele não é o firmware original da máquina e não deve ser gravado na placa original sem autorização e procedimento específico.

Comunicação serial: 115200 baud, texto ASCII, um comando por linha terminada em newline.

## 2. Pinagem declarada no sketch

| Função | Pino Arduino |
|---|---:|
| X STEP | D2 |
| X DIR | D5 |
| Y STEP | D3 |
| Y DIR | D6 |
| Z STEP | D4 |
| Z DIR | D7 |
| ENABLE compartilhado | D8 |
| Botão superior Z | A1 |
| Botão inferior Z (HOLD) | D11 |

O firmware declara botão pressionado como HIGH e usa entradas `INPUT`. Confirme o circuito elétrico real, pull-ups/pull-downs e níveis lógicos antes de confiar nessa leitura.

Convenção lógica do sketch: Z+ = descida; Z− = subida. A convenção lógica precisa ser comparada com o sentido mecânico real.

## 3. Comandos aceitos

| Comando | Parâmetros | Resposta/efeito esperado |
|---|---|---|
| `PING` | nenhum | `PONG` |
| `STATUS` | nenhum | `STATUS MODE=n` |
| `LIMITS` | nenhum | `LIMITS TOP=... BOTTOM=... RAW_TOP=... RAW_BOTTOM=...` |
| `POS` | nenhum | `POS X=n Y=n Z=n` (contadores em passos) |
| `ZERO` | opcional: X/Y/Z | Zera todos os contadores ou somente o eixo indicado; responde `OK ZERO`. |
| `MOVE X` | passos com sinal, passos/s | Movimento finito no eixo; responde `ACK MOVE`, depois `DONE` ou status de limite. |
| `JOG_START X` | direção +1/−1, passos/s | Inicia ou renova JOG; responde `ACK JOG` ao iniciar. |
| `JOG_STOP` | nenhum | Interrompe JOG; responde `OK JOG_STOP`. |
| `STOP` | nenhum | Interrompe o modo atual; responde `OK STOP`. |
| `Z_APPROACH` | passos de descida, passos/s, passos de recuo | Inicia aproximação Z; termina por botão ou quantidade máxima de passos. |
| `Z_RETRACT` | passos, passos/s | Comanda subida Z; responde `ACK Z_RETRACT`, depois `DONE Z_RETRACT`. |

Os nomes X/Y/Z são intercambiáveis nos comandos `MOVE` e `JOG_START`, desde que o eixo esteja válido. O firmware rejeita comandos inválidos ou movimentos incompatíveis enquanto outro modo está ativo, com respostas `ERR ...` ou `ERR BUSY`.

## 4. Lógica de movimento

O firmware mantém um estado de movimento (ocioso, movimento finito, JOG, aproximação Z ou retração Z). O loop principal lê comandos e executa pulsos de passo para o eixo ativo. Há somente um eixo em movimento por vez.

- Velocidade aceita pelo firmware: 1 a 10000 passos/s.
- Pulso STEP declarado: 5 microssegundos.
- JOG tem timeout de 300 ms sem renovação.
- Drivers são desligados após 2000 ms ociosos.
- X e Y têm limites de software de ±10000 passos no contador do firmware.
- Limites físicos direcionais de Z são verificados durante movimentos normais/JOG: botão inferior bloqueia descida; botão superior bloqueia subida.
- ENABLE é ativo em LOW para os drivers A4988 no sketch.

Esses valores são parâmetros de software do sketch; não representam limites mecânicos certificados.

## 5. Aproximação e retração Z

### `Z_APPROACH down_steps speed retract_steps`

1. Valida quantidade de passos, recuo e velocidade.
2. Exige firmware ocioso.
3. Se qualquer botão Z já estiver pressionado, responde imediatamente com `Z_APPROACH_READY LIMIT_TOP` ou `Z_APPROACH_READY LIMIT_BOTTOM`.
4. Caso contrário inicia descida lógica Z+.
5. Durante a aproximação, se qualquer um dos botões for detectado, encerra a descida e responde com o status correspondente.
6. Se a quantidade máxima de passos terminar primeiro, responde `Z_APPROACH_READY MAX_STEPS`.

O parâmetro `retract_steps` é validado/recebido, mas a retração é comandada separadamente pela GUI com `Z_RETRACT`; não ocorre automaticamente dentro de `Z_APPROACH`.

### `Z_RETRACT steps speed`

Comanda subida lógica Z−. O firmware bloqueia a retração se o botão superior estiver pressionado. O botão inferior não bloqueia a subida, pois a intenção é permitir afastamento do contato inferior.

## 6. Relação com a GUI

A GUI espera respostas do firmware pelo controlador serial. Na análise, X e Z usam velocidade fixa de 500 passos/s. Para cada ponto, a GUI envia movimento X (se necessário), aproximação Z, aguarda a permanência individual e então envia retração Z.

A GUI trata os status `Z_APPROACH_READY MAX_STEPS`, `... LIMIT_TOP`, `... LIMIT_BOTTOM` e `... LIMIT` como chegadas válidas para iniciar a permanência. Assim, o tempo de permanência começa após o fim da aproximação, mas esse fim pode ter ocorrido por limite de passos sem contato físico.

## 7. Limitações técnicas

- Os contadores de posição são contadores de pulsos, não encoders.
- Não há homing físico implementado/validado neste firmware.
- Os limites X/Y são limites de software baseados nos contadores; perdem referência após perda de passos ou ZERO em local desconhecido.
- As entradas dos botões dependem da ligação elétrica e do nível lógico real.
- O timeout JOG não é um circuito de emergência independente.
- STOP é um comando serial e depende de comunicação/firmware funcionais.
- O firmware usa `String` para acumular comandos seriais; não foi documentado teste de robustez prolongado.
- Nenhum teste físico integral é declarado por esta documentação.

## 8. Segurança

Antes de ligar motores:
1. conferir a placa correta e a pinagem;
2. conferir o circuito dos dois botões e seu nível elétrico;
3. testar PING/LIMITS sem motores;
4. testar um eixo por vez com deslocamento curto;
5. confirmar que os sentidos +/− e os limites correspondem à mecânica;
6. manter STOP e corte de energia acessíveis.

**Não sobrescreva o firmware original da máquina.** Use o sketch somente na placa de teste/controlador pretendida, depois de confirmar a identificação da placa e a fiação.

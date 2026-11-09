# Guia de estudo — IC_Maquina_Marcos v0.1.0

Este guia descreve o código que está publicado na branch `main`. Ele deve ser lido junto com o código-fonte: a documentação explica responsabilidades e fluxo, mas não substitui ensaios de bancada nem comprova segurança física.

## 1. Visão geral

O projeto usa Python/Tkinter para a interface e supervisão, comunicação serial USB para enviar comandos a um Arduino e firmware C++ para gerar pulsos STEP/DIR nos drivers A4988.

Fluxo simplificado:

```text
Operador
  |
  v
run_gui.py
  |
  v
src/GUI/main_window.py  <---->  src/GUI/analysis_scroll.py
  |
  v
src/controller/arduino.py
  | USB / serial (115200 baud)
  v
firmware/controller.ino
  |
  v
CNC Shield V3 -> A4988 -> motores X, Y e Z
```

O módulo `axis.py` calcula deslocamentos e posições teóricas; `machine.py` agrupa os modelos dos três eixos. Esses modelos não medem a posição mecânica.

## 2. Estrutura e responsabilidade dos arquivos

| Arquivo | Responsabilidade |
|---|---|
| `run_gui.py` | Cria a janela Tkinter, instala a extensão rolável da Análise e inicia o loop de eventos. |
| `src/GUI/main_window.py` | Janela principal, conexão, operação/JOG, sequência automática, calibração, terminal, tema e atualização de status. |
| `src/GUI/analysis_scroll.py` | Substitui a construção visual da aba Análise por uma lista rolável com campos X e permanência por ponto. |
| `src/GUI/spatial_map.py` | Widget de mapa 2D para desenhar e editar pontos; não controla os motores nem integra automaticamente os pontos à análise. |
| `src/controller/arduino.py` | Abre a serial, envia comandos, recebe linhas em thread e espera respostas de movimento. |
| `src/controller/axis.py` | Converte distância em mm para passos e calcula posição teórica. |
| `src/controller/machine.py` | Agrupa X/Y/Z e mantém posições lógicas estimadas. |
| `src/controller/point_sequence.py` | Estrutura de dados de pontos X ordenados. A GUI também mantém listas de entradas para executar a análise. |
| `firmware/controller.ino` | Firmware de teste: interpreta comandos, controla um movimento por vez, verifica botões e atualiza contadores de passos. |
| `arduino_tests/` | Sketches de testes anteriores de serial, protocolo e motores. |
| `testes/` | Testes automatizados de matemática e modelo lógico. |

## 3. Inicialização da GUI

`run_gui.py` importa `MainWindow` e `install_analysis_scroll`. Antes de criar a janela, chama `install_analysis_scroll(MainWindow)`. Essa função substitui os métodos visuais `_analysis` e `create_point_fields` da classe para mostrar a lista de pontos dentro de uma área rolável. A lógica de movimento continua em `main_window.py`.

A janela principal cria:
- modelo `Machine` com eixos X, Y e Z;
- controlador serial, inicialmente desconectado;
- variáveis Tkinter para campos, posições, estado e parâmetros;
- abas Operação, Análise, Terminal, Calibração e Mapa Espacial;
- atualização periódica da interface e leitura de mensagens seriais.

## 4. Modelo matemático

### `Axis`

O eixo recebe passos completos por volta, microstepping, deslocamento mecânico por volta, posição lógica inicial e, opcionalmente, fator experimental em passos/mm.

A conversão geral é:

`passos = distância_mm × passos_por_mm`

O código arredonda a quantidade de passos para inteiro e calcula a posição teórica correspondente. `calculate_move()` calcula sem comandar hardware; `move_to()` atualiza a posição lógica do objeto.

O fator inicial de 400 passos/mm configurado pela GUI é provisório. Deve ser substituído por calibração medida para cada eixo. Microsteps comandados não garantem deslocamento físico exato.

### `Machine`

Mantém referências aos objetos X/Y/Z, permite consultar um eixo, atualizar posição teórica e zerar a posição lógica de um ou todos os eixos. Não executa homing nem verifica sensores físicos.

### `PointSequence`

Armazena pontos `MeasurementPoint(x_mm)`, controla índice atual e oferece operações de adicionar, substituir, remover, limpar, iniciar e avançar. A sequência de execução da GUI também captura os valores dos campos para que alterações na tela durante a execução não alterem a lista já iniciada.

## 5. Comunicação serial — `ArduinoController`

A GUI usa a porta selecionada (padrão visual COM3) e 115200 baud. Ao conectar, o controlador abre a serial, aguarda a inicialização do Arduino, limpa buffers, envia `PING` e espera `PONG`. Uma thread leitora coloca mensagens recebidas em uma fila para a GUI.

Métodos relevantes:
- `connect()` / `disconnect()`: abrir e fechar a comunicação;
- `send()`: enviar comando e aguardar uma resposta;
- `send_nowait()`: enviar sem esperar resposta;
- `read_available()`: retirar mensagens já recebidas;
- `wait_for_motion()`: aguardar conclusão ou status de limite;
- `move_steps()`: comandar movimento finito;
- `jog_start()` / `jog_stop()`: controlar JOG;
- `z_approach()`: iniciar aproximação e aguardar status de chegada;
- `z_retract()`: comandar retração;
- `position()`, `limits()`, `status()`: consultar estado.

A serial é um canal compartilhado. Não se deve presumir que comandos concorrentes de várias threads possam aguardar respostas independentes sem coordenação.

## 6. Operação manual (JOG)

Na aba Operação, o operador seleciona velocidade em passos/s e mantém pressionado um botão de direção do eixo. A GUI renova periodicamente o comando JOG; ao soltar, envia parada. O firmware também aplica timeout de JOG como mecanismo adicional de interrupção caso a renovação cesse.

A posição exibida é calculada a partir de contadores de passos retornados pelo firmware e convertida para mm. Não é leitura de encoder.

## 7. Análise por pontos

A aba permite criar de 1 a 100 pontos. Cada linha contém:
- coordenada X em mm;
- tempo de permanência em segundos.

Ao criar os pontos, cada campo de permanência recebe o tempo-base definido na aba Calibração. O operador pode editar o tempo individual. Se o tempo-base for alterado depois, campos ainda iguais ao valor-base anterior são atualizados; valores personalizados são preservados.

Ao executar:
1. a GUI valida os valores X e tempos (finitos; permanência maior ou igual a zero);
2. exige conexão serial e parâmetros Z válidos;
3. captura os valores em listas e inicia um worker em thread;
4. para cada ponto, move X se necessário;
5. executa `Z_APPROACH` com limite de passos e velocidade fixa de 500 passos/s;
6. considera como chegadas válidas os status `MAX_STEPS`, `LIMIT_TOP`, `LIMIT_BOTTOM` e `LIMIT` no formato de resposta esperado;
7. espera o tempo individual do ponto;
8. comanda `Z_RETRACT` a 500 passos/s;
9. atualiza posição/progresso e segue ao próximo ponto.

A velocidade da sequência automática é fixa em 500 passos/s para X e Z, independentemente da velocidade de JOG ou do campo de movimento manual de calibração.

**Interpretação importante:** o firmware considera tanto o acionamento de um dos botões durante a aproximação quanto o esgotamento da quantidade programada de passos como condição de término da aproximação. A GUI inicia a permanência depois de receber um desses status. Portanto, `MAX_STEPS` significa que a distância programada terminou; não significa que um contato físico foi detectado.

Se a execução lançar uma exceção, a GUI tenta enviar `STOP` e apresenta a análise como interrompida. Isso não substitui uma parada física de emergência.

## 8. Calibração

A aba Calibração permite editar fatores passos/mm para X/Y/Z e configurar:
- deslocamento de descida Z (mm);
- velocidade de calibração;
- recuo Z (mm);
- tempo-base de permanência (s);
- quantidade e velocidade de um movimento de teste por passos.

A opção de salvar grava os parâmetros em `calibration.json`, na pasta de execução. Esse arquivo contém parâmetros locais da máquina e por isso é ignorado pelo Git. Preserve uma cópia de segurança local. Não publique calibrações específicas do equipamento sem intenção.

A posição zero é lógica. Sem homing/sensor de referência validado, a aplicação não conhece a origem física.

## 9. Mapa Espacial

`SpatialMap` desenha uma geometria 2D (por exemplo, círculo ou quadrado) e permite criar, selecionar, editar e excluir pontos com coordenadas X/Y. No estado atual, o mapa é uma ferramenta visual separada: seus pontos não são automaticamente enviados à lista de análise nem comandados aos motores.

## 10. Tema, terminal e estado

A GUI inicia em tema claro e permite alternar para escuro. O terminal envia comandos textuais ao firmware e exibe respostas. A janela de estado dos botões Z consulta periodicamente o comando `LIMITS`.

## 11. Como estudar o projeto

Ordem recomendada:
1. `src/controller/axis.py` — matemática;
2. `src/controller/machine.py` e `point_sequence.py` — modelo;
3. `src/controller/arduino.py` — comunicação;
4. `src/GUI/analysis_scroll.py` — composição visual da análise;
5. `src/GUI/main_window.py` — integração da interface e fluxo;
6. `firmware/controller.ino` — protocolo e acionamento físico.

Leia a seção de validação e segurança antes de qualquer ensaio com motores ou amostra.

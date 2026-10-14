# IC_Maquina_Marcos — v0.1.0: guia de estudo

> **Objetivo deste documento:** explicar a estrutura, o fluxo e as responsabilidades do código para que o projeto possa ser estudado e evoluído por versões.
>
> **Base congelada:** branch `fix/z-contact-dwell-python`, commit de código antes desta documentação: `c1b74d0075559ef967bb089bf1fa1d50341f4d1e`.
>
> Esta documentação não substitui a leitura do código-fonte. Ela descreve o que o código faz hoje, inclusive limitações e possíveis inconsistências; não presume que tudo foi validado fisicamente.

## 1. O que é a v0.1.0

A v0.1.0 é a primeira versão de referência que vamos tratar como base de estudo. Mudanças futuras devem ser feitas de forma incremental e registradas em commits, sem sobrescrever silenciosamente esta base.

O programa tem uma interface gráfica em Python (Tkinter), um modelo matemático dos eixos, uma camada de comunicação serial e um firmware de teste para Arduino. O firmware em `arduino_tests/controlador_arduino_python_A.ino` é um sketch de teste do projeto; **não é uma instrução para regravar a placa original da máquina**.

## 2. Mapa do projeto

| Arquivo/pasta | Responsabilidade |
|---|---|
| `run_gui.py` | Ponto de entrada normal da aplicação; cria a janela Tkinter e instala a extensão da aba Análise. |
| `src/GUI/main_window.py` | Janela principal, abas, parâmetros, JOG, sequência de pontos, calibração, terminal e coordenação da execução. |
| `src/GUI/analysis_scroll.py` | Substitui a construção visual da aba Análise para permitir rolagem de uma lista de pontos. Não é o controlador de movimento. |
| `src/GUI/spatial_map.py` | Mapa 2D para desenhar/editar pontos sobre um corpo de prova. Por si só, clicar no mapa não movimenta os motores. |
| `src/controller/arduino.py` | Abre a serial, envia comandos, recebe linhas em uma fila e espera respostas do Arduino. |
| `src/controller/axis.py` | Matemática de um eixo: distância, direção, passos e posição teórica. Não controla hardware. |
| `src/controller/machine.py` | Reúne X, Y e Z e mantém as posições lógicas estimadas. |
| `src/controller/point_sequence.py` | Estrutura de dados para uma lista ordenada de posições X. |
| `arduino_tests/controlador_arduino_python_A.ino` | Firmware de teste: protocolo serial, geração de pulsos, JOG, movimentos, limites e contagem de passos. |
| `testes/` | Testes automatizados de parte da matemática/modelo. Não comprovam segurança nem funcionamento físico. |
| `requirements.txt` | Dependências Python: PySerial e pytest. |
| `calibration.json` | Arquivo local criado ao salvar calibração; não precisa existir antes da primeira execução. |

### Caminho principal dos comandos

```text
Operador
  ↓
Tkinter — src/GUI/main_window.py
  ↓
ArduinoController — src/controller/arduino.py
  ↓ USB/serial: comandos em texto terminados em newline
Firmware Arduino — controlador_arduino_python_A.ino
  ↓
CNC Shield V3 → drivers A4988 → motores
```

O modelo `Axis`/`Machine` calcula e exibe posições em Python; o Arduino também conta passos em memória. Nenhum dos dois, sem referência física/homing confirmado, conhece necessariamente a posição mecânica absoluta real.

## 3. Conceitos fundamentais

- **Passo/microstep:** comando discreto enviado ao driver. O número enviado pelo programa é uma contagem de pulsos STEP; a relação com deslocamento físico depende do motor, microstepping, transmissão e calibração.
- **passos/s:** velocidade de comando expressa em pulsos por segundo. Não é uma velocidade em mm/s até que se conheça a calibração passos/mm.
- **passos/mm:** fator que converte distância em milímetros para pulsos. É provisório até ser medido e validado para cada eixo.
- **posição estimada:** posição calculada a partir dos passos contados. Pode divergir da posição real por perda de passos, folga, escorregamento ou referência incorreta.
- **ZERO lógico:** define o contador/posição como zero na posição em que o mecanismo está. Não move o eixo até um sensor de origem e não executa homing.
- **JOG:** movimento contínuo enquanto o operador mantém o botão; a GUI repete periodicamente o comando para renovar o prazo de segurança do firmware.
- **limite físico:** botão que deveria impedir o movimento no sentido de risco. A polaridade, a identidade de cada botão e o sentido mecânico devem ser validados com teste seguro antes de confiar na automação.
- **timeout:** tempo máximo de espera por uma resposta. Um timeout de comunicação não garante que o motor tenha parado fisicamente.

## 4. Python, módulo por módulo

### 4.1 `run_gui.py`

1. Importa Tkinter e `MainWindow`.
2. Importa `install_analysis_scroll` e aplica essa extensão à classe.
3. Cria a raiz da janela (`tk.Tk()`), define escala de interface e inicia `MainWindow`.
4. `root.mainloop()` mantém a interface respondendo a cliques e eventos.

**Detalhe importante:** a função `install_analysis_scroll(MainWindow)` altera em tempo de execução os métodos `MainWindow._analysis` e `MainWindow.create_point_fields`. Por isso, a aba Análise que aparece ao iniciar por `python run_gui.py` é montada por `analysis_scroll.py`, não pela implementação inicial de `_analysis` em `main_window.py`. Essa é uma extensão visual, não uma segunda implementação do movimento.

### 4.2 `src/controller/axis.py` — matemática de um eixo

A classe `Axis` recebe:
- `steps_per_revolution`: passos completos por volta do motor;
- `microstepping`: subdivisões configuradas no driver;
- `mm_per_revolution`: deslocamento mecânico por volta;
- `current_position_mm`: posição lógica atual;
- `calibrated_steps_per_mm`: calibração experimental opcional.

**Propriedade `microsteps_per_revolution`:** multiplica passos por volta pelo fator de microstepping.

**Propriedade `microsteps_per_mm`:** usa a calibração experimental se ela existir; caso contrário calcula `(passos por volta × microstepping) / mm por volta`.

**`set_calibration(steps_per_mm)`:** valida que o valor seja positivo e salva a calibração no objeto.

**`calculate_move(target_position_mm)`:**
1. subtrai a posição atual do alvo;
2. determina direção (+1, -1 ou 0);
3. transforma o módulo da distância em passos, arredondando para inteiro;
4. calcula a posição teórica resultante a partir dos passos arredondados;
5. retorna um dicionário com distância, direção, quantidade de passos e posição teórica.

Essa função só faz contas: não envia nada ao Arduino.

**`move_to(target_position_mm)`:** chama `calculate_move`, atualiza a posição lógica para a posição teórica calculada e devolve o resultado. Não deve ser confundido com uma confirmação de movimento físico.

### 4.3 `src/controller/machine.py` — agrupamento dos eixos

- O construtor recebe os objetos `Axis` de X, Y e Z.
- `__post_init__` cria o dicionário `axes` para consultar um eixo pelo nome.
- `get_axis(name)` normaliza o nome para maiúsculas e rejeita eixos que não sejam X/Y/Z.
- `move_to(axis, target_mm)` encaminha a conta ao objeto do eixo escolhido.
- `zero(axis=None)` zera a posição lógica de um eixo ou de todos.
- `positions()` retorna um dicionário com as posições lógicas atuais.

A classe não impõe limites mecânicos, não faz homing e não conversa com o Arduino.

### 4.4 `src/controller/point_sequence.py` — sequência de pontos

- `MeasurementPoint` guarda uma coordenada `x_mm`.
- `PointSequence.add` acrescenta um ponto.
- `set_points` substitui a lista inteira e reinicia o índice.
- `remove` apaga um item e tenta manter o índice consistente.
- `clear` esvazia a lista.
- `start` começa no primeiro ponto e rejeita uma lista vazia.
- `current` devolve o ponto do índice atual, se válido.
- `advance` avança o índice e informa se ainda há pontos.
- `finished` informa se a sequência não vazia já passou do último ponto.

Na GUI atual, a lista usada pelo trabalhador de análise também é passada diretamente como lista de números; a classe `PointSequence` existe como modelo, mas não conduz sozinha a execução dos movimentos.

### 4.5 `src/controller/arduino.py` — comunicação serial

**Inicialização (`__init__`):** guarda porta, baud rate e timeout; cria uma fila para mensagens recebidas, um evento para encerrar o leitor e referências para porta/thread.

**`is_connected`:** verifica se existe uma porta serial aberta.

**`connect`:**
1. importa PySerial e mostra uma mensagem clara se não estiver instalado;
2. abre a porta (padrão da GUI: COM3, 115200 baud);
3. espera dois segundos para permitir a reinicialização comum de algumas placas;
4. limpa buffers;
5. envia `PING` e exige resposta exatamente `PONG`;
6. inicia uma thread leitora que coloca linhas recebidas na fila.

**`_reader_loop`:** lê linhas da serial em segundo plano, decodifica ASCII e põe mensagens não vazias na fila. Isso evita que toda a recepção dependa de uma leitura bloqueante dentro do desenho da GUI.

**`_write_line` / `send_nowait`:** validam que o comando não esteja vazio e que haja conexão, acrescentam newline, escrevem e descarregam o buffer. “Nowait” significa que o método não espera pela resposta final.

**`send(command)`:** limpa a fila de recepção, envia o comando e espera uma linha até o prazo limite. É útil para comandos simples de consulta; se vários comandos forem enviados concorrentemente, limpar a fila pode descartar respostas que outro fluxo esperava.

**`read_available()`:** esvazia as linhas que já chegaram sem aguardar por novas.

**`wait_for_motion(timeout_s, ready_prefix)`:** espera a conclusão de um movimento. Levanta erro para respostas iniciadas por `ERR`; retorna quando recebe um status de limite, um prefixo esperado ou `DONE`; levanta timeout se não houver resposta a tempo.

**`jog_start`:** valida o eixo e a velocidade e envia `JOG_START EIXO DIREÇÃO VELOCIDADE`.

**`jog_stop`:** envia `JOG_STOP` quando conectado.

**`stop`:** envia `JOG_STOP` e `STOP`.

**`move_steps`:** envia `MOVE`, aguarda resposta e transforma status de limite em exceção.

**`z_approach`:** envia `Z_APPROACH`, aguarda `Z_APPROACH_READY...` e devolve o texto exato recebido. A GUI usa esse texto para decidir se houve contato ou se acabou o limite de passos.

**`z_retract`:** envia `Z_RETRACT`, espera a conclusão e exige resposta iniciada por `DONE`.

**`request_position`, `ping`, `status`, `limits`, `position`:** helpers para consultar posição, conexão e limites.

**Desconexão:** tenta pedir parada, sinaliza à thread de leitura que termine, fecha a porta e limpa a fila.

### 4.6 `src/GUI/main_window.py` — interface e orquestração

A classe `MainWindow` monta a janela e liga controles a funções.

**`__init__`:**
- define título, tamanho e tema inicial;
- cria três eixos com parâmetros iniciais `Axis(200, 16, 8, calibrated_steps_per_mm=400)`;
- cria o objeto `Machine` e a estrutura de pontos;
- cria variáveis Tkinter que ligam texto/entradas à interface;
- carrega calibração local, monta abas, aplica tema;
- configura a rotina de fechamento e inicia a verificação serial periódica.

**Atenção à calibração inicial:** 400 passos/mm é o valor inicial colocado no código, não uma afirmação de que todos os eixos foram medidos e validados em 400 passos/mm. Deve ser tratado como provisório.

**`_scrollable_tab`:** coloca o conteúdo de uma aba dentro de um Canvas com barra vertical e configurações para rolagem.

**`_build`:** monta o cabeçalho, conexão serial, abas Operação/Análise/Terminal/Calibração/Mapa Espacial e rodapé de status.

**`_operation`:** cria indicadores de posição, controles JOG X/Y/Z, botão PARAR e botão de zero lógico.

**`_analysis`:** implementação original da aba Análise dentro da classe. Ao iniciar pelo `run_gui.py`, ela é substituída pela implementação de `analysis_scroll.py`.

**`create_point_fields`:** na implementação original, cria entradas para uma quantidade de pontos entre 1 e 100. A versão de `analysis_scroll.py` substitui esse método para criar os mesmos campos dentro de uma área rolável.

**`clear_points`:** remove os campos, limpa a sequência e desativa a execução até que novos campos sejam criados.

**`execute_analysis`:**
1. converte os valores X digitados em números, aceitando vírgula decimal;
2. exige conexão com Arduino;
3. valida os parâmetros do Z;
4. registra os pontos, marca análise em execução, desabilita o botão de executar;
5. inicia um worker em thread para que a interface continue responsiva.

**`_analysis_worker(points)`:** é o fluxo automático principal da v0.1.0.
1. lê a posição X lógica atual;
2. converte descida e recuo de mm para passos usando o fator do eixo Z;
3. para cada X, envia um movimento de X se necessário;
4. envia `Z_APPROACH` e aguarda a resposta do firmware;
5. se a resposta não contiver a palavra `LIMIT`, considera que não houve contato confirmado e interrompe sem iniciar o recuo automático;
6. se passar por essa condição, espera o tempo de permanência;
7. envia `Z_RETRACT`;
8. atualiza a posição e o progresso;
9. se houver exceção, tenta enviar STOP e apresenta a falha.

A GUI move X para cada ponto e depois executa a aproximação Z. A variável local `current` é atualizada com o alvo X após cada ponto. O tempo de permanência começa depois da resposta que a GUI interpreta como contato.

**`_progress` / `_finished`:** atualizam a mensagem de progresso, reabilitam o botão de execução e mostram erro se necessário.

**`_calibration`:** cria entradas para passos/mm dos três eixos, movimento de teste por passos e parâmetros da aproximação Z (descida máxima, velocidade, recuo e permanência).

**`_calibration_move`:** valida passos/velocidade, pede parada de JOG e envia um movimento manual de teste para um único eixo.

**`_apply_z_values`:** verifica descida > 0, velocidade > 0, recuo > 0 e permanência ≥ 0.

**`apply_calibration`:** valida e aplica os fatores passos/mm a cada objeto `Axis`, depois valida os parâmetros Z.

**`save_calibration`:** grava fatores de eixo e parâmetros Z em `calibration.json`.

**`_load_calibration` / `_reload_calibration`:** carregam o JSON se existir. Se o arquivo não existir, ficam os valores padrão. O tratamento atual ignora erros de leitura/formato; isso evita travar a abertura, mas também pode esconder um arquivo de configuração inválido.

**`_terminal` / `_terminal_write` / `send_terminal_command`:** oferecem um campo para enviar comandos de texto diretamente ao firmware e ver uma resposta.

**`_poll_serial`:** a cada 100 ms, pede posição aproximadamente a cada 250 ms quando conectado e quando a análise não está ativa; processa linhas recebidas para atualizar posição/estado dos botões ou mostrá-las no terminal.

**`_update_limit_from_button_line` / `_update_limit_from_limits_line`:** transformam status serial em rótulos “ACIONADO”/“LIVRE”.

**`open_limit_window` / `_poll_limits_window` / `close_limit_window`:** abrem a janela dos dois botões e consultam `LIMITS` a cada 500 ms.

**`_apply_position_line`:** lê uma resposta como `POS X=... Y=... Z=...`; converte contagem de passos para mm e atualiza a posição lógica exibida.

**`refresh_positions`:** escreve as posições em mm com três casas decimais.

**`_jog_press` / `_schedule_jog_refresh` / `_refresh_jog` / `_jog_release` / `_send_jog_stop`:** iniciam JOG ao pressionar, renovam o comando periodicamente e param ao soltar. O código inverte a direção lógica do JOG de X (`-direction if axis == "X" else direction`), mas não faz essa inversão para Y/Z; a correspondência entre +/− na tela e o movimento físico precisa ser verificada no equipamento.

**`stop`:** encerra JOG e envia STOP ao Arduino.

**`connect` / `disconnect`:** conectam à porta escolhida e encerram JOG/janela de limites antes de fechar a comunicação.

**`zero`:** envia `ZERO` ao Arduino e zera as posições lógicas Python. Isso não faz homing.

**`_colors` / `toggle_dark_mode` / `_apply_theme`:** aplicam tema claro/escuro.

**`close`:** fecha a janela de limites, tenta parar JOG, desconecta e destrói a janela.

### 4.7 `src/GUI/analysis_scroll.py`

A função `install_analysis_scroll(MainWindow)` define versões novas de `_analysis` e `create_point_fields` e atribui essas funções à classe recebida. O efeito é que a lista de pontos passa a ficar em um Canvas com barra de rolagem. A execução real continua em `MainWindow.execute_analysis` e `MainWindow._analysis_worker`.

### 4.8 `src/GUI/spatial_map.py`

A classe `SpatialMap` desenha um corpo de prova 2D (círculo ou quadrado), permite zoom, adicionar/selecionar/apagar pontos e editar coordenadas X/Y. Ela:
- converte coordenadas mm ↔ pixels;
- impede que pontos sejam colocados fora da geometria escolhida;
- mantém uma lista de dicionários `{"x": ..., "y": ...}`;
- redesenha mapa e lista ao alterar pontos/tema.

**Limitação atual:** o mapa mantém seus pontos internamente e não está ligado à sequência de análise X. Os pontos desenhados no mapa não são enviados automaticamente aos motores. A aba Análise usa uma lista separada de coordenadas X.

## 5. Firmware Arduino de teste

Arquivo: `arduino_tests/controlador_arduino_python_A.ino`.

### Pinagem declarada no sketch

- X STEP D2 / DIR D5
- Y STEP D3 / DIR D6
- Z STEP D4 / DIR D7
- ENABLE D8
- botão superior A1
- botão inferior D11
- nível declarado como pressionado: HIGH

O sketch declara a convenção lógica `Z+ = descida` e `Z- = subida`. Essa convenção lógica precisa coincidir com o sentido mecânico real.

### Partes principais

- **Constantes:** baud rate, pinos, duração do pulso STEP, timeout do JOG, tempo para desligar drivers ociosos e limites de software X/Y.
- **`stepPin` / `dirPin` / `axisIndex` / `validAxis`:** traduzem nome do eixo para pino/índice e validam X/Y/Z.
- **`zTopPressed` / `zBottomPressed`:** leem os botões.
- **`validSpeed` / `intervalUs` / `pulseStep`:** validam velocidade e geram os pulsos STEP.
- **`enableDrivers` / `disableDrivers`:** habilitam/desabilitam os drivers pelo pino ENABLE (no A4988, ENABLE em LOW habilita).
- **`softLimitBlocks`:** bloqueia movimento além dos limites de passos X/Y definidos no sketch; não é uma medição de posição real.
- **`setDirection`:** define o pino DIR e espera brevemente para estabilização.
- **`zLimitBlocks`:** escolhe qual botão bloqueia cada sentido de movimento Z.
- **`startMove`:** valida comando, exige o controlador ocioso, verifica limites e começa movimento finito.
- **`startJog`:** começa ou renova JOG contínuo; rejeita comandos incompatíveis enquanto outro movimento está ativo.
- **`startZApproach`:** prepara a aproximação Z com limite de passos.
- **`startZRetract`:** prepara a subida por quantidade definida de passos.
- **`executeMotion`:** executado repetidamente pelo `loop`; verifica limites, gera um pulso por iteração, atualiza contador e emite status de conclusão.
- **`handleCommand`:** interpreta comandos seriais `PING`, `STATUS`, `LIMITS`, `POS`, `ZERO`, `MOVE`, `JOG_START`, `JOG_STOP`, `STOP`, `Z_APPROACH` e `Z_RETRACT`.
- **`readSerial`:** acumula caracteres até newline e chama o interpretador de comandos.
- **`setup`:** configura pinos e serial.
- **`loop`:** lê comandos, executa movimento e desabilita drivers após o período ocioso configurado.

### Protocolo serial usado pela aplicação

| Comando | Finalidade |
|---|---|
| `PING` | Verifica comunicação; espera `PONG`. |
| `STATUS` | Consulta modo do firmware. |
| `LIMITS` | Lê estado dos botões. |
| `POS` | Lê contadores X/Y/Z em passos. |
| `ZERO` ou `ZERO X` | Zera um ou todos os contadores. |
| `MOVE X <passos_com_sinal> <passos/s>` | Movimento finito de um eixo. |
| `JOG_START X <+1 ou -1> <passos/s>` | Inicia/renova JOG. |
| `JOG_STOP` | Para JOG. |
| `STOP` | Para o modo de movimento atual. |
| `Z_APPROACH <passos_de_descida> <passos/s> <passos_de_recuo>` | Inicia aproximação limitada por botão ou passos máximos. |
| `Z_RETRACT <passos> <passos/s>` | Sobe pelo número de passos solicitado. |

O protocolo é texto ASCII com newline no fim de cada comando. O firmware e Python precisam concordar exatamente sobre nomes e formato das respostas.

## 6. Sequência de análise pretendida

A intenção do fluxo Python é:

1. ir até a coordenada X do ponto;
2. descer Z até o firmware informar o status interpretado como contato, limitado por uma quantidade máxima de passos;
3. esperar o tempo de permanência configurado;
4. subir Z pela distância de recuo configurada;
5. avançar para o próximo X.

A descida máxima não significa que a máquina sempre deva percorrer essa distância: ela deveria funcionar como limite de segurança. Se o botão de contato não for detectado antes de esgotar os passos, a GUI deve interromper e não iniciar o recuo automático como se o contato tivesse ocorrido.

## 7. Pontos de atenção conhecidos antes de teste físico

**Leia esta seção antes de usar a sequência automática.** São observações do código atual, não correções aplicadas.

1. **Possível conflito na identificação do botão de contato.** A GUI chama `Z_APPROACH` de aproximação/contato, mas o sketch atual inicia o movimento Z+ e `zLimitBlocks(+1)` verifica `zTopPressed()`. O rótulo da GUI chama o botão inferior D11 de “Z+”, enquanto o firmware verifica o botão superior para bloquear Z+. É necessário confirmar a ligação real, o sentido real e a função pretendida de cada botão antes de confiar no limite.
2. **A resposta `LIMIT_TOP` pode ser confundida com contato.** Se o botão superior já estiver pressionado ao iniciar, o firmware responde `Z_APPROACH_READY LIMIT_TOP`. A GUI testa apenas se a resposta contém a palavra `LIMIT`; portanto, ela pode aceitar `LIMIT_TOP` como se fosse o contato esperado, esperar e mandar recuar. A validação deve ser mais específica depois que o status correto do botão de contato estiver definido.
3. **O parâmetro `retract_steps` de `Z_APPROACH` não é usado pelo sketch atual para recuar automaticamente.** A GUI envia esse número no comando, mas o firmware apenas o recebe e não o usa na rotina `startZApproach`. O recuo é comandado separadamente pela GUI com `Z_RETRACT`.
4. **`dwell_ms` em `ArduinoController.z_approach` não é enviado nem usado.** O tempo de permanência atual é implementado com `time.sleep(dwell)` no worker Python depois do status interpretado como contato.
5. **As posições são estimativas.** `POS` representa contadores de passos, não sensores de posição absoluta. Perda de passos ou um ZERO feito em local desconhecido torna a posição exibida diferente da real.
6. **A comunicação serial tem um único canal.** `send()` limpa a fila de respostas antes de enviar; não se deve presumir que vários comandos/threads possam esperar respostas independentes com segurança.
7. **Os parâmetros 400 passos/mm são provisórios.** Calibrar cada eixo e registrar o resultado medido antes de movimentos de precisão.
8. **Os testes automatizados atuais validam principalmente contas e o modelo.** Eles não simulam os botões reais, o A4988, a mecânica, o sentido dos eixos nem a resposta física a um STOP.

**Regra de operação do projeto:** movimentar somente um eixo por vez, testar primeiro com movimento pequeno e área livre, manter acesso ao botão/parada e não tentar descobrir o limite máximo queimando drivers. Antes da automação de contato, resolver e testar os itens 1 e 2.

## 8. Testes automatizados

A partir da raiz do repositório:

```powershell
pytest
```

Os testes de `test_axis.py` verificam conversão de distância em passos, movimento positivo/negativo, posição zero e atualização da posição teórica. Os testes de `test_machine.py` verificam o agrupamento dos três eixos e o zero lógico. Passar nesses testes não prova que o motor se desloca exatamente a distância prevista.

## 9. Como executar a GUI

Na pasta do projeto, no PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run_gui.py
```

Se o ambiente virtual ainda não existir, crie-o antes com `python -m venv .venv`. Verifique a porta COM e confirme a comunicação com o Arduino de teste. Não faça upload de firmware para a placa original da máquina como parte desta etapa.

## 10. Método para evoluir depois da v0.1.0

Para cada mudança:
1. identificar o comportamento desejado;
2. apontar quais arquivos precisam mudar;
3. explicar o papel de cada alteração antes de aplicá-la;
4. manter a v0.1.0 como referência imutável;
5. fazer mudanças pequenas, com commits claros;
6. executar testes automatizados;
7. testar comunicação sem motor e depois um eixo por vez;
8. validar os limites físicos antes de testar aproximação automática;
9. registrar o que foi testado em software e o que foi efetivamente testado na máquina.

Não afirmar que um recurso é seguro ou validado fisicamente só porque o código compila ou os testes de matemática passam.

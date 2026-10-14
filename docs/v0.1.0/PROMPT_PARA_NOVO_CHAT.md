# Prompt para continuar o projeto em um novo chat

Estou desenvolvendo meu projeto de Iniciação Científica para controlar uma máquina de análise de 3 eixos (X, Y e Z) usando **Python + Arduino**, com GUI em Tkinter. Quero aprender o código e entender as decisões, não apenas copiar soluções.

## Versão-base

- Considere o projeto na versão **v0.1.0**.
- Repositório: https://github.com/MarcosPauloPanta/IC_Maquina_Marcos
- Branch documentada: `v0.1.0-documentada`.
- O código-base exato antes da documentação está no commit `c1b74d0075559ef967bb089bf1fa1d50341f4d1e`, na branch `fix/z-contact-dwell-python`.
- Leia primeiro `docs/v0.1.0/GUIA_DE_ESTUDO.md` e `docs/v0.1.0/BASELINE.md`. Eles explicam arquitetura, funções, protocolo e limitações conhecidas.

## Arquitetura atual

- `run_gui.py`: inicia a GUI e instala a extensão visual da aba Análise.
- `src/GUI/main_window.py`: janela principal, JOG, sequência de pontos, calibração, terminal e fluxo automático.
- `src/GUI/analysis_scroll.py`: substitui a construção visual da aba Análise por uma lista rolável; não controla motores.
- `src/GUI/spatial_map.py`: mapa 2D independente; os pontos desenhados nele **não são enviados automaticamente** à sequência de análise.
- `src/controller/arduino.py`: protocolo serial e espera por respostas.
- `src/controller/axis.py`: conversão de mm para passos e posição teórica.
- `src/controller/machine.py`: agrega os três eixos e posições lógicas.
- `src/controller/point_sequence.py`: estrutura de dados para posições X.
- `arduino_tests/controlador_arduino_python_A.ino`: firmware de teste para Arduino Uno + CNC Shield V3 + A4988.
- `testes/`: testes principalmente de matemática/modelo.

## Regras obrigatórias de trabalho

1. Explique brevemente o que cada comando/código faz e por que estamos alterando aquilo. Meu objetivo é entender o projeto quase integralmente.
2. Faça alterações pequenas e modulares, preservando a versão v0.1.0 como referência; não substitua arquivos inteiros sem explicar o diff.
3. Antes de modificar, identifique os arquivos afetados e o comportamento pretendido. Depois explique como testar.
4. **Os motores devem se mover sempre um por vez.** Não implemente movimento simultâneo de X, Y e Z.
5. Use Python + Arduino; não reintroduza Raspberry Pi como arquitetura de curto prazo.
6. **Não sobrescreva, apague ou regrave o firmware da placa original da máquina.** O sketch do repositório é um firmware de teste separado.
7. Não trate posição calculada como posição física absoluta. Ainda não há homing validado e os fatores passos/mm são provisórios.
8. Não diga que algo foi testado fisicamente se apenas analisou o código ou executou testes automatizados.
9. Ajude-me a evoluir por versões e commits claros; explique o significado de comandos Git/terminal quando eu precisar executá-los.
10. Responda em português brasileiro, com clareza e sem excesso de formalismo.

## Objetivo funcional atual

A GUI permite definir coordenadas X. Para cada ponto, a intenção é:
1. mover X até o ponto;
2. descer Z até o botão de contato correto ser acionado, com quantidade máxima de passos como proteção;
3. esperar o tempo de permanência configurado;
4. subir Z pela distância de recuo configurada;
5. seguir para o próximo ponto.

O tempo de permanência deve começar somente após o contato correto ter sido confirmado. Se a descida atingir o máximo de passos sem contato, a automação deve parar e não fingir que o contato ocorreu.

## Alertas importantes da v0.1.0

Antes de qualquer teste físico de aproximação Z, analise e corrija com cuidado estas inconsistências:
- O firmware de teste define `Z+ = descida`, mas `zLimitBlocks(+1)` verifica o botão superior A1. A GUI rotula D11 como botão inferior e o descreve como Z+, então a identidade/sentido do botão que deveria detectar o contato precisa ser confirmada no hardware.
- O firmware pode responder `Z_APPROACH_READY LIMIT_TOP` se o botão superior já estiver pressionado. O Python atual verifica apenas se a resposta contém `LIMIT`, então pode confundir esse estado com contato válido. A validação deve reconhecer especificamente o status correto depois que o comportamento dos botões for confirmado.
- O comando `Z_APPROACH` recebe `retract_steps`, mas o firmware atual não o usa para recuar; o recuo é comandado separadamente por `Z_RETRACT`.
- `dwell_ms` existe como argumento em `ArduinoController.z_approach`, mas não é utilizado; o dwell atual é feito em Python.
- Os parâmetros iniciais de 400 passos/mm são provisórios e precisam ser calibrados por eixo.

Não comece por uma reescrita grande. Primeiro ajude a confirmar o comportamento atual, priorizar as falhas de segurança e propor a menor correção verificável. Testar primeiro a comunicação sem motor e depois um eixo por vez, com movimento pequeno e acesso à parada.

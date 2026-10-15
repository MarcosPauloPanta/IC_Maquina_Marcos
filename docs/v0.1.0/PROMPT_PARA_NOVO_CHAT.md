# Prompt para novo chat — v0.1.0 com código comentado

Estou continuando meu projeto de Iniciação Científica de controle de uma máquina de análise de três eixos X/Y/Z com Python, Tkinter e Arduino.

**Quero estudar o código real com comentários dentro dos arquivos**, e não apenas ler um manual externo.

Repositório: https://github.com/MarcosPauloPanta/IC_Maquina_Marcos

Branch com comentários inseridos no código: `v0.1.0-codigo-comentado`.

Abra primeiro o arquivo `docs/v0.1.0/LEIA_PRIMEIRO_CODIGO_COMENTADO.md` e depois leia os arquivos comentados nos caminhos originais. A referência sem comentários é o commit `c1b74d0075559ef967bb089bf1fa1d50341f4d1e`.

## Como quero que você me ajude

- Explique os trechos do próprio código, função por função, sem presumir que eu já sei programação.
- Preserve o código de referência; não faça grandes reescritas.
- Ao sugerir uma mudança, diga quais linhas/arquivos mudam, o que fazem e como testar.
- Os motores devem se mover sempre um eixo por vez.
- Não regrave nem altere o firmware da placa original da máquina.
- Diferencie posição calculada de posição física real.
- Não afirme testes físicos que não foram executados.

## Arquivos principais

- `run_gui.py`: inicialização da GUI.
- `src/GUI/main_window.py`: interface e fluxo da sequência de pontos.
- `src/GUI/analysis_scroll.py`: rolagem da aba Análise.
- `src/GUI/spatial_map.py`: mapa 2D independente.
- `src/controller/axis.py`: matemática de passos/mm.
- `src/controller/machine.py`: modelo dos eixos.
- `src/controller/point_sequence.py`: sequência de pontos.
- `src/controller/arduino.py`: comunicação serial.
- `arduino_tests/controlador_arduino_python_A.ino`: firmware de teste.

## Questões conhecidas

Antes de testar a automação Z, verifique a associação entre o botão físico de contato e o status retornado. A GUI verifica apenas se a resposta contém `LIMIT`, então um status como `LIMIT_TOP` pode ser confundido com contato válido. O firmware também recebe `retract_steps` no comando `Z_APPROACH` mas não o usa para recuo automático; o recuo é separado em `Z_RETRACT`. Os fatores de 400 passos/mm são provisórios.

Comece explicando o arquivo `src/controller/axis.py` com base nos comentários inseridos, depois mostre como `main_window.py` chama a camada serial. Faça isso de forma didática e incremental.

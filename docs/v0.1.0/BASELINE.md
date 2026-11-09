# Baseline — v0.1.0 consolidada

## Identificação

- Projeto: IC_Maquina_Marcos
- Repositório: https://github.com/MarcosPauloPanta/IC_Maquina_Marcos
- Branch oficial de referência: `main`
- Versão documental: `v0.1.0` (primeira versão pública consolidada)
- Commit de integração inicial: `17e1306ca69908bf7cf7fa3d157d95339e800d97`
- Pull Request de integração: [#1 — Add per-point dwell and Z contact-aware analysis](https://github.com/MarcosPauloPanta/IC_Maquina_Marcos/pull/1)

## O que esta versão contém

A versão consolidada reúne a GUI Python/Tkinter, o modelo lógico dos eixos, a comunicação serial, a sequência de análise por pontos, a calibração configurável, o mapa espacial 2D e o firmware de teste Arduino em `firmware/controller.ino`.

A sequência de análise permite configurar X e tempo de permanência para cada ponto. A execução automática usa 500 passos/s em X e Z, move um eixo por vez, realiza aproximação Z, aguarda a permanência individual e comanda a retração antes de avançar.

## Arquivos centrais

- `run_gui.py`
- `src/GUI/main_window.py`
- `src/GUI/analysis_scroll.py`
- `src/GUI/spatial_map.py`
- `src/controller/arduino.py`
- `src/controller/axis.py`
- `src/controller/machine.py`
- `src/controller/point_sequence.py`
- `firmware/controller.ino`
- `arduino_tests/`
- `testes/`

## Interpretação do baseline

O commit `17e1306...` registra a integração da branch `feat/analysis-per-point-dwell` na `main`. Os commits seguintes de documentação atualizam README, instruções e arquivos em `docs/v0.1.0/`; portanto, o HEAD atual da `main` é o baseline publicado completo, não apenas o commit de integração.

Branches antigas foram mantidas como histórico de desenvolvimento. A branch `main` é a referência oficial para baixar e estudar a versão consolidada.

## Estado de validação

- Estrutura e responsabilidades do software: documentadas.
- Protocolo serial e firmware de teste: documentados a partir dos arquivos publicados.
- Testes automatizados: existem testes de matemática/modelo; execute `python -m pytest` no ambiente local para verificar o resultado atual.
- Teste físico integral da sequência automática: não declarado como concluído.
- Calibração física de todos os eixos e homing: não declarados como validados.
- Firmware original da máquina: deve permanecer preservado, sem sobrescrita.

**Importante:** versão documentada não significa máquina certificada, calibrada ou validada em operação real.

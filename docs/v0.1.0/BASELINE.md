# Identificação da versão

- **Versão de referência:** v0.1.0
- **Repositório:** https://github.com/MarcosPauloPanta/IC_Maquina_Marcos
- **Branch com documentação:** `v0.1.0-documentada`
- **Branch de código usada como base:** `fix/z-contact-dwell-python`
- **Commit exato do código antes de adicionar esta documentação:** `c1b74d0075559ef967bb089bf1fa1d50341f4d1e`
- **Commit que adicionou o guia:** `10bac025bc96a50eb22353b6a86bb2684cafd5eb`

## O que significa esta referência

A pasta `docs/v0.1.0/` documenta a base do projeto. Os arquivos de código originais continuam nos seus caminhos habituais (`src/`, `arduino_tests/`, `testes/`). O código-base não foi reescrito para inserir comentários, evitando alterar comportamento só para documentar.

Para comparar ou recuperar exatamente o código anterior à documentação, use o commit `c1b74d0075559ef967bb089bf1fa1d50341f4d1e`. Para ler o guia na branch documentada, abra `docs/v0.1.0/GUIA_DE_ESTUDO.md`.

## Arquivos principais congelados no baseline

- `run_gui.py`
- `src/GUI/main_window.py`
- `src/GUI/analysis_scroll.py`
- `src/GUI/spatial_map.py`
- `src/controller/arduino.py`
- `src/controller/axis.py`
- `src/controller/machine.py`
- `src/controller/point_sequence.py`
- `arduino_tests/controlador_arduino_python_A.ino`
- `testes/test_axis.py`
- `testes/test_machine.py`

## Estado de validação

- Documentação de estrutura e fluxo: registrada.
- Testes automatizados: existem testes para matemática/modelo; execute `pytest` localmente para confirmar o estado do ambiente.
- Teste físico da sequência automática Z: **não confirmado**.
- Firmware da placa original da máquina: **não deve ser sobrescrito**.

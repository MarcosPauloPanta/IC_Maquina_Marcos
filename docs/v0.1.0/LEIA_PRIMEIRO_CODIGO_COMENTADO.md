# v0.1.0 — código comentado por dentro

Esta branch é uma cópia do código de referência com explicações inseridas **dentro dos próprios arquivos**.

## Como usar

- **Branch:** `v0.1.0-codigo-comentado`
- **Base de código:** `fix/z-contact-dwell-python`
- **Commit de referência anterior aos comentários:** `c1b74d0075559ef967bb089bf1fa1d50341f4d1e`

Os arquivos Python continuam nos mesmos caminhos (`run_gui.py`, `src/GUI/`, `src/controller/`, `testes/`) e os sketches Arduino continuam em `arduino_tests/`. Assim, é possível abrir cada arquivo no editor e estudar comentários ao lado do código que explicam.

## O que foi adicionado

- Docstrings no início dos módulos, explicando a responsabilidade do arquivo.
- Comentários `## O QUE FAZ` junto a classes e funções Python.
- Comentários `// ESTUDO` antes das funções principais do firmware Arduino.
- Explicações adicionais em trechos delicados: threads, comunicação serial, posição estimada, limites e aproximação Z.

As alterações pretendem adicionar apenas documentação. As docstrings de módulo passam a preencher o atributo Python `__doc__`, mas não mudam a lógica de movimento. Nenhum teste físico é declarado como realizado.

## Limitações e avisos

- A documentação explica o comportamento existente, não garante que esteja correto ou seguro.
- A lógica de identificação do contato Z tem inconsistências conhecidas; consulte `GUIA_DE_ESTUDO.md`.
- O firmware é de teste. Não o grave na placa original da máquina.
- A cópia comentada é uma branch separada; a versão de referência permanece disponível no commit indicado acima.

## Próximo passo sugerido

Abra `src/controller/axis.py` primeiro, pois contém a matemática mais simples; depois estude `machine.py`, `arduino.py` e finalmente `src/GUI/main_window.py`. Leia `arduino_tests/controlador_arduino_python_A.ino` junto com `arduino.py` para relacionar os comandos Python às respostas do firmware.

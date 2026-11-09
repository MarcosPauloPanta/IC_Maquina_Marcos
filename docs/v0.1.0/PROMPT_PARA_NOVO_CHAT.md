# Continuidade do projeto — contexto para uma próxima sessão

Estou desenvolvendo o projeto de Iniciação Científica IC_Maquina_Marcos, um sistema experimental de controle de uma máquina de três eixos X/Y/Z usando Python, GUI Tkinter e Arduino.

## Versão de referência

- Repositório: https://github.com/MarcosPauloPanta/IC_Maquina_Marcos
- Branch oficial: `main`
- Versão documental: v0.1.0 consolidada.
- Leia primeiro:
  - `docs/v0.1.0/BASELINE.md`
  - `docs/v0.1.0/GUIA_DE_ESTUDO.md`
  - `docs/v0.1.0/PROTOCOLO_E_FIRMWARE.md`
  - `docs/v0.1.0/VALIDACAO_E_SEGURANCA.md`

## Arquitetura

- `run_gui.py`: inicia a GUI.
- `src/GUI/main_window.py`: janela principal, operação, análise, calibração e terminal.
- `src/GUI/analysis_scroll.py`: lista rolável com X e tempo de permanência por ponto.
- `src/GUI/spatial_map.py`: mapa 2D independente da sequência de análise.
- `src/controller/arduino.py`: comunicação serial.
- `src/controller/axis.py`: conversão mm/passos e posição teórica.
- `src/controller/machine.py`: modelo lógico dos eixos.
- `src/controller/point_sequence.py`: estrutura de pontos X.
- `firmware/controller.ino`: firmware de teste para Arduino Uno/CNC Shield V3/A4988.
- `arduino_tests/`: testes e sketches auxiliares.
- `testes/`: testes automatizados de modelo.

## Regras obrigatórias

1. Explique o que cada mudança faz e por que é necessária; meu objetivo é entender o código.
2. Faça alterações pequenas, modulares e documentadas.
3. Preserve o firmware original da máquina e seu backup. Nunca o sobrescreva nem o regrave.
4. Os motores devem ser comandados um por vez.
5. Não trate posição por contagem de passos como posição física absoluta.
6. Não afirme validação física quando só houver análise de código ou testes automatizados.
7. Antes de qualquer teste físico, revise a documentação de segurança e confirme placa, pinagem, botões, sentidos e parada.
8. Use Python + Arduino como arquitetura do projeto.

## Comportamento da análise publicado

A GUI captura uma lista de coordenadas X e tempos de permanência individuais. Para cada ponto, desloca X (se necessário), inicia aproximação Z, espera um status válido, aguarda o dwell daquele ponto e comanda retração Z antes de avançar. A velocidade da análise é fixa em 500 passos/s para X e Z.

A aproximação termina se qualquer botão Z for detectado ou se a quantidade máxima de passos for concluída. A GUI trata esses status como chegada; portanto, o fim por MAX_STEPS não prova contato físico. A retração é um comando separado.

## Limitações que devem permanecer visíveis

- Calibração inicial 400 passos/mm é provisória.
- Sem homing validado, ZERO é apenas uma referência lógica.
- Os botões são declarados como HIGH quando pressionados no sketch; confirmar circuito e pinagem reais.
- A retração é bloqueada pelo botão superior.
- O mapa 2D não alimenta automaticamente a análise.
- Os testes Python não validam motores, eletrônica ou segurança física.

Antes de propor mudanças, leia os arquivos atuais da branch `main` e compare-os com esta documentação. Não presuma que uma descrição antiga corresponde ao código atual.

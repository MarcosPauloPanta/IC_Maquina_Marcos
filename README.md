# IC_Maquina_Marcos

Projeto de Iniciação Científica para desenvolvimento de um sistema de controle experimental de uma máquina de três eixos (X, Y e Z), com interface em Python/Tkinter e controle de motores por Arduino.

> **Versão pública de referência:** v0.1.0 consolidada na branch `main`.  
> **Estado:** versão de software documentada; validação física integral da máquina ainda não declarada.

## Visão geral

A aplicação permite conectar-se ao Arduino por comunicação serial, acompanhar posições estimadas, operar os eixos por JOG, configurar calibração, definir uma sequência de pontos de análise em X e visualizar um mapa espacial 2D.

A sequência automática de análise opera os eixos **um por vez**: desloca X até cada ponto, executa a aproximação de Z, aguarda o tempo de permanência individual daquele ponto e comanda a retração de Z antes de avançar.

## Arquitetura

`GUI Tkinter` → `ArduinoController` → USB/serial → `firmware/controller.ino` → CNC Shield V3 → drivers A4988 → motores.

| Caminho | Responsabilidade |
|---|---|
| `run_gui.py` | Ponto de entrada da aplicação; instala a extensão visual rolável da aba Análise. |
| `src/GUI/main_window.py` | Janela principal, abas, JOG, análise, calibração, terminal e coordenação dos movimentos. |
| `src/GUI/analysis_scroll.py` | Lista rolável de pontos da aba Análise. |
| `src/GUI/spatial_map.py` | Mapa 2D para criar e editar pontos visuais; não comanda motores nem alimenta automaticamente a sequência de análise. |
| `src/controller/arduino.py` | Comunicação serial, envio de comandos e espera por respostas do firmware. |
| `src/controller/axis.py` | Conversão matemática entre mm, passos e posição teórica. |
| `src/controller/machine.py` | Agrupa os modelos dos eixos X, Y e Z. |
| `src/controller/point_sequence.py` | Estrutura de dados para uma sequência ordenada de posições X. |
| `firmware/controller.ino` | Firmware de teste para Arduino Uno, CNC Shield V3 e A4988. |
| `arduino_tests/` | Sketches e experimentos de comunicação e acionamento usados durante o desenvolvimento. |
| `testes/` | Testes automatizados do modelo matemático e da máquina lógica. |
| `requirements.txt` | Dependências Python. |
| `docs/v0.1.0/` | Documentação técnica, estado da versão e orientações de validação. |

## Recursos da interface

- **Operação:** conexão serial, posições estimadas, JOG individual por eixo, parada e zero lógico.
- **Análise:** sequência de coordenadas X, tempo de permanência individual por ponto e velocidade automática fixa de 500 passos/s para X e Z.
- **Calibração:** fatores passos/mm por eixo e parâmetros de aproximação/retração/permanência de Z; os valores podem ser salvos localmente em `calibration.json`.
- **Terminal:** envio manual de comandos seriais.
- **Mapa Espacial:** desenho/edição de pontos em uma geometria 2D; atualmente independente da sequência de análise.

## Requisitos e execução

- Python compatível com as dependências listadas em `requirements.txt`.
- Arduino/firmware de teste compatível com o protocolo descrito em `docs/v0.1.0/PROTOCOLO_E_FIRMWARE.md`.
- Conexão USB serial e drivers eletrônicos adequados.

No PowerShell, a partir da raiz do repositório:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python run_gui.py
```

Para executar os testes automatizados:

```powershell
python -m pytest
```

Para gerar um executável Windows, pode-se usar PyInstaller (não incluído nas dependências obrigatórias do projeto):

```powershell
python -m pip install pyinstaller
python -m PyInstaller --onefile run_gui.py
```

O executável é gerado em `dist/`. O arquivo `.spec` gerado/configurado pelo PyInstaller pode ser versionado quando fizer parte do processo de empacotamento do laboratório.

## Estado, calibração e limitações

- A posição apresentada é **estimada por contagem de passos**, não medida por encoder ou sistema de homing validado.
- O comando ZERO define uma referência lógica no local atual; não procura fisicamente a origem.
- Os fatores iniciais de 400 passos/mm no código são valores provisórios, não uma calibração física universal dos três eixos.
- O mapa espacial 2D é visual e independente da sequência automática de X.
- Os testes Python cobrem principalmente cálculos e o modelo lógico. Eles não comprovam precisão mecânica, comportamento dos botões, integridade elétrica ou segurança física.
- O firmware em `firmware/controller.ino` é um firmware de teste. **Não sobrescreva nem regrave o firmware original da máquina.**

## Segurança antes de qualquer ensaio físico

1. Confirmar a placa conectada, a pinagem real, a polaridade dos botões e o sentido mecânico de cada eixo.
2. Preservar o firmware original e seu backup.
3. Testar primeiro a comunicação sem motores e, depois, um eixo por vez, com deslocamentos pequenos.
4. Manter STOP e corte de energia acessíveis.
5. Confirmar os limites superior/inferior de Z e a resposta de parada antes de aproximar uma amostra.
6. Não considerar a posição lógica como posição física absoluta.
7. Interromper o ensaio se a resposta dos botões ou o sentido de movimento divergir do esperado.

A documentação registra o comportamento implementado e as limitações conhecidas; não equivale a certificação de segurança nem a declaração de testes físicos concluídos.

## Documentação detalhada

- [Estado da versão e baseline](docs/v0.1.0/BASELINE.md)
- [Guia de estudo e arquitetura](docs/v0.1.0/GUIA_DE_ESTUDO.md)
- [Protocolo serial e firmware](docs/v0.1.0/PROTOCOLO_E_FIRMWARE.md)
- [Validação, testes e segurança](docs/v0.1.0/VALIDACAO_E_SEGURANCA.md)
- [Prompt para continuidade do projeto](docs/v0.1.0/PROMPT_PARA_NOVO_CHAT.md)

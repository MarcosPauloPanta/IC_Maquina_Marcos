# IC_Maquina_Marcos

Projeto de Iniciação Científica para controle experimental de uma máquina de três eixos (X, Y e Z).

## Arquitetura

GUI Python -> modelo matemático / máquina -> comunicação serial -> Arduino -> A4988 -> motores.

- axis.py: matemática de um eixo.
- machine.py: coordenação dos eixos e posição lógica.
- arduino.py: comunicação serial.
- gui/main_window.py: interface do operador.
- testes/: testes automatizados.

## Estado importante

A posição mostrada pela aplicação é posição estimada, não uma medição física absoluta. Sem homing ou sensor de referência, zerar a máquina significa definir um zero lógico na posição atual.

Os valores de passos/mm usados pela GUI são provisórios e devem ser substituídos pelos parâmetros experimentais calibrados.

## Executar

No PowerShell, a partir da raiz:

    .\.venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    python run_gui.py

Testes:

    pytest

## Protocolo serial provisório

A GUI atualmente monta comandos como:

    MOVE X 1 1000
    MOVE Z -1 500

O sketch Arduino deverá implementar exatamente o protocolo escolhido antes de movimentos reais.

## Segurança

O controlador original da máquina deve permanecer preservado.

Antes de liberar movimentos reais:

1. testar comunicação sem motor;
2. testar um eixo por vez;
3. validar limites e sentidos;
4. integrar os dois botões de segurança do eixo Z;
5. definir comportamento para perda de comunicação;
6. só então executar movimentos maiores.

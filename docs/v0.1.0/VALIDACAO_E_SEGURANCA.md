# Validação, testes e segurança — v0.1.0

## 1. O que está coberto por testes automatizados

Os arquivos em `testes/` verificam principalmente:
- conversão de deslocamento em mm para passos/microsteps;
- direção positiva, negativa e deslocamento nulo;
- atualização da posição teórica;
- agrupamento dos três eixos no modelo `Machine`;
- zero lógico de um eixo sem alterar os demais.

Execute na raiz do repositório:

```powershell
python -m pip install -r requirements.txt
python -m pytest
```

Os testes automatizados não acionam motores, botões, drivers ou mecânica. Um resultado aprovado demonstra somente que os casos de software testados passaram.

## 2. O que não está comprovado

Não declarar como concluídos sem ensaio específico:
- precisão dimensional real de X/Y/Z;
- calibração final em passos/mm;
- homing ou referência absoluta;
- sentido físico dos eixos;
- polaridade/acionamento real dos botões;
- parada física segura em todas as condições;
- comportamento após perda de USB/serial ou travamento do computador;
- sequência automática completa com amostra;
- operação prolongada sem aquecimento ou perda de passos.

## 3. Alertas do estado publicado

1. **Posição estimada:** o valor exibido vem de contagem de passos. Perda de passos, folga, escorregamento ou ZERO em posição desconhecida podem causar divergência física.
2. **Calibração provisória:** o valor inicial de 400 passos/mm não substitui medição individual por eixo.
3. **Aproximação Z:** qualquer um dos botões (superior ou inferior) pode encerrar a aproximação; o esgotamento de `down_steps` também encerra e é tratado pela GUI como chegada válida. O operador deve entender que `MAX_STEPS` não confirma contato com a amostra.
4. **Retração:** é comandada separadamente após o tempo de permanência. Se o botão superior estiver pressionado, o firmware bloqueia a subida.
5. **Entradas elétricas:** o sketch declara HIGH como pressionado e configura entradas INPUT. A ligação real deve ser conferida; uma entrada flutuante pode produzir leituras incorretas se o circuito não fornecer nível definido.
6. **STOP:** a parada enviada pela GUI depende do canal serial e do firmware. Não substitui botão físico de emergência/corte de energia.
7. **Mapa espacial:** pontos desenhados no mapa 2D não são integrados automaticamente à sequência de análise.
8. **Comunicação:** a GUI e o Arduino compartilham um único fluxo serial; não presumir segurança para múltiplos comandos concorrentes.

## 4. Roteiro recomendado de validação

Executar somente com autorização e supervisão do laboratório:

### Etapa A — inspeção sem movimento
- Identificar a placa conectada e confirmar que não é a placa original com firmware que deve ser preservado.
- Conferir alimentação, aterramento, drivers, corrente ajustada, conectores e pinagem.
- Conferir como os botões superior e inferior estão ligados e qual nível lógico produzem em repouso/acionados.
- Manter a parada/corte de energia acessível.

### Etapa B — comunicação sem motores
- Conectar em baud rate correto.
- Testar `PING`/`PONG`.
- Consultar `STATUS`, `LIMITS` e `POS`.
- Acionar cada botão manualmente e confirmar que somente o estado esperado muda.

### Etapa C — movimento controlado
- Testar um eixo por vez.
- Usar velocidade e deslocamento pequenos.
- Confirmar sentido físico e atualização do contador.
- Testar STOP e limites em condições controladas, sem aproximar amostra.

### Etapa D — sequência de análise
- Somente depois de validar botões e sentidos, executar sem amostra e com parâmetros conservadores.
- Confirmar X, descida Z, status recebido, temporização individual e retração.
- Testar separadamente o fim por botão e o fim por MAX_STEPS.
- Registrar resultado, data, configuração e qualquer anomalia.

### Etapa E — amostra
- Só avançar após revisão dos resultados anteriores e autorização do responsável pelo equipamento.
- Manter operador junto à máquina e parada acessível durante todo o ensaio.

## 5. Registro de validação

Preencha este registro quando os ensaios forem realizados. Não marque como aprovado sem evidência.

| Item | Estado nesta publicação |
|---|---|
| Testes Python automatizados | Disponíveis; executar no ambiente local |
| Comunicação serial | Já desenvolvida; verificar na bancada |
| JOG de cada eixo | Implementado; validação física deve ser registrada |
| Limites físicos Z | Implementados no sketch; ligação/sentido exigem confirmação |
| Análise por pontos | Implementada no software; sequência física integral não declarada como validada |
| Calibração dimensional final | Não declarada como concluída |
| Homing físico | Não declarado como implementado/validado |
| Segurança funcional integral | Não certificada |

## 6. Regra de preservação

O firmware original da máquina e seu backup devem permanecer intactos. `firmware/controller.ino` é um sketch de teste deste projeto e não deve ser usado para sobrescrever a placa original.

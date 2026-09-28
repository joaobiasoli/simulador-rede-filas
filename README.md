# Simulador de Redes de Filas — T1 (Simulação e Métodos Analíticos)

Simulador de eventos discretos para redes de filas com **qualquer topologia**
(G/G/c/K, capacidade finita ou infinita, roteamento probabilístico, inclusive
retorno para a própria fila). A entrada é um arquivo `.yml` no mesmo estilo do
simulador disponibilizado no módulo 3.

## Requisitos
- Python 3.8+
- PyYAML: `python3 -m pip install pyyaml`
  (no Windows, use `python` no lugar de `python3` em todos os comandos)

## Como executar
```bash
python3 simulador.py modelo_t1.yml
```

## Formato do arquivo de entrada (.yml)
```yaml
!PARAMETERS              # opcional (compatível com o simulador do módulo 3)

arrivals:                # filas que recebem clientes do exterior e tempo da 1ª chegada
   Q1: 2.0

queues:
   Q1:
      servers: 1         # número de servidores
      # capacity omitido => capacidade infinita
      minArrival: 2.0    # intervalo entre chegadas externas (só filas com chegada externa)
      maxArrival: 4.0
      minService: 1.0    # tempo de atendimento
      maxService: 2.0
   Q2:
      servers: 2
      capacity: 5
      minService: 4.0
      maxService: 6.0

network:                 # roteamento: source -> target com probabilidade
-  source: Q1
   target: Q2
   probability: 0.2
# A probabilidade que falta para 1,0 em cada fila vai para o EXTERIOR (saída).
# Uma fila sem nenhuma rota envia 100% dos clientes para fora.

rndnumbersPerSeed: 100000   # quantidade de aleatórios (critério de parada)
seeds:                      # uma simulação para cada semente
- 1
```
Em vez de `rndnumbersPerSeed`/`seeds`, pode-se informar uma lista fixa de
aleatórios em `rndnumbers:` (útil para conferir a simulação à mão).

## Funcionamento
- **Gerador:** congruente linear, `X = (a·X + c) mod M`, com a = 1664525,
  c = 1013904223, M = 2³² (normalizado em [0,1)).
- **Escalonador:** fila de prioridade (heap) ordenada pelo tempo do evento.
- **Eventos:** `CHEGADA` (do exterior), `SAIDA` (para o exterior) e
  `PASSAGEM` (de uma fila de origem para uma fila de destino).
- **Roteamento:** quando um cliente começa a ser atendido, sorteia-se um número
  em [0,1) e compara-se com as probabilidades acumuladas da fila para definir
  o destino (outra fila, a própria fila ou o exterior). Filas com um único
  destino não consomem aleatório no roteamento. Em seguida sorteia-se o tempo
  de atendimento, que é o mesmo intervalo seja qual for o destino.
- **Perda:** um cliente que chega (do exterior ou por passagem) numa fila cheia
  é contabilizado como perda nessa fila.
- **Parada:** a simulação termina assim que o último aleatório (ex.: o
  100.000º) é usado. O tempo global é o instante do último evento tratado.
- **Saída:** para cada fila, o tempo acumulado e a probabilidade de cada
  estado, e o número de perdas. Ao final, o tempo global da simulação.

## Arquivos de exemplo
| Arquivo | Modelo |
|---|---|
| `modelo_t1.yml` | Rede de 3 filas do T1 (resultado em `resultado_t1.txt`) |
| `tandem_m6.yml` | Filas em tandem do M6 |
| `fila_simples_m4.yml` | Fila G/G/2/5 do M4 |
| `lista_fixa.yml` | Uso de lista fixa de aleatórios |

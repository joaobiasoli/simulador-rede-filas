
"""
Simulador de Redes de Filas (eventos discretos) - T1 Simulacao e Metodos Analiticos
Uso:  python3 simulador.py modelo.yml

Formato de entrada: mesmo estilo .yml do simulador do modulo 3
(secoes arrivals, queues, network, rndnumbersPerSeed/seeds ou rndnumbers).
"""
import sys, heapq, math
import yaml

class FimDosAleatorios(Exception):
    """Lancada quando se pede um aleatorio alem do limite: encerra a simulacao."""

class GeradorLCG:
    """Metodo Congruente Linear: X(i+1) = (a*X(i) + c) mod M ; retorna X/M em [0,1)."""
    A, C, M = 1664525, 1013904223, 2**32

    def __init__(self, semente, limite):
        self.ultimo = semente % self.M
        self.restantes = limite
        self.usados = 0

    def next_random(self):
        if self.restantes <= 0:
            raise FimDosAleatorios
        self.ultimo = (self.A * self.ultimo + self.C) % self.M
        self.restantes -= 1
        self.usados += 1
        return self.ultimo / self.M


class GeradorLista:
    """Usa uma lista fixa de numeros (secao rndnumbers do .yml) - util para depurar a mao."""
    def __init__(self, numeros):
        self.numeros = list(numeros); self.i = 0
        self.restantes = len(self.numeros); self.usados = 0

    def next_random(self):
        if self.restantes <= 0:
            raise FimDosAleatorios
        r = self.numeros[self.i]; self.i += 1
        self.restantes -= 1; self.usados += 1
        return r

class Fila:
    def __init__(self, nome, servidores, capacidade, min_cheg, max_cheg, min_at, max_at):
        self.nome = nome
        self.servidores = servidores
        self.capacidade = capacidade          
        self.min_cheg, self.max_cheg = min_cheg, max_cheg
        self.min_at, self.max_at = min_at, max_at
        self.status = 0                     
        self.perdas = 0
        self.tempos = [0.0]                   
        self.rotas = []                      

    def cabe(self):
        return self.capacidade is None or self.status < self.capacidade

    def entra(self):
        self.status += 1
        if self.status >= len(self.tempos):
            self.tempos.append(0.0)

    def sai(self):
        self.status -= 1


class Evento:
    CHEGADA, SAIDA, PASSAGEM = "CHEGADA", "SAIDA", "PASSAGEM"
    _seq = 0

    def __init__(self, tipo, tempo, origem, destino=None):
        self.tipo, self.tempo, self.origem, self.destino = tipo, tempo, origem, destino
        Evento._seq += 1; self.seq = Evento._seq   

    def __lt__(self, outro):
        return (self.tempo, self.seq) < (outro.tempo, outro.seq)


class Escalonador:
    def __init__(self): self.heap = []
    def agenda(self, ev): heapq.heappush(self.heap, ev)
    def proximo(self): return heapq.heappop(self.heap)
    def vazio(self): return not self.heap


class Simulador:
    def __init__(self, filas, chegadas_iniciais, rnd):
        self.filas = filas                   
        self.rnd = rnd
        self.esc = Escalonador()
        self.tempo = 0.0
        for nome, t in chegadas_iniciais.items():
            self.esc.agenda(Evento(Evento.CHEGADA, t, filas[nome]))

 
    def uniforme(self, a, b):
        return a + (b - a) * self.rnd.next_random()

    def acumula_tempo(self, t):
        delta = t - self.tempo
        for f in self.filas.values():
            f.tempos[f.status] += delta
        self.tempo = t

    def roteia(self, fila):
        """Sorteia o destino do cliente atendido (None = exterior), probabilidades acumuladas."""
        if len(fila.rotas) == 1:             
            return fila.rotas[0][0]
        r = self.rnd.next_random()
        acum = 0.0
        for destino, p in fila.rotas:
            acum += p
            if r < acum:
                return destino
        return fila.rotas[-1][0]

    def agenda_atendimento(self, fila):
        destino = self.roteia(fila)
        t = self.tempo + self.uniforme(fila.min_at, fila.max_at)
        if destino is None:
            self.esc.agenda(Evento(Evento.SAIDA, t, fila))
        else:
            self.esc.agenda(Evento(Evento.PASSAGEM, t, fila, destino))

   
    def entra_na_fila(self, fila):
        if fila.cabe():
            fila.entra()
            if fila.status <= fila.servidores:
                self.agenda_atendimento(fila)
        else:
            fila.perdas += 1

    def libera_servidor(self, fila):
        fila.sai()
        if fila.status >= fila.servidores:
            self.agenda_atendimento(fila)

    def chegada(self, ev):
        self.acumula_tempo(ev.tempo)
        self.entra_na_fila(ev.origem)
        f = ev.origem
        self.esc.agenda(Evento(Evento.CHEGADA,
                               self.tempo + self.uniforme(f.min_cheg, f.max_cheg), f))

    def saida(self, ev):
        self.acumula_tempo(ev.tempo)
        self.libera_servidor(ev.origem)

    def passagem(self, ev):
        self.acumula_tempo(ev.tempo)
        self.libera_servidor(ev.origem)
        self.entra_na_fila(ev.destino)

    def executa(self):
        trata = {Evento.CHEGADA: self.chegada, Evento.SAIDA: self.saida,
                 Evento.PASSAGEM: self.passagem}
        try:
            while self.rnd.restantes > 0 and not self.esc.vazio():
                ev = self.esc.proximo()
                trata[ev.tipo](ev)
        except FimDosAleatorios:
            pass


def carrega_modelo(caminho):
    with open(caminho, encoding="utf-8") as fh:
        texto = fh.read().replace("!PARAMETERS", "")  
    cfg = yaml.safe_load(texto)

    filas = {}
    for nome, q in cfg["queues"].items():
        filas[nome] = Fila(nome, int(q["servers"]), q.get("capacity"),
                           q.get("minArrival"), q.get("maxArrival"),
                           float(q["minService"]), float(q["maxService"]))

    for r in cfg.get("network", []) or []:
        filas[r["source"]].rotas.append((filas[r["target"]], float(r["probability"])))
    for f in filas.values():
        soma = sum(p for _, p in f.rotas)
        if soma > 1 + 1e-9:
            sys.exit(f"Erro: probabilidades de roteamento de {f.nome} somam {soma} > 1")
        if soma < 1 - 1e-9:
            f.rotas.append((None, 1 - soma))   

    return cfg, filas

def relatorio(sim, cfg, semente):
    T = sim.tempo
    print("=" * 66)
    print(f"Semente: {semente}   Aleatorios usados: {sim.rnd.usados}")
    print("=" * 66)
    for f in sim.filas.values():
        cap = "inf" if f.capacidade is None else f.capacidade
        tipo = f"G/G/{f.servidores}" + ("" if f.capacidade is None else f"/{f.capacidade}")
        print(f"\nFila {f.nome} ({tipo})")
        if f.min_cheg is not None:
            print(f"  Chegadas: {f.min_cheg} .. {f.max_cheg}")
        print(f"  Atendimento: {f.min_at} .. {f.max_at}")
        rotas = ", ".join(f"{'saida' if d is None else d.nome}={p:.2f}" for d, p in f.rotas)
        print(f"  Roteamento: {rotas}")
        print(f"  {'Estado':>6} {'Tempo acumulado':>18} {'Probabilidade':>14}")
        for i, t in enumerate(f.tempos):
            print(f"  {i:>6} {t:>18.4f} {100 * t / T:>13.2f}%")
        print(f"  Perda de clientes: {f.perdas}")
    print(f"\nTempo global da simulacao: {T:.4f}")
    print("=" * 66)

def main():
    if len(sys.argv) < 2:
        sys.exit("Uso: python3 simulador.py <modelo.yml>")
    cfg, _ = carrega_modelo(sys.argv[1])
    if "rndnumbers" in cfg:
        execucoes = [("lista", lambda: GeradorLista(cfg["rndnumbers"]))]
    else:
        n = int(cfg.get("rndnumbersPerSeed", 100000))
        execucoes = [(s, (lambda s=s: GeradorLCG(s, n))) for s in cfg.get("seeds", [1])]
    for semente, cria_gerador in execucoes:
        _, filas = carrega_modelo(sys.argv[1])     
        sim = Simulador(filas, cfg["arrivals"], cria_gerador())
        sim.executa()
        relatorio(sim, cfg, semente)

if __name__ == "__main__":
    main()

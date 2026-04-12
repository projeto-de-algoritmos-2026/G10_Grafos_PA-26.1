"""
Modulo de construcao do grafo e algoritmo de Dijkstra.

Grafo de ASNs do IX.br:
- Nos: ASNs (Sistemas Autonomos) presentes nos IXs brasileiros
- Arestas: dois ASNs conectados se compartilham pelo menos um IX
- Peso: 1 / num de IXs compartilhados (mais IXs em comum = menor peso)
"""

import heapq
from collections import defaultdict


def construir_grafo(dados):
    """
    Constroi grafo de ASNs a partir dos dados do PeeringDB.

    Retorna:
        grafo: dict de adjacencia {asn: [(vizinho, peso), ...]}
        info_asn: dict {asn: {'name': str, 'ixs': [str], 'max_speed': int}}
    """
    print("Construindo grafo de ASNs...\n")

    # Dict de nomes reais das redes (asn -> nome)
    nomes = dados.get("nomes", {})

    # Mapeia cada ASN para seus IXs e cada IX para seus ASNs
    info_asn = defaultdict(lambda: {"name": "", "ixs": [], "max_speed": 0})
    ix_para_asns = {}

    for ix in dados["ixs"]:
        ix_id = str(ix["id"])
        participantes = dados["participantes"].get(ix_id, [])
        asns_neste_ix = set()

        for p in participantes:
            asn = p["asn"]
            asns_neste_ix.add(asn)
            # Usa nome real da rede (do endpoint /net), senao usa o do participante
            info_asn[asn]["name"] = nomes.get(str(asn), p["name"])
            info_asn[asn]["ixs"].append(ix["name"])
            info_asn[asn]["max_speed"] = max(info_asn[asn]["max_speed"], p["speed"])

        ix_para_asns[ix_id] = asns_neste_ix

    print(f"  Total de ASNs unicos: {len(info_asn)}")

    # Conta IXs em comum entre cada par de ASNs
    pares_ixs_comuns = defaultdict(int)

    for ix_id, asns in ix_para_asns.items():
        asns_lista = sorted(asns)

        if len(asns_lista) > 500:
            print(f"  IX {ix_id} tem {len(asns_lista)} ASNs — processando...")

        for i in range(len(asns_lista)):
            for j in range(i + 1, len(asns_lista)):
                par = (asns_lista[i], asns_lista[j])
                pares_ixs_comuns[par] += 1

    # Monta grafo como dict de adjacencia
    grafo = defaultdict(list)

    for (asn1, asn2), num_ixs in pares_ixs_comuns.items():
        peso = 1.0 / num_ixs
        grafo[asn1].append((asn2, peso))
        grafo[asn2].append((asn1, peso))

    # Garante que ASNs isolados aparecam no grafo
    for asn in info_asn:
        if asn not in grafo:
            grafo[asn] = []

    n_arestas = sum(len(v) for v in grafo.values()) // 2
    print(f"  Arestas (pares de ASNs): {n_arestas}")
    print()

    return dict(grafo), dict(info_asn)


def dijkstra(grafo, origem, destino):
    """
    Algoritmo de Dijkstra para caminho mais curto.

    Implementacao manual com heapq (fila de prioridade).

    Parametros:
        grafo: dict de adjacencia {no: [(vizinho, peso), ...]}
        origem: no de partida
        destino: no de chegada

    Retorna:
        (distancia, caminho) ou (inf, []) se nao houver caminho
    """
    distancias = {vertice: float("inf") for vertice in grafo}
    distancias[origem] = 0
    predecessores = {vertice: None for vertice in grafo}
    fila = [(0, origem)]
    visitados = set()

    while fila:
        custo_atual, vertice_atual = heapq.heappop(fila)

        if vertice_atual in visitados:
            continue
        visitados.add(vertice_atual)

        if vertice_atual == destino:
            break

        for vizinho, peso_aresta in grafo.get(vertice_atual, []):
            if vizinho in visitados:
                continue

            novo_custo = custo_atual + peso_aresta
            if novo_custo < distancias[vizinho]:
                distancias[vizinho] = novo_custo
                predecessores[vizinho] = vertice_atual
                heapq.heappush(fila, (novo_custo, vizinho))

    caminho = _reconstruir_caminho(predecessores, origem, destino)
    return distancias[destino], caminho


def _reconstruir_caminho(predecessores, origem, destino):
    """Reconstroi o caminho a partir do dict de predecessores."""
    caminho = []
    atual = destino
    while atual is not None:
        caminho.append(atual)
        atual = predecessores[atual]
    caminho.reverse()
    return caminho if caminho and caminho[0] == origem else []


def estatisticas(grafo, info_asn):
    """Exibe estatisticas do grafo de ASNs."""
    n = len(grafo)
    n_arestas = sum(len(v) for v in grafo.values()) // 2
    graus = {asn: len(vizinhos) for asn, vizinhos in grafo.items()}
    grau_medio = sum(graus.values()) / n if n > 0 else 0

    print("=" * 55)
    print("  ESTATISTICAS DO GRAFO")
    print("=" * 55)
    print(f"  ASNs (nos):         {n}")
    print(f"  Conexoes (arestas): {n_arestas}")
    print(f"  Grau medio:         {grau_medio:.1f} conexoes por ASN")

    # Top 10 ASNs mais conectados
    top = sorted(graus.items(), key=lambda x: x[1], reverse=True)[:10]
    print(f"\n  Top 10 ASNs mais conectados:")
    print(f"  {'ASN':<10} {'Conexoes':<10} {'Nome'}")
    print(f"  {'-'*10} {'-'*10} {'-'*30}")
    for asn, grau in top:
        nome = info_asn.get(asn, {}).get("name", "?")[:30]
        print(f"  AS{asn:<7} {grau:<10} {nome}")
    print()

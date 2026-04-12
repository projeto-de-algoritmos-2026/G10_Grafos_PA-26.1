"""
Modulo de coleta de dados do PeeringDB.

Busca localidades do IX.br e seus participantes (ASNs),
resolve nomes reais das redes, e salva em cache local.
"""

import requests
import json
import time
import os

PEERINGDB_API = "https://www.peeringdb.com/api"
CACHE_FILE = os.path.join(os.path.dirname(__file__), "ixbr_cache.json")


def _get(url, tentativas=3):
    """GET com retry e backoff para lidar com rate limiting (429)."""
    for i in range(tentativas):
        resp = requests.get(url, timeout=60)
        if resp.status_code == 429:
            espera = 2 ** (i + 1)  # 2s, 4s, 8s
            print(f"    Rate limited, aguardando {espera}s...")
            time.sleep(espera)
            continue
        resp.raise_for_status()
        return resp
    resp.raise_for_status()
    return resp


def buscar_ixs_do_ixbr():
    """Busca todas as localidades do IX.br no PeeringDB."""
    print("Buscando localidades do IX.br no PeeringDB...")
    url = f"{PEERINGDB_API}/ix?name__contains=IX.br"
    resposta = _get(url)

    ixs = []
    for ix in resposta.json()["data"]:
        ixs.append({
            "id": ix["id"],
            "name": ix["name"],
            "city": ix.get("city", "N/A"),
        })

    print(f"  Encontradas {len(ixs)} localidades.\n")
    return ixs


def buscar_nomes_redes(asns):
    """
    Busca nomes reais das redes no PeeringDB pelo endpoint /net.
    O endpoint netixlan retorna o nome do IX, nao da rede.

    Parametros:
        asns: set de ASNs para buscar

    Retorna:
        dict {asn: nome_da_rede}
    """
    print(f"Buscando nomes de {len(asns)} redes no PeeringDB...")
    nomes = {}

    # Busca em lotes pequenos com delay para evitar rate limiting
    asns_lista = list(asns)
    lote_size = 50

    for i in range(0, len(asns_lista), lote_size):
        lote = asns_lista[i:i + lote_size]
        asns_param = ",".join(str(a) for a in lote)
        url = f"{PEERINGDB_API}/net?asn__in={asns_param}"

        try:
            resposta = _get(url)
            for net in resposta.json()["data"]:
                nomes[net["asn"]] = net["name"]
        except Exception as e:
            print(f"  Erro ao buscar lote de redes: {e}")

        if i + lote_size < len(asns_lista):
            time.sleep(1.5)

    print(f"  Nomes resolvidos: {len(nomes)} de {len(asns)}\n")
    return nomes


def buscar_participantes_do_ix(ix_id, ix_name):
    """Busca ASNs participantes de um IX especifico."""
    url = f"{PEERINGDB_API}/netixlan?ix_id={ix_id}"
    resposta = _get(url)

    asns_vistos = set()
    participantes = []
    for p in resposta.json()["data"]:
        asn = p["asn"]
        if asn not in asns_vistos:
            asns_vistos.add(asn)
            participantes.append({
                "asn": asn,
                "name": f"AS{asn}",  # placeholder, sera resolvido depois
                "speed": p.get("speed", 0),
            })

    print(f"  {ix_name}: {len(participantes)} ASNs")
    return participantes


def coletar_dados(usar_cache=True):
    """
    Coleta dados de todas as localidades do IX.br.
    Usa cache JSON local se disponivel.

    Retorna:
        dict com 'ixs', 'participantes' e 'nomes' (asn -> nome da rede)
    """
    if usar_cache:
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                dados = json.load(f)
                n_ixs = len(dados["ixs"])
                n_conex = sum(len(v) for v in dados["participantes"].values())
                print(f"Cache carregado: {n_ixs} localidades, {n_conex} conexoes.\n")
                return dados
        except FileNotFoundError:
            print("Cache nao encontrado. Baixando dados...\n")

    ixs = buscar_ixs_do_ixbr()

    participantes = {}
    todos_asns = set()
    for ix in ixs:
        try:
            parts = buscar_participantes_do_ix(ix["id"], ix["name"])
            participantes[str(ix["id"])] = parts
            for p in parts:
                todos_asns.add(p["asn"])
            time.sleep(1.0)
        except Exception as e:
            print(f"  Erro ao buscar {ix['name']}: {e}")

    # Resolve nomes reais das redes
    nomes = buscar_nomes_redes(todos_asns)

    # Atualiza nomes nos participantes
    for ix_id, parts in participantes.items():
        for p in parts:
            if p["asn"] in nomes:
                p["name"] = nomes[p["asn"]]

    # Salva nomes separadamente para uso no grafo
    nomes_str = {str(k): v for k, v in nomes.items()}
    dados = {"ixs": ixs, "participantes": participantes, "nomes": nomes_str}

    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    print(f"\nDados salvos em cache.\n")

    return dados

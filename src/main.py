"""
IX.br — Analise de Topologia com Grafos e Caminho Mais Curto

Coleta dados do PeeringDB, constroi grafo de ASNs do IX.br
e calcula o caminho mais curto entre dois ASNs usando Dijkstra.

Uso:
    python3 src/main.py                  -> modo interativo
    python3 src/main.py 16735 8167      -> caminho direto entre 2 ASNs
"""

import sys
from api import coletar_dados
from grafo import construir_grafo, dijkstra, estatisticas


# ==============================================================================
# MAPEAMENTO CIDADE -> ESTADO
# ==============================================================================

# Fallback para cidades sem /UF no campo city do PeeringDB
_CIDADE_UF_FALLBACK = {
    "Curitiba": "PR",
    "Porto Velho": "RO",
    "Feira de Santana": "BA",
    "Caruaru": "PE",
    "Ribeirão Preto": "SP",
}

ESTADOS_NOME = {
    "AC": "Acre", "AL": "Alagoas", "AM": "Amazonas", "AP": "Amapá",
    "BA": "Bahia", "CE": "Ceará", "DF": "Distrito Federal",
    "ES": "Espírito Santo", "GO": "Goiás", "MA": "Maranhão",
    "MG": "Minas Gerais", "MS": "Mato Grosso do Sul", "MT": "Mato Grosso",
    "PA": "Pará", "PB": "Paraíba", "PE": "Pernambuco", "PI": "Piauí",
    "PR": "Paraná", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte",
    "RO": "Rondônia", "RR": "Roraima", "RS": "Rio Grande do Sul",
    "SC": "Santa Catarina", "SE": "Sergipe", "SP": "São Paulo",
    "TO": "Tocantins",
}


def _extrair_uf(city_str):
    """Extrai UF de 'Cidade/UF' ou usa fallback."""
    if "/" in city_str:
        return city_str.split("/")[-1].strip()
    return _CIDADE_UF_FALLBACK.get(city_str, "??")


def mapear_asns_por_estado(dados, info_asn):
    """
    Mapeia ASNs por estado (UF) a partir das localidades IX.br.

    Retorna:
        dict {uf: [(asn, nome, cidade_ix), ...]} ordenado por UF
    """
    from collections import defaultdict
    estado_asns = defaultdict(set)
    asn_cidade = {}

    for ix in dados["ixs"]:
        ix_id = str(ix["id"])
        uf = _extrair_uf(ix["city"])
        cidade = ix["city"].split("/")[0].strip()

        for p in dados["participantes"].get(ix_id, []):
            asn = p["asn"]
            estado_asns[uf].add(asn)
            # Guarda a primeira cidade encontrada para o ASN nesse estado
            if asn not in asn_cidade:
                asn_cidade[asn] = cidade

    # Converte para lista ordenada
    resultado = {}
    for uf in sorted(estado_asns.keys()):
        lista = []
        for asn in sorted(estado_asns[uf]):
            nome = info_asn.get(asn, {}).get("name", f"AS{asn}")
            cidade = asn_cidade.get(asn, "?")
            lista.append((asn, nome, cidade))
        resultado[uf] = lista

    return resultado


def listar_asns_por_estado(dados, info_asn, page_size=15):
    """Lista ASNs agrupados por estado com paginacao interativa."""
    estado_asns = mapear_asns_por_estado(dados, info_asn)
    ufs = list(estado_asns.keys())

    # Mostra estados disponíveis
    print(f"\n  Estados com presenca no IX.br ({len(ufs)}):\n")
    for i, uf in enumerate(ufs, 1):
        nome_estado = ESTADOS_NOME.get(uf, uf)
        total = len(estado_asns[uf])
        print(f"  {i:>3}. {uf} - {nome_estado:<25} ({total} ASNs)")
    print()

    # Escolhe estado
    entrada = input("  Escolha o estado (numero ou sigla): ").strip().upper()
    uf_escolhida = None

    try:
        idx = int(entrada) - 1
        if 0 <= idx < len(ufs):
            uf_escolhida = ufs[idx]
    except ValueError:
        if entrada in estado_asns:
            uf_escolhida = entrada

    if not uf_escolhida:
        print("  Estado nao encontrado.\n")
        return

    # Paginacao
    asns = estado_asns[uf_escolhida]
    nome_estado = ESTADOS_NOME.get(uf_escolhida, uf_escolhida)
    total = len(asns)
    pagina = 0
    total_paginas = (total + page_size - 1) // page_size

    while True:
        inicio = pagina * page_size
        fim = min(inicio + page_size, total)

        print()
        print(f"  ASNs em {uf_escolhida} - {nome_estado}")
        print(f"  Pagina {pagina + 1}/{total_paginas} ({total} ASNs)")
        print()
        print(f"  {'#':<5} {'ASN':<10} {'Nome':<35} {'Cidade IX'}")
        print(f"  {'-'*5} {'-'*10} {'-'*35} {'-'*20}")

        for i, (asn, nome, cidade) in enumerate(asns[inicio:fim], inicio + 1):
            print(f"  {i:<5} AS{asn:<8} {nome[:35]:<35} {cidade}")

        print()

        # Navegacao
        opcoes = []
        if pagina > 0:
            opcoes.append("[a] anterior")
        if pagina < total_paginas - 1:
            opcoes.append("[p] proxima")
        opcoes.append("[v] voltar")

        print(f"  {' | '.join(opcoes)}")
        nav = input("  > ").strip().lower()

        if nav == "p" and pagina < total_paginas - 1:
            pagina += 1
        elif nav == "a" and pagina > 0:
            pagina -= 1
        elif nav == "v" or nav == "":
            break
        else:
            print("  Opcao invalida.")


# ==============================================================================
# FUNCOES DE BUSCA DE ASN
# ==============================================================================

def buscar_asn(info_asn, texto, limite=20):
    """
    Busca ASNs por nome (ex: 'Vivo', 'Google') ou por numero.
    Retorna lista de (asn, nome, num_ixs).
    """
    resultados = []
    for asn, info in info_asn.items():
        nome = info.get("name", "")
        # Busca por numero ou por nome
        if texto.isdigit() and texto in str(asn):
            resultados.append((asn, nome, len(info.get("ixs", []))))
        elif not texto.isdigit() and texto.lower() in nome.lower():
            resultados.append((asn, nome, len(info.get("ixs", []))))

    resultados.sort(key=lambda x: -x[2])  # ordena por num de IXs (mais relevante primeiro)
    return resultados[:limite]


def exibir_busca(resultados):
    """Exibe resultados de busca formatados."""
    if not resultados:
        print("  Nenhum ASN encontrado.\n")
        return

    print(f"\n  {'#':<5} {'ASN':<10} {'IXs':<5} {'Nome'}")
    print(f"  {'-'*5} {'-'*10} {'-'*5} {'-'*35}")
    for i, (asn, nome, num_ixs) in enumerate(resultados, 1):
        print(f"  {i:<5} AS{asn:<8} {num_ixs:<5} {nome[:35]}")
    print()


def escolher_asn(info_asn, prompt):
    """
    Permite o usuario escolher um ASN buscando por nome ou numero.
    Retorna o ASN (int) ou None.
    """
    texto = input(prompt).strip()
    if not texto:
        return None

    # Se digitou um numero exato que existe, usa direto
    try:
        asn_direto = int(texto)
        if asn_direto in info_asn:
            nome = info_asn[asn_direto]["name"]
            print(f"  -> AS{asn_direto} ({nome})")
            return asn_direto
    except ValueError:
        pass

    # Busca por nome/numero parcial
    resultados = buscar_asn(info_asn, texto)

    if not resultados:
        print(f"  Nenhum ASN encontrado para '{texto}'.\n")
        return None

    if len(resultados) == 1:
        asn, nome, _ = resultados[0]
        print(f"  -> AS{asn} ({nome})")
        return asn

    # Multiplos resultados: usuario escolhe
    print(f"  Resultados para '{texto}':")
    exibir_busca(resultados)

    try:
        idx = int(input("  Escolha o numero (#): ").strip()) - 1
        if 0 <= idx < len(resultados):
            asn, nome, _ = resultados[idx]
            print(f"  -> AS{asn} ({nome})\n")
            return asn
    except (ValueError, IndexError):
        pass

    print("  Selecao invalida.\n")
    return None


# ==============================================================================
# EXIBICAO DE RESULTADOS
# ==============================================================================

def exibir_caminho(grafo, info_asn, asn_origem, asn_destino):
    """Calcula e exibe o caminho mais curto entre dois ASNs."""
    if asn_origem not in grafo:
        print(f"  AS{asn_origem} nao esta no grafo.\n")
        return
    if asn_destino not in grafo:
        print(f"  AS{asn_destino} nao esta no grafo.\n")
        return

    custo, caminho = dijkstra(grafo, asn_origem, asn_destino)

    if not caminho:
        print(f"\n  Nao ha caminho entre AS{asn_origem} e AS{asn_destino}.\n")
        return

    nome_orig = info_asn.get(asn_origem, {}).get("name", "?")
    nome_dest = info_asn.get(asn_destino, {}).get("name", "?")

    print()
    print("=" * 55)
    print("  CAMINHO MAIS CURTO (Dijkstra)")
    print("=" * 55)
    print(f"  De:     AS{asn_origem} ({nome_orig})")
    print(f"  Para:   AS{asn_destino} ({nome_dest})")
    print(f"  Saltos: {len(caminho) - 1}")
    print(f"  Custo:  {custo:.4f}")
    print()
    print("  Rota:")
    print("  " + "-" * 51)

    for i, asn in enumerate(caminho):
        nome = info_asn.get(asn, {}).get("name", "?")
        num_ixs = len(info_asn.get(asn, {}).get("ixs", []))

        if i == 0:
            tag = "[ORIGEM] "
        elif i == len(caminho) - 1:
            tag = "[DESTINO]"
        else:
            tag = f"[salto {i}] "

        print(f"  {tag:<11} AS{asn} — {nome} ({num_ixs} IXs)")

        if i < len(caminho) - 1:
            prox = caminho[i + 1]
            for vizinho, peso in grafo.get(asn, []):
                if vizinho == prox:
                    ixs_comuns = int(1.0 / peso) if peso > 0 else 0
                    print(f"  {'':11} |  IXs em comum: {ixs_comuns}, peso: {peso:.4f}")
                    break

    print("  " + "-" * 51)
    print()


# ==============================================================================
# MENU INTERATIVO
# ==============================================================================

def menu(grafo, info_asn, dados):
    """Menu interativo principal."""
    print()
    print("=" * 55)
    print("  IX.br — Topologia de Interconexao (ASNs)")
    print("  Dados: PeeringDB | Algoritmo: Dijkstra")
    print("=" * 55)
    print()
    print("  O que e um ASN?")
    print("  ASN (Autonomous System Number) e o identificador")
    print()
    print("  Voce pode buscar por NOME (ex: 'Vivo') ou")
    print("  digitar o numero do ASN diretamente.")
    print()
    print("  Para achar ASNs, confira a opção 3!")

    while True:
        print("  [1] Calcular rota entre ASNs")
        print("  [2] Buscar ASN por nome")
        print("  [3] Listar ASNs por estado")
        print("  [4] Estatisticas do grafo")
        print("  [5] Sair")

        opcao = input("\n  Escolha: ").strip()

        if opcao == "1":
            print()
            origem = escolher_asn(info_asn, "  ASN de ORIGEM (nome ou numero): ")
            if not origem:
                continue
            destino = escolher_asn(info_asn, "  ASN de DESTINO (nome ou numero): ")
            if not destino:
                continue
            exibir_caminho(grafo, info_asn, origem, destino)

        elif opcao == "2":
            texto = input("\n  Buscar ASN: ").strip()
            if texto:
                resultados = buscar_asn(info_asn, texto, limite=30)
                exibir_busca(resultados)

        elif opcao == "3":
            listar_asns_por_estado(dados, info_asn)

        elif opcao == "4":
            estatisticas(grafo, info_asn)

        elif opcao == "5":
            print("\n  Ate mais!\n")
            break

        else:
            print("  Opcao invalida.\n")


# ==============================================================================
# EXECUCAO PRINCIPAL
# ==============================================================================

def main():
    print()
    print("=" * 55)
    print("  IX.br — Analise de Topologia com Grafos")
    print("=" * 55)
    print()

    # 1. Coleta dados
    dados = coletar_dados(usar_cache=True)

    # 2. Constroi grafo
    grafo, info_asn = construir_grafo(dados)

    # 3. Modo direto via CLI: python main.py 16735 8167
    if len(sys.argv) == 3:
        try:
            asn_a = int(sys.argv[1])
            asn_b = int(sys.argv[2])
            exibir_caminho(grafo, info_asn, asn_a, asn_b)
            return
        except ValueError:
            print("  ASNs devem ser numeros inteiros.\n")

    # 4. Modo interativo
    menu(grafo, info_asn, dados)


if __name__ == "__main__":
    main()

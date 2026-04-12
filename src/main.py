import heapq

# Importa o dicionário diretamente do arquivo database.py
try:
    from database import MAPA_SAO_PAULO # pode modificar aqui para o nome do arquivo e variável que contém o mapa
except ImportError:
    print("Erro: Arquivo 'database.py' não encontrado.")
    MAPA_SAO_PAULO = {}

def dijkstra(grafo, origem, destino):
    """Implementação do algoritmo para encontrar o caminho mais curto."""
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

    return distancias[destino], _reconstruir_caminho(predecessores, origem, destino)

def _reconstruir_caminho(predecessores, origem, destino):
    caminho = []
    atual = destino
    while atual is not None:
        caminho.append(atual)
        atual = predecessores[atual]
    caminho.reverse()
    return caminho if caminho and caminho[0] == origem else []

# --- Interface ---

def menu():
    if not MAPA_SAO_PAULO:
        return

    while True:
        print("\n" + "="*40)
        print("   NAVEGADOR TURÍSTICO - SÃO PAULO")
        print("="*40)
        print("[1] Ver locais e Calcular Rota")
        print("[2] Sair")
        
        opcao = input("\nEscolha: ")

        if opcao == "1":
            locais = list(MAPA_SAO_PAULO.keys())
            print("\n📍 Locais disponíveis:")
            for i, local in enumerate(locais, 1):
                print(f"{i}. {local}")
            
            try:
                idx_origem = int(input("\nNúmero da ORIGEM: ")) - 1
                idx_destino = int(input("Número do DESTINO: ")) - 1
                
                origem = locais[idx_origem]
                destino = locais[idx_destino]

                tempo, rota = dijkstra(MAPA_SAO_PAULO, origem, destino)

                if rota:
                    print(f"\n✅ ROTA ENCONTRADA EM {tempo} MINUTOS!")
                    print(f"📌 Itinerário: {' -> '.join(rota)}")
                else:
                    print("\n❌ Não há conexão entre esses locais.")
            except (ValueError, IndexError):
                print("\n⚠️ Seleção inválida.")

        elif opcao == "2":
            print("Saindo do navegador...")
            break

if __name__ == "__main__":
    menu()
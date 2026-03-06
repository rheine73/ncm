import os
import csv
from datetime import datetime

SNAPSHOT_FOLDER = "snapshots"
NCM_ATUAL_FILE = "tabela_ncm_atual.csv"
NCM_MONITORADAS = "ncms.csv"


def criar_pasta_snapshot():
    if not os.path.exists(SNAPSHOT_FOLDER):
        os.makedirs(SNAPSHOT_FOLDER)


def detectar_delimitador(arquivo):
    with open(arquivo, 'r', encoding='utf-8') as f:
        linha = f.readline()
        if ";" in linha:
            return ";"
        return ","


def carregar_tabela(arquivo):
    delimitador = detectar_delimitador(arquivo)
    tabela = {}

    with open(arquivo, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter=delimitador)
        next(reader)  # pula cabeçalho
        for linha in reader:
            if len(linha) >= 2:
                ncm = linha[0].strip()
                descricao = linha[1].strip()
                tabela[ncm] = descricao

    return tabela


def carregar_ncms_monitoradas():
    lista = []
    with open(NCM_MONITORADAS, 'r') as f:
        next(f)
        for linha in f:
            lista.append(linha.strip())
    return lista


def salvar_snapshot(tabela):
    hoje = datetime.now().strftime("%Y_%m_%d")
    caminho = os.path.join(SNAPSHOT_FOLDER, f"ncm_{hoje}.csv")

    with open(caminho, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["NCM", "DESCRICAO"])
        for ncm, desc in tabela.items():
            writer.writerow([ncm, desc])

    return caminho


def obter_snapshot_anterior():
    arquivos = sorted(os.listdir(SNAPSHOT_FOLDER))
    if len(arquivos) < 2:
        return None

    return os.path.join(SNAPSHOT_FOLDER, arquivos[-2])


def comparar_tabelas(atual, anterior, monitoradas):
    print("\n=== RELATÓRIO DE ALTERAÇÕES ===\n")

    for ncm in monitoradas:

        if ncm not in anterior and ncm in atual:
            print(f"🟢 NCM NOVA: {ncm}")

        elif ncm in anterior and ncm not in atual:
            print(f"🔴 NCM REMOVIDA: {ncm}")

        elif ncm in anterior and ncm in atual:
            if anterior[ncm] != atual[ncm]:
                print(f"🟡 DESCRIÇÃO ALTERADA: {ncm}")
                print(f"   Antes: {anterior[ncm]}")
                print(f"   Agora: {atual[ncm]}")
                print("")


if __name__ == "__main__":

    print("=== MONITOR ESTRUTURAL NCM ===")

    criar_pasta_snapshot()

    if not os.path.exists(NCM_ATUAL_FILE):
        print("Arquivo tabela_ncm_atual.csv não encontrado.")
        exit()

    tabela_atual = carregar_tabela(NCM_ATUAL_FILE)
    snapshot_path = salvar_snapshot(tabela_atual)

    snapshot_anterior_path = obter_snapshot_anterior()

    if not snapshot_anterior_path:
        print("Primeiro snapshot criado. Rode novamente para comparar.")
        exit()

    tabela_anterior = carregar_tabela(snapshot_anterior_path)
    monitoradas = carregar_ncms_monitoradas()

    comparar_tabelas(tabela_atual, tabela_anterior, monitoradas)

    print("\nFinalizado.")
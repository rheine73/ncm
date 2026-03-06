import requests
import csv

url = "https://portalunico.siscomex.gov.br/classif/api/publico/nomenclatura/download/json"

print("Baixando tabela NCM oficial...")

resp = requests.get(url)
resp.raise_for_status()

data = resp.json()

lista = data["Nomenclaturas"]

print(f"Data última atualização: {data['Data_Ultima_Atualizacao_NCM']}")
print(f"Ato legal: {data['Ato']}")
print(f"Total NCMs encontradas: {len(lista)}")

with open("tabela_ncm_atual.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["NCM", "DESCRICAO"])

    for item in lista:
        codigo = item.get("Codigo")
        descricao = item.get("Descricao")

        if codigo and descricao:
            writer.writerow([codigo, descricao])

print("Arquivo tabela_ncm_atual.csv gerado com sucesso.")
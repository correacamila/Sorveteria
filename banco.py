import json

ARQUIVO = "dados.json"

def ler_dados():
    with open(ARQUIVO, "r", encoding="utf-8") as arquivo:
        return json.load(arquivo)

def salvar_dados(dados):
    with open(ARQUIVO, "w", encoding="utf-8") as arquivo:
        json.dump(dados, arquivo, ensure_ascii=False, indent=4)
# 🍦 Doce Neve — Sorveteria

Projeto escolar feito com Python, Flask, HTML e CSS.

## Estrutura

- `app.py` → controla as rotas e liga as páginas aos dados.
- `banco.py` → lê e salva os dados no `dados.json`.
- `modelos.py` → cria usuários e pedidos.
- `dados.json` → guarda os dados.
- `templates/` → páginas HTML.
- `static/` → arquivo CSS.
- `requirements.txt` → dependência do Flask.

## Como executar no Windows CMD

```text
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
set FLASK_APP=app.py
flask run --debug
```

Depois, abra:

`http://127.0.0.1:5000`

## Usuário inicial

E-mail: `correa@gmail.com`

Senha: `1234567890`

## Observação

O `app.py` foi mantido sem alterações, como solicitado.

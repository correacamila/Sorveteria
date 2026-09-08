class Usuario:
    def __init__(self, id_usuario, nome, email, senha, adm=False, principal=False):
        self.id = id_usuario
        self.nome = nome
        self.email = email
        self.senha = senha
        self.adm = adm
        self.principal = principal

class Produto:
    def __init__(self, id_produto, nome, descricao, categoria, preco):
        self.id = id_produto
        self.nome = nome
        self.descricao = descricao
        self.categoria = categoria
        self.preco = preco

class Pedido:
    def __init__(self, id_pedido, usuario_id, produto, quantidade):
        self.id = id_pedido
        self.usuario_id = usuario_id
        self.produto = produto.nome
        self.preco = produto.preco
        self.quantidade = quantidade
        self.total = produto.preco * quantidade
        self.status = "Recebido"

def criar_usuario(id_usuario, nome, email, senha):
    return {
        "id": id_usuario,
        "nome": nome,
        "email": email,
        "senha": senha,
        "adm": False,
        "principal": False
    }


def criar_pedido(id_pedido, usuario_id, produto, quantidade):
    return {
        "id": id_pedido,
        "usuario_id": usuario_id,
        "produto": produto["nome"],
        "preco": produto["preco"],
        "quantidade": quantidade,
        "total": produto["preco"] * quantidade,
        "status": "Recebido"
    }
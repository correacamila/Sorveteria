from datetime import date, datetime
from banco import db


class Usuario(db.Model):
    __tablename__ = "usuarios"
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha = db.Column(db.String(255), nullable=False)
    apelido = db.Column(db.String(50), default="")
    foto = db.Column(db.String(200), default="inicial_neutro.png")
    data_entrada = db.Column(db.Date, default=date.today)
    adm = db.Column(db.Boolean, default=False)
    principal = db.Column(db.Boolean, default=False)


class Produto(db.Model):
    __tablename__ = "produtos"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text)
    categoria = db.Column(db.String(50))
    preco = db.Column(db.Float, nullable=False)

    # Foto do sorvete no cardápio
    imagem = db.Column(db.String(200), default="")

    # Desenho usado como conquista/avatar
    icone = db.Column(db.String(200), default="")


class Pedido(db.Model):
    __tablename__ = "pedidos"
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, nullable=False)
    produto_id = db.Column(db.Integer)
    produto = db.Column(db.String(100), nullable=False)
    preco = db.Column(db.Float, nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    total = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(30), default="Recebido")
    data_pedido = db.Column(db.DateTime, default=datetime.now)

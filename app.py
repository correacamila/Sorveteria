import os
from uuid import uuid4

from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from banco import db
from modelos import Usuario, Produto, Pedido


app = Flask(__name__)
app.secret_key = "chave-sorveteria-doce-neve"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(app.root_path, "doce_neve.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024

UPLOAD_PRODUTOS = os.path.join(app.root_path, "static", "uploads", "produtos")
UPLOAD_AVATARES = os.path.join(app.root_path, "static", "uploads", "avatares")
EXTENSOES = {"png", "jpg", "jpeg", "webp", "gif"}
LIMITE_ICONE = 5
STATUS = ["Recebido", "Em preparação", "Pronto", "Entregue"]

os.makedirs(UPLOAD_PRODUTOS, exist_ok=True)
os.makedirs(UPLOAD_AVATARES, exist_ok=True)
db.init_app(app)


def exigir_login():
    if "usuario" not in session:
        return redirect(url_for("login"))
    if not db.session.get(Usuario, session["usuario"]):
        session.clear()
        return redirect(url_for("login"))
    return None


def exige_adm():
    erro = exigir_login()
    if erro:
        return erro
    if not db.session.get(Usuario, session["usuario"]).adm:
        flash("Acesso permitido apenas para administradores.", "erro")
        return redirect(url_for("inicio"))
    return None


def salvar_upload(arquivo, pasta):
    if not arquivo or not arquivo.filename:
        return ""
    nome = secure_filename(arquivo.filename)
    extensao = nome.rsplit(".", 1)[-1].lower() if "." in nome else ""
    if extensao not in EXTENSOES:
        return ""
    nome_final = f"{uuid4().hex}.{extensao}"
    arquivo.save(os.path.join(pasta, nome_final))
    return nome_final

def caminho_foto(foto):
    # Monta o caminho correto da foto para o HTML.
    if not foto:
        return "avatares/inicial_neutro.png"

    if foto.startswith("uploads/"):
        return foto

    return "avatares/" + foto


def produtos_mais_vendidos(limite=3):
    pedidos = Pedido.query.filter_by(status="Entregue").all()
    vendas = {}
    for pedido in pedidos:
        vendas[pedido.produto_id] = vendas.get(pedido.produto_id, 0) + pedido.quantidade

    produtos = Produto.query.all()
    produtos.sort(key=lambda p: (vendas.get(p.id, 0), p.id), reverse=True)
    return [(p, vendas.get(p.id, 0)) for p in produtos[:limite] if vendas.get(p.id, 0) > 0]


def total_comprado(usuario_id, produto_id):
    return sum(
        p.quantidade
        for p in Pedido.query.filter_by(
            usuario_id=usuario_id, produto_id=produto_id, status="Entregue"
        ).all()
    )


def icones_desbloqueados(usuario):
    # Administrador possui todas as conquistas.
    if usuario.adm:
        return Produto.query.order_by(Produto.id).all()

    # Usuário desbloqueia conforme suas compras.
    return [
        produto
        for produto in Produto.query.order_by(Produto.id).all()
        if total_comprado(usuario.id, produto.id) >= LIMITE_ICONE
    ]


def ranking_usuarios():
    usuarios = Usuario.query.order_by(Usuario.nome).all()
    ranking = []
    for usuario in usuarios:
        total = sum(
            p.quantidade
            for p in Pedido.query.filter_by(usuario_id=usuario.id, status="Entregue").all()
        )
        ranking.append({"usuario": usuario, "total": total})
    ranking.sort(key=lambda item: (-item["total"], item["usuario"].nome.lower()))
    for posicao, item in enumerate(ranking, 1):
        item["posicao"] = posicao
    return ranking


def estatisticas():
    pedidos = Pedido.query.all()
    entregues = [p for p in pedidos if p.status == "Entregue"]
    vendas = {}
    for pedido in entregues:
        item = vendas.setdefault(pedido.produto_id, {"quantidade": 0, "total": 0})
        item["quantidade"] += pedido.quantidade
        item["total"] += pedido.total

    produtos = Produto.query.all()
    vendas_produtos = sorted(
        [(p, vendas.get(p.id, {}).get("quantidade", 0), vendas.get(p.id, {}).get("total", 0))
         for p in produtos],
        key=lambda x: (-x[1], x[0].nome.lower())
    )

    categorias = {}
    for produto, quantidade, _ in vendas_produtos:
        categorias[produto.categoria or "Sem categoria"] = (
            categorias.get(produto.categoria or "Sem categoria", 0) + quantidade
        )

    return {
        "usuarios": Usuario.query.count(),
        "produtos": Produto.query.count(),
        "pedidos": len(pedidos),
        "entregues": len(entregues),
        "pendentes": len(pedidos) - len(entregues),
        "faturamento": sum(p.total for p in entregues),
        "vendas_produtos": vendas_produtos,
        "categorias": sorted(categorias.items(), key=lambda x: x[1], reverse=True),
    }


@app.context_processor
def dados_menu():
    return {
        "ranking_top": ranking_usuarios()[:5],
        "icone_limite": LIMITE_ICONE,
    }


@app.route("/")
def inicio():
    favoritos = produtos_mais_vendidos(3)
    novidade = Produto.query.order_by(Produto.id.desc()).first()
    return render_template("inicio.html", favoritos=favoritos, novidade=novidade)


@app.route("/cardapio")
def cardapio():
    categoria = request.args.get("categoria", "Todos")
    consulta = Produto.query.order_by(Produto.id.desc())
    if categoria != "Todos":
        consulta = Produto.query.filter_by(categoria=categoria).order_by(Produto.id.desc())

    produtos = consulta.all()
    categorias = [p.categoria for p in Produto.query.order_by(Produto.categoria).all() if p.categoria]
    categorias = list(dict.fromkeys(categorias))
    return render_template("cardapio.html", produtos=produtos, categorias=categorias, categoria_atual=categoria)


@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "POST":
        nome = request.form["nome"].strip()
        email = request.form["email"].strip().lower()
        senha = request.form["senha"]

        if Usuario.query.filter_by(email=email).first():
            flash("Este e-mail já está cadastrado.", "erro")
            return redirect(url_for("cadastro"))

        usuario = Usuario(
            nome=nome,
            email=email,
            senha=generate_password_hash(senha),
            apelido=nome.split()[0],
            foto="inicial_neutro.png",
            adm=False,
            principal=False,
        )
        db.session.add(usuario)
        db.session.commit()
        flash("Cadastro realizado com sucesso!", "sucesso")
        return redirect(url_for("login"))

    return render_template("cadastro.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        senha = request.form["senha"]
        usuario = Usuario.query.filter_by(email=email).first()

        if usuario and check_password_hash(usuario.senha, senha):
            session["usuario"] = usuario.id
            session["adm"] = usuario.adm
            flash("Login realizado com sucesso!", "sucesso")
            return redirect(url_for("inicio"))

        flash("E-mail ou senha incorretos.", "erro")
    return render_template("login.html")

@app.route("/logout/confirmar")
def logout_confirmar():
    return render_template("confirmar.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Você saiu da conta.", "sucesso")
    return redirect(url_for("inicio"))


@app.route("/perfil", methods=["GET", "POST"])
def perfil():
    erro = exigir_login()
    if erro:
        return erro

    usuario = db.session.get(Usuario, session["usuario"])

    if request.method == "POST":
        arquivo = request.files.get("foto_upload")
        nova_foto = salvar_upload(arquivo, UPLOAD_AVATARES)

        # Também permite escolher um ícone já desbloqueado.
        foto_escolhida = request.form.get("foto", "")
        iniciais = (
            {"admin_fem.png", "admin_mas.png", "admin_neutro.png"}
            if usuario.adm
            else {"inicial_fem.png", "inicial_mas.png", "inicial_neutro.png"}
        )
        permitidas = iniciais | {
            p.imagem
            for p in icones_desbloqueados(usuario)
            if p.imagem
        }

        if foto_escolhida in permitidas:
            usuario.foto = foto_escolhida

        db.session.commit()
        flash("Imagem do perfil atualizada!", "sucesso")
        return redirect(url_for("perfil"))

    return render_template(
        "perfil.html",
        usuario=usuario,
        desbloqueados=icones_desbloqueados(usuario),
        produtos=Produto.query.all(),
        limite=LIMITE_ICONE,
    )


@app.route("/pedido", methods=["GET", "POST"])
def novo_pedido():
    erro = exigir_login()
    if erro:
        return erro

    produto_id = request.args.get("produto_id", type=int)
    if request.method == "POST":
        produto_id = request.form.get("produto_id", type=int)
        quantidade = request.form.get("quantidade", type=int)
        produto = db.session.get(Produto, produto_id)

        if not produto:
            flash("Produto não encontrado.", "erro")
            return redirect(url_for("novo_pedido"))
        if not quantidade or quantidade < 1:
            flash("A quantidade deve ser pelo menos 1.", "erro")
            return redirect(url_for("novo_pedido"))

        pedido = Pedido(
            usuario_id=session["usuario"],
            produto_id=produto.id,
            produto=produto.nome,
            preco=produto.preco,
            quantidade=quantidade,
            total=produto.preco * quantidade,
            status="Recebido",
        )
        db.session.add(pedido)
        db.session.commit()
        flash("Pedido realizado com sucesso!", "sucesso")
        return redirect(url_for("pedidos"))

    return render_template(
        "novo_pedido.html",
        produtos=Produto.query.order_by(Produto.nome).all(),
        produto_id=produto_id,
    )


@app.route("/pedidos")
def pedidos():
    erro = exigir_login()
    if erro:
        return erro
    meus_pedidos = (
        Pedido.query.filter_by(usuario_id=session["usuario"])
        .order_by(Pedido.id.desc()).all()
    )
    return render_template("pedidos.html", pedidos=meus_pedidos)


@app.route("/ranking")
def ranking():
    erro = exigir_login()
    if erro:
        return erro

    usuario = db.session.get(Usuario, session["usuario"])
    ranking = ranking_usuarios()

    posicao = next(
        (item["posicao"] for item in ranking
         if item["usuario"].id == usuario.id),
        "-"
    )

    return render_template(
        "ranking.html",
        ranking=ranking,
        usuario=usuario,
        posicao=posicao,
        caminho_foto=caminho_foto
    )

@app.route("/dashboard")
def dashboard():
    erro = exige_adm()
    if erro:
        return erro

    pedidos = Pedido.query.filter_by(status="Entregue").all()

    # Compras por sorvete
    vendas = {}

    for pedido in pedidos:
        nome = pedido.produto
        vendas[nome] = vendas.get(nome, 0) + pedido.quantidade

    # Rendimento por data
    rendimento = {}

    for pedido in pedidos:
        data = pedido.data_pedido.strftime("%d/%m")
        rendimento[data] = rendimento.get(data, 0) + pedido.total

    return render_template(
        "dashboard.html",
        vendas=vendas,
        rendimento=rendimento
    )

@app.route("/relatorio")
def relatorio():
    acesso = exige_adm()
    if acesso:
        return acesso

    dados = estatisticas()
    return render_template("relatorio.html", **dados)


@app.route("/admin")
def admin():
    acesso = exige_adm()
    if acesso:
        return acesso
    return render_template("admin.html", dados=estatisticas())


@app.route("/admin/pedidos")
def admin_pedidos():
    acesso = exige_adm()
    if acesso:
        return acesso

    pedidos = Pedido.query.order_by(Pedido.id.desc()).all()
    for pedido in pedidos:
        usuario = db.session.get(Usuario, pedido.usuario_id)
        pedido.cliente = usuario.nome if usuario else "Usuário não encontrado"
    return render_template("admin_pedidos.html", pedidos=pedidos)


@app.route("/admin/pedidos/<int:id>", methods=["POST"])
def alterar_status(id):
    acesso = exige_adm()
    if acesso:
        return acesso

    pedido = db.session.get(Pedido, id)
    status = request.form.get("status")
    if pedido and status in STATUS:
        pedido.status = status
        db.session.commit()
        flash("Status atualizado.", "sucesso")
    return redirect(url_for("admin_pedidos"))


@app.route("/admin/usuarios")
def admin_usuarios():
    acesso = exige_adm()
    if acesso:
        return acesso

    return render_template(
        "admin_usuarios.html",
        clientes=Usuario.query.filter_by(adm=False).order_by(Usuario.nome).all(),
        administradores=Usuario.query.filter_by(adm=True).order_by(Usuario.nome).all(),
    )


@app.route("/admin/usuarios/<int:id>/tornar-adm", methods=["POST"])
def tornar_adm(id):
    acesso = exige_adm()
    if acesso:
        return acesso
    usuario = db.session.get(Usuario, id)
    if usuario:
        usuario.adm = True
        db.session.commit()
    return redirect(url_for("admin_usuarios"))


@app.route("/admin/usuarios/<int:id>/remover-adm", methods=["POST"])
def remover_adm(id):
    acesso = exige_adm()
    if acesso:
        return acesso
    usuario = db.session.get(Usuario, id)
    if usuario and not usuario.principal and usuario.id != session["usuario"]:
        usuario.adm = False
        db.session.commit()
    return redirect(url_for("admin_usuarios"))

@app.route("/admin/usuarios/<int:id>/remover/confirmar")
def confirmar_remocao_usuario(id):
    acesso = exige_adm()

    if acesso:
        return acesso

    usuario = db.session.get(Usuario, id)

    if not usuario or usuario.principal or usuario.id == session["usuario"]:
        flash("Não é possível remover este usuário.", "erro")
        return redirect(url_for("admin_usuarios"))

    return render_template(
        "confirmar_exclusao.html",
        tipo="usuario",
        usuario=usuario
    )

@app.route("/admin/usuarios/<int:id>/remover", methods=["POST"])
def remover_usuario(id):
    acesso = exige_adm()
    if acesso:
        return acesso
    usuario = db.session.get(Usuario, id)
    if usuario and not usuario.principal and usuario.id != session["usuario"]:
        db.session.delete(usuario)
        db.session.commit()
    return redirect(url_for("admin_usuarios"))


@app.route("/admin/produtos")
def admin_produtos():
    acesso = exige_adm()
    if acesso:
        return acesso
    return render_template("admin_produtos.html", produtos=Produto.query.order_by(Produto.id.desc()).all())


@app.route("/admin/produtos/adicionar", methods=["POST"])
def adicionar_produto():
    acesso = exige_adm()
    if acesso:
        return acesso

    try:
        preco = float(request.form["preco"].replace(",", "."))
    except ValueError:
        flash("Informe um preço válido.", "erro")
        return redirect(url_for("admin_produtos"))

    # Salva a foto do sorvete
    imagem = salvar_upload(request.files.get("imagem"), UPLOAD_PRODUTOS)

    # Salva o desenho da conquista
    icone = salvar_upload(request.files.get("icone"), UPLOAD_PRODUTOS)

    produto = Produto(
        nome=request.form["nome"].strip(),
        descricao=request.form["descricao"].strip(),
        categoria=request.form["categoria"].strip(),
        preco=preco,
        imagem="uploads/produtos/" + imagem if imagem else "",
        icone="uploads/produtos/" + icone if icone else "",
    )

    db.session.add(produto)
    db.session.commit()

    flash("Sorvete cadastrado com sucesso!", "sucesso")
    return redirect(url_for("admin_produtos"))


@app.route("/admin/produtos/<int:id>/editar", methods=["GET", "POST"])
def editar_produto(id):
    acesso = exige_adm()
    if acesso:
        return acesso

    produto = db.session.get(Produto, id)

    if not produto:
        flash("Produto não encontrado.", "erro")
        return redirect(url_for("admin_produtos"))

    if request.method == "POST":
        try:
            produto.preco = float(request.form["preco"].replace(",", "."))
        except ValueError:
            flash("Informe um preço válido.", "erro")
            return redirect(url_for("editar_produto", id=id))

        produto.nome = request.form["nome"].strip()
        produto.descricao = request.form["descricao"].strip()
        produto.categoria = request.form["categoria"].strip()

        # Atualiza a foto do sorvete, se enviada
        imagem = salvar_upload(request.files.get("imagem"), UPLOAD_PRODUTOS)
        if imagem:
            produto.imagem = "uploads/produtos/" + imagem

        # Atualiza o ícone da conquista, se enviado
        icone = salvar_upload(request.files.get("icone"), UPLOAD_PRODUTOS)
        if icone:
            produto.icone = "uploads/produtos/" + icone

        db.session.commit()

        flash("Sorvete atualizado!", "sucesso")
        return redirect(url_for("admin_produtos"))

    return render_template("editar_produto.html", produto=produto)

@app.route("/admin/produtos/<int:id>/remover", methods=["POST"])
def remover_produto(id):
    acesso = exige_adm()
    if acesso:
        return acesso

    produto = db.session.get(Produto, id)
    if produto:
        db.session.delete(produto)
        db.session.commit()
        flash("Sorvete removido.", "sucesso")
    return redirect(url_for("admin_produtos"))


@app.route("/admin/financeiro")
def admin_financeiro():
    acesso = exige_adm()
    if acesso:
        return acesso

    entregues = Pedido.query.filter_by(status="Entregue").all()
    usuarios = Usuario.query.all()
    produtos = Produto.query.all()

    gastos_clientes = [
        {
            "nome": u.nome,
            "total": sum(p.total for p in entregues if p.usuario_id == u.id),
        }
        for u in usuarios
    ]

    faturamento_produtos = []
    for produto in produtos:
        vendas = [p for p in entregues if p.produto_id == produto.id]
        faturamento_produtos.append({
            "nome": produto.nome,
            "quantidade": sum(p.quantidade for p in vendas),
            "total": sum(p.total for p in vendas),
        })

    return render_template(
        "admin_financeiro.html",
        gastos_clientes=gastos_clientes,
        faturamento_produtos=faturamento_produtos,
    )

@app.route("/conta/excluir/confirmar")
def confirmar_exclusao_conta():
    erro = exigir_login()
    if erro:
        return erro

    return render_template("confirmar_exclusao.html", tipo="conta")

@app.route("/admin/produtos/<int:id>/excluir/confirmar")
def confirmar_exclusao_produto(id):
    acesso = exige_adm()
    if acesso:
        return acesso

    produto = db.session.get(Produto, id)

    if not produto:
        flash("Produto não encontrado.", "erro")
        return redirect(url_for("admin_produtos"))

    return render_template(
        "confirmar_exclusao.html",
        tipo="produto",
        produto=produto
    )

def criar_dados_iniciais():
    # Cria o primeiro administrador e o cardápio inicial sem JSON.
    if not Usuario.query.filter_by(email="admin.docedeneve@gmail.com").first():
        db.session.add(Usuario(
            nome="Administrador",
            email="admin.docedeneve@gmail.com",
            senha=generate_password_hash("1234567890"),
            apelido="Admin",
            foto="admin_mas.png",
            adm=True,
            principal=True,
        ))

    if not Produto.query.first():
        iniciais = [
            ("Chocolate Cremoso", "Sorvete de chocolate cremoso.", "Clássicos", 8.50, "avatares/chocolate.png"),
            ("Morango", "Sorvete de morango refrescante.", "Frutas", 8.00, "avatares/morango.png"),
            ("Ninho com Nutella", "Leite em pó com creme de avelã.", "Especiais", 11.50, "avatares/ninho_nutella.png"),
            ("Baunilha", "Clássico sorvete de baunilha.", "Clássicos", 7.50, "avatares/baunilha.png"),
            ("Maracujá", "Sorvete de maracujá doce e refrescante.", "Frutas", 8.50, "avatares/maracuja.png"),
            ("Chocomenta", "Chocolate com um toque refrescante de menta.", "Especiais", 7.00, "avatares/chocomenta.png"),
        ]
        for nome, descricao, categoria, preco, imagem in iniciais:
            db.session.add(Produto(
                nome=nome, descricao=descricao, categoria=categoria,
                preco=preco, imagem=imagem
            ))

    db.session.commit()


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        criar_dados_iniciais()
    app.run(debug=True)

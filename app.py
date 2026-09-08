from flask import Flask, render_template, request, redirect, url_for, session, flash
from banco import ler_dados, salvar_dados
from modelos import criar_usuario, criar_pedido

app = Flask(__name__)
app.secret_key = "chave-sorveteria-doce-neve"

def exige_adm():
    if "usuario" not in session:
        return redirect(url_for("login"))

    dados = ler_dados()
    usuario = None

    for item in dados["usuarios"]:
        if item["id"] == session["usuario"]:
            usuario = item
            break

    if usuario is None:
        session.clear()
        return redirect(url_for("login"))

    if not usuario["adm"]:
        return redirect(url_for("inicio"))

    return None

def exigir_login():
    if "usuario" not in session:
        return redirect(url_for("login"))
    return None

@app.route("/admin")
def admin():
    acesso = exige_adm()
    if acesso:
        return acesso

    dados = ler_dados()

    total_pedidos = len(dados["pedidos"])
    total_usuarios = len(dados["usuarios"])
    total_produtos = len(dados["produtos"])

    faturamento = sum(pedido["total"] for pedido in dados["pedidos"] if pedido["status"] == "Entregue")

    pedidos_entregues = 0
    pedidos_pendentes = 0

    for pedido in dados["pedidos"]:
        if pedido["status"] == "Entregue":
            pedidos_entregues += 1
        else:
            pedidos_pendentes += 1

    gastos_clientes = []

    for usuario in dados["usuarios"]:
        total_cliente = 0

        for pedido in dados["pedidos"]:
            if pedido["usuario_id"] == usuario["id"] and pedido["status"] == "Entregue":
                total_cliente += pedido["total"]

        gastos_clientes.append({
            "nome": usuario["nome"],
            "total": total_cliente
        })

    faturamento_produtos = []

    for produto in dados["produtos"]:
        total_produto = 0
        quantidade_vendida = 0

        for pedido in dados["pedidos"]:
            if pedido["produto"] == produto["nome"] and pedido["status"] == "Entregue":
                total_produto += pedido["total"]
                quantidade_vendida += pedido["quantidade"]

        faturamento_produtos.append({
            "nome": produto["nome"],
            "quantidade": quantidade_vendida,
            "total": total_produto
        }) 

    return render_template(
    "admin.html",
    total_pedidos=total_pedidos,
    total_usuarios=total_usuarios,
    total_produtos=total_produtos,
    faturamento=faturamento,
    pedidos_entregues=pedidos_entregues,
    pedidos_pendentes=pedidos_pendentes,
    gastos_clientes=gastos_clientes,
    faturamento_produtos=faturamento_produtos
)

@app.route("/")
def inicio():
    dados = ler_dados()
    return render_template("inicio.html", produtos=dados["produtos"])

@app.route("/cardapio")
def cardapio():
    dados = ler_dados()
    categoria = request.args.get("categoria", "Todos")
    produtos = []

    for produto in dados["produtos"]:
        if categoria == "Todos" or produto["categoria"] == categoria:
            produtos.append(produto)

    categorias = []

    for produto in dados["produtos"]:
        if produto["categoria"] not in categorias:
            categorias.append(produto["categoria"])

    return render_template("cardapio.html", produtos=produtos, categorias=categorias, categoria_atual=categoria
    )

@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "POST":
        nome = request.form["nome"].strip()
        email = request.form["email"].strip().lower()
        senha = request.form["senha"]

        dados = ler_dados()

        for usuario in dados["usuarios"]:
            if usuario["email"] == email:
                flash("Este e-mail já está cadastrado.", "erro")
                return redirect(url_for("cadastro"))

        usuario = criar_usuario(
            dados["proximo_id_usuario"],
            nome,
            email,
            senha
        )

        dados["usuarios"].append(usuario)
        dados["proximo_id_usuario"] += 1

        salvar_dados(dados)

        flash("Cadastro realizado com sucesso!", "sucesso")

        return redirect(url_for("login"))

    return render_template("cadastro.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        senha = request.form["senha"]

        dados = ler_dados()
        usuario_encontrado = None

        for usuario in dados["usuarios"]:
            if usuario["email"] == email and usuario["senha"] == senha:
                usuario_encontrado = usuario
                break

        if usuario_encontrado:
            session["usuario"] = usuario_encontrado["id"]
            session["adm"] = usuario_encontrado["adm"]

            flash("Login realizado com sucesso!", "sucesso")
            return redirect(url_for("inicio"))

        flash("E-mail ou senha incorretos.", "erro")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Você saiu da conta.", "sucesso")
    return redirect(url_for("inicio"))

@app.route("/pedido", methods=["GET", "POST"])
def novo_pedido():
    erro = exigir_login()
    if erro:
        return erro

    dados = ler_dados()

    if request.method == "POST":
        produto_id = int(request.form["produto_id"])
        quantidade = int(request.form["quantidade"])

        produto = None

        for item in dados["produtos"]:
            if item["id"] == produto_id:
                produto = item
                break

        if produto is None:
            flash("Produto não encontrado.", "erro")
            return redirect(url_for("novo_pedido"))

        if quantidade < 1:
            flash("A quantidade deve ser pelo menos 1.", "erro")
            return redirect(url_for("novo_pedido"))

        pedido = criar_pedido(
            dados["proximo_id_pedido"],
            session["usuario"],
            produto,
            quantidade
        )

        dados["pedidos"].append(pedido)
        dados["proximo_id_pedido"] += 1

        salvar_dados(dados)

        flash("Pedido realizado com sucesso!", "sucesso")
        return redirect(url_for("pedidos"))
    return render_template("novo_pedido.html", produtos=dados["produtos"])

@app.route("/pedidos")
def pedidos():
    erro = exigir_login()
    if erro:
        return erro

    dados = ler_dados()
    meus_pedidos = []

    for pedido in dados["pedidos"]:
        if pedido["usuario_id"] == session["usuario"]:
            meus_pedidos.append(pedido)
    return render_template("pedidos.html", pedidos=meus_pedidos)

@app.route("/perfil")
def perfil():
    erro = exigir_login()
    if erro:
        return erro

    dados = ler_dados()
    usuario = None

    for item in dados["usuarios"]:
        if item["id"] == session["usuario"]:
            usuario = item
            break

    return render_template("perfil.html", usuario=usuario)

@app.route("/relatorio")
def relatorio():
    erro = exigir_login()
    if erro:
        return erro

    dados = ler_dados()

    total_pedidos = len(dados["pedidos"])
    faturamento = 0

    for pedido in dados["pedidos"]:
        if pedido["status"] == "Entregue":
            faturamento += pedido["total"]

    return render_template("relatorio.html", total_pedidos=total_pedidos, faturamento=faturamento, total_produtos=len(dados["produtos"]), total_usuarios=len(dados["usuarios"]))

@app.route("/admin/pedidos")
def admin_pedidos():
    acesso = exige_adm()

    if acesso:
        return acesso

    dados = ler_dados()
    pedidos = []

    for pedido in dados["pedidos"]:
        usuario = None

        for item in dados["usuarios"]:
            if item["id"] == pedido["usuario_id"]:
                usuario = item
                break

        pedido_visual = pedido.copy()

        if usuario:
            pedido_visual["cliente"] = usuario["nome"]
        else:
            pedido_visual["cliente"] = "Usuário não encontrado"

        pedidos.append(pedido_visual)

    return render_template(
        "admin_pedidos.html",
        pedidos=pedidos
    )

@app.route("/admin/pedidos/<int:id>", methods=["POST"])
def alterar_status(id):
    acesso = exige_adm()

    if acesso:
        return acesso

    dados = ler_dados()

    status = request.form["status"]

    if status in ["Recebido", "Em preparação", "Pronto", "Entregue"]:
        for pedido in dados["pedidos"]:
            if pedido["id"] == id:
                pedido["status"] = status
                break

    salvar_dados(dados)

    return redirect(url_for("admin_pedidos"))

@app.route("/admin/usuarios")
def admin_usuarios():
    acesso = exige_adm()

    if acesso:
        return acesso

    dados = ler_dados()

    return render_template(
        "admin_usuarios.html",
        usuarios=dados["usuarios"]
    )

@app.route("/admin/usuarios/<int:id>/tornar-adm", methods=["POST"])
def tornar_adm(id):
    acesso = exige_adm()

    if acesso:
        return acesso

    dados = ler_dados()

    for usuario in dados["usuarios"]:
        if usuario["id"] == id:
            usuario["adm"] = True
            break

    salvar_dados(dados)

    return redirect(url_for("admin_usuarios"))

@app.route("/admin/usuarios/<int:id>/remover-adm", methods=["POST"])
def remover_adm(id):
    acesso = exige_adm()

    if acesso:
        return acesso

    dados = ler_dados()

    for usuario in dados["usuarios"]:
        if usuario["id"] == id:

            if usuario["principal"]:
                return redirect(url_for("admin_usuarios"))

            if usuario["id"] == session["usuario"]:
                return redirect(url_for("admin_usuarios"))

            usuario["adm"] = False
            break

    salvar_dados(dados)

    return redirect(url_for("admin_usuarios"))

@app.route("/admin/usuarios/<int:id>/remover", methods=["POST"])
def remover_usuario(id):
    acesso = exige_adm()

    if acesso:
        return acesso

    dados = ler_dados()

    for usuario in dados["usuarios"]:
        if usuario["id"] == id:

            if usuario["principal"]:
                return redirect(url_for("admin_usuarios"))

            if usuario["id"] == session["usuario"]:
                return redirect(url_for("admin_usuarios"))

            dados["usuarios"].remove(usuario)
            break

    salvar_dados(dados)

    return redirect(url_for("admin_usuarios"))

@app.route("/admin/produtos")
def admin_produtos():
    acesso = exige_adm()

    if acesso:
        return acesso

    dados = ler_dados()

    return render_template(
        "admin_produtos.html",
        produtos=dados["produtos"]
    )


@app.route("/admin/produtos/adicionar", methods=["POST"])
def adicionar_produto():
    acesso = exige_adm()

    if acesso:
        return acesso

    dados = ler_dados()

    nome = request.form["nome"].strip()
    descricao = request.form["descricao"].strip()
    categoria = request.form["categoria"].strip()
    preco = float(request.form["preco"])

    produto = {
        "id": dados["proximo_id_produto"],
        "nome": nome,
        "descricao": descricao,
        "categoria": categoria,
        "preco": preco
    }

    dados["produtos"].append(produto)
    dados["proximo_id_produto"] += 1

    salvar_dados(dados)

    return redirect(url_for("admin_produtos"))

@app.route("/admin/produtos/<int:id>/editar", methods=["GET", "POST"])
def editar_produto(id):
    acesso = exige_adm()

    if acesso:
        return acesso

    dados = ler_dados()
    produto = None

    for item in dados["produtos"]:
        if item["id"] == id:
            produto = item
            break

    if produto is None:
        return redirect(url_for("admin_produtos"))

    if request.method == "POST":
        produto["nome"] = request.form["nome"].strip()
        produto["descricao"] = request.form["descricao"].strip()
        produto["categoria"] = request.form["categoria"].strip()
        produto["preco"] = float(request.form["preco"])

        salvar_dados(dados)

        return redirect(url_for("admin_produtos"))

    return render_template(
        "editar_produto.html",
        produto=produto
    )

@app.route("/admin/produtos/<int:id>/remover", methods=["POST"])
def remover_produto(id):
    acesso = exige_adm()

    if acesso:
        return acesso

    dados = ler_dados()

    dados["produtos"] = [
        produto
        for produto in dados["produtos"]
        if produto["id"] != id
    ]

    salvar_dados(dados)

    return redirect(url_for("admin_produtos"))
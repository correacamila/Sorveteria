from flask import Flask,render_template,request,redirect,url_for,session,flash
from banco import ler_dados,salvar_dados
from modelos import criar_usuario,criar_pedido

app=Flask(__name__)
app.secret_key="chave-sorveteria-doce-neve"

def exigir_login():
    if "usuario" not in session:return redirect(url_for("login"))
    return None

def exige_adm():
    if "usuario" not in session:return redirect(url_for("login"))
    dados=ler_dados()
    usuario=None
    for item in dados["usuarios"]:
        if item["id"]==session["usuario"]:
            usuario=item
            break
    if usuario is None:
        session.clear()
        return redirect(url_for("login"))
    if not usuario["adm"]:return redirect(url_for("inicio"))
    return None

@app.route("/")
def inicio():
    dados=ler_dados()
    return render_template("inicio.html",produtos=dados["produtos"])

@app.route("/cardapio")
def cardapio():
    dados=ler_dados()
    categoria=request.args.get("categoria","Todos")
    produtos=[p for p in dados["produtos"] if categoria=="Todos" or p["categoria"]==categoria]
    categorias=[]
    for p in dados["produtos"]:
        if p["categoria"] not in categorias:categorias.append(p["categoria"])
    return render_template("cardapio.html",produtos=produtos,categorias=categorias,categoria_atual=categoria)

@app.route("/cadastro",methods=["GET","POST"])
def cadastro():
    if request.method=="POST":
        nome=request.form["nome"].strip()
        email=request.form["email"].strip().lower()
        senha=request.form["senha"]
        dados=ler_dados()
        for usuario in dados["usuarios"]:
            if usuario["email"]==email:
                flash("Este e-mail já está cadastrado.","erro")
                return redirect(url_for("cadastro"))
        usuario=criar_usuario(dados["proximo_id_usuario"],nome,email,senha)
        dados["usuarios"].append(usuario)
        dados["proximo_id_usuario"]+=1
        salvar_dados(dados)
        flash("Cadastro realizado com sucesso!","sucesso")
        return redirect(url_for("login"))
    return render_template("cadastro.html")

@app.route("/login",methods=["GET","POST"])
def login():
    if request.method=="POST":
        email=request.form["email"].strip().lower()
        senha=request.form["senha"]
        dados=ler_dados()
        usuario_encontrado=None
        for usuario in dados["usuarios"]:
            if usuario["email"]==email and usuario["senha"]==senha:
                usuario_encontrado=usuario
                break
        if usuario_encontrado:
            session["usuario"]=usuario_encontrado["id"]
            session["adm"]=usuario_encontrado["adm"]
            flash("Login realizado com sucesso!","sucesso")
            return redirect(url_for("inicio"))
        flash("E-mail ou senha incorretos.","erro")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Você saiu da conta.","sucesso")
    return redirect(url_for("inicio"))

@app.route("/perfil")
def perfil():
    erro=exigir_login()
    if erro:return erro
    dados=ler_dados()
    usuario=None
    for item in dados["usuarios"]:
        if item["id"]==session["usuario"]:
            usuario=item
            break
    return render_template("perfil.html",usuario=usuario)

@app.route("/pedido",methods=["GET","POST"])
def novo_pedido():
    erro=exigir_login()
    if erro:return erro
    dados=ler_dados()
    produto_id=request.args.get("produto_id",type=int)
    if request.method=="POST":
        produto_id=int(request.form["produto_id"])
        quantidade=int(request.form["quantidade"])
        produto=None
        for item in dados["produtos"]:
            if item["id"]==produto_id:
                produto=item
                break
        if produto is None:
            flash("Produto não encontrado.","erro")
            return redirect(url_for("novo_pedido"))
        if quantidade<1:
            flash("A quantidade deve ser pelo menos 1.","erro")
            return redirect(url_for("novo_pedido"))
        pedido=criar_pedido(dados["proximo_id_pedido"],session["usuario"],produto,quantidade)
        dados["pedidos"].append(pedido)
        dados["proximo_id_pedido"]+=1
        salvar_dados(dados)
        flash("Pedido realizado com sucesso!","sucesso")
        return redirect(url_for("pedidos"))
    return render_template("novo_pedido.html",produtos=dados["produtos"],produto_id=produto_id)

@app.route("/pedidos")
def pedidos():
    erro=exigir_login()
    if erro:return erro
    dados=ler_dados()
    meus_pedidos=[p for p in dados["pedidos"] if p["usuario_id"]==session["usuario"]]
    return render_template("pedidos.html",pedidos=meus_pedidos)

@app.route("/relatorio")
def relatorio():
    erro=exigir_login()
    if erro:return erro
    dados=ler_dados()
    pedidos_entregues=sum(1 for p in dados["pedidos"] if p["status"]=="Entregue")
    pedidos_pendentes=sum(1 for p in dados["pedidos"] if p["status"]!="Entregue")
    faturamento=sum(p["total"] for p in dados["pedidos"] if p["status"]=="Entregue")
    return render_template("relatorio.html",total_pedidos=len(dados["pedidos"]),pedidos_entregues=pedidos_entregues,pedidos_pendentes=pedidos_pendentes,faturamento=faturamento,total_produtos=len(dados["produtos"]),total_usuarios=len(dados["usuarios"]))

@app.route("/admin")
def admin():
    acesso=exige_adm()
    if acesso:return acesso
    return render_template("admin.html")

@app.route("/admin/pedidos")
def admin_pedidos():
    acesso=exige_adm()
    if acesso:return acesso
    dados=ler_dados()
    pedidos=[]
    for pedido in dados["pedidos"]:
        usuario=None
        for item in dados["usuarios"]:
            if item["id"]==pedido["usuario_id"]:
                usuario=item
                break
        pedido_visual=pedido.copy()
        pedido_visual["cliente"]=usuario["nome"] if usuario else "Usuário não encontrado"
        pedidos.append(pedido_visual)
    return render_template("admin_pedidos.html",pedidos=pedidos)

@app.route("/admin/pedidos/<int:id>",methods=["POST"])
def alterar_status(id):
    acesso=exige_adm()
    if acesso:return acesso
    dados=ler_dados()
    status=request.form["status"]
    if status in ["Recebido","Em preparação","Pronto","Entregue"]:
        for pedido in dados["pedidos"]:
            if pedido["id"]==id:
                pedido["status"]=status
                break
    salvar_dados(dados)
    return redirect(url_for("admin_pedidos"))

@app.route("/admin/usuarios")
def admin_usuarios():
    acesso=exige_adm()
    if acesso:return acesso
    dados=ler_dados()
    clientes=[u for u in dados["usuarios"] if not u["adm"]]
    administradores=[u for u in dados["usuarios"] if u["adm"]]
    clientes.sort(key=lambda u:u["nome"].lower())
    administradores.sort(key=lambda u:u["nome"].lower())
    return render_template("admin_usuarios.html",clientes=clientes,administradores=administradores)

@app.route("/admin/usuarios/<int:id>/tornar-adm",methods=["POST"])
def tornar_adm(id):
    acesso=exige_adm()
    if acesso:return acesso
    dados=ler_dados()
    for usuario in dados["usuarios"]:
        if usuario["id"]==id:
            usuario["adm"]=True
            break
    salvar_dados(dados)
    return redirect(url_for("admin_usuarios"))

@app.route("/admin/usuarios/<int:id>/remover-adm",methods=["POST"])
def remover_adm(id):
    acesso=exige_adm()
    if acesso:return acesso
    dados=ler_dados()
    for usuario in dados["usuarios"]:
        if usuario["id"]==id:
            if usuario["principal"] or usuario["id"]==session["usuario"]:
                return redirect(url_for("admin_usuarios"))
            usuario["adm"]=False
            break
    salvar_dados(dados)
    return redirect(url_for("admin_usuarios"))

@app.route("/admin/usuarios/<int:id>/remover",methods=["POST"])
def remover_usuario(id):
    acesso=exige_adm()
    if acesso:return acesso
    dados=ler_dados()
    for usuario in dados["usuarios"]:
        if usuario["id"]==id:
            if usuario["principal"] or usuario["id"]==session["usuario"]:
                return redirect(url_for("admin_usuarios"))
            dados["usuarios"].remove(usuario)
            break
    salvar_dados(dados)
    return redirect(url_for("admin_usuarios"))

@app.route("/admin/produtos")
def admin_produtos():
    acesso=exige_adm()
    if acesso:return acesso
    dados=ler_dados()
    return render_template("admin_produtos.html",produtos=dados["produtos"])

@app.route("/admin/produtos/adicionar",methods=["POST"])
def adicionar_produto():
    acesso=exige_adm()
    if acesso:return acesso
    dados=ler_dados()
    produto={
        "id":dados["proximo_id_produto"],
        "nome":request.form["nome"].strip(),
        "descricao":request.form["descricao"].strip(),
        "categoria":request.form["categoria"].strip(),
        "preco":float(request.form["preco"])
    }
    dados["produtos"].append(produto)
    dados["proximo_id_produto"]+=1
    salvar_dados(dados)
    return redirect(url_for("admin_produtos"))

@app.route("/admin/produtos/<int:id>/editar",methods=["GET","POST"])
def editar_produto(id):
    acesso=exige_adm()
    if acesso:return acesso
    dados=ler_dados()
    produto=next((p for p in dados["produtos"] if p["id"]==id),None)
    if produto is None:return redirect(url_for("admin_produtos"))
    if request.method=="POST":
        produto["nome"]=request.form["nome"].strip()
        produto["descricao"]=request.form["descricao"].strip()
        produto["categoria"]=request.form["categoria"].strip()
        produto["preco"]=float(request.form["preco"])
        salvar_dados(dados)
        return redirect(url_for("admin_produtos"))
    return render_template("editar_produto.html",produto=produto)

@app.route("/admin/produtos/<int:id>/remover",methods=["POST"])
def remover_produto(id):
    acesso=exige_adm()
    if acesso:return acesso
    dados=ler_dados()
    dados["produtos"]=[p for p in dados["produtos"] if p["id"]!=id]
    salvar_dados(dados)
    return redirect(url_for("admin_produtos"))

@app.route("/admin/financeiro")
def admin_financeiro():
    acesso=exige_adm()
    if acesso:return acesso
    dados=ler_dados()
    gastos_clientes=[]
    for usuario in dados["usuarios"]:
        total=sum(p["total"] for p in dados["pedidos"] if p["usuario_id"]==usuario["id"] and p["status"]=="Entregue")
        gastos_clientes.append({"nome":usuario["nome"],"total":total})
    faturamento_produtos=[]
    for produto in dados["produtos"]:
        total=0
        quantidade=0
        for pedido in dados["pedidos"]:
            if pedido["produto"]==produto["nome"] and pedido["status"]=="Entregue":
                total+=pedido["total"]
                quantidade+=pedido["quantidade"]
        faturamento_produtos.append({"nome":produto["nome"],"quantidade":quantidade,"total":total})
    return render_template("admin_financeiro.html",gastos_clientes=gastos_clientes,faturamento_produtos=faturamento_produtos)
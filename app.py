from flask import Flask, render_template, request, redirect, session, jsonify
import psycopg
import os
import random
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

app = Flask(__name__)

app.secret_key = os.environ.get("SECRET_KEY")

DATABASE_URL = os.environ.get("DATABASE_URL")


# =========================
# CONEXÃO COM O BANCO
# =========================

def conectar_banco():
    return psycopg.connect(DATABASE_URL)


# =========================
# PÁGINAS
# =========================

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/jogador")
def jogador():
    return render_template("jogador.html")

# =========================
# PAINEL DO JOGADOR
# =========================

@app.route("/painel")
def painel():

    if "usuario_id" not in session:
        return redirect("/login")

    conexao = conectar_banco()
    cursor = conexao.cursor()

    cursor.execute(
        "SELECT login FROM usuarios WHERE id = %s",
        (session["usuario_id"],)
    )

    usuario = cursor.fetchone()

    cursor.execute(
        """
        SELECT id, nome
        FROM personagens
        WHERE usuario_id = %s
        """,
        (session["usuario_id"],)
    )

    personagem = cursor.fetchone()

    cursor.close()
    conexao.close()

    return render_template(
        "painel.html",
        usuario=usuario,
        personagem=personagem
    )


# =========================
# CRIAR CONTA
# =========================

@app.route("/criar-conta", methods=["GET", "POST"])
def criar_conta():

    if request.method == "POST":

        login = request.form["login"]
        senha = request.form["senha"]

        if not login or not senha:
            return "Preencha todos os campos."

        senha_hash = generate_password_hash(senha)

        conexao = conectar_banco()
        cursor = conexao.cursor()

        cursor.execute(
            """
            INSERT INTO usuarios (login, senha)
            VALUES (%s, %s)
            """,
            (login, senha_hash)
        )

        conexao.commit()

        cursor.close()
        conexao.close()

        return redirect("/login")

    return render_template("criar_conta.html")

# =========================
# LOGIN
# =========================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        login = request.form["login"]
        senha = request.form["senha"]

        conexao = conectar_banco()
        cursor = conexao.cursor()

        cursor.execute(
            """
            SELECT id, senha
            FROM usuarios
            WHERE login = %s
            """,
            (login,)
        )

        usuario = cursor.fetchone()

        cursor.close()
        conexao.close()

        if usuario and check_password_hash(usuario[1], senha):

            session["usuario_id"] = usuario[0]

            return redirect("/painel")

        return render_template("erro_login.html")

    return render_template("login.html")

# =========================
# LOGOUT
# =========================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# =========================
# CONFIGURAÇÕES DO RPG
# =========================

PERICIAS = [
    "Luta",
    "Pontaria",
    "Furtividade",
    "Acrobacia",
    "Vigor",
    "Percepção",
    "Tecnologia",
    "Medicina",
    "Ocultismo",
    "Persuasão",
    "Intimidação",
    "Intuição",
    "Atletismo"
]


ATRIBUTO_DAS_PERICIAS = {
    "Luta": "fisico",
    "Pontaria": "fisico",
    "Furtividade": "fisico",
    "Acrobacia": "fisico",
    "Vigor": "fisico",
    "Percepção": "mente",
    "Tecnologia": "mente",
    "Medicina": "mente",
    "Ocultismo": "mente",
    "Persuasão": "emocao",
    "Intimidação": "emocao",
    "Intuição": "emocao",
    "Atletismo": "fisico"
}


OCUPACOES = {
    "Atleta / Criança ativa": [
        "Luta",
        "Acrobacia"
    ],

    "Menino de ciência / curioso": [
        "Tecnologia",
        "Percepção"
    ],

    "Menino de história / leitor": [
        "Ocultismo",
        "Percepção"
    ],

    "Líder de turma / popular": [
        "Persuasão",
        "Intimidação"
    ],

    "Menino quieto / observador": [
        "Furtividade",
        "Intuição"
    ],

    "Menino doente / frágil": [
        "Medicina",
        "Vigor"
    ],

    "Menino de rua / sobrevivente": [
        "Furtividade",
        "Intuição"
    ],

    "Menino religioso / supersticioso": [
        "Ocultismo",
        "Intimidação"
    ]
}

PERFIS = [
    "Executor",
    "Analista",
    "Vigilante"
]


VIDA_POR_FISICO = {
    "d4": 5,
    "d6": 6,
    "d8": 8,
    "d10": 10
}


# =========================
# CRIAR FICHA
# =========================

@app.route("/criar-ficha", methods=["GET", "POST"])
def criar_ficha():

    if "usuario_id" not in session:
        return redirect("/login")

    if request.method == "POST":

        nome = request.form["nome"]
        perfil = request.form["perfil"]
        ocupacao = request.form["ocupacao"]
        vantagem_texto = request.form.get("vantagem_texto")
        fisico = request.form["fisico"]
        mente = request.form["mente"]
        emocao = request.form["emocao"]

        pv_maximo = VIDA_POR_FISICO[fisico]
        pv_atual = pv_maximo

        conexao = conectar_banco()
        cursor = conexao.cursor()

        cursor.execute(
            """
            INSERT INTO personagens (
                usuario_id,
                nome,
                perfil,
                ocupacao,
                vantagem_texto,
                vantagem_pericia,
                fisico,
                mente,
                emocao,
                pv_maximo,
                pv_atual
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                session["usuario_id"],
                nome,
                perfil,
                ocupacao,
                vantagem_texto,
                None,
                fisico,
                mente,
                emocao,
                pv_maximo,
                pv_atual
            )
        )

        personagem_id = cursor.fetchone()[0]

        for pericia in PERICIAS:

            afinidade = request.form.get(
                "pericia_" + pericia
            )

            atributo = ATRIBUTO_DAS_PERICIAS[pericia]

            cursor.execute(
                """
                INSERT INTO pericias (
                    personagem_id,
                    nome,
                    afinidade,
                    atributo
                )
                VALUES (%s, %s, %s, %s)
                """,
                (
                    personagem_id,
                    pericia,
                    afinidade,
                    atributo
                )
            )

        conexao.commit()

        cursor.close()
        conexao.close()

        return redirect("/painel")

    return render_template(
        "criar_ficha.html",
        pericias=PERICIAS,
        perfis=PERFIS,
        ocupacoes=OCUPACOES
    )


# =========================
# FICHA DO JOGADOR
# =========================

@app.route("/ficha")
def ficha():

    if "usuario_id" not in session:
        return redirect("/login")

    conexao = conectar_banco()
    cursor = conexao.cursor()

    cursor.execute(
        """
        SELECT
            id,
            nome,
            perfil,
            ocupacao,
            vantagem_texto,
            vantagem_pericia,
            fisico,
            mente,
            emocao,
            pv_maximo,
            pv_atual
        FROM personagens
        WHERE usuario_id = %s
        """,
        (session["usuario_id"],)
    )

    personagem = cursor.fetchone()

    if not personagem:

        cursor.close()
        conexao.close()

        return redirect("/criar-ficha")

    cursor.execute(
        """
        SELECT id, nome, afinidade
        FROM pericias
        WHERE personagem_id = %s
        """,
        (personagem[0],)
    )

    pericias = cursor.fetchall()

    cursor.close()
    conexao.close()

    return render_template(
        "ficha.html",
        personagem=personagem,
        pericias=pericias,
        OCUPACOES=OCUPACOES
    )


# =========================
# DELETAR FICHA
# =========================

@app.route("/deletar-ficha", methods=["POST"])
def deletar_ficha():

    if "usuario_id" not in session:
        return redirect("/login")

    conexao = conectar_banco()
    cursor = conexao.cursor()

    cursor.execute(
        """
        SELECT id
        FROM personagens
        WHERE usuario_id = %s
        """,
        (session["usuario_id"],)
    )

    personagem = cursor.fetchone()

    if personagem:

        personagem_id = personagem[0]

        cursor.execute(
            """
            DELETE FROM historico
            WHERE personagem_id = %s
            """,
            (personagem_id,)
        )

        cursor.execute(
            """
            DELETE FROM pericias
            WHERE personagem_id = %s
            """,
            (personagem_id,)
        )

        cursor.execute(
            """
            DELETE FROM personagens
            WHERE id = %s AND usuario_id = %s
            """,
            (
                personagem_id,
                session["usuario_id"]
            )
        )

    conexao.commit()

    cursor.close()
    conexao.close()

    return redirect("/painel")


# =========================
#  PERÍCIA
# =========================

@app.route("/rolar-pericia/<int:pericia_id>")
def rolar_pericia(pericia_id):

    if "usuario_id" not in session:
        return jsonify({"erro": "Não logado"}), 401

    conexao = conectar_banco()
    cursor = conexao.cursor()

    cursor.execute(
        """
        SELECT
            p.personagem_id,
            p.nome,
            p.afinidade,
            p.atributo,
            c.ocupacao,
            c.fisico,
            c.mente,
            c.emocao,
            c.vantagem_pericia
        FROM pericias p
        JOIN personagens c
            ON p.personagem_id = c.id
        WHERE
            p.id = %s
            AND c.usuario_id = %s
        """,
        (pericia_id, session["usuario_id"])
    )

    dados = cursor.fetchone()

    if not dados:
        cursor.close()
        conexao.close()

        return jsonify({
            "erro": "Perícia não encontrada"
        }), 404

    personagem_id = dados[0]
    nome = dados[1]
    afinidade = dados[2]
    atributo = dados[3]
    ocupacao = dados[4]
    fisico = dados[5]
    mente = dados[6]
    emocao = dados[7]
    vantagem_pericia = dados[8]

    valores = {
        "fisico": fisico,
        "mente": mente,
        "emocao": emocao
    }

    dado = valores[atributo]

    lados = int(dado.replace("d", ""))

    rolagem = random.randint(1, lados)

    bonus_ocupacao = 0

    print("========== TESTE OCUPAÇÃO ==========")
    print("Ocupação recebida:", repr(ocupacao))
    print("Perícia recebida:", repr(nome))
    print("Ocupações disponíveis:", OCUPACOES)
    print("Ocupação existe?:", ocupacao in OCUPACOES)

    if ocupacao in OCUPACOES:
        print("Perícias da ocupação:", OCUPACOES[ocupacao])
        print("Perícia pertence?:", nome in OCUPACOES[ocupacao])

        if nome in OCUPACOES[ocupacao]:
            bonus_ocupacao = 1

    print("BÔNUS OCUPAÇÃO FINAL:", bonus_ocupacao)
    print("====================================")

    # Bônus da vantagem escolhida pelo mestre
    bonus_vantagem = 0

    if vantagem_pericia == nome:
        bonus_vantagem = 1

    resultado_final = (
        rolagem
        + int(afinidade)
        + bonus_ocupacao
        + bonus_vantagem
    )

    texto = f"Rolou {nome}: {resultado_final}"

    if bonus_vantagem > 0:
        texto += " (+1 vantagem)"

    cursor.execute(
        """
        INSERT INTO historico (
            personagem_id,
            texto
        )
        VALUES (%s, %s)
        """,
        (personagem_id, texto)
    )

    conexao.commit()

    cursor.close()
    conexao.close()

    return jsonify({
        "pericia": nome,
        "dado": dado,
        "rolagem": rolagem,
        "bonus": afinidade,
        "bonus_vantagem": bonus_vantagem,
        "bonus_ocupacao": bonus_ocupacao,
        "resultado": resultado_final
    })

# =========================
# ROLAR ATRIBUTO
# =========================

@app.route("/rolar-atributo/<atributo>")
def rolar_atributo(atributo):

    if "usuario_id" not in session:
        return jsonify({"erro": "Não logado"}), 401

    if atributo not in [
        "fisico",
        "mente",
        "emocao"
    ]:
        return jsonify({"erro": "Atributo inválido"}), 400

    conexao = conectar_banco()
    cursor = conexao.cursor()

    cursor.execute(
        """
        SELECT fisico, mente, emocao
        FROM personagens
        WHERE usuario_id = %s
        """,
        (session["usuario_id"],)
    )

    personagem = cursor.fetchone()

    if not personagem:

        cursor.close()
        conexao.close()

        return jsonify({"erro": "Personagem não encontrado"}), 404

    valores = {
        "fisico": personagem[0],
        "mente": personagem[1],
        "emocao": personagem[2]
    }

    dado = valores[atributo]

    lados = int(dado.replace("d", ""))

    rolagem = random.randint(1, lados)

    resultado = rolagem + 0

    cursor.execute(
        """
        SELECT id
        FROM personagens
        WHERE usuario_id = %s
        """,
        (session["usuario_id"],)
    )

    personagem_id = cursor.fetchone()[0]

    texto = f"Rolou {atributo}: {resultado}"

    cursor.execute(
        """
        INSERT INTO historico (
            personagem_id,
            texto
        )
        VALUES (%s, %s)
        """,
        (
            personagem_id,
            texto
        )
    )

    conexao.commit()

    cursor.close()
    conexao.close()

    return jsonify({
        "atributo": atributo,
        "dado": dado,
        "resultado": resultado
    })


# =========================
# MESTRE
# =========================

SENHA_MESTRE = os.environ.get("SENHA_MESTRE")

@app.route("/mestre", methods=["GET", "POST"])
def mestre():

    if request.method == "POST":

        senha = request.form["senha"]

        if senha == SENHA_MESTRE:

            session["mestre"] = True

            return redirect("/painel-mestre")

        return render_template("erro_mestre.html")

    return render_template("mestre.html")

# =========================
# PAINEL DO MESTRE
# =========================

@app.route("/painel-mestre")
def painel_mestre():

    if not session.get("mestre"):
        return redirect("/mestre")

    conexao = conectar_banco()
    cursor = conexao.cursor()

    cursor.execute(
        """
        SELECT
            p.id,
            p.nome,
            p.perfil,
            p.ocupacao,
            p.pv_atual,
            p.pv_maximo,
            u.login
        FROM personagens p
        JOIN usuarios u
            ON p.usuario_id = u.id
        ORDER BY p.id
        """
    )

    personagens = cursor.fetchall()

    cursor.execute(
        """
        SELECT
            h.personagem_id,
            h.texto
        FROM historico h
        ORDER BY h.id DESC
        LIMIT 5
        """
    )

    historicos = cursor.fetchall()

    cursor.close()
    conexao.close()

    return render_template(
        "painel_mestre.html",
        personagens=personagens,
        historicos=historicos
    )

# =========================
# LOGOUT DO MESTRE
# =========================

@app.route("/logout-mestre")
def logout_mestre():

    session.pop("mestre", None)

    return redirect("/")


# =========================
# FICHA DO MESTRE
# =========================

@app.route("/ficha-mestre/<int:personagem_id>")
def ficha_mestre(personagem_id):

    if not session.get("mestre"):
        return redirect("/mestre")

    conexao = conectar_banco()
    cursor = conexao.cursor()

    cursor.execute(
        """
        SELECT
            id,
            nome,
            perfil,
            ocupacao,
            vantagem_texto,
            vantagem_pericia,
            fisico,
            mente,
            emocao,
            pv_maximo,
            pv_atual
        FROM personagens
        WHERE id = %s
        """,
        (personagem_id,)
    )

    personagem = cursor.fetchone()

    if not personagem:

        cursor.close()
        conexao.close()

        return "Personagem não encontrado", 404

    cursor.execute(
        """
        SELECT
            id,
            nome,
            afinidade,
            atributo
        FROM pericias
        WHERE personagem_id = %s
        """,
        (personagem_id,)
    )

    pericias = cursor.fetchall()

    cursor.close()
    conexao.close()

    return render_template(
        "ficha_mestre.html",
        personagem=personagem,
        pericias=pericias
    )

@app.route("/definir-vantagem/<int:personagem_id>", methods=["POST"])
def definir_vantagem(personagem_id):

    if not session.get("mestre"):
        return redirect("/mestre")

    vantagem_pericia = request.form.get("vantagem_pericia")

    conexao = conectar_banco()
    cursor = conexao.cursor()

    cursor.execute(
        """
        UPDATE personagens
        SET vantagem_pericia = %s
        WHERE id = %s
        """,
        (vantagem_pericia, personagem_id)
    )

    conexao.commit()

    cursor.close()
    conexao.close()

    return redirect(f"/ficha-mestre/{personagem_id}")

# =========================
# EDITAR PV
# =========================

@app.route("/editar-pv/<int:personagem_id>", methods=["POST"])
def editar_pv(personagem_id):

    if not session.get("mestre"):
        return redirect("/mestre")

    try:
        pv_atual = int(request.form["pv_atual"])
    except (ValueError, TypeError):
        return "PV inválido", 400

    conexao = conectar_banco()
    cursor = conexao.cursor()

    cursor.execute(
        """
        SELECT pv_maximo
        FROM personagens
        WHERE id = %s
        """,
        (personagem_id,)
    )

    personagem = cursor.fetchone()

    if not personagem:

        cursor.close()
        conexao.close()

        return "Personagem não encontrado", 404

    pv_maximo = personagem[0]

    pv_atual = max(0, min(pv_atual, pv_maximo))

    cursor.execute(
        """
        UPDATE personagens
        SET pv_atual = %s
        WHERE id = %s
        """,
        (pv_atual, personagem_id)
    )

    conexao.commit()

    cursor.close()
    conexao.close()

    origem = request.form.get("origem")

    if origem == "painel":
        return redirect("/painel-mestre")

    return redirect(f"/ficha-mestre/{personagem_id}")

# =========================
# ☝︎✌︎💧︎❄︎☜︎☼︎
# =========================

@app.route("/1225")
def pagina_1225():
    return render_template("1225.html")

@app.route("/☝︎✌︎💧︎❄︎☜︎☼︎")
def pagina_segredo():
    return render_template("1225.html")

# =========================
# INICIAR SERVIDOR
# =========================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000
    )
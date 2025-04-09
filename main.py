from flask import Flask, request, jsonify
from datetime import datetime
import re
import os
import json
import firebase_admin
from firebase_admin import credentials, firestore

app = Flask(__name__)

# Carrega credencial do Firebase da variável de ambiente
firebase_json = os.environ.get("FIREBASE_CREDENTIAL")
cred_dict = json.loads(firebase_json)
cred = credentials.Certificate(cred_dict)
firebase_admin.initialize_app(cred)
db = firestore.client()

valor_re = re.compile(r"(recebi|ganhei|gastei|paguei)?\s?R?\$?\s?([\d,.]+)", re.IGNORECASE)

@app.route("/webhook", methods=["GET"])
def verificar_webhook():
    verify_token = "meujovem2024"
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode and token:
        if mode == "subscribe" and token == verify_token:
            return str(challenge), 200
        else:
            return "Token de verificação inválido", 403
    return "Requisição inválida", 400

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    try:
        mensagem = data["entry"][0]["changes"][0]["value"]["messages"][0]["text"]["body"]
        telefone = data["entry"][0]["changes"][0]["value"]["contacts"][0]["wa_id"]
        print(f"📩 Mensagem recebida de {telefone}: {mensagem}")
        tipo = "despesa" if any(p in mensagem.lower() for p in ["gastei", "paguei"]) else "receita"
        valor_match = valor_re.search(mensagem)
        valor = float(valor_match.group(2).replace(".", "").replace(",", ".")) if valor_match else 0.0

        categoria = subcategoria = banco = descricao = ""
        if "categoria" in mensagem.lower():
            try:
                categoria_sub = mensagem.lower().split("categoria")[1].strip()
                partes = categoria_sub.split()
                categoria = partes[0].capitalize()
                if len(partes) > 1:
                    subcategoria = " ".join(partes[1:]).capitalize()
            except:
                pass

        if "no " in mensagem.lower():
            banco = mensagem.lower().split("no ")[1].split(" ")[0].capitalize()

        descricao = mensagem
        data_lancamento = datetime.now().strftime("%Y-%m-%d")

        doc = {
            "tipo": tipo,
            "banco": banco,
            "categoria": categoria,
            "subcategoria": subcategoria,
            "descricao": descricao,
            "valor": valor,
            "data": data_lancamento
        }

        db.collection("lancamentos").add(doc)
        print("✅ Lançamento salvo com sucesso!")

        return jsonify({"status": "ok", "message": "Lançamento recebido!"}), 200

    except Exception as e:
        print("❌ Erro:", e)
        return jsonify({"status": "erro", "mensagem": str(e)}), 500

@app.route("/", methods=["GET"])
def home():
    return "API do Controle Financeiro via WhatsApp está ativa!", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)

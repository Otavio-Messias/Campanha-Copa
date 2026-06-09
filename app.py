import io
import os
from pathlib import Path
from flask import Flask, render_template, jsonify, request, send_file
import pandas as pd
from werkzeug.utils import secure_filename
from processor import (
    process_all, compute_kpis, top_vendedores_qtd, top_vendedores_valor,
    top_compradores_qtd, top_compradores_valor, empresas_qtd, empresas_valor,
    faturamento_por_dia, evolucao_por_semana, comparativo_semanas,
    get_semanas_disponiveis, filter_df, DADOS_DIR, AUX_DIR,
    AUX_VENDEDORES, AUX_EMP_PNEUS, AUX_EMP_PECAS
)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50MB

# Senha simples de acesso
ACCESS_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "copa2026")

_cached_df = None
_files_loaded = []


def reload_data():
    global _cached_df, _files_loaded
    _cached_df, _files_loaded = process_all()
    return _cached_df, _files_loaded


def get_data():
    global _cached_df, _files_loaded
    return _cached_df, _files_loaded


reload_data()


# ---------- Auth ----------

@app.route("/login")
def login_page():
    return render_template("login.html")


@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json()
    if data and data.get("senha") == ACCESS_PASSWORD:
        return jsonify({"ok": True})
    return jsonify({"ok": False, "erro": "Senha incorreta"}), 401


# ---------- Pages ----------

@app.route("/")
def index():
    return render_template("index.html")


# ---------- Upload ----------

ALLOWED = {".xlsx", ".xls"}


def _allowed(filename):
    return Path(filename).suffix.lower() in ALLOWED


@app.route("/api/upload/dados", methods=["POST"])
def upload_dados():
    files = request.files.getlist("files")
    if not files:
        return jsonify({"erro": "Nenhum arquivo enviado"}), 400

    saved = []
    erros = []
    for f in files:
        fname = secure_filename(f.filename)
        if not _allowed(fname):
            erros.append(f"{fname}: formato inválido (use .xlsx)")
            continue
        # Preserve original name with spaces (secure_filename strips them)
        original = f.filename.strip()
        dest = DADOS_DIR / original
        DADOS_DIR.mkdir(parents=True, exist_ok=True)
        f.save(dest)
        saved.append(original)

    df, files_loaded = reload_data()
    semanas = get_semanas_disponiveis(df) if df is not None and not df.empty else []

    return jsonify({
        "salvos": saved,
        "erros": erros,
        "arquivos_total": files_loaded,
        "semanas": semanas,
        "registros": len(df) if df is not None else 0,
    })


@app.route("/api/upload/auxiliares", methods=["POST"])
def upload_auxiliares():
    mapping = {
        "vendedores": AUX_VENDEDORES,
        "empresas_pneus": AUX_EMP_PNEUS,
        "empresas_pecas": AUX_EMP_PECAS,
    }
    saved = []
    erros = []
    for field, dest_path in mapping.items():
        f = request.files.get(field)
        if not f or not f.filename:
            continue
        if not _allowed(f.filename):
            erros.append(f"{f.filename}: formato inválido")
            continue
        AUX_DIR.mkdir(parents=True, exist_ok=True)
        f.save(dest_path)
        saved.append(dest_path.name)

    if saved:
        reload_data()

    return jsonify({"salvos": saved, "erros": erros})


@app.route("/api/arquivos")
def listar_arquivos():
    dados = sorted([f.name for f in DADOS_DIR.glob("*.xlsx")]) if DADOS_DIR.exists() else []
    return jsonify({
        "dados": dados,
        "vendedores": AUX_VENDEDORES.exists(),
        "empresas_pneus": AUX_EMP_PNEUS.exists(),
        "empresas_pecas": AUX_EMP_PECAS.exists(),
    })


@app.route("/api/arquivos/deletar", methods=["POST"])
def deletar_arquivo():
    data = request.get_json()
    nome = data.get("nome", "").strip()
    if not nome:
        return jsonify({"erro": "Nome inválido"}), 400
    path = DADOS_DIR / nome
    if path.exists() and path.suffix.lower() in ALLOWED:
        path.unlink()
        reload_data()
        return jsonify({"ok": True})
    return jsonify({"erro": "Arquivo não encontrado"}), 404


# ---------- Dashboard API ----------

@app.route("/api/atualizar", methods=["POST"])
def atualizar():
    df, files = reload_data()
    semanas = get_semanas_disponiveis(df) if df is not None and not df.empty else []
    return jsonify({
        "status": "ok",
        "arquivos": files,
        "total_registros": len(df) if df is not None else 0,
        "semanas": semanas,
    })


@app.route("/api/dashboard")
def dashboard():
    df, files = get_data()
    tipo = request.args.get("tipo", "Pneus")
    semana = request.args.get("semana", "Todas")
    filtered = filter_df(df, tipo_campanha=tipo, semana=semana)
    return jsonify({
        "kpis": compute_kpis(filtered),
        "top_vendedores_qtd": top_vendedores_qtd(filtered),
        "top_vendedores_valor": top_vendedores_valor(filtered),
        "top_compradores_qtd": top_compradores_qtd(filtered),
        "top_compradores_valor": top_compradores_valor(filtered),
        "empresas_qtd": empresas_qtd(filtered),
        "empresas_valor": empresas_valor(filtered),
        "faturamento_dia": faturamento_por_dia(filtered),
        "evolucao": evolucao_por_semana(filtered),
        "comparativo": comparativo_semanas(filter_df(df, tipo_campanha=tipo)),
        "semanas_disponiveis": get_semanas_disponiveis(df),
        "arquivos_carregados": files,
    })


@app.route("/api/exportar_excel")
def exportar_excel():
    df, _ = get_data()
    tipo = request.args.get("tipo", "Pneus")
    semana = request.args.get("semana", "Todas")
    filtered = filter_df(df, tipo_campanha=tipo, semana=semana)

    if filtered is None or filtered.empty:
        return jsonify({"error": "Sem dados para exportar"}), 400

    export_cols = {
        "nota": "Nota", "data_venda": "Data Venda", "nome_cliente": "Cliente",
        "nome_vendedor": "Vendedor", "nome_empresa": "Empresa",
        "preco_final": "Faturamento (R$)", "semana": "Semana", "tipo_campanha": "Tipo Campanha",
    }
    export_df = filtered[list(export_cols.keys())].rename(columns=export_cols)
    export_df["Data Venda"] = export_df["Data Venda"].dt.strftime("%d/%m/%Y")

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        export_df.to_excel(writer, index=False, sheet_name="Dados Tratados")
        kpis = compute_kpis(filtered)
        pd.DataFrame([
            {"Indicador": "Faturamento Total", "Valor": f"R$ {kpis['faturamento_total']:,.2f}"},
            {"Indicador": "Ticket Médio", "Valor": f"R$ {kpis['ticket_medio']:,.2f}"},
            {"Indicador": "Qtd. Vendas (Notas)", "Valor": kpis["qtd_vendas"]},
            {"Indicador": "Clientes Únicos", "Valor": kpis["clientes_unicos"]},
            {"Indicador": "Vendedores Únicos", "Valor": kpis["vendedores_unicos"]},
            {"Indicador": "Empresas Únicas", "Valor": kpis["empresas_unicas"]},
        ]).to_excel(writer, index=False, sheet_name="KPIs")
        comp = comparativo_semanas(filter_df(df, tipo_campanha=tipo))
        if comp:
            pd.DataFrame(comp).to_excel(writer, index=False, sheet_name="Comparativo Semanas")

    buf.seek(0)
    nome = f"Dashboard_{tipo.replace(' ', '_')}_{semana.replace(' ', '_')}.xlsx"
    return send_file(buf, as_attachment=True, download_name=nome,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("RENDER", "") == ""
    print("=" * 60)
    print("  CAMPANHA COPA - Dashboard Executivo")
    print(f"  Acesse: http://localhost:{port}")
    print(f"  Senha: {ACCESS_PASSWORD}")
    print("=" * 60)
    app.run(debug=debug, host="0.0.0.0", port=port)

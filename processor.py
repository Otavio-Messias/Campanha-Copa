import os
import re
import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).parent
DADOS_DIR = BASE_DIR / "Dados"
AUX_DIR = BASE_DIR / "Auxiliares"
AUX_VENDEDORES = AUX_DIR / "Vendedores.xlsx"
AUX_EMP_PNEUS = AUX_DIR / "Empresas Pneus.xlsx"
AUX_EMP_PECAS = AUX_DIR / "Empresas Peças e Serviços.xlsx"

CLIENTES_EXCLUIR = [
    "prodoeste",
    "mercedes benz",
    "mercedes-benz",
    "uberdiesel",
]

CLIENTES_EXCLUIR_EXATOS = [
    "com energia ltda",
]


def _filtrar_clientes(df):
    mask = pd.Series([True] * len(df), index=df.index)
    
    # Correspondência parcial — remove qualquer nome que CONTENHA o termo
    for termo in CLIENTES_EXCLUIR:
        mask = mask & ~df["nome_cliente"].str.lower().str.contains(termo, na=False)
    
    # Correspondência exata — remove apenas se o nome for EXATAMENTE igual
    for termo in CLIENTES_EXCLUIR_EXATOS:
        mask = mask & ~(df["nome_cliente"].str.lower().str.strip() == termo)
    
    return df[mask].copy()


def _load_auxiliares():
    vendedores = {}
    empresas_pneus = {}
    empresas_pecas = {}

    for path, target in [(AUX_VENDEDORES, None), (AUX_EMP_PNEUS, None), (AUX_EMP_PECAS, None)]:
        if not path.exists():
            continue
        df = pd.read_excel(path, dtype=str)
        df.columns = df.columns.str.strip()
        cod_col = df.columns[0]
        nome_col = df.columns[1]
        bucket = vendedores if path == AUX_VENDEDORES else (empresas_pneus if path == AUX_EMP_PNEUS else empresas_pecas)
        for _, row in df.iterrows():
            try:
                key = str(int(float(str(row[cod_col]).strip())))
            except Exception:
                key = str(row[cod_col]).strip()
            bucket[key] = str(row[nome_col]).strip()

    return vendedores, empresas_pneus, empresas_pecas


def _parse_filename(filename):
    name = Path(filename).stem
    semana_match = re.search(r"semana\s*(\d+)", name, re.IGNORECASE)
    semana = f"Semana {semana_match.group(1)}" if semana_match else "Semana ?"
    if re.search(r"pneu", name, re.IGNORECASE):
        tipo = "Pneus"
    elif re.search(r"pe[çc]a|servico|servi[çc]o", name, re.IGNORECASE):
        tipo = "Peças e Serviços"
    else:
        tipo = "Outros"
    return semana, tipo


def _read_erp_file(filepath):
    df = pd.read_excel(filepath, header=0)
    col_positions = {"A": 0, "K": 10, "M": 12, "N": 13, "O": 14, "R": 17}

    if df.shape[1] < 18:
        col_map_names = {}
        for i, col in enumerate(df.columns):
            col_str = str(col).strip().upper()
            if ("EMPRESA" in col_str or col_str == "A") and "A" not in col_map_names:
                col_map_names["A"] = i
            elif "PREÇO" in col_str or "PRECO" in col_str or "FINAL" in col_str:
                col_map_names["K"] = i
            elif "VENDA" in col_str and "M" not in col_map_names:
                col_map_names["M"] = i
            elif "NOTA" in col_str:
                col_map_names["N"] = i
            elif "VENDEDOR" in col_str:
                col_map_names["O"] = i
            elif "CLIENTE" in col_str:
                col_map_names["R"] = i
        col_positions.update(col_map_names)

    cols = df.columns.tolist()

    def get_col(letter):
        pos = col_positions.get(letter)
        if pos is not None and pos < len(cols):
            return df.iloc[:, pos]
        return pd.Series([None] * len(df))

    result = pd.DataFrame()
    result["cod_empresa"] = get_col("A")
    result["preco_final"] = pd.to_numeric(get_col("K"), errors="coerce").fillna(0)
    result["data_venda"] = pd.to_datetime(get_col("M"), errors="coerce")
    result["nota"] = get_col("N")
    result["cod_vendedor"] = get_col("O")
    result["nome_cliente"] = get_col("R").astype(str)
    return result


def _filtrar_clientes(df):
    mask = pd.Series([True] * len(df), index=df.index)
    for termo in CLIENTES_EXCLUIR:
        mask = mask & ~df["nome_cliente"].str.lower().str.contains(termo, na=False)
    return df[mask].copy()


def _enrich(df, vendedores, empresas_map):
    def get_empresa(cod):
        try:
            key = str(int(float(str(cod))))
        except Exception:
            key = str(cod)
        return empresas_map.get(key, "Empresa Não Encontrada")

    def get_vendedor(cod):
        try:
            key = str(int(float(str(cod))))
        except Exception:
            key = str(cod)
        return vendedores.get(key, "Vendedor Não Encontrado")

    df["nome_empresa"] = df["cod_empresa"].apply(get_empresa)
    df["nome_vendedor"] = df["cod_vendedor"].apply(get_vendedor)
    return df


def _agrupar_notas(df):
    grouped = (
        df.groupby(
            ["nota", "data_venda", "nome_cliente", "nome_vendedor", "nome_empresa",
             "semana", "tipo_campanha", "cod_empresa", "cod_vendedor"],
            as_index=False,
            dropna=False,
        )
        .agg(preco_final=("preco_final", "sum"))
    )
    return grouped


def process_all():
    vendedores, empresas_pneus, empresas_pecas = _load_auxiliares()
    all_frames = []
    files_loaded = []

    if not DADOS_DIR.exists():
        return pd.DataFrame(), []

    for f in sorted(DADOS_DIR.glob("*.xlsx")):
        semana, tipo = _parse_filename(f.name)
        empresas_map = empresas_pneus if tipo == "Pneus" else empresas_pecas
        try:
            df = _read_erp_file(f)
        except Exception as e:
            print(f"Erro ao ler {f.name}: {e}")
            continue
        df["semana"] = semana
        df["tipo_campanha"] = tipo
        df["arquivo"] = f.name
        df = _filtrar_clientes(df)
        df = _enrich(df, vendedores, empresas_map)
        df = _agrupar_notas(df)
        all_frames.append(df)
        files_loaded.append(f.name)

    if not all_frames:
        return pd.DataFrame(), files_loaded

    final = pd.concat(all_frames, ignore_index=True)
    final["data_venda"] = pd.to_datetime(final["data_venda"], errors="coerce")
    return final, files_loaded


def compute_kpis(df):
    if df is None or df.empty:
        return {"faturamento_total": 0, "ticket_medio": 0, "qtd_vendas": 0,
                "clientes_unicos": 0, "vendedores_unicos": 0, "empresas_unicas": 0}
    faturamento = float(df["preco_final"].sum())
    qtd_notas = int(df["nota"].nunique())
    ticket = faturamento / qtd_notas if qtd_notas > 0 else 0
    return {
        "faturamento_total": round(faturamento, 2),
        "ticket_medio": round(ticket, 2),
        "qtd_vendas": qtd_notas,
        "clientes_unicos": int(df["nome_cliente"].nunique()),
        "vendedores_unicos": int(df["nome_vendedor"].nunique()),
        "empresas_unicas": int(df["nome_empresa"].nunique()),
    }


def top_vendedores_qtd(df, n=10):
    if df is None or df.empty: return []
    t = df.groupby("nome_vendedor")["nota"].nunique().sort_values(ascending=False).head(n)
    return [{"nome": k, "valor": int(v)} for k, v in t.items()]


def top_vendedores_valor(df, n=10):
    if df is None or df.empty: return []
    t = df.groupby("nome_vendedor")["preco_final"].sum().sort_values(ascending=False).head(n)
    return [{"nome": k, "valor": round(float(v), 2)} for k, v in t.items()]


def top_compradores_qtd(df, n=10):
    if df is None or df.empty: return []
    t = df.groupby("nome_cliente")["nota"].nunique().sort_values(ascending=False).head(n)
    return [{"nome": k, "valor": int(v)} for k, v in t.items()]


def top_compradores_valor(df, n=10):
    if df is None or df.empty: return []
    t = df.groupby("nome_cliente")["preco_final"].sum().sort_values(ascending=False).head(n)
    return [{"nome": k, "valor": round(float(v), 2)} for k, v in t.items()]


def empresas_qtd(df, n=10):
    if df is None or df.empty: return []
    t = df.groupby("nome_empresa")["nota"].nunique().sort_values(ascending=False).head(n)
    return [{"nome": k, "valor": int(v)} for k, v in t.items()]


def empresas_valor(df, n=10):
    if df is None or df.empty: return []
    t = df.groupby("nome_empresa")["preco_final"].sum().sort_values(ascending=False).head(n)
    return [{"nome": k, "valor": round(float(v), 2)} for k, v in t.items()]


def faturamento_por_dia(df):
    if df is None or df.empty: return []
    t = df.groupby(df["data_venda"].dt.date)["preco_final"].sum().reset_index()
    t = t.sort_values("data_venda")
    return [{"data": str(r["data_venda"]), "valor": round(float(r["preco_final"]), 2)} for _, r in t.iterrows()]


def evolucao_por_semana(df):
    if df is None or df.empty: return []
    result = []
    for semana in sorted(df["semana"].unique()):
        sub = df[df["semana"] == semana]
        fat = float(sub["preco_final"].sum())
        qtd = int(sub["nota"].nunique())
        result.append({
            "semana": semana,
            "faturamento": round(fat, 2),
            "qtd_vendas": qtd,
            "ticket_medio": round(fat / qtd if qtd > 0 else 0, 2),
            "clientes_unicos": int(sub["nome_cliente"].nunique()),
            "vendedores_unicos": int(sub["nome_vendedor"].nunique()),
        })
    return result


def comparativo_semanas(df):
    return evolucao_por_semana(df)


def get_semanas_disponiveis(df):
    if df is None or df.empty: return []
    return sorted(df["semana"].unique().tolist())


def filter_df(df, tipo_campanha=None, semana=None):
    if df is None or df.empty: return df
    result = df.copy()
    if tipo_campanha and tipo_campanha != "Todos":
        result = result[result["tipo_campanha"] == tipo_campanha]
    if semana and semana != "Todas":
        result = result[result["semana"] == semana]
    return result

# utils/format.py
import pandas as pd
import re
import streamlit as st

PALETTE = ["#007dc3", "#00a8e0", "#7ad1e6", "#004b8d", "#0095d9"]

def brl(valor):
    """Formata número para Real (R$)."""
    try:
        if pd.isna(valor):
            return "—"
        return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return str(valor)

def parse_currency_br(valor):
    """Converte string monetária BR para float."""
    if pd.isna(valor) or valor == "":
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)
    s = str(valor).strip()
    neg = s.startswith("-") or s.startswith("(")
    s = re.sub(r"[R$\s\(\)]", "", s)
    s = s.replace(".", "").replace(",", ".")
    try:
        v = float(s)
        return -v if neg and v > 0 else v
    except Exception:
        return 0.0

def normalize_text(texto):
    """Normaliza nomes (capitalização simples e trim)."""
    if pd.isna(texto):
        return ""
    texto = str(texto).strip()
    if texto == "":
        return ""
    return " ".join(p.capitalize() for p in texto.split())

@st.cache_data(ttl=600)
def normalize_dataframe(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Normaliza estrutura de planilhas de vendas (NovaBrasil)."""
    df = df_raw.copy()
    col_map = {
        "Empresa": "Emissora",
        "DESCRIÇÃO": "Cliente",
        "CONTATO COML.": "Executivo",
        "VALOR": "Faturamento",
        "REF.": "data_ref",
        "REF": "data_ref",
    }
    df = df.rename(columns=col_map)

    # garante colunas básicas
    for col in ["Emissora", "Cliente", "Executivo", "Faturamento"]:
        if col not in df.columns:
            df[col] = ""
    for col in ["Emissora", "Cliente", "Executivo"]:
        df[col] = df[col].apply(normalize_text)

    # ===============================
    # DETECÇÃO ROBUSTA DE DATAS
    # ===============================
    if "data_ref" in df.columns:
        df["data_ref"] = df["data_ref"].astype(str).str.strip()

        def try_parse_date(val):
            """Tenta converter datas em formatos variados sem warning."""
            if not isinstance(val, str):
                return pd.to_datetime(val, errors="coerce")
            if re.match(r"^\d{4}-\d{2}-\d{2}$", val):
                return pd.to_datetime(val, format="%Y-%m-%d", errors="coerce")
            if re.match(r"^\d{2}/\d{2}/\d{4}$", val):
                return pd.to_datetime(val, format="%d/%m/%Y", errors="coerce")
            if val.replace(".", "").isdigit() and len(val) >= 5:
                try:
                    return pd.to_datetime(float(val), unit="D", origin="1899-12-30")
                except Exception:
                    return pd.NaT
            return pd.to_datetime(val, errors="coerce", dayfirst=True)

        df["data_ref"] = df["data_ref"].apply(try_parse_date)

    elif "Ano" in df.columns and "Mês" in df.columns:
        df["data_ref"] = pd.to_datetime(
            dict(year=df["Ano"].astype(int), month=df["Mês"].astype(int), day=1),
            errors="coerce"
        )
    else:
        st.error("❌ A planilha precisa conter 'REF.' ou colunas 'Ano' e 'Mês'.")
        return pd.DataFrame()

    df = df.dropna(subset=["data_ref"])
    if df.empty:
        st.warning("⚠️ Nenhuma data válida foi identificada na base.")
        return pd.DataFrame()

    # adiciona colunas de tempo
    df["Ano"] = df["data_ref"].dt.year
    df["Mes"] = df["data_ref"].dt.month
    df["MesLabel"] = df["data_ref"].dt.strftime("%b/%y")

    # converte valores
    df["Faturamento"] = df["Faturamento"].apply(parse_currency_br)

    # ===============================
    # NORMALIZAÇÃO FINAL
    # =C
    # evita warning de colunas mixed type
    df.columns = df.columns.map(str)
    # evita warning de índice misto
    df.index = df.index.astype(str)
    df = df.reset_index(drop=True)

    return df
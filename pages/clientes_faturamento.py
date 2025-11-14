import streamlit as st
import numpy as np
import pandas as pd
from utils.format import brl, PALETTE
from utils.loaders import load_main_base
from utils.export import create_excel_bytes # type: ignore

# Função helper de coloração
def color_delta(val):
    if pd.isna(val) or val == 0:
        return ""
    try:
        v = float(val)
        if v > 0:
            return "color: #16a34a; font-weight: 600;" # verde
        if v < 0:
            return "color: #dc2626; font-weight: 600;" # vermelho
    except (ValueError, TypeError):
        return ""
    return ""


def render(df, mes_ini, mes_fim):
    st.header("Clientes & Faturamento")

    # --- Inicializa DFs brutas ---
    base_clientes_raw = pd.DataFrame()
    base_emissora_raw = pd.DataFrame()
    tx_raw = pd.DataFrame()
    t16_raw = pd.DataFrame()
    t15_raw = pd.DataFrame()
    t14_raw = pd.DataFrame()
    # ---

    df = df.rename(columns={c: c.lower() for c in df.columns})
    _, ultima_atualizacao = load_main_base()

    if "faturamento" not in df.columns:
        st.error("Coluna 'Faturamento' ausente na base.")
        return

    anos = sorted(df["ano"].dropna().unique())
    if not anos:
        st.info("Sem anos válidos.")
        return
    if len(anos) >= 2:
        ano_base, ano_comp = anos[-2], anos[-1]
    else:
        ano_base = ano_comp = anos[-1]

    base_periodo = df[df["mes"].between(mes_ini, mes_fim)]

    # ==============================
    # 1.1 Número de Clientes por Emissora
    # ==============================
    st.subheader("1.1 Número de Clientes por Emissora (Comparativo)")
    base_clientes_raw = (
        base_periodo.groupby(["emissora", "ano"])["cliente"]
        .nunique().unstack(fill_value=0).reset_index()
    )

    for ano in [ano_base, ano_comp]:
        if ano not in base_clientes_raw.columns:
            base_clientes_raw[ano] = 0

    base_clientes_raw["Δ"] = base_clientes_raw[ano_comp] - base_clientes_raw[ano_base]
    base_clientes_raw["Δ%"] = np.where(
        base_clientes_raw[ano_base] > 0,
        (base_clientes_raw["Δ"] / base_clientes_raw[ano_base]) * 100,
        np.nan,
    )

    base_clientes_display = base_clientes_raw.copy()
    base_clientes_display.columns = base_clientes_display.columns.map(str)
    base_clientes_display.insert(0, "#", range(1, len(base_clientes_display) + 1))

    styler_1_1 = base_clientes_display.style.map(
        color_delta, subset=["Δ", "Δ%"]
    ).format(
        {"Δ%": lambda x: "—" if pd.isna(x) else f"{x:.2f}%"}
    )
    
    st.dataframe(
        styler_1_1,
        hide_index=True,
        width="stretch" 
    )
    st.divider()


    # ==============================
    # 1.2 Faturamento por Emissora (Comparativo)
    # ==============================
    st.subheader("1.2 Faturamento por Emissora (Comparativo)")
    base_emissora_raw = (
        base_periodo.groupby(["emissora", "ano"])["faturamento"]
        .sum().unstack(fill_value=0).reset_index()
    )

    for ano in [ano_base, ano_comp]:
        if ano not in base_emissora_raw.columns:
            base_emissora_raw[ano] = 0.0

    base_emissora_raw["Δ"] = base_emissora_raw[ano_comp] - base_emissora_raw[ano_base]
    base_emissora_raw["Δ%"] = np.where(
        base_emissora_raw[ano_base] > 0,
        (base_emissora_raw["Δ"] / base_emissora_raw[ano_base]) * 100,
        np.nan,
    )

    base_emissora_display = base_emissora_raw.copy()
    base_emissora_display.columns = base_emissora_display.columns.map(str)
    base_emissora_display.insert(0, "#", range(1, len(base_emissora_display) + 1))

    styler_1_3 = base_emissora_display.style.map(
        color_delta, subset=["Δ", "Δ%"]
    ).format(
        {
            str(ano_base): brl,
            str(ano_comp): brl,
            "Δ": brl,
            "Δ%": lambda x: "—" if pd.isna(x) else f"{x:.2f}%"
        }
    )
    
    st.dataframe(
        styler_1_3,
        hide_index=True,
        width="stretch" 
    )
    st.divider()


    # ==============================
    # 1.3 Faturamento por Executivo
    # ==============================
    st.subheader("1.3 Faturamento por Executivo")
    tx_raw = (
        base_periodo.groupby(["executivo", "ano"])["faturamento"]
        .sum().unstack(fill_value=0).reset_index()
    )

    for ano in [ano_base, ano_comp]:
        if ano not in tx_raw.columns:
            tx_raw[ano] = 0.0

    tx_raw["Δ"] = tx_raw[ano_comp] - tx_raw[ano_base]
    tx_raw["Δ%"] = np.where(tx_raw[ano_base] > 0, (tx_raw["Δ"] / tx_raw[ano_base]) * 100, np.nan)

    tx_display = tx_raw.copy()
    tx_display.columns = tx_display.columns.map(str)
    tx_display.insert(0, "#", range(1, len(tx_display) + 1))

    styler_1_2 = tx_display.style.map(
        color_delta, subset=["Δ", "Δ%"]
    ).format(
        {
            str(ano_base): brl,
            str(ano_comp): brl,
            "Δ": brl,
            "Δ%": lambda x: "—" if pd.isna(x) else f"{x:.2f}%"
        }
    )

    st.dataframe(
        styler_1_2,
        hide_index=True,
        width="stretch" 
    )
    st.divider()


    # ==============================
    # 1.4 Média de investimento por cliente (por emissora)
    # ==============================
    st.subheader("1.4 Média de investimento por cliente (por emissora)")
    t16_raw = base_periodo.groupby("emissora").agg(
        Faturamento=("faturamento", "sum"),
        Clientes=("cliente", "nunique")
    ).reset_index()
    
    t16_raw["Média por cliente"] = np.where(
        t16_raw["Clientes"] == 0, 
        np.nan, 
        t16_raw["Faturamento"] / t16_raw["Clientes"]
    )
    
    t16_disp = t16_raw.copy()
    t16_disp = t16_disp.rename(columns={"emissora": "Emissora"})
    t16_disp["Faturamento"] = t16_disp["Faturamento"].apply(brl)
    t16_disp["Média por cliente"] = t16_disp["Média por cliente"].apply(lambda x: "—" if pd.isna(x) else brl(x))
    
    t16_disp.insert(0, "#", range(1, len(t16_disp) + 1))
    
    st.dataframe(
        t16_disp, 
        width="stretch", 
        hide_index=True
    )
    st.divider()


    # ==============================
    # 1.5 Faturamento por Emissora (Total)
    # ==============================
    st.subheader("1.5 Faturamento por Emissora (Total)")
    t15_raw = base_periodo.groupby("emissora", as_index=False)["faturamento"].sum().sort_values("faturamento", ascending=False)
    
    t15_disp = t15_raw.rename(columns={"emissora": "Emissora", "faturamento": "Faturamento"})
    t15_disp["Faturamento"] = t15_disp["Faturamento"].apply(brl)
    
    t15_disp.insert(0, "#", range(1, len(t15_disp) + 1))
    
    st.dataframe(
        t15_disp, 
        width="stretch", 
        hide_index=True
    )
    st.divider()


    # ==============================
    # 1.6 Comparativo mês a mês (tabela)
    # ==============================
    st.subheader("1.6 Comparativo mês a mês (tabela)")
    
    mes_map = {
        1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
        7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"
    }
    
    base_para_tabela = base_periodo.copy()
    base_para_tabela["mes_nome"] = base_para_tabela["mes"].map(mes_map)

    t14_agg = (
        base_para_tabela.groupby(["ano", "mes", "mes_nome"])["faturamento"]
        .sum()
        .reset_index()
    )

    t14_raw = t14_agg.pivot(
        index=["mes", "mes_nome"],
        columns="ano",
        values="faturamento"
    ).fillna(0.0)

    if not t14_raw.empty:
        t14_raw = t14_raw.sort_index(level="mes")
        t14_raw.index = t14_raw.index.get_level_values('mes_nome')
        t14_raw.index.name = "Mês"
        
        t14_disp = t14_raw.copy()
        t14_disp.columns = t14_disp.columns.map(str) 
        
        format_dict = {col: brl for col in t14_disp.columns}
            
        st.dataframe(
            t14_disp.style.format(format_dict),
            width="stretch", 
            hide_index=False
        )
    else:
        st.info("Sem dados suficientes para o comparativo mensal.")


    # --- INÍCIO DA SEÇÃO DE EXPORTAÇÃO ---
    st.divider()
    
    # --- INÍCIO DA ALTERAÇÃO (Botão type) ---
    if st.button("📥 Exportar Dados da Página", type="secondary"):
        st.session_state.show_clientes_export = True
    # --- FIM DA ALTERAÇÃO ---

    if st.session_state.get("show_clientes_export", False):
        
        @st.dialog("Opções de Exportação - Clientes & Faturamento")
        def export_dialog():
            
            table_options = {
                "1.1 Clientes (Emissora)": base_clientes_raw,
                "1.2 Fat. (Emissora)": base_emissora_raw,
                "1.3 Fat. (Executivo)": tx_raw,
                "1.4 Média (Cliente)": t16_raw,
                "1.5 Fat. Total (Emissora)": t15_raw,
                "1.6 Comp. (Mês a Mês)": t14_raw,
            }
            
            available_options = [name for name, df in table_options.items() if not df.empty]
            
            if not available_options:
                st.warning("Nenhuma tabela com dados foi gerada nesta página.")
                if st.button("Fechar", type="secondary"):
                    st.session_state.show_clientes_export = False
                    st.rerun()
                return

            st.write("Selecione as tabelas para incluir no arquivo Excel:")
            
            selected_names = st.multiselect(
                "Tabelas para exportar",
                options=available_options,
                default=available_options
            )
            
            tables_to_export = {name: {'df': table_options[name]} for name in selected_names}
            
            if not tables_to_export:
                st.error("Selecione pelo menos uma tabela.")
                return

            try:
                excel_data = create_excel_bytes(tables_to_export)
                
                st.download_button(
                    label="Clique para Baixar o Excel",
                    data=excel_data,
                    file_name="export_clientes_e_faturamento.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    on_click=lambda: st.session_state.update(show_clientes_export=False),
                    type="secondary" # Botão de download branco
                )
            except Exception as e:
                st.error(f"Erro ao gerar Excel: {e}")

            if st.button("Cancelar", key="cancel_export", type="secondary"):
                st.session_state.show_clientes_export = False
                st.rerun()

        export_dialog()
    # --- FIM DA SEÇÃO DE EXPORTAÇÃO ---
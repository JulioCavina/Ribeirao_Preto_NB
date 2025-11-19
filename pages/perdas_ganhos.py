import streamlit as st
from utils.format import brl
import pandas as pd
import numpy as np
# CORREÇÃO: Importa a nova função ZIP
from utils.export import create_zip_package 

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


# --- INÍCIO DA ALTERAÇÃO (Aceita show_labels) ---
def render(df, mes_ini, mes_fim, show_labels):
# --- FIM DA ALTERAÇÃO ---
    
    df_perdas_raw = pd.DataFrame()
    df_ganhos_raw = pd.DataFrame()
    var_cli_raw = pd.DataFrame()
    var_emis_raw = pd.DataFrame()
    
    df = df.rename(columns={c: c.lower() for c in df.columns})
    anos = sorted(df["ano"].dropna().unique())
    if not anos:
        st.info("Sem anos válidos na base.")
        return

    if len(anos) >= 2:
        ano_base, ano_comp = anos[-2], anos[-1]
    else:
        ano_base = ano_comp = anos[-1]

    st.header(f"Perdas & Ganhos ({ano_base} vs {ano_comp})")

    if "cliente" not in df.columns or "faturamento" not in df.columns:
        st.error("Colunas obrigatórias 'Cliente' e 'Faturamento' ausentes.")
        return

    base_periodo = df[df["mes"].between(mes_ini, mes_fim)]
    baseA = base_periodo[base_periodo["ano"] == ano_base]
    baseB = base_periodo[base_periodo["ano"] == ano_comp]

    cliA, cliB = set(baseA["cliente"].unique()), set(baseB["cliente"].unique())
    perdas = sorted(cliA - cliB)
    ganhos = sorted(cliB - cliA)

    totalA = baseA["faturamento"].sum()
    totalB = baseB["faturamento"].sum()
    perdas_valor = baseA[baseA["cliente"].isin(perdas)]["faturamento"].sum()
    ganhos_valor = baseB[baseB["cliente"].isin(ganhos)]["faturamento"].sum()

    perdas_pct = (perdas_valor / totalA * 100) if totalA > 0 else 0
    ganhos_pct = (ganhos_valor / totalB * 100) if totalB > 0 else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Perdas - Clientes", len(perdas))
    c2.metric("Perdas - Valor", brl(perdas_valor))
    c3.metric(f"% do Total {ano_base}", f"{perdas_pct:.2f}%")

    c4, c5, c6 = st.columns(3)
    c4.metric("Ganhos - Clientes", len(ganhos))
    c5.metric("Ganhos - Valor", brl(ganhos_valor))
    c6.metric(f"% do Total {ano_comp}", f"{ganhos_pct:.2f}%")

    st.divider()

    colA, colB = st.columns(2)
    with colA:
        st.subheader("Clientes Perdidos")
        if perdas:
            df_perdas_raw = (
                baseA[baseA["cliente"].isin(perdas)][["cliente", "faturamento"]]
                .groupby("cliente")
                .sum()
                .sort_values("faturamento", ascending=False)
                .reset_index()
            )
            
            if not df_perdas_raw.empty:
                total_row = {
                    "cliente": "Totalizador",
                    "faturamento": df_perdas_raw["faturamento"].sum()
                }
                df_perdas_raw = pd.concat([df_perdas_raw, pd.DataFrame([total_row])], ignore_index=True)
            
            df_perdas_raw.insert(0, "#", list(range(1, len(df_perdas_raw))) + ["Total"])
            
            t_display = df_perdas_raw.copy()
            t_display['#'] = t_display['#'].astype(str)
            t_display["faturamento"] = t_display["faturamento"].apply(brl)

            st.dataframe(
                t_display, 
                width="stretch", 
                hide_index=True,
                column_config={"#": None}
            )
        else:
            st.info("Nenhum cliente perdido.")

    with colB:
        st.subheader("Clientes Ganhos")
        if ganhos:
            df_ganhos_raw = (
                baseB[baseB["cliente"].isin(ganhos)][["cliente", "faturamento"]]
                .groupby("cliente")
                .sum()
                .sort_values("faturamento", ascending=False)
                .reset_index()
            )
            
            if not df_ganhos_raw.empty:
                total_row = {
                    "cliente": "Totalizador",
                    "faturamento": df_ganhos_raw["faturamento"].sum()
                }
                df_ganhos_raw = pd.concat([df_ganhos_raw, pd.DataFrame([total_row])], ignore_index=True)

            df_ganhos_raw.insert(0, "#", list(range(1, len(df_ganhos_raw))) + ["Total"])
            
            t_display = df_ganhos_raw.copy()
            t_display['#'] = t_display['#'].astype(str)
            t_display["faturamento"] = t_display["faturamento"].apply(brl)

            st.dataframe(
                t_display, 
                width="stretch", 
                hide_index=True,
                column_config={"#": None}
            )
        else:
            st.info("Nenhum cliente novo.")

    st.divider()

    st.subheader("Variações de faturamento por Cliente")
    var_cli_raw = base_periodo.groupby(["cliente", "ano"])["faturamento"].sum().unstack(fill_value=0).reset_index()
    
    for ano in [ano_base, ano_comp]:
        if ano not in var_cli_raw.columns:
            var_cli_raw[ano] = 0.0
            
    var_cli_raw["Δ"] = var_cli_raw[ano_comp] - var_cli_raw[ano_base]
    var_cli_raw["Δ%"] = np.where(var_cli_raw[ano_base] > 0, (var_cli_raw["Δ"] / var_cli_raw[ano_base]) * 100, np.nan)
    
    if not var_cli_raw.empty:
        total_A = var_cli_raw[ano_base].sum()
        total_B = var_cli_raw[ano_comp].sum()
        total_delta = total_B - total_A
        total_pct = (total_delta / total_A * 100) if total_A > 0 else np.nan
        
        total_row = {
            "cliente": "Totalizador",
            ano_base: total_A,
            ano_comp: total_B,
            "Δ": total_delta,
            "Δ%": total_pct
        }
        var_cli_raw = pd.concat([var_cli_raw, pd.DataFrame([total_row])], ignore_index=True)
    
    var_cli_disp = var_cli_raw.copy()
    var_cli_disp.columns = var_cli_disp.columns.map(str)
    
    styler_cli = var_cli_disp.style.map(
        color_delta, subset=["Δ", "Δ%"]
    ).format(
        {
            str(ano_base): brl,
            str(ano_comp): brl,
            "Δ": brl,
            "Δ%": lambda x: "—" if pd.isna(x) else f"{x:.2f}%"
        },
        na_rep="—"
    )
    st.dataframe(styler_cli, width="stretch", hide_index=True)
    st.divider()


    st.subheader("Variações de faturamento por Emissora")
    var_emis_raw = base_periodo.groupby(["emissora", "ano"])["faturamento"].sum().unstack(fill_value=0).reset_index()
    
    for ano in [ano_base, ano_comp]:
        if ano not in var_emis_raw.columns:
            var_emis_raw[ano] = 0.0
            
    var_emis_raw["Δ"] = var_emis_raw[ano_comp] - var_emis_raw[ano_base]
    var_emis_raw["Δ%"] = np.where(var_emis_raw[ano_base] > 0, (var_emis_raw["Δ"] / var_emis_raw[ano_base]) * 100, np.nan)
    
    if not var_emis_raw.empty:
        total_A = var_emis_raw[ano_base].sum()
        total_B = var_emis_raw[ano_comp].sum()
        total_delta = total_B - total_A
        total_pct = (total_delta / total_A * 100) if total_A > 0 else np.nan
        
        total_row = {
            "emissora": "Totalizador",
            ano_base: total_A,
            ano_comp: total_B,
            "Δ": total_delta,
            "Δ%": total_pct
        }
        var_emis_raw = pd.concat([var_emis_raw, pd.DataFrame([total_row])], ignore_index=True)
        
    var_emis_disp = var_emis_raw.copy()
    var_emis_disp.columns = var_emis_disp.columns.map(str)
    
    styler_emis = var_emis_disp.style.map(
        color_delta, subset=["Δ", "Δ%"]
    ).format(
        {
            str(ano_base): brl,
            str(ano_comp): brl,
            "Δ": brl,
            "Δ%": lambda x: "—" if pd.isna(x) else f"{x:.2f}%"
        },
        na_rep="—"
    )
    st.dataframe(styler_emis, width="stretch", hide_index=True)
    
    
    # --- SEÇÃO DE EXPORTAÇÃO ---
    st.divider()
    
    if st.button("📥 Exportar Dados da Página", type="secondary"):
        st.session_state.show_perdas_export = True

    if st.session_state.get("show_perdas_export", False):
        
        @st.dialog("Opções de Exportação - Perdas & Ganhos")
        def export_dialog():
            
            table_options = {
                "1. Clientes Perdidos": {'df': df_perdas_raw},
                "2. Clientes Ganhos": {'df': df_ganhos_raw},
                "3. Variações (Cliente)": {'df': var_cli_raw},
                "4. Variações (Emissora)": {'df': var_emis_raw}
            }
            
            available_options = [name for name, data in table_options.items() if data.get('df') is not None and not data['df'].empty]
            
            if not available_options:
                st.warning("Nenhuma tabela com dados foi gerada nesta página.")
                if st.button("Fechar", type="secondary"):
                    st.session_state.show_perdas_export = False
                    st.rerun()
                return

            st.write("Selecione os itens para incluir no **Pacote de Arquivos (.zip)**:")
            
            selected_names = st.multiselect(
                "Itens para exportar",
                options=available_options,
                default=available_options
            )
            
            tables_to_export = {}
            for name in selected_names:
                # Passa o df
                if name in table_options:
                    tables_to_export[name] = table_options[name]

            if not tables_to_export:
                st.error("Selecione pelo menos um item.")
                return

            try:
                # CHAMADA CORRIGIDA: usa create_zip_package
                zip_data = create_zip_package(tables_to_export)
                
                st.download_button(
                    label="Clique para baixar o pacote de arquivos",
                    data=zip_data,
                    file_name="Dashboard_Perdas_Ganhos.zip",
                    mime="application/zip",
                    on_click=lambda: st.session_state.update(show_perdas_export=False),
                    type="secondary" # Mantém o estilo secundário
                )
            except Exception as e:
                st.error(f"Erro ao gerar o pacote ZIP: {e}")

            if st.button("Cancelar", key="cancel_export", type="secondary"):
                st.session_state.show_perdas_export = False
                st.rerun()

        export_dialog()
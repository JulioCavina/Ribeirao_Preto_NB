import streamlit as st
import plotly.express as px
from utils.format import brl, PALETTE
import pandas as pd
import plotly.graph_objects as go 
from utils.export import create_excel_bytes # type: ignore

def render(df, mes_ini, mes_fim):
    st.header("Visão Geral")
    
    # --- Inicializa DFs e Figs ---
    evol_raw = pd.DataFrame()
    base_emis_raw = pd.DataFrame()
    base_exec_raw = pd.DataFrame()
    fig_evol = go.Figure()
    fig_emis = go.Figure()
    fig_exec = go.Figure()
    # ---

    df = df.rename(columns={c: c.lower() for c in df.columns})

    if "meslabel" not in df.columns:
        if "ano" in df.columns and "mes" in df.columns:
            df["meslabel"] = pd.to_datetime(dict(
                year=df["ano"].astype(int),
                month=df["mes"].astype(int),
                day=1
            )).dt.strftime("%b/%y")
        else:
            df["meslabel"] = ""

    anos = sorted(df["ano"].dropna().unique())
    if not anos:
        st.info("Sem anos válidos na base.")
        return
    if len(anos) >= 2:
        ano_base, ano_comp = anos[-2], anos[-1]
    else:
        ano_base = ano_comp = anos[-1]

    ano_base_str = str(ano_base)[-2:]
    ano_comp_str = str(ano_comp)[-2:]
    label_delta_abs = f"Δ Absoluto ({ano_comp_str}-{ano_base_str})"
    label_delta_pct = f"Δ % ({ano_comp_str} vs {ano_base_str})"

    base_periodo = df[df["mes"].between(mes_ini, mes_fim)]
    baseA = base_periodo[base_periodo["ano"] == ano_base]
    baseB = base_periodo[base_periodo["ano"] == ano_comp]

    totalA = float(baseA["faturamento"].sum()) if not baseA.empty else 0.0
    totalB = float(baseB["faturamento"].sum()) if not baseB.empty else 0.0
    delta_abs = totalB - totalA
    delta_pct = (delta_abs / totalA * 100) if totalA > 0.0 else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(f"Total {ano_base}", brl(totalA))
    c2.metric(f"Total {ano_comp}", brl(totalB))
    c3.metric(label_delta_abs, brl(delta_abs))
    c4.metric(label_delta_pct, f"{delta_pct:.2f}%" if totalA > 0 else "—")

    
    st.markdown("<p class='custom-chart-title'>Evolução Mensal</p>", unsafe_allow_html=True)
    
    evol_raw = base_periodo.groupby(["ano", "meslabel", "mes"], as_index=False)["faturamento"].sum().sort_values(["ano", "mes"])
    
    if not evol_raw.empty:
        fig_evol = px.line(
            evol_raw, x="meslabel", y="faturamento",
            color=evol_raw["ano"].astype(str), markers=True,
            color_discrete_sequence=PALETTE
        )
        fig_evol.update_layout(height=400, legend=dict(orientation="h", y=1.1), template="plotly_white")
        fig_evol.update_yaxes(tickprefix="R$ ", separatethousands=True)
        st.plotly_chart(fig_evol, width="stretch") 
    else:
        st.info("Sem dados para o período selecionado.")


    col1, col2 = st.columns(2)

    with col1:
        st.markdown("<p class='custom-chart-title'>Faturamento por Emissora</p>", unsafe_allow_html=True)
        base_emis_raw = base_periodo.groupby("emissora", as_index=False)["faturamento"].sum().sort_values("faturamento", ascending=False)
        
        if not base_emis_raw.empty:
            fig_emis = px.bar(base_emis_raw, x="emissora", y="faturamento", color_discrete_sequence=[PALETTE[0]])
            fig_emis.update_layout(height=400, xaxis_title=None, yaxis_title="Faturamento", template="plotly_white")
            fig_emis.update_yaxes(tickprefix="R$ ", separatethousands=True)
            st.plotly_chart(fig_emis, width="stretch")
        else:
            st.info("Sem dados de emissoras para o período.")

    with col2:
        st.markdown("<p class='custom-chart-title'>Faturamento por Executivo</p>", unsafe_allow_html=True)
        base_exec_raw = base_periodo.groupby("executivo", as_index=False)["faturamento"].sum().sort_values("faturamento", ascending=False)
        
        if not base_exec_raw.empty:
            fig_exec = px.bar(base_exec_raw, x="executivo", y="faturamento", color_discrete_sequence=[PALETTE[3]])
            fig_exec.update_layout(height=400, xaxis_title=None, yaxis_title="Faturamento", template="plotly_white")
            fig_exec.update_yaxes(tickprefix="R$ ", separatethousands=True)
            st.plotly_chart(fig_exec, width="stretch")
        else:
            st.info("Sem dados de executivos para o período.")

    ultima = st.session_state.get("ultima_atualizacao", None)
    if ultima:
        st.caption(f"Última atualização da base de dados: {ultima}")

    # --- INÍCIO DA SEÇÃO DE EXPORTAÇÃO ---
    st.divider()
    
    # --- INÍCIO DA ALTERAÇÃO (Botão type) ---
    if st.button("📥 Exportar Dados da Página", type="secondary"):
        st.session_state.show_visao_geral_export = True
    # --- FIM DA ALTERAÇÃO ---

    if st.session_state.get("show_visao_geral_export", False):
        
        @st.dialog("Opções de Exportação - Visão Geral")
        def export_dialog():
            
            all_options = {
                "Evolução Mensal (Dados)": {'df': evol_raw},
                "Evolução Mensal (Gráfico)": {'img': fig_evol},
                "Fat. por Emissora (Dados)": {'df': base_emis_raw},
                "Fat. por Emissora (Gráfico)": {'img': fig_emis},
                "Fat. por Executivo (Dados)": {'df': base_exec_raw},
                "Fat. por Executivo (Gráfico)": {'img': fig_exec},
            }
            
            available_options = []
            for name, data in all_options.items():
                if data.get('df') is not None and not data['df'].empty:
                    available_options.append(name)
                elif data.get('img') is not None and data['img'].data:
                    available_options.append(name)

            if not available_options:
                st.warning("Nenhum dado ou gráfico foi gerado nesta página.")
                if st.button("Fechar", type="secondary"):
                    st.session_state.show_visao_geral_export = False
                    st.rerun()
                return

            st.write("Selecione os itens para incluir no arquivo Excel:")
            
            selected_names = st.multiselect(
                "Itens para exportar",
                options=available_options,
                default=available_options 
            )
            
            tables_to_export = {}
            for name in selected_names:
                data = all_options[name]
                if 'img' in data:
                    try:
                        img_bytes = data['img'].to_image(format="png", engine="kaleido")
                        tables_to_export[name] = {'img': img_bytes}
                    except Exception as e:
                        st.error(f"Erro ao gerar imagem '{name}': {e}")
                else:
                    tables_to_export[name] = data

            if not tables_to_export:
                st.error("Selecione pelo menos um item.")
                return

            try:
                excel_data = create_excel_bytes(tables_to_export)
                
                st.download_button(
                    label="Clique para Baixar o Excel",
                    data=excel_data,
                    file_name="export_visao_geral.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    on_click=lambda: st.session_state.update(show_visao_geral_export=False),
                    type="secondary" # Botão de download branco
                )
            except Exception as e:
                st.error(f"Erro ao gerar Excel: {e}")

            if st.button("Cancelar", key="cancel_export", type="secondary"):
                st.session_state.show_visao_geral_export = False
                st.rerun()

        export_dialog()
    # --- FIM DA SEÇÃO DE EXPORTAÇÃO ---
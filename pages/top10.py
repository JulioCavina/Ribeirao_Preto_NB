# pages/top10.py
import streamlit as st
import plotly.express as px
from utils.format import brl, PALETTE
from utils.export import create_excel_bytes # type: ignore
import pandas as pd
import plotly.graph_objects as go

def render(df, mes_ini, mes_fim):
    st.header("Top 10 Maiores Anunciantes")
    
    top10_raw = pd.DataFrame()
    fig = go.Figure() 

    df = df.rename(columns={c: c.lower() for c in df.columns})

    if "emissora" not in df.columns or "ano" not in df.columns:
        st.error("Colunas 'Emissora' e/ou 'Ano' ausentes.")
        return

    base_periodo = df[df["mes"].between(mes_ini, mes_fim)]

    emis_list = sorted(base_periodo["emissora"].dropna().unique())
    anos_list = sorted(base_periodo["ano"].dropna().unique())

    if not emis_list or not anos_list:
        st.info("Sem dados para selecionar emissora/ano.")
        return

    col1, col2 = st.columns(2)
    emis = col1.selectbox("Emissora", emis_list)
    ano = col2.selectbox("Ano", anos_list, index=len(anos_list)-1)

    base = base_periodo[
        (base_periodo["ano"] == ano) & (base_periodo["emissora"] == emis)
    ]
    
    top10_raw = (
        base.groupby("cliente", as_index=False)["faturamento"]
        .sum()
        .sort_values("faturamento", ascending=False)
        .head(10)
    )

    if not top10_raw.empty:
        top10_raw.insert(0, "#", range(1, len(top10_raw) + 1))
        
        top10_display = top10_raw.copy()
        top10_display["faturamento_fmt"] = top10_display["faturamento"].apply(brl)

        tabela = top10_display[["#", "cliente", "faturamento_fmt"]].rename(
            columns={"cliente": "Cliente", "faturamento_fmt": "Faturamento"}
        )
        st.dataframe(tabela, width="stretch", hide_index=True)

        fig = px.bar(
            top10_display, 
            x="cliente",
            y="faturamento",
            color_discrete_sequence=[PALETTE[0]],
        )
        fig.update_layout(height=400, showlegend=False, template="plotly_white")
        st.plotly_chart(fig, width="stretch")
    else:
        st.info("Sem dados para essa emissora/ano.")


    # --- INÍCIO DA SEÇÃO DE EXPORTAÇÃO (MODIFICADA) ---
    st.divider()
    
    if st.button("📥 Exportar Dados da Página", type="secondary"):
        st.session_state.show_top10_export = True

    if st.session_state.get("show_top10_export", False):
        
        @st.dialog("Opções de Exportação - Top 10")
        def export_dialog():
            
            # 1. Define todas as opções
            all_options = {
                "Top 10 (Dados)": {'df': top10_raw},
                "Top 10 (Gráfico)": {'img': fig}
            }
            
            # 2. Filtra opções disponíveis
            available_options = []
            for name, data in all_options.items():
                if data.get('df') is not None and not data['df'].empty:
                    available_options.append(name)
                elif data.get('img') is not None and data['img'].data:
                    available_options.append(name)
            
            if not available_options:
                st.warning("Nenhuma tabela com dados foi gerada nesta página.")
                if st.button("Fechar", type="secondary"):
                    st.session_state.show_top10_export = False
                    st.rerun()
                return

            st.write("Selecione os itens para incluir no arquivo Excel:")
            
            # 3. Multiselect sem checkbox
            selected_names = st.multiselect(
                "Itens para exportar",
                options=available_options,
                default=available_options
            )
            
            # 4. Remove o st.checkbox
            
            # 5. Prepara o dicionário final
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
                st.error("Nenhuma opção de exportação selecionada.")
                return

            try:
                excel_data = create_excel_bytes(tables_to_export)
                
                st.download_button(
                    label="Clique para Baixar o Excel",
                    data=excel_data,
                    file_name="export_top_10.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    on_click=lambda: st.session_state.update(show_top10_export=False),
                    type="secondary"
                )
            except Exception as e:
                st.error(f"Erro ao gerar Excel: {e}")

            if st.button("Cancelar", key="cancel_export", type="secondary"):
                st.session_state.show_top10_export = False
                st.rerun()

        export_dialog()
    # --- FIM DA SEÇÃO DE EXPORTAÇÃO ---
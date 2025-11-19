# pages/top10.py
import streamlit as st
import plotly.express as px
from utils.format import brl, PALETTE
# CORREÇÃO: Importa a nova função ZIP
from utils.export import create_zip_package 
import pandas as pd
import plotly.graph_objects as go
import numpy as np # Adicionado para a função get_pretty_ticks

# Função de formatação para abreviações em Português
def format_pt_br_abrev(val):
    if pd.isna(val):
        return "R$ 0" # Neutro para NaN
    
    # Salva o sinal
    sign = "-" if val < 0 else ""
    val_abs = abs(val)

    if val_abs == 0:
        return "R$ 0"
    if val_abs >= 1_000_000:
        # Ex: "R$ 1,2 Mi"
        return f"{sign}R$ {val_abs/1_000_000:,.1f} Mi".replace(",", "X").replace(".", ",").replace("X", ".")
    if val_abs >= 1_000:
         # Ex: "R$ 12 mil"
        return f"{sign}R$ {val_abs/1_000:,.0f} mil".replace(",", "X").replace(".", ",").replace("X", ".")
    
    # Para valores < 1000, usa a formatação completa (brl)
    return brl(val)

# Função para criar "ticks bonitos" (copiada do visao_geral)
def get_pretty_ticks(max_val, num_ticks=5):
    if max_val <= 0:
        return [0], ["R$ 0"], 100 
        
    ideal_interval = max_val / num_ticks
    magnitude = 10**np.floor(np.log10(ideal_interval))
    residual = ideal_interval / magnitude
    
    if residual < 1.5: nice_interval = 1 * magnitude
    elif residual < 3: nice_interval = 2 * magnitude
    elif residual < 7: nice_interval = 5 * magnitude
    else: nice_interval = 10 * magnitude
        
    max_y_rounded = np.ceil(max_val / nice_interval) * nice_interval
    
    # Usa a função de formatação PT-BR local
    tick_values = np.arange(0, max_y_rounded + nice_interval, nice_interval)
    tick_texts = [format_pt_br_abrev(v) for v in tick_values] 
    
    y_axis_cap = max_y_rounded * 1.05
    
    return tick_values, tick_texts, y_axis_cap


def render(df, mes_ini, mes_fim, show_labels):
    
    st.header("Top 10 Maiores Anunciantes")
    
    top10_raw = pd.DataFrame()
    fig = go.Figure() 
    top10_raw_export = pd.DataFrame()

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
        
        top10_with_total = top10_raw.copy()
        total_row = {
            "cliente": "Totalizador",
            "faturamento": top10_with_total["faturamento"].sum()
        }
        top10_with_total = pd.concat([top10_with_total, pd.DataFrame([total_row])], ignore_index=True)
        
        top10_with_total.insert(0, "#", list(range(1, len(top10_raw) + 1)) + ["Total"])
        
        top10_raw_export = top10_with_total.copy()

        top10_display = top10_with_total.copy()
        top10_display['#'] = top10_display['#'].astype(str)
        
        top10_display["faturamento_fmt"] = top10_display["faturamento"].apply(brl)

        tabela = top10_display[["#", "cliente", "faturamento_fmt"]].rename(
            columns={"cliente": "Cliente", "faturamento_fmt": "Faturamento"}
        )
        st.dataframe(tabela, width="stretch", hide_index=True) 

        # --- Alteração: Renomear eixos e formatar Y-axis ---
        fig = px.bar(
            top10_raw.head(10), 
            x="cliente",
            y="faturamento",
            color_discrete_sequence=[PALETTE[0]],
            labels={ # Renomeia os eixos X e Y
                "cliente": "Cliente",
                "faturamento": "Faturamento"
            }
        )
        
        # Formatação do Eixo Y (PT-BR Abreviação)
        max_y = top10_raw.head(10)['faturamento'].max()
        tick_values, tick_texts, y_axis_cap = get_pretty_ticks(max_y)

        fig.update_layout(
            height=400, 
            showlegend=False, 
            template="plotly_white",
        )
        
        fig.update_yaxes(
            tickvals=tick_values,
            ticktext=tick_texts,
            range=[0, y_axis_cap],
            title="Faturamento" # Garante o título Faturamento
        )
        
        if show_labels:
            fig.update_traces(
                text=top10_raw.head(10)['faturamento'].apply(format_pt_br_abrev),
                textposition='outside'
            )
        
        st.plotly_chart(fig, width="stretch") 
    else:
        st.info("Sem dados para essa emissora/ano.")


    # --- SEÇÃO DE EXPORTAÇÃO ---
    st.divider()
    
    if st.button("📥 Exportar Dados da Página", type="secondary"):
        st.session_state.show_top10_export = True

    if st.session_state.get("show_top10_export", False):
        
        @st.dialog("Opções de Exportação - Top 10")
        def export_dialog():
            
            all_options = {
                "Top 10 (Dados)": {'df': top10_raw_export}, 
                "Top 10 (Gráfico)": {'fig': fig} # Passa o objeto fig
            }
            
            available_options = []
            for name, data in all_options.items():
                if data.get('df') is not None and not data['df'].empty:
                    available_options.append(name)
                elif data.get('fig') is not None and data['fig'].data:
                    available_options.append(name)
            
            if not available_options:
                st.warning("Nenhuma tabela com dados foi gerada nesta página.")
                if st.button("Fechar", type="secondary"):
                    st.session_state.show_top10_export = False
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
                # Passa o df ou a fig
                if name in all_options:
                    tables_to_export[name] = all_options[name]
            
            if not tables_to_export:
                st.error("Selecione pelo menos um item.")
                return

            try:
                # CHAMADA CORRIGIDA: usa create_zip_package
                zip_data = create_zip_package(tables_to_export)
                
                st.download_button(
                    label="Clique para baixar o pacote de arquivos",
                    data=zip_data,
                    file_name="Dashboard_Top10.zip",
                    mime="application/zip",
                    on_click=lambda: st.session_state.update(show_top10_export=False),
                    type="secondary" # Mantém o estilo secundário
                )
            except Exception as e:
                st.error(f"Erro ao gerar o pacote ZIP: {e}")

            if st.button("Cancelar", key="cancel_export", type="secondary"):
                st.session_state.show_top10_export = False
                st.rerun()

        export_dialog()
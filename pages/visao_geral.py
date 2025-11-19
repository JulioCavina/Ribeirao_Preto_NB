import streamlit as st
import plotly.express as px
from utils.format import brl, PALETTE
import pandas as pd
import plotly.graph_objects as go 
import numpy as np
# Importa a nova função de pacote ZIP
from utils.export import create_zip_package 

# Função de formatação (agora lida com negativos)
def format_pt_br_abrev(val):
    if pd.isna(val):
        return "R$ 0" # Neutro para NaN
    
    # Salva o sinal
    sign = "-" if val < 0 else ""
    val_abs = abs(val)

    if val_abs == 0:
        return "R$ 0"
    if val_abs >= 1_000_000:
        return f"{sign}R$ {val_abs/1_000_000:,.1f} Mi".replace(",", "X").replace(".", ",").replace("X", ".")
    if val_abs >= 1_000: # 1000 a 999.999
        return f"{sign}R$ {val_abs/1_000:,.0f} mil".replace(",", "X").replace(".", ",").replace("X", ".")
    
    # Para valores < 1000, usa a formatação completa (brl)
    return brl(val)

# Função para criar "ticks bonitos"
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
    
    tick_values = np.arange(0, max_y_rounded + nice_interval, nice_interval)
    tick_texts = [format_pt_br_abrev(v) for v in tick_values]
    
    y_axis_cap = max_y_rounded * 1.05
    
    return tick_values, tick_texts, y_axis_cap

def render(df, mes_ini, mes_fim, show_labels):
    st.header("Visão Geral")
    
    evol_raw = pd.DataFrame()
    base_emis_raw = pd.DataFrame()
    base_exec_raw = pd.DataFrame()
    fig_evol = go.Figure()
    fig_emis = go.Figure()
    fig_exec = go.Figure()

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

    # Cards Abreviados
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(f"Total {ano_base}", format_pt_br_abrev(totalA))
    c2.metric(f"Total {ano_comp}", format_pt_br_abrev(totalB))
    c3.metric(label_delta_abs, format_pt_br_abrev(delta_abs))
    c4.metric(label_delta_pct, f"{delta_pct:.2f}%" if totalA > 0 else "—")

    
    st.markdown("<p class='custom-chart-title'>Evolução Mensal</p>", unsafe_allow_html=True)
    
    evol_raw = base_periodo.groupby(["ano", "meslabel", "mes"], as_index=False)["faturamento"].sum().sort_values(["ano", "mes"])
    
    if not evol_raw.empty:
        fig_evol = px.line(
            evol_raw,
            x="meslabel",
            y="faturamento",
            color=evol_raw["ano"].astype(str),
            markers=True,
            template="plotly_white",
            color_discrete_sequence=PALETTE,
            labels={
                "meslabel": "Mês",
                "faturamento": "Faturamento",
                "ano": "Ano"
            }
        )
        
        # Correção Eixo Y (PT-BR)
        max_y = evol_raw['faturamento'].max()
        tick_values, tick_texts, y_axis_cap = get_pretty_ticks(max_y)

        fig_evol.update_layout(
            height=400, 
            legend=dict(orientation="h", y=1.1, title_text="Ano"),
            template="plotly_white"
        )
        
        fig_evol.update_yaxes(
            tickvals=tick_values,
            ticktext=tick_texts,
            range=[0, y_axis_cap]
        )
        
        # Correção Rótulos (Fundo Branco e Fonte Preta)
        if show_labels:
            for trace in fig_evol.data:
                ano_trace = trace.name
                df_trace = evol_raw[evol_raw["ano"].astype(str) == ano_trace]
                
                for i in range(len(df_trace)):
                    row = df_trace.iloc[i]
                    fig_evol.add_annotation(
                        x=row["meslabel"],
                        y=row["faturamento"],
                        text=format_pt_br_abrev(row["faturamento"]),
                        showarrow=False,
                        yshift=10, 
                        font=dict(
                            size=10,
                            color="black" # Fonte preta
                        ),
                        bgcolor="rgba(255, 255, 255, 0.7)", # Fundo branco 70%
                        borderpad=2
                    )
        
        st.plotly_chart(fig_evol, width="stretch") 
    else:
        st.info("Sem dados para o período selecionado.")


    col1, col2 = st.columns(2)

    with col1:
        st.markdown("<p class='custom-chart-title'>Faturamento por Emissora</p>", unsafe_allow_html=True)
        base_emis_raw = base_periodo.groupby("emissora", as_index=False)["faturamento"].sum().sort_values("faturamento", ascending=False)
        
        if not base_emis_raw.empty:
            fig_emis = px.bar(base_emis_raw, x="emissora", y="faturamento", color_discrete_sequence=[PALETTE[0]])
            
            # Correção Eixo Y (PT-BR)
            max_y = base_emis_raw['faturamento'].max()
            tick_values, tick_texts, y_axis_cap = get_pretty_ticks(max_y)
            
            fig_emis.update_layout(
                height=400, 
                xaxis_title=None, 
                yaxis_title="Faturamento", 
                template="plotly_white"
            )
            
            fig_emis.update_yaxes(
                tickvals=tick_values,
                ticktext=tick_texts,
                range=[0, y_axis_cap]
            )
            
            if show_labels:
                fig_emis.update_traces(
                    text=base_emis_raw['faturamento'].apply(format_pt_br_abrev),
                    textposition='outside'
                )
            
            st.plotly_chart(fig_emis, width="stretch") 
        else:
            st.info("Sem dados de emissoras para o período.")

    with col2:
        st.markdown("<p class='custom-chart-title'>Faturamento por Executivo</p>", unsafe_allow_html=True)
        base_exec_raw = base_periodo.groupby("executivo", as_index=False)["faturamento"].sum().sort_values("faturamento", ascending=False)
        
        if not base_exec_raw.empty:
            fig_exec = px.bar(base_exec_raw, x="executivo", y="faturamento", color_discrete_sequence=[PALETTE[3]])
            
            # Correção Eixo Y (PT-BR)
            max_y = base_exec_raw['faturamento'].max()
            tick_values, tick_texts, y_axis_cap = get_pretty_ticks(max_y)

            fig_exec.update_layout(
                height=400, 
                xaxis_title=None, 
                yaxis_title="Faturamento", 
                template="plotly_white"
            )
            
            fig_exec.update_yaxes(
                tickvals=tick_values,
                ticktext=tick_texts,
                range=[0, y_axis_cap]
            )

            if show_labels:
                fig_exec.update_traces(
                    text=base_exec_raw['faturamento'].apply(format_pt_br_abrev),
                    textposition='outside'
                )
            
            st.plotly_chart(fig_exec, width="stretch") 
        else:
            st.info("Sem dados de executivos para o período.")

    ultima = st.session_state.get("ultima_atualizacao", None)
    if ultima:
        st.caption(f"Última atualização da base de dados: {ultima}")

    # --- SEÇÃO DE EXPORTAÇÃO ---
    st.divider()
    
    # Adicionamos uma chave de estado para controlar a abertura do diálogo de exportação
    if st.button("📥 Exportar Dados da Página", type="secondary"):
        st.session_state.show_visao_geral_export = True

    if st.session_state.get("show_visao_geral_export", False):
        
        @st.dialog("Opções de Exportação - Visão Geral")
        def export_dialog():
            
            all_options = {
                "Evolução Mensal (Dados)": {'df': evol_raw},
                "Evolução Mensal (Gráfico)": {'fig': fig_evol}, 
                "Fat. por Emissora (Dados)": {'df': base_emis_raw},
                "Fat. por Emissora (Gráfico)": {'fig': fig_emis}, 
                "Fat. por Executivo (Dados)": {'df': base_exec_raw},
                "Fat. por Executivo (Gráfico)": {'fig': fig_exec},
            }
            
            available_options = []
            for name, data in all_options.items():
                if data.get('df') is not None and not data['df'].empty:
                    available_options.append(name)
                elif data.get('fig') is not None and data['fig'].data:
                    available_options.append(name)

            if not available_options:
                st.warning("Nenhuma tabela ou gráfico com dados foi gerado nesta página.")
                if st.button("Fechar", type="secondary"):
                    st.session_state.show_visao_geral_export = False
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
                data = all_options[name]
                
                # Garante que passamos o df ou a fig
                if 'fig' in data or 'df' in data:
                    tables_to_export[name] = data

            if not tables_to_export:
                st.error("Selecione pelo menos um item.")
                return

            try:
                # CHAMADA CORRIGIDA: usa create_zip_package
                zip_data = create_zip_package(tables_to_export) 
                
                # CORREÇÃO 2: Botão volta para o estilo 'secondary' e rótulo atualizado
                st.download_button(
                    label="Clique para baixar o pacote de arquivos",
                    data=zip_data,
                    file_name="Dashboard_Vendas_Export.zip",
                    mime="application/zip",
                    on_click=lambda: st.session_state.update(show_visao_geral_export=False),
                    type="secondary" # Volta para o estilo secundário (branco/azul)
                )
            except Exception as e:
                st.error(f"Erro ao gerar o pacote ZIP: {e}")

            if st.button("Cancelar", key="cancel_export", type="secondary"):
                st.session_state.show_visao_geral_export = False
                st.rerun()

        export_dialog()
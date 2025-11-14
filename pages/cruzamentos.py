import streamlit as st
import pandas as pd
import numpy as np
from utils.format import brl
import plotly.graph_objects as go
from itertools import combinations
from utils.export import create_excel_bytes # type: ignore

def render(df, mes_ini, mes_fim):
    st.header("Cruzamentos & Interseções entre Emissoras")

    # --- Inicializa DFs brutas para o exportador ---
    df_excl_raw = pd.DataFrame()
    df_comp_raw = pd.DataFrame()
    top_shared_raw = pd.DataFrame()
    mat_raw = pd.DataFrame()
    fig_mat = go.Figure() 
    # ---

    df = df.rename(columns={c: c.lower() for c in df.columns})

    # Verificações básicas
    if "cliente" not in df.columns or "emissora" not in df.columns or "faturamento" not in df.columns:
        st.error("Colunas obrigatórias 'Cliente', 'Emissora' e 'Faturamento' ausentes.")
        return

    # Filtra pelo intervalo de meses
    base_periodo = df[df["mes"].between(mes_ini, mes_fim)]

    if base_periodo.empty:
        st.info("Sem dados para o período selecionado.")
        return

    # Agrupa por cliente e emissora
    agg = base_periodo.groupby(["cliente", "emissora"], as_index=False)["faturamento"].sum()
    agg["presenca"] = np.where(agg["faturamento"] > 0, 1, 0)

    # Cria pivot de presença E faturamento
    pres_pivot = agg.pivot_table(index="cliente", columns="emissora", values="presenca", fill_value=0)
    val_pivot = agg.pivot_table(index="cliente", columns="emissora", values="faturamento", fill_value=0.0) 
    
    emis_count = pres_pivot.sum(axis=1)

    exclusivos_mask = emis_count == 1
    compartilhados_mask = emis_count >= 2

    excl_info, comp_info = [], []
    emissoras = sorted(agg["emissora"].unique())

    for emis in emissoras:
        cli_excl = pres_pivot.loc[exclusivos_mask & (pres_pivot[emis] == 1)].index
        fat_excl = agg[(agg["cliente"].isin(cli_excl)) & (agg["emissora"] == emis)]["faturamento"].sum()
        cli_comp = pres_pivot.loc[compartilhados_mask & (pres_pivot[emis] == 1)].index
        fat_comp = agg[(agg["cliente"].isin(cli_comp)) & (agg["emissora"] == emis)]["faturamento"].sum()
        fat_total = agg[agg["emissora"] == emis]["faturamento"].sum()
        pct_excl = (fat_excl / fat_total * 100) if fat_total > 0 else 0
        pct_comp = (fat_comp / fat_total * 100) if fat_total > 0 else 0

        excl_info.append({
            "Emissora": emis,
            "Clientes Exclusivos": len(cli_excl),
            "Faturamento Exclusivo": fat_excl,
            "% Faturamento": pct_excl
        })
        comp_info.append({
            "Emissora": emis,
            "Clientes Compartilhados": len(cli_comp),
            "Faturamento Compartilhado": fat_comp,
            "% Faturamento": pct_comp
        })

    # ============================
    # Tabela 3.1 – Exclusivos
    # ============================
    st.subheader("3.1 Clientes Exclusivos por Emissora")
    df_excl_raw = pd.DataFrame(excl_info) 

    if not df_excl_raw.empty:
        df_excl_display = df_excl_raw.sort_values("Faturamento Exclusivo", ascending=False).reset_index(drop=True)
        df_excl_display.insert(0, "#", range(1, len(df_excl_display) + 1))
        df_excl_display["Faturamento Exclusivo"] = df_excl_display["Faturamento Exclusivo"].apply(brl)
        df_excl_display["% Faturamento"] = df_excl_display["% Faturamento"].apply(lambda x: f"{x:.2f}%")
        st.dataframe(df_excl_display, width='stretch', hide_index=True)
    else:
        st.info("Nenhum cliente exclusivo encontrado.")

    st.divider()

    # ============================
    # Tabela 3.2 – Compartilhados
    # ============================
    st.subheader("3.2 Clientes Compartilhados por Emissora")
    df_comp_raw = pd.DataFrame(comp_info) 

    if not df_comp_raw.empty:
        df_comp_display = df_comp_raw.sort_values("Faturamento Compartilhado", ascending=False).reset_index(drop=True)
        df_comp_display.insert(0, "#", range(1, len(df_comp_display) + 1))
        df_comp_display["Faturamento Compartilhado"] = df_comp_display["Faturamento Compartilhado"].apply(brl)
        df_comp_display["% Faturamento"] = df_comp_display["% Faturamento"].apply(lambda x: f"{x:.2f}%")
        st.dataframe(df_comp_display, width='stretch', hide_index=True)
    else:
        st.info("Nenhum cliente compartilhado encontrado.")

    st.divider()

    # ============================
    # 3.3 Top Clientes Compartilhados
    # ============================
    st.subheader("3.3 Top clientes compartilhados (2+ emissoras)")
    
    if compartilhados_mask.any():
        share_clients = pres_pivot[compartilhados_mask].index
        top_shared_raw = ( 
            base_periodo[base_periodo["cliente"].isin(share_clients)]
            .groupby("cliente", as_index=False)["faturamento"].sum()
            .sort_values("faturamento", ascending=False)
            .head(20)
        )
        
        top_shared_disp = top_shared_raw.rename(columns={"cliente": "Cliente", "faturamento": "Faturamento"})
        top_shared_disp["Faturamento"] = top_shared_disp["Faturamento"].apply(brl)
        top_shared_disp.insert(0, "#", range(1, len(top_shared_disp) + 1))
        
        st.dataframe(top_shared_disp, width="stretch", hide_index=True)
    else:
        st.info("Não há clientes compartilhados para os filtros atuais.")
        
    st.divider()

    # ============================
    # 3.4 Matriz de Interseção
    # ============================
    if "cruzamentos_metric" not in st.session_state:
        st.session_state.cruzamentos_metric = "Clientes"
    metric = st.session_state.cruzamentos_metric

    btn_label_clientes = "Clientes em comum"
    btn_label_fat = "Faturamento em comum (R$)"
    metric_label = btn_label_clientes if metric == "Clientes" else btn_label_fat
    
    st.subheader(f"3.4 Interseções entre emissoras (matriz) - {metric_label}")
    
    emis_list = sorted(list(pres_pivot.columns))
    
    if len(emis_list) < 2:
        st.info("A matriz de interseção requer pelo menos 2 emissoras com dados.")
    else:
        btn_type_clientes = "primary" if metric == "Clientes" else "secondary"
        btn_type_fat = "primary" if metric == "Faturamento" else "secondary"
        
        _, col1, col2, _ = st.columns([2, 1.8, 1.8, 2]) 

        with col1:
            if st.button(btn_label_clientes, type=btn_type_clientes, use_container_width=True):
                st.session_state.cruzamentos_metric = "Clientes"
                st.rerun() 

        with col2:
            if st.button(btn_label_fat, type=btn_type_fat, use_container_width=True):
                st.session_state.cruzamentos_metric = "Faturamento"
                st.rerun() 

        mat_raw = pd.DataFrame(0.0, index=emis_list, columns=emis_list)

        if metric.startswith("Clientes"):
            for a, b in combinations(emis_list, 2):
                comuns = ((pres_pivot[a] == 1) & (pres_pivot[b] == 1)).sum()
                mat_raw.loc[a, b] = comuns
                mat_raw.loc[b, a] = comuns
            for e in emis_list:
                mat_raw.loc[e, e] = (pres_pivot[e] == 1).sum()
            z = mat_raw.values
            hover = "<b>%{y} x %{x}</b><br>Clientes: %{z}<extra></extra>"
        
        else: # Faturamento em comum
            for a, b in combinations(emis_list, 2):
                menor = np.minimum(val_pivot[a], val_pivot[b])
                vlr = menor[menor > 0].sum()
                mat_raw.loc[a, b] = vlr
                mat_raw.loc[b, a] = vlr
            for e in emis_list:
                mat_raw.loc[e, e] = val_pivot[e].sum()
            z = mat_raw.values
            hover = "<b>%{y} x %{x}</b><br>Valor: R$ %{z:,.2f}<extra></extra>"

        fig_mat = go.Figure(
            data=go.Heatmap(
                z=z, x=mat_raw.columns, y=mat_raw.index, 
                colorscale="Blues", hovertemplate=hover, 
                showscale=True
            )
        )
        fig_mat.update_layout(height=420, template="plotly_white", margin=dict(l=0, r=10, t=10, b=0))
        st.plotly_chart(fig_mat, width="stretch")
        
    # --- INÍCIO DA SEÇÃO DE EXPORTAÇÃO (MODIFICADA) ---
    st.divider()
    
    if st.button("📥 Exportar Dados da Página", type="secondary"):
        st.session_state.show_cruzamentos_export = True

    if st.session_state.get("show_cruzamentos_export", False):
        
        @st.dialog("Opções de Exportação - Cruzamentos")
        def export_dialog():
            
            # 1. Define todas as opções
            all_options = {
                "3.1 Exclusivos": {'df': df_excl_raw},
                "3.2 Compartilhados": {'df': df_comp_raw},
                "3.3 Top Compartilhados": {'df': top_shared_raw},
                "3.4 Matriz (Dados)": {'df': mat_raw},
                "3.4 Matriz (Gráfico)": {'img': fig_mat} 
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
                    st.session_state.show_cruzamentos_export = False
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
                    file_name="export_cruzamentos_e_intersecoes.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    on_click=lambda: st.session_state.update(show_cruzamentos_export=False),
                    type="secondary"
                )
            except Exception as e:
                st.error(f"Erro ao gerar Excel: {e}")

            if st.button("Cancelar", key="cancel_export", type="secondary"):
                st.session_state.show_cruzamentos_export = False
                st.rerun()

        export_dialog()
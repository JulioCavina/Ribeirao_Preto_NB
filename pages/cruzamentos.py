import streamlit as st
import pandas as pd
import numpy as np
from utils.format import brl
import plotly.graph_objects as go
from itertools import combinations
# CORREÇÃO: Importa a nova função ZIP
from utils.export import create_zip_package 

def render(df, mes_ini, mes_fim, show_labels):
    # --- INÍCIO DA ALTERAÇÃO (Formato PT-BR: mil/Mi) ---
    # Função de formatação para abreviações em Português
    def format_pt_br_abrev(val):
        if pd.isna(val) or val == 0:
            # Retorna "R$ 0,00" para consistência
            return brl(0) 
        if val >= 1_000_000:
            # Ex: "R$ 1,2 Mi"
            return f"R$ {val/1_000_000:,.1f} Mi"
        if val >= 1_000:
             # Ex: "R$ 12 mil"
            return f"R$ {val/1_000:,.0f} mil"
        # Para valores menores, usa a formatação completa (brl)
        return brl(val)
    # --- FIM DA ALTERAÇÃO ---

    st.header("Cruzamentos & Interseções entre Emissoras")

    df_excl_raw = pd.DataFrame()
    df_comp_raw = pd.DataFrame()
    top_shared_raw = pd.DataFrame()
    mat_raw = pd.DataFrame()
    fig_mat = go.Figure() 

    df = df.rename(columns={c: c.lower() for c in df.columns})

    if "cliente" not in df.columns or "emissora" not in df.columns or "faturamento" not in df.columns:
        st.error("Colunas obrigatórias 'Cliente', 'Emissora' e 'Faturamento' ausentes.")
        return

    base_periodo = df[df["mes"].between(mes_ini, mes_fim)]

    if base_periodo.empty:
        st.info("Sem dados para o período selecionado.")
        return

    agg = base_periodo.groupby(["cliente", "emissora"], as_index=False)["faturamento"].sum()
    agg["presenca"] = np.where(agg["faturamento"] > 0, 1, 0)

    pres_pivot = agg.pivot_table(index="cliente", columns="emissora", values="presenca", fill_value=0)
    val_pivot = agg.pivot_table(index="cliente", columns="emissora", values="faturamento", fill_value=0.0) 
    
    emis_count = pres_pivot.sum(axis=1)

    exclusivos_mask = emis_count == 1
    compartilhados_mask = emis_count >= 2

    excl_info, comp_info = [], []
    emissoras = sorted(agg["emissora"].unique())
    fat_total_geral = 0.0 

    for emis in emissoras:
        cli_excl = pres_pivot.loc[exclusivos_mask & (pres_pivot[emis] == 1)].index
        fat_excl = agg[(agg["cliente"].isin(cli_excl)) & (agg["emissora"] == emis)]["faturamento"].sum()
        cli_comp = pres_pivot.loc[compartilhados_mask & (pres_pivot[emis] == 1)].index
        fat_comp = agg[(agg["cliente"].isin(cli_comp)) & (agg["emissora"] == emis)]["faturamento"].sum()
        fat_total = agg[agg["emissora"] == emis]["faturamento"].sum()
        fat_total_geral += fat_total 
        
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
        df_excl_raw = df_excl_raw.sort_values("Faturamento Exclusivo", ascending=False).reset_index(drop=True)
        
        total_cli = df_excl_raw["Clientes Exclusivos"].sum()
        total_fat = df_excl_raw["Faturamento Exclusivo"].sum()
        total_pct = (total_fat / fat_total_geral * 100) if fat_total_geral > 0 else np.nan
        
        total_row = {
            "Emissora": "Totalizador",
            "Clientes Exclusivos": total_cli,
            "Faturamento Exclusivo": total_fat,
            "% Faturamento": total_pct
        }
        df_excl_raw = pd.concat([df_excl_raw, pd.DataFrame([total_row])], ignore_index=True)
        df_excl_raw.insert(0, "#", list(range(1, len(df_excl_raw))) + ["Total"])
        
        df_excl_display = df_excl_raw.copy()
        df_excl_display['#'] = df_excl_display['#'].astype(str)
        df_excl_display["Faturamento Exclusivo"] = df_excl_display["Faturamento Exclusivo"].apply(brl)
        df_excl_display["% Faturamento"] = df_excl_display["% Faturamento"].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "—")
        
        st.dataframe(
            df_excl_display, 
            width='stretch', 
            hide_index=True,
            column_config={"#": None} 
        )
    else:
        st.info("Nenhum cliente exclusivo encontrado.")

    st.divider()

    # ============================
    # Tabela 3.2 – Compartilhados
    # ============================
    st.subheader("3.2 Clientes Compartilhados por Emissora")
    df_comp_raw = pd.DataFrame(comp_info) 

    if not df_comp_raw.empty:
        df_comp_raw = df_comp_raw.sort_values("Faturamento Compartilhado", ascending=False).reset_index(drop=True)
        
        total_cli = df_comp_raw["Clientes Compartilhados"].sum()
        total_fat = df_comp_raw["Faturamento Compartilhado"].sum()
        total_pct = (total_fat / fat_total_geral * 100) if fat_total_geral > 0 else np.nan
        
        total_row = {
            "Emissora": "Totalizador",
            "Clientes Compartilhados": total_cli,
            "Faturamento Compartilhado": total_fat,
            "% Faturamento": total_pct
        }
        df_comp_raw = pd.concat([df_comp_raw, pd.DataFrame([total_row])], ignore_index=True)
        df_comp_raw.insert(0, "#", list(range(1, len(df_comp_raw))) + ["Total"])
        
        df_comp_display = df_comp_raw.copy()
        df_comp_display['#'] = df_comp_display['#'].astype(str)
        df_comp_display["Faturamento Compartilhado"] = df_comp_display["Faturamento Compartilhado"].apply(brl)
        df_comp_display["% Faturamento"] = df_comp_display["% Faturamento"].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "—")
        
        st.dataframe(
            df_comp_display, 
            width='stretch', 
            hide_index=True,
            column_config={"#": None}
        )
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
        
        if not top_shared_raw.empty:
            total_row = {
                "cliente": "Totalizador",
                "faturamento": top_shared_raw["faturamento"].sum()
            }
            top_shared_raw = pd.concat([top_shared_raw, pd.DataFrame([total_row])], ignore_index=True)
        
        top_shared_raw.insert(0, "#", list(range(1, len(top_shared_raw))) + ["Total"])

        top_shared_disp = top_shared_raw.copy()
        top_shared_disp = top_shared_disp.rename(columns={"cliente": "Cliente", "faturamento": "Faturamento"})
        top_shared_disp['#'] = top_shared_disp['#'].astype(str)
        top_shared_disp["Faturamento"] = top_shared_disp["Faturamento"].apply(brl)
        
        st.dataframe(
            top_shared_disp, 
            width="stretch", 
            hide_index=True,
            column_config={"#": None}
        )
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
        z_text = None 
        text_colors_2d = [] 

        if metric.startswith("Clientes"):
            for a, b in combinations(emis_list, 2):
                comuns = ((pres_pivot[a] == 1) & (pres_pivot[b] == 1)).sum()
                mat_raw.loc[a, b] = comuns
                mat_raw.loc[b, a] = comuns
            for e in emis_list:
                mat_raw.loc[e, e] = (pres_pivot[e] == 1).sum()
            z = mat_raw.values
            hover = "<b>%{y} x %{x}</b><br>Clientes: %{z}<extra></extra>"
            z_text = z.astype(int).astype(str) 
            
            max_val = np.nanmax(z) if z.size > 0 else 0
            threshold = max_val * 0.4
            text_colors_2d = [['white' if v > threshold else 'black' for v in row] for row in z]
            
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
            
            # --- INÍCIO DA ALTERAÇÃO (Aplica novo formato PT-BR) ---
            z_text = [[format_pt_br_abrev(v) for v in row] for row in z]
            # --- FIM DA ALTERAÇÃO ---

            max_val = np.nanmax(z) if z.size > 0 else 0
            threshold = max_val * 0.4
            text_colors_2d = [['white' if v > threshold else 'black' for v in row] for row in z]


        fig_mat = go.Figure(
            data=go.Heatmap(
                z=z, x=mat_raw.columns, y=mat_raw.index, 
                colorscale="Blues", hovertemplate=hover, 
                showscale=True
            )
        )
        
        if show_labels and z_text is not None and text_colors_2d:
            for i, row in enumerate(z):
                for j, val in enumerate(row):
                    fig_mat.add_annotation(
                        x=mat_raw.columns[j],
                        y=mat_raw.index[i],
                        text=z_text[i][j],
                        showarrow=False,
                        font=dict(
                            color=text_colors_2d[i][j]
                        )
                    )

        fig_mat.update_layout(height=420, template="plotly_white", margin=dict(l=0, r=10, t=10, b=0))
        st.plotly_chart(fig_mat, width="stretch")
        
    # --- SEÇÃO DE EXPORTAÇÃO ---
    st.divider()
    
    if st.button("📥 Exportar Dados da Página", type="secondary"):
        st.session_state.show_cruzamentos_export = True

    if st.session_state.get("show_cruzamentos_export", False):
        
        @st.dialog("Opções de Exportação - Cruzamentos")
        def export_dialog():
            
            all_options = {
                "3.1 Exclusivos": {'df': df_excl_raw},
                "3.2 Compartilhados": {'df': df_comp_raw},
                "3.3 Top Compartilhados": {'df': top_shared_raw},
                "3.4 Matriz (Dados)": {'df': mat_raw.reset_index().rename(columns={'index':'Emissora'})},
                "3.4 Matriz (Gráfico)": {'fig': fig_mat} # Passa o objeto fig
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
                    st.session_state.show_cruzamentos_export = False
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
                    file_name="Dashboard_Cruzamentos.zip",
                    mime="application/zip",
                    on_click=lambda: st.session_state.update(show_cruzamentos_export=False),
                    type="secondary" # Mantém o estilo secundário
                )
            except Exception as e:
                st.error(f"Erro ao gerar o pacote ZIP: {e}")

            if st.button("Cancelar", key="cancel_export", type="secondary"):
                st.session_state.show_cruzamentos_export = False
                st.rerun()

        export_dialog()
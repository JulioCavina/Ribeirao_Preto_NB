# utils/filters.py
import streamlit as st
import pandas as pd

def aplicar_filtros(df):
    """Aplica filtros interativos no corpo principal da página, com estado persistente.
    
    A persistência é garantida pelo uso da chave (key) no widget e pela inicialização 
    do valor em st.session_state.
    """

    # ==================== NORMALIZAÇÃO (para garantir as colunas) ====================
    df.columns = df.columns.str.strip().str.lower()

    # Garante a existência das colunas necessárias para o filtro
    if "mês" not in df.columns:
        possiveis = ["mes", "month", "mês referência", "mes_ref", "data", "date"]
        for c in possiveis:
            if c in df.columns:
                if pd.api.types.is_datetime64_any_dtype(df[c]):
                    df["mês"] = df[c].dt.month
                else:
                    df["mês"] = pd.to_numeric(df[c], errors="coerce")
                break
        else:
            df["mês"] = 1

    if "ano" not in df.columns:
        possiveis_ano = ["ano_ref", "ano referência", "year", "data", "date"]
        for c in possiveis_ano:
            if c in df.columns:
                if pd.api.types.is_datetime64_any_dtype(df[c]):
                    df["ano"] = df[c].dt.year
                else:
                    df["ano"] = pd.to_numeric(df[c], errors="coerce")
                break
        else:
            df["ano"] = 2024

    for col in ["emissora", "executivo", "cliente"]:
        if col not in df.columns:
            df[col] = ""

    # ==================== DADOS BASE PARA FILTROS ====================
    anos = sorted(df["ano"].dropna().unique())
    emisoras = sorted(df["emissora"].dropna().unique())
    execs = sorted(df["executivo"].dropna().unique())
    clientes = sorted(df["cliente"].dropna().unique())
    
    meses_disponiveis = sorted(df["mês"].dropna().unique())
    if not meses_disponiveis:
        mes_min, mes_max = 1, 12
    else:
        mes_min, mes_max = int(min(meses_disponiveis)), int(max(meses_disponiveis))

    # ==================== LÓGICA DE PERSISTÊNCIA (SESSION STATE) ====================
    # Inicializa o st.session_state se a chave não existir.
    
    # 1. Ano: Default para o ano mais recente disponível
    if "filtro_anos" not in st.session_state:
        st.session_state["filtro_anos"] = anos[-1:] if anos else []

    # 2. Emissora: Default para todas as emissoras
    if "filtro_emis" not in st.session_state:
        st.session_state["filtro_emis"] = emisoras

    # 3. Executivo: Default para todos os executivos
    if "filtro_execs" not in st.session_state:
        st.session_state["filtro_execs"] = execs

    # 4. Cliente: Default para nenhum cliente selecionado
    if "filtro_clientes" not in st.session_state:
        st.session_state["filtro_clientes"] = []

    # 5. Meses: Default para o intervalo completo de meses disponíveis
    if "filtro_meses" not in st.session_state:
        st.session_state["filtro_meses"] = (mes_min, mes_max)
        
    # ==================== WIDGETS DE FILTRO ====================
    with st.container():
        # COR DA FONTE ALTERADA DE #ffffff PARA #002b5c
        st.markdown("<h3 style='color:#002b5c;'>Filtros Globais</h3>", unsafe_allow_html=True)

        with st.container():
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # CORREÇÃO: Removido 'default='. O Streamlit lê o valor de st.session_state["filtro_anos"]
                st.multiselect(
                    "Ano(s):",
                    anos,
                    key="filtro_anos" 
                )

            with col2:
                # CORREÇÃO: Removido 'default='
                st.multiselect(
                    "Emissora(s):",
                    emisoras,
                    key="filtro_emis"
                )

            with col3:
                # CORREÇÃO: Removido 'default='
                st.multiselect(
                    "Executivo(s):",
                    execs,
                    key="filtro_execs"
                )

        col4, col5 = st.columns(2)
        
        with col4:
            # CORREÇÃO: Removido 'default='
            st.multiselect(
                "Cliente(s):", 
                clientes,
                key="filtro_clientes"
            )

        with col5:
            # CORREÇÃO: Removido 'value='. O Streamlit lê de st.session_state["filtro_meses"]
            st.slider(
                "Intervalo de Meses - Selecione o período:",
                min_value=mes_min,
                max_value=mes_max,
                step=1,
                key="filtro_meses"
            )

    # ==================== APLICA FILTROS ====================
    # Lê os valores atuais do session_state (que foram atualizados pelos widgets)
    ano_sel = st.session_state["filtro_anos"]
    emis_sel = st.session_state["filtro_emis"]
    exec_sel = st.session_state["filtro_execs"]
    cli_sel = st.session_state["filtro_clientes"]
    mes_ini, mes_fim = st.session_state["filtro_meses"]
    
    df_filtrado = df[
        (df["ano"].isin(ano_sel)) &
        (df["emissora"].isin(emis_sel)) &
        (df["executivo"].isin(exec_sel)) &
        (df["mês"].between(mes_ini, mes_fim))
    ]

    if cli_sel:
        df_filtrado = df_filtrado[df_filtrado["cliente"].isin(cli_sel)]

    st.divider()

    # Retorna os valores selecionados
    return df_filtrado, ano_sel, emis_sel, exec_sel, cli_sel, mes_ini, mes_fim
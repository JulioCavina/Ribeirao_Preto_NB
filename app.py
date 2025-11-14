# app.py
import os
import streamlit as st
from PIL import Image
import pandas as pd
from datetime import datetime, timedelta # Necessário para o cookie
import base64 
# A biblioteca correta (PLURAL), que está no seu requirements.txt
import streamlit_cookies_manager 

# Importações locais
from utils.loaders import load_main_base, load_crowley_base
from utils.filters import aplicar_filtros
from pages import inicio, visao_geral, clientes_faturamento, perdas_ganhos, cruzamentos, top10, crowley
from utils.format import normalize_dataframe


# ==================== CONFIGURAÇÕES GERAIS ====================
st.set_page_config(
    page_title="Dashboard Vendas Ribeirão Preto",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== LÓGICA DE AUTENTICAÇÃO (COM COOKIES) ====================

# Inicializa o gerenciador de cookies
# CORREÇÃO: A biblioteca PLURAL não aceita 'key' na inicialização.
cookies = streamlit_cookies_manager.CookieManager()
if not cookies.ready():
    # Hack para esperar o componente carregar
    st.spinner("Carregando...")
    st.stop()

# 1. Verifica se a sessão atual é autenticada.
#    Se não for, verifica se existe um cookie de autenticação válido.
if not st.session_state.get("authenticated", False):
    # A sintaxe .get() está correta para ler
    auth_cookie = cookies.get("auth_token")
    if auth_cookie == "user_is_logged_in":
        # Se o cookie existir, autentica a sessão
        st.session_state.authenticated = True
    else:
        # Se nem a sessão nem o cookie existirem, força o login
        st.session_state.authenticated = False

# 2. Se, após tudo, não estiver autenticado, mostra o formulário de login
if not st.session_state.authenticated:
    
    # Esconde elementos do app
    hide_elements_style = """
        <style>
            [data-testid="stSidebar"] {display: none;}
            [data-testid="stHeader"] {display: none;}
            [data-testid="stToolbar"] {display: none;}
            .main {padding-top: 2rem;}
        </style>
    """
    st.markdown(hide_elements_style, unsafe_allow_html=True)

    # Centraliza o formulário
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        logo_path = os.path.join("assets", "logomarca_novabrasil.jpg")
        if os.path.exists(logo_path):
            st.image(logo_path, width=200)
        
        st.markdown("#### 🔒 Acesso Restrito")
        
        with st.form(key="login_form"):
            password = st.text_input(
                "Por favor, insira a senha para acessar o dashboard:", 
                type="password",
                key="password_input"
            )
            
            # Botão de submissão do formulário
            submitted = st.form_submit_button("Entrar")

        if submitted:
            if password.strip().lower() == "omelete":
                # SUCESSO NO LOGIN
                st.session_state.authenticated = True
                
                # A biblioteca PLURAL usa sintaxe de dicionário e um .save()
                cookies["auth_token"] = "user_is_logged_in"
                cookies.save() 
                
                st.rerun() # Força o recarregamento imediato
            else:
                # Senha incorreta
                st.error("Senha incorreta. Tente novamente.")
                st.session_state.authenticated = False
    
    # 3. Para a execução do script aqui. 
    st.stop()


# =============================================================
# === O APP PRINCIPAL RODA A PARTIR DAQUI SÓ SE AUTENTICADO ===
# =============================================================

# === INJEÇÃO DO ÍCONE PNG (FAVICON) ===
def set_favicon(icon_path):
    try:
        if not os.path.exists(icon_path):
            # st.warning(f"⚠️ Aviso: Ícone não encontrado em {icon_path}.")
            return

        with open(icon_path, "rb") as f:
            icon_base64 = base64.b64encode(f.read()).decode()
            
        favicon_html = f"""
            <link rel="icon" type="image/png" href="data:image/png;base64,{icon_base64}">
            <link rel="shortcut icon" type="image/png" href="data:image/png;base64,{icon_base64}">
        """
        st.markdown(favicon_html, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"❌ Erro ao processar o ícone: {e}")

set_favicon(os.path.join("assets", "icone.png"))


# === APLICA ESTILO GLOBAL ===
def local_css(file_name):
    if os.path.exists(file_name):
        with open(file_name, encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    else:
        st.warning(f"Arquivo de estilo não encontrado: {file_name}")

local_css("utils/style.css")

# Oculta o menu lateral automático do Streamlit
hide_default_format = """
    <style>
    [data-testid="stSidebarNav"] {display: none;}
    </style>
"""
st.markdown(hide_default_format, unsafe_allow_html=True)


# ==================== TEMA GLOBAL (AZUL NOVABRASIL) ====================
st.markdown("""
<style>
:root {
    --azul-nb: #007bff;
    --azul-escuro: #004a99;
}

/* 1. Torna a regra de TAGS específica para o MultiSelect (Filtros) */
[data-testid="stMultiSelect"] [data-baseweb="tag"] {
    background-color: var(--azul-nb) !important;
    color: white !important;
    border-radius: 6px !important;
}
[data-testid="stMultiSelect"] [data-baseweb="tag"] span {
    color: white !important;
    font-weight: 600 !important;
}
[data-testid="stMultiSelect"] [data-baseweb="tag"] svg {
    fill: white !important;
}

[data-baseweb="select"] > div {
    border: 1.5px solid var(--azul-nb) !important;
    border-radius: 8px !important;
    background-color: rgba(0,123,255,0.03) !important;
}
[data-baseweb="select"]:focus-within > div {
    border-color: var(--azul-escuro) !important;
    box-shadow: 0 0 0 3px rgba(0,123,255,0.2) !important;
}
.stSlider .rc-slider-track { background: var(--azul-nb) !important; height: 6px !important; }
.stSlider .rc-slider-rail { background: rgba(0,123,255,0.15) !important; height: 6px !important; }
.stSlider .rc-slider-handle {
    border: 2px solid var(--azul-escuro) !important;
    background: var(--azul-nb) !important;
    box-shadow: 0 0 5px rgba(0,91,187,0.3) !important;
}

/* Aumenta a fonte do texto geral (st.write) dentro do diálogo */
[data-testid="stDialog"] [data-testid="stMarkdownContainer"] p {
    font-size: 1.1rem !important;
    color: #002b5c !important; /* Cor principal do texto */
}

/* Aumenta a fonte do label (título) do multiselect e checkbox dentro do diálogo */
[data-testid="stDialog"] label {
    font-size: 1.1rem !important;
    font-weight: 600 !important;
    color: #003366 !important;
}

.sidebar-nav-btn {
    display: block;
    padding: 10px 15px;
    margin: 5px 15px; 
    border-radius: 8px; 
    color: #004a99; 
    text-decoration: none !important; 
    font-weight: 600;
    transition: all 0.1s;
    background-color: transparent;
    cursor: pointer;
    text-align: center; 
}
.sidebar-nav-btn:hover {
    background-color: rgba(0, 123, 255, 0.1);
    color: #007bff;
    text-decoration: none !important; 
}
.sidebar-nav-btn.active {
    background-color: var(--azul-nb) !important;
    color: white !important;
    font-weight: 700 !important;
    border-radius: 8px !important; 
    text-align: center !important; 
    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
}
.sidebar-nav-container + div > p {
    font-size: 0.9rem; 
    font-weight: 600; 
    color: #004a99; 
}
label, .stMarkdown h3, .stMarkdown h4 {
    color: #003366 !important;
    font-size: 1rem !important;
    font-weight: 600 !important;
}
</style>
""", unsafe_allow_html=True)


# ==================== LOGO E PALETA ====================
PALETTE = ["#007dc3", "#00a8e0", "#7ad1e6", "#004b8d", "#0095d9"]
logo_path = os.path.join("assets", "logomarca_novabrasil.jpg")
if os.path.exists(logo_path):
    logo = Image.open(logo_path)
    # --- INÍCIO DA ALTERAÇÃO (Logo Sidebar) ---
    st.sidebar.image(logo, use_container_width=True) # Corrigido de width='stretch'
    # --- FIM DA ALTERAÇÃO ---

# ==================== CARREGAMENTO DE DADOS (LÓGICA CORRIGIDA) ====================
st.title("Dashboard Vendas Ribeirão Preto")
st.caption("Menu lateral para navegar • Filtros no topo • Exportação em Excel")

# O loaders.py agora só verifica a pasta /data.
df, ultima_atualizacao = load_main_base()

# Se 'df' não existir (pasta /data está vazia), pede o upload.
if df is None or df.empty:
    st.warning("⚠️ Nenhuma base de dados encontrada.")
    st.info("Por favor, carregue a planilha de vendas (.xlsx) para iniciar.")
    
    uploaded_file = st.file_uploader(
        "Selecione o arquivo Excel (.xlsx)", 
        type=["xlsx"],
        accept_multiple_files=False
    )
    
    if uploaded_file is not None:
        try:
            # --- LÓGICA DE SALVAMENTO NO DISCO ---
            base_dir = os.path.dirname(__file__)
            data_dir = os.path.join(base_dir, "data")
            if not os.path.exists(data_dir):
                os.makedirs(data_dir)
            
            save_path = os.path.join(data_dir, "temp_data_uploaded.xlsx")
            with open(save_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            st.success("✅ Arquivo carregado. O dashboard será iniciado.")
            st.rerun()

        except Exception as e:
            st.error(f"Erro ao processar o arquivo: {e}")
            
    st.stop() # Para a execução aqui até que o arquivo seja carregado


# ==================== MENU LATERAL (CUSTOMIZADO) ====================
st.sidebar.title("📋 Navegação")
pages = {
    "Início": inicio,
    "Visão Geral": visao_geral,
    "Clientes & Faturamento": clientes_faturamento,
    "Perdas & Ganhos": perdas_ganhos,
    "Cruzamentos & Interseções": cruzamentos,
    "Top 10": top10,
    "Crowley ABC": crowley,
}
page_display = {
    "Início": "🏠 Início",
    "Visão Geral": "📊 Visão Geral",
    "Clientes & Faturamento": "💼 Clientes & Faturamento",
    "Perdas & Ganhos": "📉 Perdas & Ganhos",
    "Cruzamentos & Interseções": "🔀 Cruzamentos & Interseções",
    "Top 10": "🏆 Top 10",
    "Crowley ABC": "📻 Crowley ABC",
}

# 1. LÓGICA DE NAVEGAÇÃO (SIMPLIFICADA)
query_params = st.query_params
nav_id = query_params.get("nav", ["0"])[0] 
page_keys = list(pages.keys()) 

try:
    pagina_ativa = page_keys[int(nav_id)] 
except (IndexError, ValueError):
    pagina_ativa = page_keys[0] 

# 2. Cria os botões HTML na Sidebar
st.sidebar.markdown('<p style="font-size:0.9rem; font-weight:600; margin-bottom: 0.5rem; text-align: center;">Selecione a página:</p>', unsafe_allow_html=True)

html_menu = []
for idx, page_name in enumerate(page_keys):
    is_active = "active" if page_name == pagina_ativa else ""
    display_name = page_display.get(page_name, page_name) 
    html_menu.append(
        f'<a class="sidebar-nav-btn {is_active}" href="?nav={idx}" target="_self">{display_name}</a>'
    )

st.sidebar.markdown(f'<div class="sidebar-nav-container">{"".join(html_menu)}</div>', unsafe_allow_html=True)
st.sidebar.divider()

# ==================== ROTEAMENTO ====================
if pagina_ativa == "Início":
    pages[pagina_ativa].render(df) 
    st.sidebar.info(f"Registros carregados: {len(df):,}".replace(",", "."))
else:
    df_filtrado, anos_sel, emis_sel, exec_sel, cli_sel, mes_ini, mes_fim = aplicar_filtros(df)

    if df_filtrado is None or df_filtrado.empty:
        st.warning("⚠️ Nenhum dado encontrado com os filtros aplicados.")
        st.stop()
    
    st.sidebar.info(f"📊 Registros filtrados: {len(df_filtrado):,}".replace(",", "."))

    if pagina_ativa == "Crowley ABC":
        pages[pagina_ativa].render(df_filtrado)
    else:
        pages[pagina_ativa].render(df_filtrado, mes_ini, mes_fim)

# ==================== RODAPÉ GLOBAL ====================
st.markdown("---")
if ultima_atualizacao:
    st.caption(f"📅 Última atualização da base de dados: **{ultima_atualizacao}**")
else:
    st.caption("📅 Última atualização da base de dados: —")
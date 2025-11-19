# app.py
import os
import streamlit as st
from PIL import Image
import pandas as pd
from datetime import datetime, timedelta
import base64 
import streamlit_cookies_manager 
import json 

# --- INÍCIO DA CORREÇÃO (Definir Idioma PT-BR) ---
import locale
import platform

# Define o locale para Português do Brasil
try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, 'Portuguese_Brazil')
    except locale.Error:
        print("AVISO: Não foi possível definir o locale para pt-BR.")
# --- FIM DA CORREÇÃO ---


# Importações locais
from utils.loaders import load_main_base
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

cookies = streamlit_cookies_manager.CookieManager()
if not cookies.ready():
    st.spinner("Carregando...")
    st.stop()

if not st.session_state.get("authenticated", False):
    auth_cookie = cookies.get("auth_token")
    if auth_cookie == "user_is_logged_in":
        st.session_state.authenticated = True
    else:
        st.session_state.authenticated = False

# Carrega Filtros do Cookie
if "filters_loaded" not in st.session_state:
    filter_cookie = cookies.get("app_filters")
    if filter_cookie:
        try:
            saved_filters = json.loads(filter_cookie)
            for key, value in saved_filters.items():
                st.session_state[key] = value
        except Exception:
            pass 
    st.session_state.filters_loaded = True 


if not st.session_state.authenticated:
    
    hide_elements_style = """
        <style>
            [data-testid="stSidebar"] {display: none;}
            [data-testid="stHeader"] {display: none;}
            [data-testid="stToolbar"] {display: none;}
            .main {padding-top: 2rem;}
        </style>
    """
    st.markdown(hide_elements_style, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        logo_path = os.path.join("assets", "NOVABRASIL_TH+_LOGOS_VETORIAIS-07.png")
        if os.path.exists(logo_path):
            st.image(logo_path, width=200)
        
        st.markdown("#### 🔒 Acesso Restrito")
        
        with st.form(key="login_form"):
            password = st.text_input(
                "Por favor, insira a senha para acessar o dashboard:", 
                type="password",
                key="password_input"
            )
            
            submitted = st.form_submit_button("Entrar")

        if submitted:
            if password.strip().lower() == "omelete":
                st.session_state.authenticated = True
                cookies["auth_token"] = "user_is_logged_in"
                cookies.save() 
                st.rerun() 
            else:
                st.error("Senha incorreta. Tente novamente.")
                st.session_state.authenticated = False
    
    st.stop()

# =============================================================
# === O APP PRINCIPAL RODA A PARTIR DAQUI SÓ SE AUTENTICADO ===
# =============================================================

def set_favicon(icon_path):
    try:
        if not os.path.exists(icon_path):
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

def local_css(file_name):
    if os.path.exists(file_name):
        with open(file_name, encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    else:
        st.warning(f"Arquivo de estilo não encontrado: {file_name}")

local_css("utils/style.css")

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
/* Estilo geral para o Pop-up */
[data-testid="stDialog"] [data-testid="stMarkdownContainer"] p {
    font-size: 1rem !important;
    color: #333 !important; 
}
[data-testid="stDialog"] label {
    font-size: 1.1rem !important;
    font-weight: 600 !important;
    color: #003366 !important;
}

/* ---------------------------------------------------- */
/* --- AJUSTES NO MODAL (POP-UP) --- */

/* Botão "Entendido": Estilo Secundário (Limpar Filtros) e Alinhamento */

/* Sobrescreve a cor do texto para ser azul nos botões secundários dentro do modal
   para garantir que siga o estilo do 'Limpar Filtros' (que usa type="secondary") */
[data-testid="stDialog"] button[kind="secondary"] {
    /* Mantém o estilo secundário (borda azul, fundo branco) */
    background-color: #ffffff !important;
    color: var(--azul-nb) !important; /* Texto Azul como em filters.py */
    border: 1.5px solid var(--azul-nb) !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    
    /* Reduz o padding para deixá-lo menor */
    padding: 8px 15px !important; 
    font-size: 1rem !important;
    height: auto !important;
    min-height: 40px !important;
    width: auto !important;
}
[data-testid="stDialog"] button[kind="secondary"]:hover {
    /* Efeito de hover de filters.py */
    background-color: #f0f8ff !important;
    color: #004b8d !important;
    border-color: #004b8d !important;
    transform: none; /* Remove a escala para não atrapalhar o layout */
}


/* 12. Substituir o círculo vermelho do X e a cor da borda do st.dialog */
[data-testid="stDialog"] [aria-label="Close"] svg {
    fill: #000 !important; /* Cor do X (Preto) */
    stroke: #000 !important;
}
[data-testid="stDialog"] [aria-label="Close"] {
    border: none !important;
    box-shadow: none !important;
    background-color: transparent !important;
}

/* Classes utilitárias para o título do Pop-up */
.popup-title-styled {
    color: #004a99; /* Azul Escuro NovaBrasil */
    text-align: center;
    font-size: 1.8rem;
    font-weight: bold;
    margin-bottom: 0.5rem;
}
.popup-subtitle {
    text-align: center;
    color: #444; /* Cinza escuro */
    margin-bottom: 1.5rem;
    font-size: 1.1rem;
}
.popup-item {
    font-size: 1rem !important;
}
/* ---------------------------------------------------- */


/* --- INÍCIO DA ALTERAÇÃO (Cor do st.toggle) --- */
/* Cor do toggle (desligado) */
[data-testid="stToggle"] [data-baseweb="checkbox"] > div {
    background-color: #ccc !important;
    border-color: #aaa !important;
}
/* Cor do toggle (ligado) */
[data-testid="stToggle"] [data-baseweb="checkbox"] input:checked + div {
    background-color: var(--azul-nb) !important;
    border-color: var(--azul-escuro) !important;
}
/* --- FIM DA ALTERAÇÃO --- */

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
logo_path = os.path.join("assets", "NOVABRASIL_TH+_LOGOS_VETORIAIS-07.png")
if os.path.exists(logo_path):
    logo = Image.open(logo_path)
    st.sidebar.image(logo, width='stretch') 

# ==================== CARREGAMENTO DE DADOS (LÓGICA CORRIGIDA) ====================
st.title("Dashboard Vendas Ribeirão Preto")
st.caption("Menu lateral para navegar • Filtros no topo • Exportação em Excel")

df, ultima_atualizacao = load_main_base()

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
            
    st.stop() 


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

query_params = st.query_params
nav_id = query_params.get("nav", ["0"])[0] 
page_keys = list(pages.keys()) 

try:
    pagina_ativa = page_keys[int(nav_id)] 
except (IndexError, ValueError):
    pagina_ativa = page_keys[0] 

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

# ==================== POP-UP DE BOAS-VINDAS (COM COOKIES 24H) ====================

@st.dialog("Banner de Boas-vindas", width="medium")
def modal_boas_vindas():
    
    # Cabeçalho Estilizado
    st.markdown("""
        <div class="popup-title-styled">Dashboard Vendas Ribeirão Preto</div>
        <div class="popup-subtitle">Projeto Data Driven NovaBrasil | Powered by Streamlit</div>
    """, unsafe_allow_html=True)

    # Área Scrollável (Usando Markdown nativo)
    with st.container(height=350, border=True):
        
        st.markdown("""
        ### Como Navegar:
        
        * **Menu Lateral:** Utilize os botões abaixo ou à esquerda na barra lateral para navegar entre as páginas.
        
        * **Filtros Globais:** No topo das páginas, selecione o filtro desejado para sua busca, selecionando entre Período, Emissora, Executivo, Meses, Clientes.
        
        * **Rótulo de dados:** Selecione para escolher a exibição de rótulo de dados nos gráficos.
        
        * **Exportação de dados:** Selecione no final das páginas para escolher quais tabelas ou gráficos deseja exportar para uma planilha de Excel.
        
        ---
        
        ### O que você vai encontrar:
        
        * **Visão Geral:** KPIs rápidos, metas e evolução.
        * **Clientes & Faturamento:** Análise detalhada por cliente/agência.
        * **Perdas & Ganhos:** Monitore Churn (saídas) e Novos Negócios.
        * **Cruzamentos:** Clientes exclusivos vs. compartilhados.
        * **Top 10:** Ranking dos maiores anunciantes.
        * **Crowley ABC:** Vindo em breve.

        ---
        """)

        # Contato
        st.markdown("""
        **Dúvidas, suporte ou sugestões:** (31) 9.9274-4574 - Silvia Freitas (CEO NovaBrasil)
        """)

    # Botão "Entendido": Volta ao alinhamento inicial (esquerda)
    st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True) # Espaçamento
    
    # Usando uma coluna única para o botão voltar ao alinhamento padrão (esquerda)
    if st.button("Entendido", type="secondary"): 
        # Salva a hora atual no cookie
        cookies["last_popup_view"] = datetime.now().isoformat()
        cookies.save()
        st.rerun()

# --- LÓGICA 24 HORAS ---
should_show_popup = False
last_view_str = cookies.get("last_popup_view")

if not last_view_str:
    # Nunca viu (ou limpou cache) -> Mostra
    should_show_popup = True
else:
    try:
        last_view = datetime.fromisoformat(last_view_str)
        # Se passou mais de 24 horas (1 dia)
        if datetime.now() - last_view > timedelta(hours=24):
            should_show_popup = True
    except ValueError:
        # Cookie inválido -> Mostra e reseta
        should_show_popup = True

# Mostra apenas se autenticado e se a regra de 24h permitir
if st.session_state.authenticated and should_show_popup:
    modal_boas_vindas()


# ==================== ROTEAMENTO ====================
if pagina_ativa == "Início":
    pages[pagina_ativa].render(df) 
    st.sidebar.info(f"Registros carregados: {len(df):,}".replace(",", "."))
else:
    df_filtrado, anos_sel, emis_sel, exec_sel, cli_sel, mes_ini, mes_fim, show_labels = aplicar_filtros(df, cookies)

    if df_filtrado is None or df_filtrado.empty:
        st.warning("⚠️ Nenhum dado encontrado com os filtros aplicados.")
        st.stop()
    
    st.sidebar.info(f"📊 Registros filtrados: {len(df_filtrado):,}".replace(",", "."))

    if pagina_ativa == "Crowley ABC":
        pages[pagina_ativa].render(df_filtrado)
    else:
        pages[pagina_ativa].render(df_filtrado, mes_ini, mes_fim, show_labels)

# ==================== RODAPÉ GLOBAL ====================
st.markdown("---")
if ultima_atualizacao:
    st.caption(f"📅 Última atualização da base de dados: **{ultima_atualizacao}**")
else:
    st.caption("📅 Última atualização da base de dados: —")

# --- CONTEÚDO CONFIDENCIAL ---
st.caption("Powered by Python | Interface Streamlit | Data Driven Novabrasil | Conteúdo Confidencial. A distribuição a terceiros não autorizados é estritamente proibida.")
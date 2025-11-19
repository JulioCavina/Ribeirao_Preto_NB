import streamlit as st
from PIL import Image
import os
# import time  <-- Removido

def render(df=None):
    # ==================== LÓGICA DE ROTEAMENTO REMOVIDA ====================
    # O 'app.py' agora controla 100% da navegação.
    
    # ==================== CSS DO GRID 2x3 (AJUSTADO PARA LINKS) ====================
    st.markdown("""
        <style>
        ".\assets\inicio\visao_geral.png"
        .nb-container {
            display: flex;
            justify-content: center;
            align-items: center;
            flex-direction: column;
            width: 100%;
            margin-top: 2rem;
        }

        .nb-grid {
            display: grid;
            grid-template-columns: repeat(3, 240px);
            grid-template-rows: repeat(2, 130px);
            gap: 1.5rem;
            justify-content: center;
        }
        
        /* Aumentando a especificidade e forçando o estilo no link <a> */
        .nb-card {
            background-color: #007dc3;
            border: 2px solid white;
            border-radius: 15px;
            
            /* FORÇANDO O ESTILO: COR BRANCA E SEM SUBLINHADO */
            color: white !important;
            text-decoration: none !important; 
            
            font-size: 1rem;
            font-weight: 600;
            height: 120px;
            width: 240px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.15);
            transition: all 0.25s ease-in-out;
            text-align: center;
        }
        
        /* Garantir que o hover também não tenha sublinhado */
        .nb-card:hover {
            background-color: #00a8e0;
            transform: scale(1.05);
            box-shadow: 0 6px 12px rgba(0, 0, 0, 0.25);
            text-decoration: none !important; /* Remove o sublinhado no hover */
        }

        .nb-card:active {
            transform: scale(0.97);
            background-color: #004b8d;
        }

        @media (max-width: 900px) {
            .nb-grid {
                grid-template-columns: repeat(2, 200px);
            }
            .nb-card {
                width: 200px;
                height: 110px;
            }
        }
        </style>
    """, unsafe_allow_html=True)
    

    # ==================== LOGO ====================
    logo_candidates = [
        os.path.join("assets", "NOVABRASIL_TH+_LOGOS_VETORIAIS-07.png"),
        os.path.join("assets", "NOVABRASIL_TH+_LOGOS_VETORIAIS-07.png"),
    ]
    logo_path = next((p for p in logo_candidates if os.path.exists(p)), None)

    if logo_path:
        logo = Image.open(logo_path)
        st.image(logo, width=240)
    else:
        st.warning("⚠️ Logo não encontrada na pasta /assets")

    # ==================== INTRODUÇÃO ====================
    st.markdown("""
    ## Bem-vindo(a)!
    Este painel foi desenvolvido para a equipe da **NovaBrasil** com o objetivo de oferecer uma visão completa sobre o desempenho comercial e de marketing da região de **Ribeirão Preto**.
    """)

    st.markdown("### Acesse diretamente uma das seções:")

    # ==================== BOTÕES HTML CLICÁVEIS (FINAL) ====================
    # CORREÇÃO: Removido o texto de placeholder quebrado
    st.markdown("""
    <div class="nb-container">
      <div class="nb-grid">
        <a href="?nav=1" target="_self" class="nb-card">Visão Geral</a>
        <a href="?nav=2" target="_self" class="nb-card">Clientes & Faturamento</a>
        <a href="?nav=3" target="_self" class="nb-card">Perdas & Ganhos</a>
        <a href="?nav=4" target="_self" class="nb-card">Cruzamentos & Interseções</a>
        <a href="?nav=5" target="_self" class="nb-card">Top 10 Anunciantes</a>
        <a href="?nav=6" target="_self" class="nb-card">Crowley ABC</a>
      </div>
    </div>
    """, unsafe_allow_html=True)
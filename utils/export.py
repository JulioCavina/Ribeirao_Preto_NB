# utils/export.py
import io
import pandas as pd
import streamlit as st 
import plotly.io as pio
import zipfile 
import openpyxl 
import os # Importado para manipulação de arquivos no ZIP (write/delete)

# Tenta importar as bibliotecas de imagem
try:
    from openpyxl.drawing.image import Image as OpenpyxlImage # type: ignore
    from PIL import Image as PillowImage # type: ignore
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


def create_zip_package(tables_to_export: dict) -> bytes:
    """
    Cria um arquivo ZIP in-memory contendo o arquivo XLSX e os gráficos HTML,
    excluindo o XLSX se apenas gráficos forem selecionados.
    
    Returns:
        Bytes do arquivo ZIP.
    """
    
    zip_buffer = io.BytesIO()
    has_real_data = False # Flag para rastrear se alguma tabela foi selecionada
    
    # Lista para rastrear os nomes de arquivos no ZIP que devem ser mantidos
    files_to_keep = []

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        
        # --- A. Geração do Arquivo Excel (.xlsx) ---
        excel_buffer = io.BytesIO()
        engine = 'openpyxl'
        
        try:
            import openpyxl
        except ImportError:
            st.error("A biblioteca 'openpyxl' é necessária para criar o Excel.")
            return b""

        with pd.ExcelWriter(excel_buffer, engine=engine) as writer:
            
            
            for sheet_name, data in tables_to_export.items():
                if data.get('df') is not None and not data['df'].empty:
                    safe_name = sheet_name.replace(":", "").replace("/", "")[:31]
                    data['df'].to_excel(writer, sheet_name=safe_name, index=False)
                    has_real_data = True
            
            # Garante que o ExcelWriter não falhe, mesmo se has_real_data for False
            if not has_real_data:
                info_df = pd.DataFrame({'Info': ['Este arquivo de dados não possui tabelas, pois apenas gráficos foram selecionados para exportação.']})
                info_df.to_excel(writer, sheet_name='Info_Vazio', index=False)
        
        # Define o nome do arquivo Excel no ZIP
        excel_filename = 'Dados_Tabelas.xlsx'
        zf.writestr(excel_filename, excel_buffer.getvalue())

        # --- B. Geração e Adição dos Gráficos HTML ao ZIP ---
        for sheet_name, data in tables_to_export.items():
            fig = data.get('fig')
            
            if fig is not None:
                try:
                    safe_name = sheet_name.replace(":", "").replace("/", "")[:31]
                    html_content = pio.to_html(fig, full_html=True, include_plotlyjs='cdn')
                    
                    file_name = f"{safe_name}_Grafico.html"
                    zf.writestr(file_name, html_content)
                    files_to_keep.append(file_name) # Adiciona o HTML para manter
                
                except Exception as e:
                    st.error(f"Falha ao gerar o HTML para '{sheet_name}'. Gráfico não incluído no pacote. Erro: {e}")
        
        # --- C. CORREÇÃO FINAL: Exclusão Condicional do Excel ---
        # A biblioteca zipfile não tem um método "remove" nativo para arquivos IN-MEMORY.
        # A forma mais robusta de remover um arquivo IN-MEMORY é recriar o ZIP 
        # *sem* o arquivo ou manipular o buffer.
        
    # --- Solução alternativa: Recriar o ZIP sem o XLSX se has_real_data for False ---
    zip_buffer.seek(0)
    if not has_real_data:
        
        temp_zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'r') as zip_read:
            with zipfile.ZipFile(temp_zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_write:
                
                for item in zip_read.infolist():
                    # Ignora o arquivo Excel e qualquer arquivo "Info_Vazio"
                    if not item.filename.startswith('Dados_Tabelas.xlsx'):
                        zip_write.writestr(item, zip_read.read(item))
        
        temp_zip_buffer.seek(0)
        return temp_zip_buffer.getvalue()


    zip_buffer.seek(0)
    return zip_buffer.getvalue()
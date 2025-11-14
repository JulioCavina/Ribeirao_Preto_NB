# utils/export.py
import io
import pandas as pd
import streamlit as st # Importa o st para st.warning

# Tenta importar as bibliotecas de imagem
try:
    from openpyxl.drawing.image import Image as OpenpyxlImage # type: ignore
    from PIL import Image as PillowImage # type: ignore
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


def create_excel_bytes(tables_to_export: dict) -> bytes:
    """
    Cria um arquivo Excel in-memory.
    
    Args:
        tables_to_export: Dicionário no formato:
        {'Nome da Aba': 
            {
                'df': pd.DataFrame (opcional),
                'img': bytes (opcional)
            }
        }
    
    Returns:
        Bytes do arquivo Excel.
    """
    output = io.BytesIO()
    
    # Openpyxl é necessário para inserir imagens
    engine = 'openpyxl'
    try:
        import openpyxl
    except ImportError:
        st.error("A biblioteca 'openpyxl' é necessária para exportar com imagens.")
        return b""

    with pd.ExcelWriter(output, engine=engine) as writer:
        
        for sheet_name, data in tables_to_export.items():
            
            # Limpa o nome da aba (Excel tem limite de 31 chars)
            safe_name = sheet_name.replace(":", "").replace("/", "")[:31]
            
            df = data.get('df')
            img_bytes = data.get('img')

            # Se tiver um DataFrame, escreve-o
            if df is not None and not df.empty:
                df.to_excel(writer, sheet_name=safe_name, index=False)
            
            # Se tiver uma imagem, a insere
            if img_bytes and PIL_AVAILABLE:
                # Se o DF também foi escrito, o gráfico vai para a próxima linha
                # Se não, ele começa no topo
                img_anchor = 'A1'
                if df is not None and not df.empty:
                    img_anchor = f'A{len(df) + 3}' # 1 (header) + len(df) + 1 (buffer)
                
                # Obtém a "folha" (worksheet)
                if safe_name not in writer.sheets:
                    # Se for só imagem, cria a aba
                    writer.book.create_sheet(safe_name)
                
                ws = writer.sheets[safe_name]
                
                # Converte bytes para o objeto de imagem do openpyxl
                img_buffer = io.BytesIO(img_bytes)
                img = OpenpyxlImage(img_buffer)
                ws.add_image(img, img_anchor)
            
            elif img_bytes and not PIL_AVAILABLE:
                st.warning("Pillow não está instalado. Não foi possível adicionar o gráfico ao Excel.")

    output.seek(0)
    return output.getvalue()
"""
Configuración para el proyecto SEN - Manejo de diferencias entre local y deploy
"""
import os
import streamlit as st

def is_deployed():
    """Detectar si estamos en un entorno de deploy"""
    return (
        os.environ.get('STREAMLIT_CLOUD', False) or 
        os.environ.get('HEROKU', False) or
        os.environ.get('RAILWAY', False) or
        'streamlit.io' in os.environ.get('HOSTNAME', '')
    )

def get_data_config():
    """Configuración específica para manejo de datos"""
    config = {
        'use_arrow_backend': False,  # Desactivar Arrow para mejor compatibilidad
        'numeric_precision': 'float64',
        'na_representation': None,
        'string_na_replacement': 'N/D'
    }
    
    if is_deployed():
        # Configuración específica para deploy
        config.update({
            'use_arrow_backend': False,
            'memory_efficient': True,
            'cache_ttl': 3600  # 1 hora
        })
    else:
        # Configuración específica para local
        config.update({
            'use_arrow_backend': False,
            'memory_efficient': False,
            'cache_ttl': 300  # 5 minutos
        })
    
    return config

def configure_streamlit():
    """Configurar Streamlit para mejor compatibilidad"""
    if is_deployed():
        # Configuración para deploy
        st.set_page_config(
            page_title="SEN - Análisis Eléctrico",
            page_icon="⚡",
            layout="wide",
            initial_sidebar_state="expanded"
        )
    else:
        # Configuración para local
        st.set_page_config(
            page_title="SEN - Análisis Eléctrico (Local)",
            page_icon="⚡",
            layout="wide",
            initial_sidebar_state="expanded"
        )

def get_pandas_config():
    """Configuración de pandas para mejor compatibilidad"""
    import pandas as pd
    
    config = {
        'mode.copy_on_write': True,
        'future.no_silent_downcasting': True
    }
    
    for key, value in config.items():
        try:
            pd.set_option(key, value)
        except:
            pass  # Ignorar opciones no disponibles en versiones antiguas

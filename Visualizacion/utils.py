import os
import json
import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime, date
import altair as alt

# Importar configuración
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
try:
    from config import get_data_config
except ImportError:
    # Fallback si no se puede importar
    def get_data_config():
        return {
            'use_arrow_backend': False,
            'numeric_precision': 'float64',
            'na_representation': None,
            'string_na_replacement': 'N/D'
        }

def cargar_datos():
    base_dir = os.path.dirname(__file__)
    ruta = os.path.join(base_dir, os.pardir, "data", "processed", "datos_electricos_organizados.json")
    with open(ruta, "r", encoding="utf-8") as f:
        raw = json.load(f)
    entradas = []
    for anio in raw:
        for mes in raw[anio]:
            for rec in raw[anio][mes]:                
                dt = datetime.fromisoformat(rec["fecha"])
                enlace = rec.get("enlace", "")
                entradas.append({"fecha": dt, "datos": rec["datos"], "enlace": enlace})
    return eliminar_dias_repetidos(entradas)

# Función para eliminar días repetidos
def eliminar_dias_repetidos(entradas):
    vistos = set()
    unicas = []
    for e in entradas:
        d = e["fecha"].date()
        if d not in vistos:
            vistos.add(d)
            unicas.append(e)
    return unicas

# Función para preparar dataframe básico
def preparar_dataframe_basico(entradas):
    filas = []
    for e in entradas:
        pred = e["datos"].get("prediccion", {})
        filas.append({
            "fecha": e["fecha"],
            "afectacion": pred.get("afectacion"),
            "disponibilidad": pred.get("disponibilidad"),
            "demanda": pred.get("demanda_maxima"),
            "deficit": pred.get("deficit"),
            "respaldo": pred.get("respaldo")
        })
    
    df = pd.DataFrame(filas).set_index("fecha").sort_index()
    
    # Asegurar tipos de datos consistentes
    if not df.empty:
        df = df.replace({pd.NA: None, np.nan: None, float('nan'): None})
        columnas_numericas = ['afectacion', 'disponibilidad', 'demanda', 'deficit', 'respaldo']
        for col in columnas_numericas:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
    
    return df

# Función para filtrar y preparar datos para análisis específicos
def filtrar_datos_por_metrica(entradas, metrica="deficit"):
    filas = []
    for e in entradas:
        # Extraer datos únicamente de la sección "prediccion" del JSON
        pred = e["datos"].get("prediccion", {})
        
        # Obtener el valor específico de la métrica
        valor_metrica = pred.get(metrica)
        
        # Si no hay datos de la métrica solicitada, omitir el registro
        if valor_metrica is None:
            continue
            
        # Datos básicos que siempre incluimos
        datos_basicos = {
            "fecha": e["fecha"],
            "demanda": pred.get("demanda_maxima"),
            "enlace": e.get("enlace", "")
        }
        
        # Agregar la métrica solicitada y cualquier dato relacionado
        if metrica == "deficit":
            # Cálculo de porcentaje de déficit
            porcentaje = None
            demanda = pred.get("demanda_maxima")
            if valor_metrica is not None and demanda is not None and demanda > 0:
                porcentaje = (valor_metrica / demanda) * 100
                  # Procesar plantas en avería para análisis de déficit
            plantas_averia = e["datos"].get("plantas", {}).get("averia", [])
            plantas_estandarizadas = set()
            try:
                from .plant_standardizer import get_canonical_plant_name
            except ImportError:
                try:
                    from plant_standardizer import get_canonical_plant_name
                except ImportError:
                    def get_canonical_plant_name(nombre):
                        return nombre
            
            for p in plantas_averia:
                planta_nombre = p.get("planta")
                if planta_nombre:
                    nombre_canonico = get_canonical_plant_name(planta_nombre)
                    if nombre_canonico:  # Solo añadir si es un nombre válido
                        plantas_estandarizadas.add(nombre_canonico)
            
            # Extender datos con información específica de déficit
            datos_metrica = {
                "deficit": valor_metrica,
                "porcentaje_deficit": porcentaje,
                "disponibilidad": pred.get("disponibilidad"),
                "afectacion": pred.get("afectacion"),
                "respaldo": pred.get("respaldo"),
                "dia_semana": e["fecha"].strftime('%A'),
                "mes": e["fecha"].strftime('%B'),
                "año": e["fecha"].year,
                "plantas_averia": list(plantas_estandarizadas)
            }
        elif metrica == "disponibilidad":
            # Datos específicos para análisis de disponibilidad
            datos_metrica = {
                "disponibilidad": valor_metrica,
                "afectacion": pred.get("afectacion"),
                "deficit": pred.get("deficit"),
                "respaldo": pred.get("respaldo"),
                "dia_semana": e["fecha"].strftime('%A'),
                "mes": e["fecha"].strftime('%B'),
                "año": e["fecha"].year,
            }
        else:
            # Para cualquier otra métrica, simplemente incluimos su valor
            datos_metrica = {metrica: valor_metrica}
        
        # Combinar datos básicos con datos específicos de la métrica
        datos_completos = {**datos_basicos, **datos_metrica}
        filas.append(datos_completos)
      # Crear DataFrame y establecer fecha como índice
    df = pd.DataFrame(filas)
    if not df.empty:
        df = df.set_index("fecha").sort_index()
        
        # Reemplazar todos los tipos de NaN con None para mejor compatibilidad
        df = df.replace({pd.NA: None, np.nan: None, float('nan'): None})
          # Convertir columnas numéricas a float64 de forma explícita
        columnas_numericas = ['demanda', 'deficit', 'disponibilidad', 'afectacion', 'respaldo', 'porcentaje_deficit']
        for col in columnas_numericas:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').astype('float64')
        
        # Agregar columnas de tendencia usando ventanas móviles si existe la métrica
        if metrica in df.columns:
            df[f'{metrica}_7d_avg'] = df[metrica].rolling(window=7, min_periods=1).mean()
            df[f'{metrica}_30d_avg'] = df[metrica].rolling(window=30, min_periods=1).mean()
    
    return df

# Preparar datos para energía solar
try:
    from .plant_standardizer import get_canonical_plant_name
except ImportError:
    # Fallback para importación directa
    try:
        from plant_standardizer import get_canonical_plant_name
    except ImportError:
        # Si no se puede importar, usar función dummy
        def get_canonical_plant_name(nombre):
            return nombre

# Obtener lista de plantas
def obtener_plantas(entradas):
    plantas = set()
    for e in entradas:
        pls = e["datos"].get("plantas", {})
        for clave in ("averia", "mantenimiento"):
            for p in pls.get(clave, []):
                nombre = p.get("planta")
                if nombre:
                    # Estandarizar el nombre de la planta
                    nombre_canonico = get_canonical_plant_name(nombre)
                    # Solo añadir nombres válidos (no None)
                    if nombre_canonico is not None:
                        plantas.add(nombre_canonico)
    return sorted(plantas)

# Función para obtener datos de estado de plantas
def datos_estado_plantas(entradas):
    filas = []
    for e in entradas:
        pls = e["datos"].get("plantas", {})
        fecha = e["fecha"]
          # Plantas en avería
        for p in pls.get("averia", []):
            nombre = p.get("planta")
            if nombre:
                # Estandarizar el nombre de la planta
                nombre_canonico = get_canonical_plant_name(nombre)
                # Solo añadir nombres válidos (no None)
                if nombre_canonico is not None:
                    filas.append({
                        "fecha": fecha,
                        "planta": nombre_canonico,
                        "estado": "Avería"
                    })
          # Plantas en mantenimiento
        for p in pls.get("mantenimiento", []):
            nombre = p.get("planta")
            if nombre:
                # Estandarizar el nombre de la planta
                nombre_canonico = get_canonical_plant_name(nombre)
                # Solo añadir nombres válidos (no None)
                if nombre_canonico is not None:
                    filas.append({
                        "fecha": fecha,
                        "planta": nombre_canonico,
                        "estado": "Mantenimiento"
                    })
    
    return pd.DataFrame(filas)

# Función para extraer métricas clave
def obtener_metricas_clave(entradas):
    ultimo_registro = max(entradas, key=lambda x: x["fecha"])
    datos = ultimo_registro["datos"]
    pred = datos.get("prediccion", {})
    
    return {
        "fecha": ultimo_registro["fecha"],
        "afectacion": pred.get("afectacion"),
        "disponibilidad": pred.get("disponibilidad"),
        "demanda_maxima": pred.get("demanda_maxima"),
        "deficit": pred.get("deficit"),
        "respaldo": pred.get("respaldo")
    }

# Función para crear gráficos interactivos con altair
def crear_grafico_temporal(df, y_column, color_column=None, title=None):
    if color_column:
        chart = alt.Chart(df.reset_index()).mark_line().encode(
            x=alt.X('fecha:T', title='Fecha'),
            y=alt.Y(f'{y_column}:Q', title=y_column.capitalize()),
            color=alt.Color(f'{color_column}:N'),
            tooltip=['fecha:T', f'{y_column}:Q', f'{color_column}:N']
        ).interactive()
    else:
        chart = alt.Chart(df.reset_index()).mark_line().encode(
            x=alt.X('fecha:T', title='Fecha'),
            y=alt.Y(f'{y_column}:Q', title=y_column.capitalize()),
            tooltip=['fecha:T', f'{y_column}:Q']
        ).interactive()
    
    if title:
        chart = chart.properties(title=title)
        
    return chart

# Función para crear gráficos de heatmap
def crear_heatmap(df, x_column, y_column, color_column, title=None):
    chart = alt.Chart(df).mark_rect().encode(
        x=alt.X(f'{x_column}:O', title=x_column.capitalize()),
        y=alt.Y(f'{y_column}:O', title=y_column.capitalize()),
        color=alt.Color(f'{color_column}:Q', scale=alt.Scale(scheme='viridis')),
        tooltip=[f'{x_column}:O', f'{y_column}:O', f'{color_column}:Q']
    ).interactive()
    
    if title:
        chart = chart.properties(title=title)
        
    return chart

# Función para mostrar KPIs
def mostrar_kpis(metricas):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Afectación", 
            f"{metricas['afectacion']} MW" if metricas['afectacion'] is not None else "N/A",
            delta=None
        )
        
    with col2:
        st.metric(
            "Disponibilidad", 
            f"{metricas['disponibilidad']} MW" if metricas['disponibilidad'] is not None else "N/A",
            delta=None
        )
        
    with col3:
        st.metric(
            "Déficit", 
            f"{metricas['deficit']} MW" if metricas['deficit'] is not None else "N/A",
            delta=None
        )

# Función para analizar tendencias
def analizar_tendencia(df, columna):
    if df.empty or columna not in df.columns:
        return "No hay datos suficientes para analizar tendencias"
    
    # Eliminar valores nulos
    serie = df[columna].dropna()
    
    if len(serie) < 2:
        return "No hay datos suficientes para analizar tendencias"
    
    # Calcular cambio porcentual y promedio
    cambio_abs = serie.iloc[-1] - serie.iloc[0]
    cambio_porc = (cambio_abs / serie.iloc[0]) * 100 if serie.iloc[0] != 0 else float('inf')
    promedio = serie.mean()
    
    # Determinar dirección de tendencia
    if cambio_abs > 0:
        direccion = "ascendente"
    elif cambio_abs < 0:
        direccion = "descendente"
    else:
        direccion = "estable"
    
    # Verificar volatilidad
    std_dev = serie.std()
    coef_var = (std_dev / promedio) * 100 if promedio != 0 else float('inf')
    
    if coef_var < 10:
        volatilidad = "baja"
    elif coef_var < 25:
        volatilidad = "moderada"
    else:
        volatilidad = "alta"
    
    return f"Tendencia {direccion} con volatilidad {volatilidad}. Cambio de {cambio_abs:.2f} MW ({cambio_porc:.1f}%) en el período analizado."

# Función para crear paletas de colores personalizadas
def get_color_palette(n_colors=3, palette_type="sequential"):
    if palette_type == "sequential":
        return alt.Scale(scheme='blues')
    elif palette_type == "diverging":
        return alt.Scale(scheme='redblue')
    else:  # categorical
        return alt.Scale(scheme='category10')

# Función para preparar datos para análisis de plantas en relación al déficit
def preparar_datos_plantas_deficit(df):
    if 'plantas_averia' not in df.columns:
        return None
    
    # Crear DataFrame para análisis de frecuencia
    filas_plantas = []
    for fecha, row in df.iterrows():
        plantas = row.get('plantas_averia', [])
        if not plantas or not isinstance(plantas, list):
            continue
        for planta in plantas:
            filas_plantas.append({
                "fecha": fecha,
                "planta": planta,
                "deficit": row.get('deficit')  # Guardar el déficit para análisis por planta
            })
    
    if not filas_plantas:
        return None
    
    df_plantas = pd.DataFrame(filas_plantas)
    return df_plantas

# Función para preparar datos para análisis de plantas en relación a la disponibilidad
def preparar_datos_plantas_disponibilidad(df):
    """
    Prepara datos de plantas específicamente para análisis de disponibilidad.
    En lugar de plantas en avería, analiza plantas operativas (disponibles).
    """
    if df.empty:
        return None
    
    # Para disponibilidad, necesitamos una lógica diferente
    # Por ahora, creamos un DataFrame básico que permita el análisis
    # En el futuro se puede expandir para incluir específicamente plantas operativas
    
    # Crear DataFrame con fechas y disponibilidad para análisis básico
    df_disponibilidad = df[['disponibilidad']].copy()
    df_disponibilidad = df_disponibilidad.dropna()
    
    # Agregar información contextual
    df_disponibilidad['fecha'] = df_disponibilidad.index
    df_disponibilidad['mes'] = df_disponibilidad.index.month
    df_disponibilidad['año'] = df_disponibilidad.index.year
    df_disponibilidad['dia_semana'] = df_disponibilidad.index.strftime('%A')
    
    return df_disponibilidad

# Función para analizar distribución temporal de cualquier métrica
def analizar_distribucion_temporal(df, metrica):
    if metrica not in df.columns or df.empty:
        return None, None
    
    # Filtrar datos no nulos para análisis
    df_analisis = df.dropna(subset=[metrica]).copy()
    
    if df_analisis.empty:
        return None, None
    
    # Mapping para traducir los nombres de los meses
    meses = {
        'January': 'Enero',
        'February': 'Febrero',
        'March': 'Marzo',
        'April': 'Abril',
        'May': 'Mayo',
        'June': 'Junio',
        'July': 'Julio',
        'August': 'Agosto',
        'September': 'Septiembre',
        'October': 'Octubre',
        'November': 'Noviembre',
        'December': 'Diciembre'
    }
    
    # Crear columna de mes numérico y nombre
    df_analisis.loc[:, "mes_num"] = df_analisis.index.month
    df_analisis.loc[:, "mes_nombre"] = df_analisis.index.strftime('%B').map(meses)
    
    # Calcular métrica promedio por mes
    metrica_por_mes = df_analisis.groupby('mes_num').agg({
        metrica: ['mean', 'count']  # Media y conteo de registros por mes
    })
    
    # Aplanar MultiIndex
    metrica_por_mes.columns = [f'{metrica}_promedio', 'conteo']
    metrica_por_mes = metrica_por_mes.reset_index()
    
    # Crear nombres de meses y añadir a dataframe
    meses_orden = list(range(1, 13))
    metrica_por_mes['mes_nombre'] = metrica_por_mes['mes_num'].apply(
        lambda m: meses[datetime(2022, m, 1).strftime('%B')]
    )
    
    # Análisis de tendencia por año-mes
    df_analisis.loc[:, "año_mes"] = df_analisis.index.strftime('%Y-%m')
    
    # Calcular promedio y conteo por año-mes
    metrica_por_año_mes = df_analisis.groupby('año_mes').agg({
        metrica: ['mean', 'count', 'max']  # Media, conteo y máximo
    }).reset_index()
    
    # Aplanar columnas
    metrica_por_año_mes.columns = ['año_mes', f'{metrica}_promedio', 'conteo', f'{metrica}_max']
    
    # Convertir a formato de fecha
    metrica_por_año_mes['año_mes'] = pd.to_datetime(metrica_por_año_mes['año_mes'] + '-01')
    
    # Ordenar cronológicamente
    metrica_por_año_mes = metrica_por_año_mes.sort_values('año_mes')
    
    return metrica_por_mes, metrica_por_año_mes

# Función para crear gráfico temporal con plotly
def crear_grafico_linea_plotly(df, x_column, y_column, title=None, color=None, show_markers=False):
    import plotly.express as px
    import plotly.graph_objects as go
    
    # Crear una copia del DataFrame para evitar modificar el original
    df_clean = df.copy()
    
    # Limpiar datos - eliminar filas donde y_column es None o NaN
    df_clean = df_clean.dropna(subset=[y_column])
    
    # Asegurar que la columna y es numérica
    df_clean[y_column] = pd.to_numeric(df_clean[y_column], errors='coerce')
    df_clean = df_clean.dropna(subset=[y_column])
    
    if df_clean.empty:
        # Si no hay datos válidos, crear un gráfico vacío con mensaje
        fig = go.Figure()
        fig.add_annotation(
            x=0.5, y=0.5,
            text="No hay datos válidos para mostrar",
            showarrow=False,
            xref="paper", yref="paper",
            font=dict(size=16)
        )
        fig.update_layout(
            title=title,
            height=400,
            xaxis=dict(showgrid=False, showticklabels=False),
            yaxis=dict(showgrid=False, showticklabels=False)
        )
        return fig
    
    # Determinar el modo (con o sin marcadores)
    mode = 'lines+markers' if show_markers else 'lines'
    
    # Configurar colores
    if color is None:
        color_sequence = ['red'] if y_column == 'deficit' else ['blue']
    else:
        color_sequence = [color]
    
    # Crear el gráfico
    fig = px.line(
        df_clean,
        x=x_column,
        y=y_column,
        markers=show_markers,
        color_discrete_sequence=color_sequence,
        title=title,
    )
    
    # Configurar línea sin puntos si no hay marcadores
    fig.update_traces(
        mode=mode, 
        line=dict(width=2.5),
        connectgaps=False  # No conectar líneas a través de gaps
    )
    
    # Mejorar diseño
    fig.update_layout(
        height=400,
        showlegend=False,
        xaxis=dict(title=x_column.replace('_', ' ').title()),
        yaxis=dict(title=y_column.replace('_', ' ').title())
    )
    
    return fig

def debug_datos(df, nombre_dataset="Dataset"):
    """Función para debuggear problemas con los datos"""
    import streamlit as st
    
    if df.empty:
        st.error(f"{nombre_dataset}: DataFrame está vacío")
        return
    
    st.write(f"**{nombre_dataset} - Información de debug:**")
    st.write(f"- Forma: {df.shape}")
    st.write(f"- Tipos de datos:")
    
    for col in df.columns:
        dtype = df[col].dtype
        nulos = df[col].isnull().sum()
        valores_unicos = df[col].nunique()
        st.write(f"  - {col}: {dtype}, {nulos} nulos, {valores_unicos} valores únicos")
        
        # Mostrar algunos valores de ejemplo
        valores_ejemplo = df[col].dropna().head(3).tolist()
        st.write(f"    Ejemplos: {valores_ejemplo}")
    
    # Verificar problemas comunes
    problemas = []
    for col in df.select_dtypes(include=[object]).columns:
        if col != 'enlace':  # Excluir columna de enlaces
            valores_problematicos = df[col].apply(lambda x: isinstance(x, str) and ('nan' in str(x).lower() or 'none' in str(x).lower())).sum()
            if valores_problematicos > 0:
                problemas.append(f"{col}: {valores_problematicos} valores con 'nan' o 'none' como string")
    
    if problemas:
        st.warning("**Problemas detectados:**")
        for problema in problemas:
            st.write(f"- {problema}")

import os
import json
import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime, date
import altair as alt

# Función para cargar todos los datos
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
    return pd.DataFrame(filas).set_index("fecha").sort_index()

# Función para filtrar y preparar datos para análisis específicos
def filtrar_datos_por_metrica(entradas, metrica="deficit"):
    """
    Filtra y procesa los datos para un tipo específico de análisis (deficit, disponibilidad, etc.)
    
    Args:
        entradas (list): Lista de registros de datos eléctricos
        metrica (str): La métrica a extraer y procesar (deficit, disponibilidad, etc.)
    
    Returns:
        pd.DataFrame: DataFrame con datos procesados para análisis de la métrica solicitada
    """
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
            from .plant_standardizer import get_canonical_plant_name
            
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
        
        # Reemplazar NaN con None para mejor manejo en las visualizaciones
        df = df.replace({pd.NA: None})
        
        # Agregar columnas de tendencia usando ventanas móviles si existe la métrica
        if metrica in df.columns:
            df[f'{metrica}_7d_avg'] = df[metrica].rolling(window=7, min_periods=1).mean()
            df[f'{metrica}_30d_avg'] = df[metrica].rolling(window=30, min_periods=1).mean()
    
    return df

# Preparar datos para energía solar
def preparar_datos_solares(entradas):
    filas = []
    for e in entradas:
        d = e["fecha"]
        sol = e["datos"].get("paneles_solares", {})
        filas.append({
            "fecha": d, 
            "produccion_mwh": sol.get("produccion_mwh"),
            "parques": sol.get("cantidad_parques"),
            "capacidad_instalada": sol.get("capacidad_instalada")
        })
    return pd.DataFrame(filas).set_index("fecha").sort_index()

# Importar el estandarizador de nombres de plantas
from .plant_standardizer import get_canonical_plant_name

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
    """Analiza la tendencia de una columna de datos y devuelve un resumen"""
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
    """
    Prepara datos para análisis de relación entre plantas en avería y déficit energético
    
    Args:
        df (pd.DataFrame): DataFrame con datos de déficit que incluye la columna 'plantas_averia'
    
    Returns:
        pd.DataFrame: DataFrame con datos de plantas y su relación con el déficit,
                    o None si no hay datos suficientes
    """
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

# Función para analizar distribución temporal de cualquier métrica
def analizar_distribucion_temporal(df, metrica):
    """
    Analiza la distribución temporal de una métrica (déficit, disponibilidad, etc.)
    
    Args:
        df (pd.DataFrame): DataFrame con los datos a analizar
        metrica (str): Nombre de la columna con la métrica a analizar
        
    Returns:
        tuple: Tuplas de DataFrames con análisis (metrica_por_mes, metrica_por_año_mes)
    """
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
    """
    Crea un gráfico de línea usando plotly
    
    Args:
        df (pd.DataFrame): DataFrame con los datos
        x_column (str): Columna para el eje X
        y_column (str): Columna para el eje Y
        title (str): Título del gráfico
        color (str): Color de la línea
        show_markers (bool): Si se muestran o no los marcadores
        
    Returns:
        plotly.graph_objects.Figure: Figura de plotly
    """
    import plotly.express as px
    
    # Determinar el modo (con o sin marcadores)
    mode = 'lines+markers' if show_markers else 'lines'
    
    # Configurar colores
    if color is None:
        color_sequence = ['red'] if y_column == 'deficit' else ['blue']
    else:
        color_sequence = [color]
    
    # Crear el gráfico
    fig = px.line(
        df,
        x=x_column,
        y=y_column,
        markers=show_markers,
        color_discrete_sequence=color_sequence,
        title=title,
    )
    
    # Configurar línea sin puntos si no hay marcadores
    fig.update_traces(
        mode=mode, 
        line=dict(width=2.5)
    )
    
    # Mejorar diseño
    fig.update_layout(
        height=400
    )
    
    return fig

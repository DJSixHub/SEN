import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
try:
    from .utils import (
        cargar_datos,
        filtrar_datos_por_metrica,
        preparar_datos_plantas_disponibilidad,
        analizar_distribucion_temporal,
        crear_grafico_linea_plotly,
        obtener_plantas
    )
except ImportError:
    from utils import (
        cargar_datos,
        filtrar_datos_por_metrica,
        preparar_datos_plantas_disponibilidad,
        analizar_distribucion_temporal,
        crear_grafico_linea_plotly,
        obtener_plantas
    )

def preparar_dataframe_disponibilidad(entradas):
    return filtrar_datos_por_metrica(entradas, "disponibilidad")

def preparar_datos_solares(entradas):
    """Preparar datos específicos de paneles solares"""
    filas_gen = []
    filas_cnt = []
    for e in entradas:
        d = e["fecha"]
        sol = e["datos"].get("paneles_solares", {})
        filas_gen.append({"fecha": d, "produccion_mwh": sol.get("produccion_mwh", 0)})
        filas_cnt.append({"fecha": d, "parques": sol.get("cantidad_parques", 0)})
    
    df_gen = pd.DataFrame(filas_gen).set_index("fecha").sort_index()
    df_cnt = pd.DataFrame(filas_cnt).set_index("fecha").sort_index()
    return df_gen, df_cnt

def mostrar_indicadores_disponibilidad(df):
    st.subheader("Indicadores Estadísticos del Período")
    
    # Filtrar valores no nulos para cálculos
    df_disponibilidad_no_nulo = df[df["disponibilidad"].notnull()]
    
    if df_disponibilidad_no_nulo.empty:
        st.error("No hay datos suficientes para calcular indicadores de disponibilidad.")
        return
    
    # Calcular métricas para el período seleccionado solo con datos válidos
    disponibilidad_promedio = df_disponibilidad_no_nulo["disponibilidad"].mean()
    disponibilidad_mediana = df_disponibilidad_no_nulo["disponibilidad"].median()
    disponibilidad_maxima = df_disponibilidad_no_nulo["disponibilidad"].max()
    disponibilidad_minima = df_disponibilidad_no_nulo["disponibilidad"].min()
    desviacion_std = df_disponibilidad_no_nulo["disponibilidad"].std()
    
    # Obtener fechas de valores máximos y mínimos
    fecha_max = None
    if not pd.isna(disponibilidad_maxima):
        max_indices = df_disponibilidad_no_nulo[df_disponibilidad_no_nulo["disponibilidad"] == disponibilidad_maxima].index
        if not max_indices.empty:
            fecha_max = max_indices[0].strftime("%d/%m/%Y")
    
    fecha_min = None
    if not pd.isna(disponibilidad_minima):
        min_indices = df_disponibilidad_no_nulo[df_disponibilidad_no_nulo["disponibilidad"] == disponibilidad_minima].index
        if not min_indices.empty:
            fecha_min = min_indices[0].strftime("%d/%m/%Y")
    
    # Análisis de cobertura
    df_demanda_no_nulo = df[(df["demanda"].notnull()) & (df["disponibilidad"].notnull())]
    if not df_demanda_no_nulo.empty:
        cobertura_promedio = (df_demanda_no_nulo["disponibilidad"] / df_demanda_no_nulo["demanda"] * 100).mean()
        dias_cobertura_completa = len(df_demanda_no_nulo[df_demanda_no_nulo["disponibilidad"] >= df_demanda_no_nulo["demanda"]])
        porcentaje_cobertura = (dias_cobertura_completa / len(df_demanda_no_nulo) * 100)
    else:
        cobertura_promedio = 0
        dias_cobertura_completa = 0
        porcentaje_cobertura = 0
    
    # Días analizados
    dias_totales = len(df_disponibilidad_no_nulo)
    
    # Mostrar KPIs en columnas
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Disponibilidad Promedio (MW)",
            value=f"{int(disponibilidad_promedio)}" if not pd.isna(disponibilidad_promedio) else "N/D"
        )
        
        st.metric(
            label="Disponibilidad Mediana (MW)",
            value=f"{int(disponibilidad_mediana)}" if not pd.isna(disponibilidad_mediana) else "N/D"
        )
    
    with col2:
        st.metric(
            label=f"Disponibilidad Máxima (MW)",
            value=f"{int(disponibilidad_maxima)}" if not pd.isna(disponibilidad_maxima) else "N/D",
            help=f"Registrada el {fecha_max}" if fecha_max else ""
        )
        
        st.metric(
            label="Disponibilidad Mínima (MW)",
            value=f"{int(disponibilidad_minima)}" if not pd.isna(disponibilidad_minima) else "N/D",
            help=f"Registrada el {fecha_min}" if fecha_min else ""
        )
    
    with col3:
        st.metric(
            label="Desviación Estándar",
            value=f"{int(desviacion_std)}" if not pd.isna(desviacion_std) else "N/D"
        )
        
        st.metric(
            label="Días Analizados",
            value=f"{dias_totales}" if dias_totales > 0 else "N/D"
        )
    
    with col4:
        st.metric(
            label="Cobertura Promedio (%)",
            value=f"{cobertura_promedio:.1f}%" if cobertura_promedio > 0 else "N/D"
        )
        
        st.metric(
            label="Días con Cobertura Completa",
            value=f"{dias_cobertura_completa} ({porcentaje_cobertura:.1f}%)",
            help=f"Días donde la disponibilidad cubrió totalmente la demanda"
        )

def analizar_plantas_disponibilidad(entradas, df):
    st.subheader("Análisis de Plantas Disponibles y su Contribución")
      # Análisis básico de tiempo operativo por planta
    from .plant_standardizer import get_valid_plant_names, get_canonical_plant_name
    
    # Obtener todas las plantas válidas
    plantas_validas = get_valid_plant_names()
    
    # Preparar datos detallados por planta y fecha
    plantas_datos = {}
    plantas_operativas = {}
    
    for entrada in entradas:
        fecha = entrada["fecha"]
        datos = entrada["datos"]
        plantas_data = datos.get("plantas", {})
        pred = datos.get("prediccion", {})
        disponibilidad_total = pred.get("disponibilidad")
        
        # Plantas en avería o mantenimiento
        plantas_no_operativas = set()
        for categoria in ["averia", "mantenimiento"]:
            for planta_info in plantas_data.get(categoria, []):
                planta_nombre = planta_info.get("planta", "")
                if planta_nombre:
                    planta_estandarizada = get_canonical_plant_name(planta_nombre)
                    if planta_estandarizada:
                        plantas_no_operativas.add(planta_estandarizada)
        
        # Procesar cada planta válida
        for planta in plantas_validas:
            if planta not in plantas_operativas:
                plantas_operativas[planta] = 0
                plantas_datos[planta] = []
            
            # Si la planta NO está en avería ni mantenimiento, está disponible
            if planta not in plantas_no_operativas:
                plantas_operativas[planta] += 1
                plantas_datos[planta].append({
                    "fecha": fecha,
                    "disponibilidad_sistema": disponibilidad_total,
                    "estado": "Operativa"
                })
    
    # Crear DataFrame de plantas operativas con métricas
    if plantas_operativas:
        df_operativas = pd.DataFrame([
            {"planta": planta, "días_operativos": dias}
            for planta, dias in plantas_operativas.items()
        ]).sort_values("días_operativos", ascending=False)
        
        # Calcular porcentaje de disponibilidad
        total_dias = len(df)
        df_operativas["porcentaje_disponibilidad"] = (df_operativas["días_operativos"] / total_dias * 100).round(1)
        
        # Calcular frecuencia por planta (similar a avería pero para disponibilidad)
        frecuencia_disponibilidad = df_operativas.set_index("planta")["días_operativos"]
        
        # Selección de planta específica para análisis detallado
        valid_plants = ["Todas las plantas"] + sorted(set(df_operativas["planta"].unique()) & set(get_valid_plant_names()))
        planta_seleccionada = st.selectbox("Seleccionar planta para análisis detallado", valid_plants, key="select_planta_disp")
        
        # Si se seleccionó una planta específica, mostrar análisis detallado
        if planta_seleccionada != "Todas las plantas":
            if planta_seleccionada in plantas_datos and plantas_datos[planta_seleccionada]:
                # Crear DataFrame para la planta seleccionada
                df_planta_data = pd.DataFrame(plantas_datos[planta_seleccionada])
                df_planta_data = df_planta_data.set_index("fecha").sort_index()
                
                # Combinar con datos de disponibilidad del sistema
                df_planta_merged = df_planta_data.join(df[["disponibilidad"]], how="inner")
                df_planta_merged = df_planta_merged.dropna(subset=["disponibilidad"])
                
                if not df_planta_merged.empty:
                    # Calcular métricas específicas para esta planta cuando está operativa
                    disponibilidad_promedio_planta = df_planta_merged["disponibilidad"].mean()
                    disponibilidad_maxima_planta = df_planta_merged["disponibilidad"].max()
                    disponibilidad_minima_planta = df_planta_merged["disponibilidad"].min()
                    disponibilidad_mediana_planta = df_planta_merged["disponibilidad"].median()
                    
                    # Agregar fechas de máximo y mínimo
                    fecha_max = df_planta_merged[df_planta_merged["disponibilidad"] == disponibilidad_maxima_planta].index[0]
                    fecha_min = df_planta_merged[df_planta_merged["disponibilidad"] == disponibilidad_minima_planta].index[0]
                    
                    # Mostrar resumen en columnas
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric(
                            label=f"Días operativa",
                            value=len(df_planta_merged),
                            help=f"{len(df_planta_merged)} días sobre {len(df)} analizados"
                        )
                        
                        st.metric(
                            label=f"Disponibilidad promedio del sistema",
                            value=f"{int(disponibilidad_promedio_planta)} MW" if not pd.isna(disponibilidad_promedio_planta) else "N/D",
                            help="Disponibilidad promedio del sistema cuando la planta está operativa"
                        )
                    
                    with col2:
                        st.metric(
                            label=f"Disponibilidad máxima del sistema",
                            value=f"{int(disponibilidad_maxima_planta)} MW" if not pd.isna(disponibilidad_maxima_planta) else "N/D",
                            help=f"Ocurrido el {fecha_max.strftime('%d/%m/%Y')}"
                        )
                        
                        st.metric(
                            label=f"Disponibilidad mínima del sistema",
                            value=f"{int(disponibilidad_minima_planta)} MW" if not pd.isna(disponibilidad_minima_planta) else "N/D",
                            help=f"Ocurrido el {fecha_min.strftime('%d/%m/%Y')}"
                        )
                    
                    with col3:
                        st.metric(
                            label=f"Disponibilidad mediana del sistema",
                            value=f"{int(disponibilidad_mediana_planta)} MW" if not pd.isna(disponibilidad_mediana_planta) else "N/D"
                        )
                        
                        # Porcentaje de tiempo operativa
                        porcentaje_operativa = (len(df_planta_merged) / len(df) * 100)
                        st.metric(
                            label=f"% Tiempo operativa",
                            value=f"{porcentaje_operativa:.1f}%",
                            help="Porcentaje del período total que la planta estuvo operativa"
                        )
                    
                    # Gráfico de línea temporal de disponibilidad del sistema cuando la planta está operativa
                    if len(df_planta_merged) > 1:
                        st.write(f"### Disponibilidad del sistema cuando {planta_seleccionada} está operativa")
                        
                        fig = px.line(
                            df_planta_merged.reset_index(),
                            x="fecha",
                            y="disponibilidad",
                            markers=False,
                            color_discrete_sequence=["blue"],
                            title=f"Disponibilidad del sistema cuando {planta_seleccionada} está operativa",
                            labels={"fecha": "Fecha", "disponibilidad": "Disponibilidad (MW)"}
                        )
                        
                        # Agregar línea de disponibilidad promedio
                        fig.add_hline(
                            y=disponibilidad_promedio_planta,
                            line_dash="dash",
                            line_color="navy",
                            annotation_text=f"Disponibilidad promedio: {int(disponibilidad_promedio_planta)} MW"
                        )
                        
                        fig.update_traces(mode='lines', line=dict(width=2.5))
                        fig.update_layout(height=400)
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Análisis por mes para esta planta
                        st.write(f"### Resumen mensual para {planta_seleccionada}")
                        
                        # Extraer mes y año para agrupación
                        df_planta_merged["año_mes"] = df_planta_merged.index.strftime("%Y-%m")
                        
                        # Agrupar por mes
                        resumen_mensual = df_planta_merged.groupby("año_mes").agg({
                            "disponibilidad": ["mean", "max", "min", "count"]
                        }).reset_index()
                        
                        # Preparar datos para visualización
                        resumen_mensual.columns = ["Mes", "Disponibilidad Promedio", "Disponibilidad Máxima", "Disponibilidad Mínima", "Días Operativa"]
                        
                        # Mostrar como tabla interactiva
                        st.dataframe(resumen_mensual, use_container_width=True)
                    else:
                        st.info(f"Solo hay un registro para {planta_seleccionada}, no es posible mostrar evolución.")
                else:
                    st.warning("No hay datos de disponibilidad del sistema para esta planta.")
            else:
                st.warning(f"No se encontraron períodos operativos para {planta_seleccionada}.")
          # Visualización de frecuencia de disponibilidad por planta
        st.write("### Tiempo operativo por planta")
        
        # Selección del tipo de visualización
        vista_seleccionada = st.radio(
            "Tipo de visualización:",
            ["Tabla de disponibilidad", "Gráfico de barras"],
            key="vista_analisis_plantas_disp"
        )
        
        # Mostrar visualización según selección
        if not df_operativas.empty:
            if vista_seleccionada == "Tabla de disponibilidad":
                st.write("Tiempo operativo por planta:")
                try:
                    # Preparar DataFrame para display con nombres de columnas mejorados
                    nombres_columnas = {
                        "planta": "Planta",
                        "días_operativos": "Días Operativos",
                        "porcentaje_disponibilidad": "% Disponibilidad"
                    }
                    
                    df_display = df_operativas.rename(columns=nombres_columnas)                    # Configurar columnas numéricas con formato
                    column_config = {}
                    for orig_col, new_col in nombres_columnas.items():
                        if orig_col in ["días_operativos", "porcentaje_disponibilidad"]:
                            fmt = "%d" if orig_col == "días_operativos" else "%.1f%%"
                            column_config[new_col] = st.column_config.NumberColumn(
                                new_col,
                                format=fmt,
                                width="medium"
                            )

                    # Mostrar la tabla
                    st.dataframe(
                        df_display,
                        use_container_width=True,
                        hide_index=True,
                        column_config=column_config
                    )
                except Exception as e:
                    st.error(f"Error al mostrar tabla: {str(e)}")
                    # Mostrar tabla simple como fallback
                    st.dataframe(df_operativas)
            else:
                # Preparar datos para gráfico - Top 10 plantas más disponibles
                df_graph = df_operativas.sort_values('días_operativos', ascending=True).tail(10)
                fig = px.bar(
                    df_graph,
                    x='días_operativos',
                    y='planta',
                    title="Top 10 plantas con mayor tiempo operativo",
                    labels={'días_operativos': 'Días operativos', 'planta': 'Planta'},
                    color='días_operativos',
                    color_continuous_scale='Blues',
                    height=400
                )
                fig.update_layout(coloraxis_showscale=False)
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No se pudieron calcular datos de disponibilidad por planta.")

def mostrar_analisis_solar(df_solar_gen, df_solar_cnt, fecha_inicio, fecha_fin):
    """Mostrar análisis específico de energía solar"""
    st.subheader("Análisis de Energía Solar y Parques Fotovoltaicos")
    
    # Filtrar datos solares por el período seleccionado
    inicio_dt = datetime.combine(fecha_inicio, datetime.min.time())
    fin_dt = datetime.combine(fecha_fin, datetime.max.time())
    
    df_gen_filtrado = df_solar_gen[(df_solar_gen.index >= inicio_dt) & (df_solar_gen.index <= fin_dt)]
    df_cnt_filtrado = df_solar_cnt[(df_solar_cnt.index >= inicio_dt) & (df_solar_cnt.index <= fin_dt)]
    
    # Estadísticas de generación solar
    if not df_gen_filtrado.empty:
        # Eliminar valores nulos
        df_gen_clean = df_gen_filtrado.dropna()
        
        if not df_gen_clean.empty:
            produccion_total = df_gen_clean["produccion_mwh"].sum()
            produccion_promedio = df_gen_clean["produccion_mwh"].mean()
            produccion_maxima = df_gen_clean["produccion_mwh"].max()
            produccion_minima = df_gen_clean["produccion_mwh"].min()
            
            # Mostrar métricas solares
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    label="Producción Total (MWh)",
                    value=f"{produccion_total:.1f}"
                )
            
            with col2:
                st.metric(
                    label="Producción Promedio (MWh)",
                    value=f"{produccion_promedio:.1f}"
                )
            
            with col3:
                st.metric(
                    label="Producción Máxima (MWh)",
                    value=f"{produccion_maxima:.1f}"
                )
            
            with col4:
                st.metric(
                    label="Producción Mínima (MWh)",
                    value=f"{produccion_minima:.1f}"
                )
            
            # Gráfico de evolución de la producción solar
            st.write("### Evolución de la Producción Solar")
            
            fig = crear_grafico_linea_plotly(
                df=df_gen_clean,
                x_column=df_gen_clean.index,
                y_column='produccion_mwh',
                title=f"Producción de energía solar ({fecha_inicio} a {fecha_fin})",
                color='blue',
                show_markers=False
            )
            
            # Añadir línea de media
            fig.add_trace(go.Scatter(
                x=[df_gen_clean.index.min(), df_gen_clean.index.max()],
                y=[produccion_promedio, produccion_promedio],
                mode='lines',
                name=f'Media: {produccion_promedio:.1f} MWh',
                line=dict(color='navy', width=1, dash='dash')
            ))
            
            fig.update_layout(
                xaxis_title="Fecha",
                yaxis_title="Producción (MWh)",
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay datos de producción solar disponibles para el período seleccionado.")
    
    # Análisis de cantidad de parques
    if not df_cnt_filtrado.empty:
        df_cnt_clean = df_cnt_filtrado.dropna()
        
        if not df_cnt_clean.empty:
            st.write("### Evolución de Parques Fotovoltaicos Activos")
            
            parques_promedio = df_cnt_clean["parques"].mean()
            parques_maximo = df_cnt_clean["parques"].max()
            
            # Gráfico de barras para parques
            fig = px.bar(
                df_cnt_clean.reset_index(),
                x='fecha',
                y='parques',
                title="Número de parques fotovoltaicos activos",
                color='parques',
                color_continuous_scale='Blues'
            )
            
            # Añadir línea de promedio
            fig.add_hline(
                y=parques_promedio,
                line_dash="dash",
                line_color="navy",
                annotation_text=f"Promedio: {parques_promedio:.1f} parques"
            )
            
            fig.update_layout(
                xaxis_title="Fecha",
                yaxis_title="Número de Parques",
                height=400,
                coloraxis_showscale=False
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Métricas de parques
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Parques Promedio", f"{parques_promedio:.1f}")
            with col2:
                st.metric("Parques Máximo", f"{int(parques_maximo)}")
        else:
            st.info("No hay datos de parques fotovoltaicos para el período seleccionado.")

def mostrar_tabla_datos_detallados(df):
    """
    Muestra una tabla interactiva con los datos detallados de disponibilidad
    Args:
        df (pd.DataFrame): DataFrame con datos de disponibilidad filtrados
    """
    st.subheader("Datos Detallados del Período Seleccionado")
    
    if df.empty:
        st.warning("No hay datos disponibles para el período seleccionado.")
        return
    
    # Opciones de visualización
    col1, col2, col3 = st.columns(3)
    with col1:
        mostrar_alta_disponibilidad = st.checkbox(
            "Mostrar solo alta disponibilidad (>2000 MW)", 
            value=False,
            key="mostrar_alta_disponibilidad"
        )
    
    with col2:
        ordenar_por = st.selectbox(
            "Ordenar por",
            options=["Fecha (↑)", "Fecha (↓)", "Disponibilidad (↑)", "Disponibilidad (↓)"],
            key="ordenar_tabla_disponibilidad"
        )
    
    with col3:
        mostrar_enlaces = st.checkbox(
            "Mostrar enlaces a noticias",
            value=True,
            key="mostrar_enlaces_disp"
        )
    
    # Aplicar filtros adicionales
    df_filtrado = df.copy()
    
    # Manejar valores nulos para evitar problemas de filtrado
    if mostrar_alta_disponibilidad:
        # Filtrar solo registros con disponibilidad alta
        df_filtrado = df_filtrado[(df_filtrado["disponibilidad"].notnull()) & (df_filtrado["disponibilidad"] > 2000)]
    
    if df_filtrado.empty:
        st.warning("No hay registros que cumplan con los criterios de filtrado.")
        return
    
    # Aplicar ordenamiento
    if ordenar_por == "Fecha (↑)":
        df_filtrado = df_filtrado.sort_index(ascending=True)
    elif ordenar_por == "Fecha (↓)":
        df_filtrado = df_filtrado.sort_index(ascending=False)
    elif ordenar_por == "Disponibilidad (↑)":
        df_no_nulos = df_filtrado[df_filtrado["disponibilidad"].notnull()]
        df_nulos = df_filtrado[df_filtrado["disponibilidad"].isnull()]
        df_filtrado = pd.concat([df_no_nulos.sort_values("disponibilidad", ascending=True), df_nulos])
    elif ordenar_por == "Disponibilidad (↓)":
        df_no_nulos = df_filtrado[df_filtrado["disponibilidad"].notnull()]
        df_nulos = df_filtrado[df_filtrado["disponibilidad"].isnull()]
        df_filtrado = pd.concat([df_no_nulos.sort_values("disponibilidad", ascending=False), df_nulos])
    
    # Reindexar para mostrar la fecha como columna
    df_mostrar = df_filtrado.reset_index()
    
    # Formatear la fecha para mejor visualización
    df_mostrar["fecha"] = df_mostrar["fecha"].dt.strftime("%Y-%m-%d")
    
    # Seleccionar columnas a mostrar
    columnas_base = [
        "fecha", "disponibilidad", "demanda", "deficit", "porcentaje_deficit",
        "cant_plantas_averia", "año", "mes", "dia_semana"
    ]
    
    # Añadir enlace si está disponible y seleccionado
    if mostrar_enlaces and "enlace" in df_mostrar.columns:
        columnas_mostrar = columnas_base + ["enlace"]
    else:
        columnas_mostrar = columnas_base
    
    # Filtrar columnas disponibles
    columnas_disponibles = [col for col in columnas_mostrar if col in df_mostrar.columns]
    
    # Cambiar nombres para mejor visualización
    nombres_columnas = {
        "fecha": "Fecha",
        "disponibilidad": "Disponibilidad (MW)",
        "demanda": "Demanda (MW)",
        "deficit": "Déficit (MW)",
        "porcentaje_deficit": "% de Déficit",
        "cant_plantas_averia": "Plantas en Avería",
        "año": "Año",
        "mes": "Mes",
        "dia_semana": "Día",
        "enlace": "Enlace al reporte"
    }
      # Formatear para mejor visualización y manejo de NaN
    df_formato = df_mostrar[columnas_disponibles].copy()
    # Convertir columnas numéricas a float y mantener NaN
    numeric_cols = [c for c in df_formato.columns if pd.api.types.is_numeric_dtype(df_formato[c])]
    for col in numeric_cols:
        df_formato[col] = pd.to_numeric(df_formato[col], errors='coerce')

    # Renombrar columnas ANTES de crear el Styler
    df_formato_renamed = df_formato.rename(columns={c: nombres_columnas.get(c, c) for c in df_formato.columns})
    
    # Crear Styler para formatear NaN como 'N/D'
    fmt_dict = {}
    for orig_col in numeric_cols:
        new_col = nombres_columnas.get(orig_col, orig_col)
        if orig_col != 'porcentaje_deficit':
            fmt_dict[new_col] = (lambda v: f"{v:.0f}" if pd.notna(v) else "N/D")
        else:
            fmt_dict[new_col] = (lambda v: f"{v:.1f}%" if pd.notna(v) else "N/D")
    
    styled_df = df_formato_renamed.style.format(fmt_dict)    # Mostrar la tabla estilizada
    st.dataframe(
        styled_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            nombres_columnas[c]: st.column_config.NumberColumn(
                nombres_columnas[c],
                format="%d" if c!='porcentaje_deficit' else "%.1f%%"
            ) for c in numeric_cols
        }
    )
      # Botón para descargar datos
    # Convertir NaN a string vacío para CSV, pero solo en las columnas, no en el índice
    df_csv = df_mostrar.copy()
    for col in df_csv.columns:
        df_csv[col] = df_csv[col].fillna("")
    csv = df_csv.to_csv(index=True).encode('utf-8')
    
    st.download_button(
        label="Descargar datos como CSV",
        data=csv,
        file_name=f"disponibilidad_energetica_filtrado.csv",
        mime="text/csv",
        key="descargar_csv_disponibilidad"
    )

def app():
    """
    Función principal del módulo de análisis de disponibilidad
    """
    st.header("Análisis Histórico de la Disponibilidad Energética")
    st.markdown("---")
    
    # Cargar datos
    try:
        entradas = cargar_datos()
    except Exception as e:
        st.error(f"Error al cargar datos: {str(e)}")
        return
    
    # Verificar que se cargaron los datos correctamente
    if not entradas:
        st.error("No se pudieron cargar los datos. Verifique la ruta de los archivos.")
        return
    
    # Preparar dataframe específico para análisis de disponibilidad
    try:
        df_completo = preparar_dataframe_disponibilidad(entradas)
        df_solar_gen, df_solar_cnt = preparar_datos_solares(entradas)
    except Exception as e:
        st.error(f"Error al procesar los datos: {str(e)}")
        return
    
    if df_completo.empty:
        st.error("No hay datos disponibles para analizar.")
        return
    
    # Añadir selector de fechas al inicio
    st.write("### Selecciona el rango de fechas a analizar")
    
    try:
        fecha_min_datos = df_completo.index.min().date()
        fecha_max_datos = df_completo.index.max().date()
    except Exception as e:
        st.error(f"Error al determinar el rango de fechas: {str(e)}")
        return

    col1, col2, col3 = st.columns([2, 2, 1])
    
    # Inicializar fechas por defecto
    if 'fecha_inicio_disponibilidad' not in st.session_state:
        st.session_state.fecha_inicio_disponibilidad = fecha_min_datos
    if 'fecha_fin_disponibilidad' not in st.session_state:
        st.session_state.fecha_fin_disponibilidad = fecha_max_datos
    
    with col1:
        fecha_inicio = st.date_input(
            "Fecha de inicio",
            value=st.session_state.fecha_inicio_disponibilidad,
            key="fecha_inicio_disponibilidad_input"
        )
    
    with col2:
        fecha_fin = st.date_input(
            "Fecha de fin",
            value=st.session_state.fecha_fin_disponibilidad,
            key="fecha_fin_disponibilidad_input"
        )
    
    with col3:
        if st.button("Ver todo", key="ver_todo_disponibilidad"):
            st.session_state.fecha_inicio_disponibilidad = fecha_min_datos
            st.session_state.fecha_fin_disponibilidad = fecha_max_datos
            st.rerun()
    
    # Actualizar session state
    st.session_state.fecha_inicio_disponibilidad = fecha_inicio
    st.session_state.fecha_fin_disponibilidad = fecha_fin
    
    # Validaciones
    if fecha_inicio > fecha_fin:
        st.error("❌ La fecha de inicio no puede ser posterior a la fecha de fin.")
        st.stop()
    
    # Verificar que las fechas estén dentro del rango de datos disponibles
    if fecha_inicio < fecha_min_datos or fecha_fin > fecha_max_datos:
        st.warning(f"⚠️ Las fechas seleccionadas están fuera del rango de datos disponibles ({fecha_min_datos.strftime('%d/%m/%Y')} - {fecha_max_datos.strftime('%d/%m/%Y')})")
        
        # Ajustar automáticamente las fechas al rango válido
        fecha_inicio_ajustada = max(fecha_inicio, fecha_min_datos)
        fecha_fin_ajustada = min(fecha_fin, fecha_max_datos)
        
        st.info(f"📅 Ajustando automáticamente al rango: {fecha_inicio_ajustada.strftime('%d/%m/%Y')} - {fecha_fin_ajustada.strftime('%d/%m/%Y')}")
        
        fecha_inicio = fecha_inicio_ajustada
        fecha_fin = fecha_fin_ajustada
    
    # Filtrar dataframe según el rango de fechas seleccionado
    inicio_dt = datetime.combine(fecha_inicio, datetime.min.time())
    fin_dt = datetime.combine(fecha_fin, datetime.max.time())
    
    # Filtrar el dataframe para el rango seleccionado
    df = df_completo[(df_completo.index >= inicio_dt) & (df_completo.index <= fin_dt)].copy()
    
    if df.empty:
        st.warning("No hay datos disponibles para el rango de fechas seleccionado.")
        return
    
    # Mostrar gráfico principal de disponibilidad con línea de media
    st.write("### Disponibilidad energética en el período seleccionado")
    
    # Filtrar valores nulos para cálculos
    df_disponibilidad_no_nulo = df.dropna(subset=["disponibilidad"])
    
    # Calcular la media de la disponibilidad solo de valores presentes
    disponibilidad_media = df_disponibilidad_no_nulo['disponibilidad'].mean() if not df_disponibilidad_no_nulo.empty else 0
    disponibilidad_max = df_disponibilidad_no_nulo['disponibilidad'].max() if not df_disponibilidad_no_nulo.empty else 0
    
    # Mostrar estadísticas antes del gráfico
    st.info(f"Disponibilidad máxima en el período seleccionado: {int(disponibilidad_max)} MW")
    
    # Crear gráfico usando el dataframe filtrado (solo valores no nulos)
    fig = crear_grafico_linea_plotly(
        df=df_disponibilidad_no_nulo,
        x_column=df_disponibilidad_no_nulo.index,
        y_column='disponibilidad',
        title=f"Evolución de la disponibilidad energética ({fecha_inicio} a {fecha_fin})",
        color='blue',
        show_markers=False
    )
      # Añadir línea de media si hay datos
    if not pd.isna(disponibilidad_media) and not df_disponibilidad_no_nulo.empty:
        fig.add_trace(go.Scatter(
            x=[df_disponibilidad_no_nulo.index.min(), df_disponibilidad_no_nulo.index.max()],
            y=[disponibilidad_media, disponibilidad_media],
            mode='lines',
            name=f'Media: {int(disponibilidad_media)} MW',
            line=dict(color='navy', width=1, dash='dash')
        ))
    
    # Añadir línea de demanda si hay datos
    if 'demanda_maxima' in df.columns:
        df_demanda_no_nulo = df.dropna(subset=["demanda_maxima"])
        if not df_demanda_no_nulo.empty:
            fig.add_trace(go.Scatter(
                x=df_demanda_no_nulo.index,
                y=df_demanda_no_nulo['demanda_maxima'],
                mode='lines',
                name='Demanda',
                line=dict(color='black', width=1.5)
            ))
    
    # Configurar diseño con límites de Y apropiados
    y_max = max(4000, int(disponibilidad_max * 1.1)) if disponibilidad_max else 4000
    
    fig.update_layout(
        title=f"Evolución de la disponibilidad energética ({fecha_inicio} a {fecha_fin})",
        xaxis_title="Fecha",
        yaxis_title="Disponibilidad (MW)",
        yaxis=dict(range=[0, y_max]),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)    # Crear pestañas para cada tipo de análisis
    tab1, tab2, tab3, tab4 = st.tabs([
        "Estadísticas", 
        "Análisis por Plantas", 
        "Energía Solar",
        "Datos Detallados"
    ])
    
    with tab1:
        # Mostrar estadísticas del período seleccionado
        mostrar_indicadores_disponibilidad(df)
        
        # Análisis por días de la semana
        st.subheader("Disponibilidad por día de la semana")
        
        # Agrupar por día de la semana
        dias_semana_orden = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        dias_semana_es = {
            "Monday": "Lunes",
            "Tuesday": "Martes",
            "Wednesday": "Miércoles",
            "Thursday": "Jueves",
            "Friday": "Viernes", 
            "Saturday": "Sábado",
            "Sunday": "Domingo"
        }
        
        # Convertir a día de la semana si no existe
        if "dia_semana" not in df.columns:
            df.loc[:, "dia_semana"] = df.index.strftime('%A')  # Día de la semana en inglés
        
        # Filtrar solo registros con disponibilidad válida
        df_dias_valido = df.dropna(subset=["disponibilidad"])
        
        if not df_dias_valido.empty:
            # Agrupar por día de la semana y calcular estadísticas
            stats_dias = df_dias_valido.groupby("dia_semana")["disponibilidad"].agg(['mean', 'min', 'max', 'count']).reset_index()
            stats_dias.columns = ['dia_semana', 'disponibilidad_promedio', 'disponibilidad_min', 'disponibilidad_max', 'conteo']
            
            # Traducir a español y ordenar
            stats_dias['dia_nombre'] = stats_dias['dia_semana'].map(dias_semana_es)
            stats_dias['orden'] = stats_dias['dia_semana'].map({dia: i for i, dia in enumerate(dias_semana_orden)})
            stats_dias = stats_dias.sort_values('orden')
            
            # Crear gráfico de barras con color azul uniforme
            fig_dias = go.Figure()
            
            # Barra que va hasta el máximo con color azul uniforme
            fig_dias.add_trace(go.Bar(
                x=stats_dias['dia_nombre'],
                y=stats_dias['disponibilidad_max'],
                name='Disponibilidad Máxima',
                marker=dict(
                    color='blue',
                    line=dict(width=0)
                ),
                text=[f'{val:.0f} MW' for val in stats_dias['disponibilidad_max']],
                textposition='outside',
                hovertemplate='<b>%{x}</b><br>Máximo: %{y:.0f} MW<extra></extra>',
                showlegend=False
            ))
            
            # Líneas discontinuas para el promedio (verde) y mínimo (azul claro)
            for i, row in stats_dias.iterrows():
                # Línea verde discontinua para la media
                fig_dias.add_shape(
                    type="line",
                    x0=i-0.4, x1=i+0.4,
                    y0=row['disponibilidad_promedio'], y1=row['disponibilidad_promedio'],
                    line=dict(color="green", width=3, dash="dash"),
                )
                
                # Línea azul claro discontinua para el mínimo
                fig_dias.add_shape(
                    type="line",
                    x0=i-0.4, x1=i+0.4,
                    y0=row['disponibilidad_min'], y1=row['disponibilidad_min'],
                    line=dict(color="lightblue", width=3, dash="dash"),
                )
            
            # Ajustar el rango del eje Y para dar más espacio
            y_max_dias = stats_dias['disponibilidad_max'].max() * 1.2
            
            fig_dias.update_layout(
                xaxis_title="Día de la semana",
                yaxis_title="Disponibilidad (MW)",
                yaxis=dict(range=[0, y_max_dias]),
                height=400,
                showlegend=False
            )
            
            st.plotly_chart(fig_dias, use_container_width=True)
        
        # Análisis por mes
        st.subheader("Disponibilidad por mes")
        
        # Añadir columna de mes si no existe
        if "mes_num" not in df.columns:
            df.loc[:, "mes_num"] = df.index.month
            df.loc[:, "mes_nombre"] = df.index.strftime('%B')  # Nombre del mes
        
        # Definir nombres de meses en español
        meses_es = {
            "January": "Enero",
            "February": "Febrero",
            "March": "Marzo",
            "April": "Abril",
            "May": "Mayo",
            "June": "Junio",
            "July": "Julio",
            "August": "Agosto",
            "September": "Septiembre",
            "October": "Octubre",
            "November": "Noviembre",
            "December": "Diciembre"
        }
        
        # Usar la función de utilidad para analizar los datos
        disponibilidad_por_mes, _ = analizar_distribucion_temporal(df, "disponibilidad")
        
        if disponibilidad_por_mes is not None:
            # Crear dataframe solo con los meses que tienen datos
            meses_con_datos = disponibilidad_por_mes[disponibilidad_por_mes['conteo'] > 0].copy()
            
            if not meses_con_datos.empty:
                # Agregar estadísticas adicionales (min/max por mes)
                df_mes_valido = df.dropna(subset=["disponibilidad"])
                if not df_mes_valido.empty:
                    df_mes_valido.loc[:, 'mes_nombre'] = df_mes_valido.index.strftime('%B')
                    stats_meses_detalle = df_mes_valido.groupby("mes_nombre")["disponibilidad"].agg(['mean', 'min', 'max', 'count']).reset_index()
                    stats_meses_detalle.columns = ['mes_nombre', 'disponibilidad_promedio', 'disponibilidad_min', 'disponibilidad_max', 'conteo']
                    
                    # Traducir nombres a español
                    stats_meses_detalle['mes_nombre_es'] = stats_meses_detalle['mes_nombre'].map(meses_es)
                    
                    # Crear gráfico de barras con color azul uniforme
                    fig_meses = go.Figure()
                    
                    # Barra que va hasta el máximo con color azul uniforme
                    fig_meses.add_trace(go.Bar(
                        x=stats_meses_detalle['mes_nombre_es'],
                        y=stats_meses_detalle['disponibilidad_max'],
                        name='Disponibilidad Máxima',
                        marker=dict(
                            color='blue',
                            line=dict(width=0)
                        ),
                        text=[f'{val:.0f} MW' for val in stats_meses_detalle['disponibilidad_max']],
                        textposition='outside',
                        hovertemplate='<b>%{x}</b><br>Máximo: %{y:.0f} MW<extra></extra>',
                        showlegend=False
                    ))
                    
                    # Líneas discontinuas para el promedio (verde) y mínimo (azul claro)
                    for i, row in stats_meses_detalle.iterrows():
                        # Línea verde discontinua para la media
                        fig_meses.add_shape(
                            type="line",
                            x0=i-0.4, x1=i+0.4,
                            y0=row['disponibilidad_promedio'], y1=row['disponibilidad_promedio'],
                            line=dict(color="green", width=3, dash="dash"),
                        )
                        
                        # Línea azul claro discontinua para el mínimo
                        fig_meses.add_shape(
                            type="line",
                            x0=i-0.4, x1=i+0.4,
                            y0=row['disponibilidad_min'], y1=row['disponibilidad_min'],
                            line=dict(color="lightblue", width=3, dash="dash"),
                        )
                    
                    # Ajustar el rango del eje Y para dar más espacio
                    y_max_meses = stats_meses_detalle['disponibilidad_max'].max() * 1.2
                    
                    fig_meses.update_layout(
                        xaxis_title="Mes",
                        yaxis_title="Disponibilidad (MW)",
                        yaxis=dict(range=[0, y_max_meses]),
                        height=400,
                        showlegend=False
                    )
                    
                    st.plotly_chart(fig_meses, use_container_width=True)
                else:
                    st.warning("No hay datos suficientes para crear gráficos mensuales.")
            else:
                st.warning("No hay datos suficientes para crear gráficos mensuales.")
        else:
            st.warning("No hay datos suficientes para crear gráficos mensuales.")
    
    with tab2:
        # Análisis de plantas disponibles
        analizar_plantas_disponibilidad(entradas, df)
    
    with tab3:
        # Análisis de energía solar
        mostrar_analisis_solar(df_solar_gen, df_solar_cnt, fecha_inicio, fecha_fin)
    
    with tab4:
        # Tabla de datos detallados
        mostrar_tabla_datos_detallados(df)

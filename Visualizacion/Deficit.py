import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from .utils import (
    cargar_datos,
    filtrar_datos_por_metrica,
    preparar_datos_plantas_deficit,
    analizar_distribucion_temporal,
    crear_grafico_linea_plotly,
    obtener_plantas
)

def preparar_dataframe_deficit(entradas):
    return filtrar_datos_por_metrica(entradas, "deficit")

def mostrar_indicadores_deficit(df):
    st.subheader("Indicadores Estadísticos del Período")
    
    # Filtrar valores no nulos para cálculos
    df_deficit_no_nulo = df[df["deficit"].notnull()]
    
    if df_deficit_no_nulo.empty:
        st.error("No hay datos suficientes para calcular indicadores de déficit.")
        return
    
    # Calcular métricas para el período seleccionado solo con datos válidos
    df_deficit_positivo = df_deficit_no_nulo[df_deficit_no_nulo["deficit"] > 0]
    
    deficit_promedio = df_deficit_no_nulo["deficit"].mean()
    deficit_mediana = df_deficit_no_nulo["deficit"].median()
    deficit_maximo = df_deficit_no_nulo["deficit"].max()
    deficit_minimo = df_deficit_positivo["deficit"].min() if not df_deficit_positivo.empty else 0
    desviacion_std = df_deficit_no_nulo["deficit"].std()
    
    # Obtener fechas de valores máximos y mínimos
    fecha_max = None
    if not pd.isna(deficit_maximo):
        max_indices = df_deficit_no_nulo[df_deficit_no_nulo["deficit"] == deficit_maximo].index
        if not max_indices.empty:
            fecha_max = max_indices[0].strftime("%d/%m/%Y")
    
    fecha_min = None
    if not pd.isna(deficit_minimo) and deficit_minimo > 0:
        min_indices = df_deficit_positivo[df_deficit_positivo["deficit"] == deficit_minimo].index
        if not min_indices.empty:
            fecha_min = min_indices[0].strftime("%d/%m/%Y")
    
    # Días con déficit
    dias_totales = len(df_deficit_no_nulo)
    dias_con_deficit = len(df_deficit_positivo)
    porcentaje_dias_deficit = (dias_con_deficit / dias_totales * 100) if dias_totales > 0 else 0
    
    # Mostrar KPIs en columnas
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Déficit Promedio (MW)",
            value=f"{int(deficit_promedio)}" if not pd.isna(deficit_promedio) else "N/D"
        )
        
        st.metric(
            label="Déficit Mediana (MW)",
            value=f"{int(deficit_mediana)}" if not pd.isna(deficit_mediana) else "N/D"
        )
    
    with col2:
        st.metric(
            label=f"Déficit Máximo (MW)",
            value=f"{int(deficit_maximo)}" if not pd.isna(deficit_maximo) else "N/D",
            help=f"Registrado el {fecha_max}" if fecha_max else ""
        )
        
        st.metric(
            label="Déficit Mínimo >0 (MW)",
            value=f"{int(deficit_minimo)}" if not pd.isna(deficit_minimo) and deficit_minimo > 0 else "0",
            help=f"Registrado el {fecha_min}" if fecha_min else ""
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
            label="Días con Déficit",
            value=f"{dias_con_deficit}" if dias_con_deficit >= 0 else "0"
        )
        
        st.metric(
            label="% Días con Déficit",
            value=f"{porcentaje_dias_deficit:.1f}%",
            help=f"{dias_con_deficit} días de {dias_totales} analizados"
        )

def analizar_plantas_deficit(entradas, df):
    st.subheader("Análisis de Plantas en Avería y su Impacto en el Déficit")
    
    # Preparar datos para análisis de plantas usando la función de utilidad
    df_plantas = preparar_datos_plantas_deficit(df)
    
    # Verificar si hay datos disponibles
    if df_plantas is None:
        st.info("No hay datos de plantas en avería disponibles.")
        return
    
    # Calcular frecuencia por planta
    if not df_plantas.empty:
        # Contar días en avería por planta
        from .plant_standardizer import get_valid_plant_names
        frecuencia = df_plantas["planta"].value_counts()
        df_freq = pd.DataFrame({
            "planta": frecuencia.index,
            "días_en_avería": frecuencia.values
        }).set_index("planta")
        
        # Selección de planta específica para análisis
        # Solo incluir plantas termoeléctricas válidas
        valid_plants = ["Todas las plantas"] + sorted(set(df_plantas["planta"].unique()) & set(get_valid_plant_names()))
        planta_seleccionada = st.selectbox("Seleccionar planta para análisis", valid_plants)
        
        # Si se seleccionó una planta específica, mostrar análisis detallado
        if planta_seleccionada != "Todas las plantas":
            # Filtrar datos solo para la planta seleccionada
            df_planta = df_plantas[df_plantas["planta"] == planta_seleccionada]
            
            if not df_planta.empty:
                # Calcular métricas específicas para esta planta
                df_planta_sin_na = df_planta.dropna(subset=["deficit"])
                
                if not df_planta_sin_na.empty:
                    deficit_promedio_planta = df_planta_sin_na["deficit"].mean()
                    deficit_maximo_planta = df_planta_sin_na["deficit"].max()
                    deficit_minimo_planta = df_planta_sin_na["deficit"].min()
                    deficit_mediana_planta = df_planta_sin_na["deficit"].median()
                    
                    # Agregar fechas de máximo y mínimo
                    fecha_max = df_planta_sin_na[df_planta_sin_na["deficit"] == deficit_maximo_planta]["fecha"].iloc[0]
                    fecha_min = df_planta_sin_na[df_planta_sin_na["deficit"] == deficit_minimo_planta]["fecha"].iloc[0]
                    
                    # Calcular desviación estándar para mostrar variabilidad
                    desviacion_std = df_planta_sin_na["deficit"].std()
                    
                    # Mostrar resumen en columnas
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric(
                            label=f"Días en avería",
                            value=len(df_planta),
                            help=f"{len(df_planta)} días sobre {len(df)} analizados"
                        )
                        
                        st.metric(
                            label=f"Déficit promedio",
                            value=f"{int(deficit_promedio_planta)} MW" if not pd.isna(deficit_promedio_planta) else "N/D"
                        )
                    
                    with col2:
                        st.metric(
                            label=f"Déficit máximo",
                            value=f"{int(deficit_maximo_planta)} MW" if not pd.isna(deficit_maximo_planta) else "N/D",
                            help=f"Ocurrido el {fecha_max.strftime('%d/%m/%Y')}"
                        )
                        
                        st.metric(
                            label=f"Déficit mínimo",
                            value=f"{int(deficit_minimo_planta)} MW" if not pd.isna(deficit_minimo_planta) else "N/D",
                            help=f"Ocurrido el {fecha_min.strftime('%d/%m/%Y')}"
                        )
                    
                    with col3:
                        st.metric(
                            label=f"Déficit mediana",
                            value=f"{int(deficit_mediana_planta)} MW" if not pd.isna(deficit_mediana_planta) else "N/D"
                        )
                        
                        st.metric(
                            label=f"Desviación estándar",
                            value=f"{int(desviacion_std)} MW" if not pd.isna(desviacion_std) else "N/D"
                        )
                    
                    # Preparar datos para visualizaciones, ordenados por fecha
                    df_plot = df_planta.sort_values("fecha").copy()
                    
                    # Gráfico de línea temporal del déficit durante averías - SOLO LÍNEAS SIN PUNTOS
                    if len(df_plot) > 1:
                        # Eliminar NaN para la visualización
                        df_plot_clean = df_plot.dropna(subset=["deficit"]).copy()
                        
                        if not df_plot_clean.empty:
                            st.write(f"### Evolución del déficit durante averías de {planta_seleccionada}")
                            
                            fig = px.line(
                                df_plot_clean,
                                x="fecha",
                                y="deficit",
                                markers=False,  # Sin marcadores (puntos)
                                color_discrete_sequence=["red"],
                                title=f"Déficit cuando {planta_seleccionada} está en avería",
                                labels={"fecha": "Fecha", "deficit": "Déficit (MW)"}
                            )
                            
                            # Agregar línea de déficit promedio específico de esta planta
                            fig.add_hline(
                                y=deficit_promedio_planta,
                                line_dash="dash",
                                line_color="black",
                                annotation_text=f"Déficit promedio: {int(deficit_promedio_planta)} MW"
                            )
                            
                            # Configurar línea sin puntos
                            fig.update_traces(mode='lines', line=dict(width=2.5))
                            fig.update_layout(height=400)
                            st.plotly_chart(fig, use_container_width=True)
                            
                            # Análisis por mes para esta planta
                            st.write(f"### Resumen mensual para {planta_seleccionada}")
                            
                            # Extraer mes y año para agrupación
                            df_plot_clean["año_mes"] = df_plot_clean["fecha"].dt.strftime("%Y-%m")
                            
                            # Agrupar por mes
                            resumen_mensual = df_plot_clean.groupby("año_mes").agg({
                                "deficit": ["mean", "max", "min", "count"]
                            }).reset_index()
                            
                            # Preparar datos para visualización
                            resumen_mensual.columns = ["Mes", "Déficit Promedio", "Déficit Máximo", "Déficit Mínimo", "Días en Avería"]
                            
                            # Mostrar como tabla interactiva
                            st.dataframe(resumen_mensual, use_container_width=True)
                            
                            # Gráfico de línea para evolución mensual (sin puntos)
                            fig_mensual = px.line(
                                resumen_mensual,
                                x="Mes",
                                y="Déficit Promedio",
                                markers=False,  # Sin marcadores (puntos)
                                title=f"Déficit promedio mensual cuando {planta_seleccionada} está en avería",
                                labels={"Mes": "Mes", "Déficit Promedio": "Déficit promedio (MW)"}
                            )
                            
                            # Configurar línea sin puntos
                            fig_mensual.update_traces(mode='lines', line=dict(width=2.5))
                            fig_mensual.update_layout(height=300)
                            st.plotly_chart(fig_mensual, use_container_width=True)
                        else:
                            st.warning("No hay datos de déficit no nulos para esta planta.")
                    else:
                        st.info(f"Solo hay un registro para {planta_seleccionada}, no es posible mostrar evolución.")
                else:
                    st.warning("No hay datos de déficit disponibles para esta planta.")
            else:
                st.warning(f"No se encontraron períodos de avería para {planta_seleccionada}.")
        
        # Visualización de frecuencia de averías por planta
        st.write("### Frecuencia de averías por planta")
        
        # Selección del tipo de visualización
        vista_seleccionada = st.radio(
            "Tipo de visualización:",
            ["Tabla de frecuencias", "Gráfico de barras"],
            key="vista_analisis_plantas"
        )
        
        # Mostrar visualización según selección
        if not df_freq.empty:
            # Filtrar para mostrar solo plantas termoeléctricas válidas
            df_freq_filtrado = df_freq[df_freq.index.isin(get_valid_plant_names())]
            
            if vista_seleccionada == "Tabla de frecuencias":
                st.write("Frecuencia de averías por planta:")
                try:
                    st.dataframe(df_freq_filtrado.sort_values('días_en_avería', ascending=False), use_container_width=True)
                except Exception as e:
                    st.error(f"Error al mostrar tabla: {str(e)}")
                    # Mostrar tabla simple como fallback
                    st.dataframe(df_freq_filtrado)
            else:
                # Preparar datos para gráfico
                df_graph = df_freq_filtrado.reset_index().sort_values('días_en_avería', ascending=True).tail(10)
                fig = px.bar(
                    df_graph,
                    x='días_en_avería',
                    y='planta',
                    title="Top 10 plantas con más días en avería",
                    labels={'días_en_avería': 'Días en avería', 'planta': 'Planta'},
                    height=400
                )
                st.plotly_chart(fig, use_container_width=True)

def analizar_distribucion_temporal_deficit(df):
    """
    Analiza la distribución temporal del déficit por meses y estacionalidad
    Args:
        df (pd.DataFrame): DataFrame con datos de déficit procesados
    """
    st.subheader("Distribución Temporal del Déficit")
      # Usar la función de utilidad para analizar distribución temporal
    deficit_por_mes, deficit_por_año_mes = analizar_distribucion_temporal(df, "deficit")
    
    if deficit_por_mes is None or deficit_por_año_mes is None:
        st.warning("No hay datos suficientes para el análisis de distribución temporal.")
        return
    
    # Análisis por mes
    st.write("#### Déficit por mes")
    
    # Obtener DataFrame filtrado para graficar (solo meses con datos)
    df_para_grafico = deficit_por_mes[deficit_por_mes['conteo'] > 0].copy()
    
    # Verificar que hay datos para graficar
    if not df_para_grafico.empty:
        # Crear gráfico de barras (como fue solicitado)
        fig = px.bar(
            df_para_grafico,
            x='mes_nombre',
            y='deficit_promedio',
            labels={'mes_nombre': 'Mes', 'deficit_promedio': 'Déficit (MW)'},
            title="Déficit promedio por mes",
            text_auto='.0f',  # Mostrar valores en barras sin decimales
            color='deficit_promedio',
            color_continuous_scale='Reds'
        )
        
        # Mostrar el número de registros por mes como información adicional
        fig.update_traces(
            hovertemplate='<b>%{x}</b><br>Déficit promedio: %{y:.0f} MW<br>Registros: %{customdata}<extra></extra>',
            customdata=df_para_grafico['conteo']
        )
        
        # Mejorar diseño
        fig.update_layout(
            xaxis_title="Mes",
            yaxis_title="Déficit promedio (MW)",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # También mostramos tabla con datos para verificación
        st.write("Desglose de datos de déficit por mes:")
        
        # Formato para mostrar
        tabla_meses = df_para_grafico[['mes_nombre', 'deficit_promedio', 'conteo']]
        tabla_meses = tabla_meses.rename(columns={
            'mes_nombre': 'Mes', 
            'deficit_promedio': 'Déficit promedio (MW)',
            'conteo': 'Días con datos'
        })
        
        # Formatear valores numéricos
        tabla_meses['Déficit promedio (MW)'] = tabla_meses['Déficit promedio (MW)'].map('{:.0f}'.format)
        
        st.dataframe(tabla_meses, use_container_width=True, hide_index=True)
    else:
        st.warning("No hay suficientes datos para mostrar el análisis por mes.")      # Análisis de tendencia anual
    st.write("#### Tendencia anual del déficit")
    
    try:
          # Verificar valores máximos para asegurar que están siendo considerados
        st.info(f"Déficit máximo en el período analizado por año-mes: {int(deficit_por_año_mes['deficit_max'].max())} MW")
        
        # Crear gráfico de tendencia usando la función de utilidad
        fig = crear_grafico_linea_plotly(
            df=deficit_por_año_mes,
            x_column='año_mes',
            y_column='deficit_promedio',
            title="Tendencia del déficit por año y mes",
            color='red',
            show_markers=False
        )
        
        # Personalizar hover
        fig.update_traces(
            hovertemplate='<b>%{x|%b %Y}</b><br>Déficit promedio: %{y:.0f} MW<br>Registros: %{customdata}<extra></extra>',
            customdata=deficit_por_año_mes['conteo']
        )
        
        # Establecer límites Y para mostrar todos los valores
        y_max = max(2000, int(deficit_por_año_mes['deficit_max'].max() * 1.1))
        fig.update_layout(yaxis=dict(range=[0, y_max]))
        
        # Mejorar formato de fechas
        fig.update_xaxes(
            dtick="M3",  # Mostrar cada 3 meses
            tickformat="%b\n%Y"
        )
          # Añadir línea de tendencia
        if len(deficit_por_año_mes) > 1:
            from scipy import stats
            
            # Convertir fechas a números ordinales para regresión lineal
            x = [(d - pd.Timestamp("1970-01-01")).days for d in deficit_por_año_mes['año_mes']]
            y = deficit_por_año_mes['deficit_promedio'].values  # Columna renombrada
            
            # Calcular regresión lineal
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
            
            # Generar puntos para la línea de tendencia
            x_trend = [min(x), max(x)]
            y_trend = [slope * xi + intercept for xi in x_trend]
            
            # Convertir x de nuevo a fechas
            x_dates = [pd.Timestamp("1970-01-01") + pd.Timedelta(days=int(xi)) for xi in x_trend]
            
            # Añadir línea de tendencia
            fig.add_trace(go.Scatter(
                x=x_dates, 
                y=y_trend,
                mode='lines',
                name='Tendencia',
                line=dict(color='black', width=2, dash='dash')
            ))
        
        st.plotly_chart(fig, use_container_width=True)
          # Añadir estadísticas de tendencia
        if len(deficit_por_año_mes) > 1:
            tendencia = "creciente" if slope > 0 else "decreciente"
            cambio_mensual = slope * 30  # Cambio aproximado por mes
            
            st.write(f"""
            **Análisis de tendencia:**
            
            - Tendencia: {tendencia}
            - Cambio promedio mensual: {abs(cambio_mensual):.1f} MW {'más' if slope > 0 else 'menos'} por mes
            - Coeficiente de determinación (R²): {r_value**2:.2f}
            - Déficit máximo registrado en el período: {int(deficit_por_año_mes['deficit_max'].max())} MW
            """)
    except Exception as e:
        st.error(f"Error al generar el análisis de tendencia: {str(e)}")
        import traceback
        st.write(traceback.format_exc())

def preparar_datos_detallados(df, filtro_año=None):
    """
    Prepara los datos para la visualización detallada, aplicando filtros si es necesario
    Args:
        df (pd.DataFrame): DataFrame con datos de déficit
        filtro_año (str, opcional): Año para filtrar los datos
    Returns:
        pd.DataFrame: DataFrame filtrado con datos detallados
    """
    df_filtrado = df.copy()
    
    # Filtrar por año si se especifica
    if filtro_año and filtro_año != "Todos los años":
        df_filtrado = df_filtrado[df_filtrado.index.year == int(filtro_año)]
    
    return df_filtrado

def mostrar_tabla_datos_detallados(df):
    """
    Muestra una tabla interactiva con los datos detallados de déficit
    Args:
        df (pd.DataFrame): DataFrame con datos de déficit filtrados
    """
    st.subheader("Datos Detallados del Período Seleccionado")
    
    if df.empty:
        st.warning("No hay datos disponibles para el período seleccionado.")
        return
    
    # Opciones de visualización
    col1, col2, col3 = st.columns(3)
    with col1:
        mostrar_solo_deficit = st.checkbox(
            "Mostrar solo días con déficit", 
            value=False,
            key="mostrar_solo_deficit"
        )
    
    with col2:
        ordenar_por = st.selectbox(
            "Ordenar por",
            options=["Fecha (↑)", "Fecha (↓)", "Déficit (↑)", "Déficit (↓)"],
            key="ordenar_tabla_deficit"
        )
    
    with col3:
        mostrar_enlaces = st.checkbox(
            "Mostrar enlaces a noticias",
            value=True,
            key="mostrar_enlaces"
        )
    
    # Aplicar filtros adicionales
    df_filtrado = df.copy()
    
    # Manejar valores nulos para evitar problemas de filtrado
    if mostrar_solo_deficit:
        # Filtrar solo registros con déficit positivo (mayor que 0)
        df_filtrado = df_filtrado[(df_filtrado["deficit"].notnull()) & (df_filtrado["deficit"] > 0)]
    
    if df_filtrado.empty:
        st.warning("No hay registros que cumplan con los criterios de filtrado.")
        return
    
    # Aplicar ordenamiento (asegurando que los valores nulos no causen problemas)
    if ordenar_por == "Fecha (↑)":
        df_filtrado = df_filtrado.sort_index(ascending=True)
    elif ordenar_por == "Fecha (↓)":
        df_filtrado = df_filtrado.sort_index(ascending=False)
    elif ordenar_por == "Déficit (↑)":
        # Para ordenar por déficit, primero colocamos los nulos al final
        df_no_nulos = df_filtrado[df_filtrado["deficit"].notnull()]
        df_nulos = df_filtrado[df_filtrado["deficit"].isnull()]
        df_filtrado = pd.concat([df_no_nulos.sort_values("deficit", ascending=True), df_nulos])
    elif ordenar_por == "Déficit (↓)":
        df_no_nulos = df_filtrado[df_filtrado["deficit"].notnull()]
        df_nulos = df_filtrado[df_filtrado["deficit"].isnull()]
        df_filtrado = pd.concat([df_no_nulos.sort_values("deficit", ascending=False), df_nulos])
    
    # Reindexar para mostrar la fecha como columna
    df_mostrar = df_filtrado.reset_index()
    
    # Formatear la fecha para mejor visualización
    df_mostrar["fecha"] = df_mostrar["fecha"].dt.strftime("%Y-%m-%d")
    
    # Seleccionar columnas a mostrar
    columnas_base = [
        "fecha", "deficit", "porcentaje_deficit", "demanda", "disponibilidad",
        "cant_plantas_averia", "impacto_motores_mw", "año", "mes", "dia_semana"
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
        "deficit": "Déficit (MW)",
        "porcentaje_deficit": "% de Déficit",
        "demanda": "Demanda (MW)",
        "disponibilidad": "Disponibilidad (MW)",
        "cant_plantas_averia": "Plantas en Avería",
        "impacto_motores_mw": "Impacto Motores (MW)",
        "año": "Año",
        "mes": "Mes",
        "dia_semana": "Día",
        "enlace": "Enlace al reporte"
    }
    
    # Formatear para mejor visualización y manejo de NaN
    df_formato = df_mostrar[columnas_disponibles].copy()
    
    # Reemplazar NaN con valores más descriptivos en formato texto
    for col in df_formato.columns:
        if col == "enlace":
            continue
        if df_formato[col].dtype == float or df_formato[col].dtype == int:
            df_formato[col] = df_formato[col].fillna("N/D")
    
    # Mostrar DataFrame
    st.write(f"Mostrando {len(df_formato)} registros")
    
    # Convertir enlaces a markdown si están disponibles
    if "enlace" in df_formato.columns and mostrar_enlaces:
        df_formato["enlace"] = df_formato["enlace"].apply(
            lambda x: f"[Ver noticia]({x})" if isinstance(x, str) and x.startswith("http") else ""
        )
    
    # Mostrar la tabla con columnas renombradas
    st.dataframe(
        df_formato.rename(columns={c: nombres_columnas.get(c, c) for c in df_formato.columns}), 
        use_container_width=True,
        hide_index=True
    )
    
    # Botón para descargar datos
    # Convertir NaN a string vacío para CSV
    df_csv = df_mostrar.fillna("")
    csv = df_csv.to_csv(index=False).encode('utf-8')
    
    st.download_button(
        label="Descargar datos como CSV",
        data=csv,
        file_name=f"deficit_energetico_filtrado.csv",
        mime="text/csv",
        key="descargar_csv_deficit"
    )

def app():
    """
    Función principal del módulo de análisis de déficit
    """
    st.header("Análisis Histórico del Déficit Energético")
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
    
    # Preparar dataframe específico para análisis de déficit
    try:
        df_completo = preparar_dataframe_deficit(entradas)
    except Exception as e:
        st.error(f"Error al procesar los datos: {str(e)}")
        return
    
    if df_completo.empty:
        st.error("No hay datos disponibles para analizar.")
        return
    
    # Añadir selector de fechas al inicio
    st.write("### Selecciona el rango de fechas a analizar")
    
    try:
        fecha_min = df_completo.index.min().date()
        fecha_max = df_completo.index.max().date()
    except Exception as e:
        st.error(f"Error al determinar el rango de fechas: {str(e)}")
        return
    
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        fecha_inicio = st.date_input(
            "Fecha de inicio",
            value=fecha_min,
            min_value=fecha_min,
            max_value=fecha_max,
            key="fecha_inicio_deficit"
        )
    
    with col2:
        fecha_fin = st.date_input(
            "Fecha de fin",
            value=fecha_max,
            min_value=fecha_min,
            max_value=fecha_max,
            key="fecha_fin_deficit"
        )
    
    with col3:
        if st.button("Ver todo", key="ver_todo_deficit"):
            fecha_inicio = fecha_min
            fecha_fin = fecha_max
            st.experimental_rerun()
    
    # Filtrar dataframe según el rango de fechas seleccionado
    inicio_dt = datetime.combine(fecha_inicio, datetime.min.time())
    fin_dt = datetime.combine(fecha_fin, datetime.max.time())
    
    # Filtrar el dataframe para el rango seleccionado
    df = df_completo[(df_completo.index >= inicio_dt) & (df_completo.index <= fin_dt)].copy()
    
    if df.empty:
        st.warning("No hay datos disponibles para el rango de fechas seleccionado.")
        return
    
    # Mostrar gráfico principal de déficit con línea de media
    st.write("### Déficit energético en el período seleccionado")
      # Filtrar valores nulos para cálculos
    df_deficit_no_nulo = df.dropna(subset=["deficit"])
    
    # Calcular la media del déficit solo de valores presentes
    deficit_medio = df_deficit_no_nulo['deficit'].mean() if not df_deficit_no_nulo.empty else 0
    deficit_max = df_deficit_no_nulo['deficit'].max() if not df_deficit_no_nulo.empty else 0
    
    # Mostrar estadísticas antes del gráfico
    st.info(f"Déficit máximo en el período seleccionado: {int(deficit_max)} MW")
      # Crear gráfico usando el dataframe filtrado (solo valores no nulos)
    fig = crear_grafico_linea_plotly(
        df=df_deficit_no_nulo,
        x_column=df_deficit_no_nulo.index,
        y_column='deficit',
        title=f"Evolución del déficit energético ({fecha_inicio} a {fecha_fin})",
        color='red',
        show_markers=False
    )
    
    # Añadir línea de media si hay datos
    if not pd.isna(deficit_medio) and not df_deficit_no_nulo.empty:
        fig.add_trace(go.Scatter(
            x=[df_deficit_no_nulo.index.min(), df_deficit_no_nulo.index.max()],
            y=[deficit_medio, deficit_medio],
            mode='lines',
            name=f'Media: {int(deficit_medio)} MW',
            line=dict(color='black', width=1, dash='dash')
        ))
    # Configurar diseño con límites de Y apropiados para mostrar todos los valores
    y_max = max(2000, int(deficit_max * 1.1)) if deficit_max else 2000  # Asegurar espacio suficiente
    
    fig.update_layout(
        title=f"Evolución del déficit energético ({fecha_inicio} a {fecha_fin})",
        xaxis_title="Fecha",
        yaxis_title="Déficit (MW)",
        yaxis=dict(range=[0, y_max]),  # Establecer límites explícitamente
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Crear pestañas para cada tipo de análisis
    tab1, tab2, tab3, tab4 = st.tabs([
        "Estadísticas", 
        "Relación con Plantas", 
        "Distribución Temporal",
        "Datos Detallados"
    ])
    
    with tab1:
        # Mostrar estadísticas del período seleccionado
        mostrar_indicadores_deficit(df)
        
        # Análisis por días de la semana
        st.subheader("Déficit por día de la semana")
        
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
            
        # Análisis por mes
        st.subheader("Déficit por mes")
        
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
          # Usar la función de utilidad para analizar los datos (solo si no lo hemos hecho antes)
        if 'deficit_por_mes' not in locals() or deficit_por_mes is None:
            deficit_por_mes, _ = analizar_distribucion_temporal(df, "deficit")
            if deficit_por_mes is None:
                st.warning("No hay datos suficientes para crear gráficos mensuales.")
                return
        
        # Crear dataframe solo con los meses que tienen datos
        meses_con_datos = deficit_por_mes[deficit_por_mes['conteo'] > 0].copy()
        
        # Crear gráfico de línea usando nuestra función de utilidad
        fig_meses = crear_grafico_linea_plotly(
            df=meses_con_datos,
            x_column='mes_nombre',
            y_column='deficit_promedio',
            title='Déficit promedio por mes',
            color='red',
            show_markers=False
        )
        
        # Asegurar que solo muestre líneas, sin puntos
        fig_meses.update_traces(mode='lines', line=dict(width=2.5, color='red'))
        
        # Mejorar diseño
        fig_meses.update_layout(
            xaxis_title="Mes",
            yaxis_title="Déficit promedio (MW)",
            height=400
        )
        
        st.plotly_chart(fig_meses, use_container_width=True)
        
        # Añadir información sobre los datos
        with st.expander("Información sobre los datos"):
            st.write("""            ### Fuente de datos
            Los datos de déficit se extraen ÚNICAMENTE de la sección "prediccion" en los reportes diarios,
            específicamente del campo "deficit". No se realizan cálculos alternativos y los registros
            sin valor de déficit en esta sección son omitidos del análisis.
            
            ### Ejemplo de estructura de datos
            ```json
            {
                "prediccion": {
                    "disponibilidad": 2053,
                    "demanda_maxima": 3400,
                    "afectacion": 1417,
                    "deficit": 1347,
                    "respaldo": null,
                    "horario_pico": "noche"
                }
            }
            ```
            """)
    
    with tab2:
        # Análisis de plantas y relación con déficit
        analizar_plantas_deficit(entradas, df)
    
    with tab3:
        # Análisis de distribución temporal del déficit
        analizar_distribucion_temporal_deficit(df)
    
    with tab4:
        # Tabla detallada de datos
        mostrar_tabla_datos_detallados(df)
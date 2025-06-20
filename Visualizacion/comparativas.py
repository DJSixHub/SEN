import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
from .utils import cargar_datos

def limpiar_valor_numerico(valor):
    """Limpiar valores que pueden tener unidades o texto adicional"""
    if valor is None:
        return 0
    
    # Si ya es numérico, devolverlo
    if isinstance(valor, (int, float)):
        return float(valor)
    
    # Si es string, limpiar
    if isinstance(valor, str):
        # Remover unidades comunes y espacios
        valor_limpio = valor.replace("MW", "").replace("MWh", "").replace("kW", "").replace("kWh", "")
        valor_limpio = valor_limpio.replace(",", "").strip()
        
        # Intentar convertir a float
        try:
            return float(valor_limpio)
        except (ValueError, TypeError):
            return 0
    
    return 0

def preparar_datos_multivariados(entradas):
    """Preparar datos para análisis multivariado con todas las variables disponibles"""
    filas = []
    for e in entradas:
        pred = e["datos"].get("prediccion", {})
        plantas = e["datos"].get("plantas", {})
        distribuida = e["datos"].get("distribuida", {})
        solar = e["datos"].get("paneles_solares", {})
        impacto = e["datos"].get("impacto", {})
        
        # Contar plantas en problemas
        plantas_averia = len(plantas.get("averia", []))
        plantas_mantenimiento = len(plantas.get("mantenimiento", []))
        total_plantas_problemas = plantas_averia + plantas_mantenimiento
        
        # Motores distribuidos - limpiar valores
        motores_impacto = limpiar_valor_numerico(distribuida.get("motores_con_problemas", {}).get("impacto_mw", 0))
        
        # Solar - limpiar valores
        solar_parques = limpiar_valor_numerico(solar.get("cantidad_parques", 0))
        solar_produccion = limpiar_valor_numerico(solar.get("produccion_mwh", 0))
        
        # Impacto máximo - limpiar valores
        impacto_max = limpiar_valor_numerico(impacto.get("maximo", {}).get("mw", 0))        
        fila = {
            "fecha": e["fecha"],
            "disponibilidad": limpiar_valor_numerico(pred.get("disponibilidad")),
            "demanda": limpiar_valor_numerico(pred.get("demanda_maxima")),
            "deficit": limpiar_valor_numerico(pred.get("deficit")),
            "afectacion": limpiar_valor_numerico(pred.get("afectacion")),
            "respaldo": limpiar_valor_numerico(pred.get("respaldo")),
            "plantas_averia": plantas_averia,
            "plantas_mantenimiento": plantas_mantenimiento,
            "total_plantas_problemas": total_plantas_problemas,
            "motores_impacto_mw": motores_impacto,
            "solar_parques": solar_parques,
            "solar_produccion_mwh": solar_produccion,
            "impacto_max_mw": impacto_max,
            "enlace": e.get("enlace", "")
        }
        
        # Solo incluir filas con datos básicos válidos
        if fila["disponibilidad"] is not None and fila["demanda"] is not None and fila["disponibilidad"] > 0 and fila["demanda"] > 0:
            filas.append(fila)    
    df = pd.DataFrame(filas)
    if not df.empty:
        df = df.set_index("fecha").sort_index()
        
        # Calcular variables derivadas con protección para división por cero
        df['cobertura_pct'] = 0
        df['deficit_pct'] = 0
        
        # Calcular cobertura solo donde demanda > 0
        mask_demanda_valida = df['demanda'] > 0
        df.loc[mask_demanda_valida, 'cobertura_pct'] = (df.loc[mask_demanda_valida, 'disponibilidad'] / df.loc[mask_demanda_valida, 'demanda'] * 100).round(2)
        df.loc[mask_demanda_valida, 'deficit_pct'] = (df.loc[mask_demanda_valida, 'deficit'] / df.loc[mask_demanda_valida, 'demanda'] * 100).round(2)
        
        df['brecha_disponibilidad_demanda'] = df['disponibilidad'] - df['demanda']
        
        # Agregar información temporal
        df['año'] = df.index.year
        df['mes'] = df.index.month
        df['dia_semana'] = df.index.strftime('%A')
    
    return df

def crear_grafico_adversarial_principal(df, fecha_inicio, fecha_fin):
    """Crear el gráfico principal de déficit vs disponibilidad con relleno adversarial"""
    # Filtrar datos por fecha
    inicio_dt = datetime.combine(fecha_inicio, datetime.min.time())
    fin_dt = datetime.combine(fecha_fin, datetime.max.time())
    
    df_filtered = df[(df.index >= inicio_dt) & (df.index <= fin_dt)].copy()
    df_filtered = df_filtered.dropna(subset=['disponibilidad', 'deficit'])
    
    if df_filtered.empty:
        return None    # Crear figura
    fig = go.Figure()
    
    # Línea de disponibilidad (azul) - solo línea
    fig.add_trace(go.Scatter(
        x=df_filtered.index,
        y=df_filtered['disponibilidad'],
        mode='lines',
        name='Disponibilidad',
        line=dict(color='blue', width=2.5),
        hovertemplate='<b>Disponibilidad</b><br>Fecha: %{x}<br>Valor: %{y:.0f} MW<extra></extra>'
    ))
    
    # Línea de déficit (roja) - solo línea
    fig.add_trace(go.Scatter(
        x=df_filtered.index,
        y=df_filtered['deficit'],
        mode='lines',
        name='Déficit',
        line=dict(color='red', width=2.5),
        hovertemplate='<b>Déficit</b><br>Fecha: %{x}<br>Valor: %{y:.0f} MW<extra></extra>'
    ))    
    # Relleno adversarial simplificado - sin puntos visibles
    # Crear coordenadas para el relleno completo
    x_coords = df_filtered.index.tolist()
    y_disponibilidad = df_filtered['disponibilidad'].tolist()
    y_deficit = df_filtered['deficit'].tolist()
    
    # Determinar el color general del relleno basado en la mayoría de los datos
    disponibilidad_mayor = (df_filtered['disponibilidad'] >= df_filtered['deficit']).sum()
    total_puntos = len(df_filtered)
    
    if disponibilidad_mayor > total_puntos / 2:
        fill_color = 'rgba(0, 255, 0, 0.15)'  # Verde translúcido (situación favorable)
        fill_name = 'Situación Favorable'
    else:
        fill_color = 'rgba(255, 0, 0, 0.15)'  # Rojo translúcido (situación crítica)
        fill_name = 'Situación Crítica'
    
    # Crear el relleno como una sola traza
    x_fill = x_coords + x_coords[::-1]  # x coords + x coords reversed
    y_fill = y_disponibilidad + y_deficit[::-1]  # y1 + y2 reversed
    
    fig.add_trace(go.Scatter(
        x=x_fill,
        y=y_fill,
        fill='toself',
        fillcolor=fill_color,
        line=dict(width=0, color='rgba(0,0,0,0)'),  # Línea invisible
        mode='none',  # Sin puntos ni líneas visibles
        showlegend=True,
        name=fill_name,
        hoverinfo='skip'
    ))
    
    # Configurar diseño
    y_max = max(df_filtered['disponibilidad'].max(), df_filtered['deficit'].max()) * 1.1
    
    fig.update_layout(
        title=f"Déficit vs Disponibilidad ({fecha_inicio} a {fecha_fin})",
        xaxis_title="Fecha",
        yaxis_title="MW",
        yaxis=dict(range=[0, y_max]),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=500
    )
    
    return fig

def crear_matriz_correlacion(df):
    """Crear matriz de correlación de variables numéricas"""
    # Seleccionar variables numéricas principales
    variables_numericas = [
        'disponibilidad', 'demanda', 'deficit', 'afectacion', 'respaldo',
        'total_plantas_problemas', 'motores_impacto_mw', 'solar_parques', 
        'solar_produccion_mwh', 'cobertura_pct', 'brecha_disponibilidad_demanda'
    ]
    
    # Filtrar variables que existen en el dataframe
    variables_existentes = [var for var in variables_numericas if var in df.columns]
    
    # Calcular matriz de correlación
    df_corr = df[variables_existentes].corr()
    
    # Crear heatmap
    fig = px.imshow(
        df_corr.values,
        x=df_corr.columns,
        y=df_corr.index,
        color_continuous_scale='RdBu_r',
        zmin=-1, zmax=1,
        title="Matriz de Correlación entre Variables del SEN"
    )
    
    # Añadir valores de correlación como texto
    for i in range(len(df_corr)):
        for j in range(len(df_corr.columns)):
            fig.add_annotation(
                x=j, y=i,
                text=f"{df_corr.iloc[i, j]:.2f}",
                showarrow=False,
                font=dict(color="white" if abs(df_corr.iloc[i, j]) > 0.5 else "black")
            )
    
    fig.update_layout(height=600)
    return fig

def crear_grafico_dispersion(df, x_var, y_var):
    """Crear gráfico de dispersión entre dos variables"""
    # Filtrar datos válidos
    df_valid = df.dropna(subset=[x_var, y_var])
    
    if df_valid.empty:
        return None
    
    # Crear gráfico de dispersión
    fig = px.scatter(
        df_valid.reset_index(),
        x=x_var,
        y=y_var,
        color='año',
        hover_data=['fecha'],
        title=f"Relación entre {x_var.title()} y {y_var.title()}",
        labels={
            x_var: f"{x_var.replace('_', ' ').title()}",
            y_var: f"{y_var.replace('_', ' ').title()}"
        }
    )
    
    # Añadir línea de tendencia
    if len(df_valid) > 1:
        # Calcular regresión lineal
        z = np.polyfit(df_valid[x_var], df_valid[y_var], 1)
        p = np.poly1d(z)
        
        fig.add_trace(go.Scatter(
            x=df_valid[x_var],
            y=p(df_valid[x_var]),
            mode='lines',
            name='Tendencia',
            line=dict(color='red', dash='dash')
        ))
    
    fig.update_layout(height=500)
    return fig

def mostrar_estadisticas_multivariadas(df):
    """Mostrar estadísticas descriptivas multivariadas"""
    st.subheader("Estadísticas Descriptivas")
    
    # Variables principales para mostrar
    variables_principales = {
        'disponibilidad': 'Disponibilidad (MW)',
        'deficit': 'Déficit (MW)',
        'demanda': 'Demanda (MW)',
        'afectacion': 'Afectación (MW)',
        'cobertura_pct': 'Cobertura (%)',
        'total_plantas_problemas': 'Plantas con Problemas'
    }
    
    stats_data = []
    for var, label in variables_principales.items():
        if var in df.columns:
            serie = df[var].dropna()
            if not serie.empty:
                stats_data.append({
                    'Variable': label,
                    'Media': f"{serie.mean():.1f}",
                    'Mediana': f"{serie.median():.1f}",
                    'Desv. Estándar': f"{serie.std():.1f}",
                    'Mínimo': f"{serie.min():.1f}",
                    'Máximo': f"{serie.max():.1f}",
                    'Registros': len(serie)
                })
    
    if stats_data:
        st.dataframe(pd.DataFrame(stats_data), use_container_width=True, hide_index=True)

def app():
    """Función principal del módulo de análisis comparativo"""
    st.header("Análisis Comparativo y Multivariado del SEN")
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
    
    # Preparar dataframe multivariado
    try:
        df_completo = preparar_datos_multivariados(entradas)
    except Exception as e:
        st.error(f"Error al procesar los datos: {str(e)}")
        return
    
    if df_completo.empty:
        st.error("No hay datos disponibles para analizar.")
        return
    
    # Selector de fechas (igual que en deficit y disponibilidad)
    st.write("### Selecciona el rango de fechas a analizar")
    
    try:
        fecha_min_datos = df_completo.index.min().date()
        fecha_max_datos = df_completo.index.max().date()
    except Exception as e:
        st.error(f"Error al determinar el rango de fechas: {str(e)}")
        return

    col1, col2, col3 = st.columns([2, 2, 1])
    
    # Inicializar fechas por defecto
    if 'fecha_inicio_comparativas' not in st.session_state:
        st.session_state.fecha_inicio_comparativas = fecha_min_datos
    if 'fecha_fin_comparativas' not in st.session_state:
        st.session_state.fecha_fin_comparativas = fecha_max_datos
    
    with col1:
        fecha_inicio = st.date_input(
            "Fecha de inicio",
            value=st.session_state.fecha_inicio_comparativas,
            key="fecha_inicio_comparativas_input"
        )
    
    with col2:
        fecha_fin = st.date_input(
            "Fecha de fin",
            value=st.session_state.fecha_fin_comparativas,
            key="fecha_fin_comparativas_input"
        )
    
    with col3:
        if st.button("Ver todo", key="ver_todo_comparativas"):
            st.session_state.fecha_inicio_comparativas = fecha_min_datos
            st.session_state.fecha_fin_comparativas = fecha_max_datos
            st.rerun()
    
    # Actualizar session state
    st.session_state.fecha_inicio_comparativas = fecha_inicio
    st.session_state.fecha_fin_comparativas = fecha_fin
    
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
    
    df = df_completo[(df_completo.index >= inicio_dt) & (df_completo.index <= fin_dt)].copy()
    
    if df.empty:
        st.warning("No hay datos disponibles para el rango de fechas seleccionado.")
        return
    
    # Gráfico principal adversarial
    st.write("### Déficit vs Disponibilidad - Análisis Adversarial")
    st.info("🟢 Verde: Disponibilidad > Déficit (Situación favorable) | 🔴 Rojo: Déficit > Disponibilidad (Situación crítica)")
    
    fig_principal = crear_grafico_adversarial_principal(df, fecha_inicio, fecha_fin)
    if fig_principal:
        st.plotly_chart(fig_principal, use_container_width=True)
    else:
        st.warning("No hay datos suficientes para crear el gráfico principal.")
    
    # Pestañas para diferentes análisis
    tab1, tab2, tab3, tab4 = st.tabs([
        "Estadísticas Multivariadas",
        "Correlaciones",
        "Análisis de Dispersión", 
        "Factores Externos"
    ])
    
    with tab1:
        mostrar_estadisticas_multivariadas(df)
        
        # Análisis de cobertura vs déficit
        st.subheader("Análisis de Cobertura de Demanda")
        
        if 'cobertura_pct' in df.columns:
            df_cobertura = df.dropna(subset=['cobertura_pct'])
            
            if not df_cobertura.empty:
                # Métricas de cobertura
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    cobertura_promedio = df_cobertura['cobertura_pct'].mean()
                    st.metric("Cobertura Promedio", f"{cobertura_promedio:.1f}%")
                
                with col2:
                    dias_cobertura_completa = len(df_cobertura[df_cobertura['cobertura_pct'] >= 100])
                    pct_dias_completa = (dias_cobertura_completa / len(df_cobertura)) * 100
                    st.metric("Días con Cobertura Completa", f"{dias_cobertura_completa} ({pct_dias_completa:.1f}%)")
                
                with col3:
                    cobertura_min = df_cobertura['cobertura_pct'].min()
                    st.metric("Cobertura Mínima", f"{cobertura_min:.1f}%")
                
                with col4:
                    cobertura_max = df_cobertura['cobertura_pct'].max()
                    st.metric("Cobertura Máxima", f"{cobertura_max:.1f}%")
                
                # Histograma de cobertura
                fig_hist = px.histogram(
                    df_cobertura,
                    x='cobertura_pct',
                    nbins=30,
                    title="Distribución de Cobertura de Demanda (%)",
                    labels={'cobertura_pct': 'Cobertura (%)', 'count': 'Días'}
                )
                fig_hist.add_vline(x=100, line_dash="dash", line_color="red", 
                                  annotation_text="Cobertura Completa (100%)")
                fig_hist.update_layout(height=400)
                st.plotly_chart(fig_hist, use_container_width=True)
    
    with tab2:
        st.subheader("Análisis de Correlaciones")
        
        # Matriz de correlación
        fig_corr = crear_matriz_correlacion(df)
        st.plotly_chart(fig_corr, use_container_width=True)
        
        # Correlaciones más fuertes
        variables_numericas = df.select_dtypes(include=[np.number]).columns.tolist()
        if len(variables_numericas) > 1:
            corr_matrix = df[variables_numericas].corr()
            
            # Encontrar correlaciones más fuertes (excluyendo diagonal)
            correlaciones_fuertes = []
            for i in range(len(corr_matrix.columns)):
                for j in range(i+1, len(corr_matrix.columns)):
                    var1 = corr_matrix.columns[i]
                    var2 = corr_matrix.columns[j]
                    corr_val = corr_matrix.iloc[i, j]
                    
                    if not pd.isna(corr_val) and abs(corr_val) > 0.5:
                        correlaciones_fuertes.append({
                            'Variable 1': var1,
                            'Variable 2': var2,
                            'Correlación': f"{corr_val:.3f}",
                            'Fuerza': 'Muy Alta' if abs(corr_val) > 0.8 else 'Alta'
                        })
            
            if correlaciones_fuertes:
                st.write("#### Correlaciones más significativas (|r| > 0.5)")
                st.dataframe(
                    pd.DataFrame(correlaciones_fuertes).sort_values('Correlación', key=lambda x: abs(x.astype(float)), ascending=False),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No se encontraron correlaciones significativas entre las variables.")
    
    with tab3:
        st.subheader("Análisis de Dispersión")
        
        # Selectores para variables
        variables_disponibles = {
            'disponibilidad': 'Disponibilidad (MW)',
            'deficit': 'Déficit (MW)',
            'demanda': 'Demanda (MW)',
            'afectacion': 'Afectación (MW)',
            'total_plantas_problemas': 'Plantas con Problemas',
            'motores_impacto_mw': 'Impacto Motores (MW)',
            'solar_parques': 'Parques Solares',
            'cobertura_pct': 'Cobertura (%)'
        }
        
        # Filtrar variables que existen en los datos
        variables_existentes = {k: v for k, v in variables_disponibles.items() if k in df.columns}
        
        if len(variables_existentes) >= 2:
            col1, col2 = st.columns(2)
            
            with col1:
                x_var = st.selectbox(
                    "Variable X",
                    list(variables_existentes.keys()),
                    format_func=lambda x: variables_existentes[x],
                    key="scatter_x"
                )
            
            with col2:
                y_var = st.selectbox(
                    "Variable Y",
                    list(variables_existentes.keys()),
                    format_func=lambda x: variables_existentes[x],
                    index=1 if len(variables_existentes) > 1 else 0,
                    key="scatter_y"
                )
            
            if x_var != y_var:
                fig_scatter = crear_grafico_dispersion(df, x_var, y_var)
                if fig_scatter:
                    st.plotly_chart(fig_scatter, use_container_width=True)
                    
                    # Calcular y mostrar correlación
                    df_valid = df.dropna(subset=[x_var, y_var])
                    if len(df_valid) > 1:
                        correlacion = df_valid[x_var].corr(df_valid[y_var])
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Coeficiente de Correlación", f"{correlacion:.4f}")
                        with col2:
                            if abs(correlacion) < 0.2:
                                interpretacion = "Muy baja"
                            elif abs(correlacion) < 0.4:
                                interpretacion = "Baja"
                            elif abs(correlacion) < 0.6:
                                interpretacion = "Moderada"
                            elif abs(correlacion) < 0.8:
                                interpretacion = "Alta"
                            else:
                                interpretacion = "Muy alta"
                            
                            st.metric("Interpretación", interpretacion)
                else:
                    st.warning("No hay datos suficientes para crear el gráfico de dispersión.")
            else:
                st.warning("Por favor seleccione dos variables diferentes.")
        else:
            st.warning("No hay suficientes variables numéricas para crear gráficos de dispersión.")
    
    with tab4:
        st.subheader("Factores Externos y Energía Renovable")
        
        # Análisis de energía solar
        if 'solar_parques' in df.columns and 'solar_produccion_mwh' in df.columns:
            df_solar = df.dropna(subset=['solar_parques', 'solar_produccion_mwh'])
            
            if not df_solar.empty and df_solar['solar_parques'].sum() > 0:
                st.write("#### Impacto de la Energía Solar")
                
                # Métricas solares
                col1, col2, col3 = st.columns(3)
                with col1:
                    promedio_parques = df_solar['solar_parques'].mean()
                    st.metric("Parques Promedio", f"{promedio_parques:.1f}")
                
                with col2:
                    produccion_total = df_solar['solar_produccion_mwh'].sum()
                    st.metric("Producción Total", f"{produccion_total:.1f} MWh")
                
                with col3:
                    produccion_promedio = df_solar['solar_produccion_mwh'].mean()
                    st.metric("Producción Promedio", f"{produccion_promedio:.1f} MWh/día")
                
                # Gráfico de evolución solar
                fig_solar = go.Figure()
                
                fig_solar.add_trace(go.Scatter(
                    x=df_solar.index,
                    y=df_solar['solar_parques'],
                    mode='lines+markers',
                    name='Parques Solares',
                    yaxis='y',
                    line=dict(color='orange')
                ))
                
                fig_solar.add_trace(go.Scatter(
                    x=df_solar.index,
                    y=df_solar['solar_produccion_mwh'],
                    mode='lines+markers',
                    name='Producción (MWh)',
                    yaxis='y2',
                    line=dict(color='gold')
                ))
                
                fig_solar.update_layout(
                    title="Evolución de la Energía Solar",
                    xaxis_title="Fecha",
                    yaxis=dict(title="Número de Parques", side="left"),
                    yaxis2=dict(title="Producción (MWh)", side="right", overlaying="y"),
                    legend=dict(x=0.01, y=0.99),
                    height=400
                )
                
                st.plotly_chart(fig_solar, use_container_width=True)
            else:
                st.info("No hay datos de energía solar disponibles para el período seleccionado.")
        
        # Análisis de motores distribuidos
        if 'motores_impacto_mw' in df.columns:
            df_motores = df.dropna(subset=['motores_impacto_mw'])
            
            if not df_motores.empty and df_motores['motores_impacto_mw'].sum() > 0:
                st.write("#### Impacto de Motores Distribuidos")
                
                # Métricas de motores
                col1, col2, col3 = st.columns(3)
                with col1:
                    impacto_promedio = df_motores['motores_impacto_mw'].mean()
                    st.metric("Impacto Promedio", f"{impacto_promedio:.1f} MW")
                
                with col2:
                    impacto_maximo = df_motores['motores_impacto_mw'].max()
                    st.metric("Impacto Máximo", f"{impacto_maximo:.1f} MW")
                
                with col3:
                    dias_con_problemas = len(df_motores[df_motores['motores_impacto_mw'] > 0])
                    pct_dias_problemas = (dias_con_problemas / len(df_motores)) * 100
                    st.metric("Días con Problemas", f"{dias_con_problemas} ({pct_dias_problemas:.1f}%)")
                
                # Gráfico de impacto de motores vs déficit
                if 'deficit' in df.columns:
                    fig_motores = px.scatter(
                        df_motores.reset_index(),
                        x='motores_impacto_mw',
                        y='deficit',
                        hover_data=['fecha'],
                        title="Relación entre Impacto de Motores y Déficit",
                        labels={
                            'motores_impacto_mw': 'Impacto Motores (MW)',
                            'deficit': 'Déficit (MW)'
                        }
                    )
                    fig_motores.update_layout(height=400)
                    st.plotly_chart(fig_motores, use_container_width=True)
            else:
                st.info("No hay datos de motores distribuidos disponibles para el período seleccionado.")
# Actualización de Datos del Sistema Eléctrico Nacional (SEN)

Este documento describe el proceso completo para actualizar los datos del SEN desde la última fecha disponible hasta la fecha actual.

## 🎯 Resumen del Proceso

El sistema mantiene datos estructurados sobre afectaciones eléctricas en Cuba, obtenidos automáticamente desde CubaDebate y procesados con LLM (Llama 3.3). La actualización incremental permite obtener solo los datos nuevos desde la última fecha registrada.

## 📋 Requisitos Previos

1. **API Key de Fireworks.ai**: Necesaria para el procesamiento con LLM
2. **Python 3.8+** con dependencias instaladas
3. **Conexión a internet** para scraping y API calls

### Configuración de API Key

```bash
# Opción 1: Variable de entorno (recomendado)
export FIREWORKS_API_KEY="tu-api-key-aqui"

# Opción 2: En Windows
set FIREWORKS_API_KEY=tu-api-key-aqui

# Opción 3: Archivo .env
echo "FIREWORKS_API_KEY=tu-api-key-aqui" >> .env
```

## 🚀 Métodos de Actualización

### 1. Actualización Automática (Recomendado)

El script `actualizar_datos.py` detecta automáticamente la última fecha disponible y actualiza hasta hoy:

```bash
# Actualización automática desde la última fecha
python actualizar_datos.py

# Con API key específica
python actualizar_datos.py --api-key "tu-api-key"

# Especificar número de páginas manualmente
python actualizar_datos.py --paginas 5

# Procesar todos los artículos (recrear JSON completo)
python actualizar_datos.py --force-all
```

### 2. Actualización Manual con daily_pipeline.py

Para control más granular del proceso:

```bash
# Actualización incremental (últimas 3 páginas)
python scraping/daily_pipeline.py --pages_lookback 3 --analize_all False

# Procesar todos los artículos disponibles
python scraping/daily_pipeline.py --analize_all True

# Rango específico de páginas
python scraping/daily_pipeline.py --a 300 --b 310 --pages_lookback 1
```

### 3. Solo Extracción JSON (datos ya descargados)

Si ya tienes artículos descargados y solo necesitas extraer datos estructurados:

```bash
python extract_json.py
```

## 📁 Estructura de Datos

```
data/
├── daily/                     # Datos organizados por día
│   ├── 2025-05-23/           # Último día disponible
│   │   └── datos_electricos_organizados.json
│   ├── articulos_2025-05-23.csv
│   └── ...
├── processed/                 # JSON principal consolidado
│   └── datos_electricos_organizados.json
└── raw/                      # Datos crudos
    └── afectaciones_electricas_cubadebate_*.csv
```

## 🔍 Verificación de Actualización

### Verificar última fecha disponible

```bash
# Ver directorios de fechas disponibles
ls data/daily/

# Ver contenido de la última fecha
ls data/daily/2025-05-23/
```

### Verificar logs de ejecución

```bash
# Ver logs del pipeline
cat logs/pipeline.log

# Ver últimas líneas de log
tail -20 logs/pipeline.log
```

### Verificar datos JSON actualizados

```python
import json
with open('data/processed/datos_electricos_organizados.json', 'r') as f:
    data = json.load(f)

# Ver años disponibles
print(list(data.keys()))

# Ver meses del 2025
print(list(data['2025'].keys()))

# Contar entradas por mes
for mes, entradas in data['2025'].items():
    print(f"{mes}: {len(entradas)} entradas")
```

## ⚡ Flujo de Trabajo Típico

1. **Ejecutar actualización automática**:
   ```bash
   python actualizar_datos.py
   ```

2. **Verificar que se encontraron datos nuevos**:
   - Revisar logs para confirmar artículos procesados
   - Verificar nuevas fechas en `data/daily/`

3. **Ejecutar aplicación Streamlit**:
   ```bash
   streamlit run streamlit_app.py
   ```

4. **Verificar datos en la interfaz**:
   - Módulo "Inicio" debe mostrar datos del último día
   - Módulos de análisis deben incluir nuevas fechas

## 🔧 Solución de Problemas

### Error: "No se encontró API key"
```bash
# Verificar variable de entorno
echo $FIREWORKS_API_KEY

# Si está vacía, configurarla
export FIREWORKS_API_KEY="tu-api-key"
```

### Error: "No se encontraron artículos nuevos"
```bash
# Aumentar el rango de búsqueda
python actualizar_datos.py --paginas 10

# O forzar reprocesamiento completo
python actualizar_datos.py --force-all
```

### Error: "Error en extracción JSON"
- Verificar conexión a internet
- Verificar que la API key sea válida
- Revisar logs en `logs/pipeline.log`

### Datos incompletos o inconsistentes
```bash
# Regenerar JSON completo desde artículos existentes
python actualizar_datos.py --force-all
```

## 📅 Automatización

### En Linux/Mac (usando cron)
```bash
# Editar crontab
crontab -e

# Agregar línea para ejecutar diariamente a las 9 AM
0 9 * * * cd /ruta/al/proyecto && python actualizar_datos.py >> logs/cron.log 2>&1
```

### En Windows (Programador de tareas)
1. Crear archivo `actualizar.bat`:
   ```bat
   @echo off
   set FIREWORKS_API_KEY=tu-api-key
   cd /d C:\ruta\al\proyecto
   python actualizar_datos.py >> logs/windows_scheduler.log 2>&1
   ```

2. Programar tarea en Windows para ejecutar el batch diariamente

## 📊 Integración con Streamlit

Una vez actualizados los datos, la aplicación Streamlit detectará automáticamente:

- **Nuevas fechas** en selectores de rango
- **Datos actualizados** en gráficos y tablas
- **Indicadores del último día** en el módulo Inicio

## 💡 Consejos Adicionales

1. **Actualización frecuente**: Ejecutar el script diariamente previene acumulación de artículos
2. **Monitoreo de logs**: Revisar regularmente `logs/pipeline.log` para detectar problemas
3. **Backup de datos**: Hacer backup periódico de `data/processed/` 
4. **Testing**: Usar `--paginas 1` para pruebas rápidas
5. **Recuperación**: En caso de problemas, usar `--force-all` para regenerar todo

## 🔗 Archivos Relacionados

- `actualizar_datos.py` - Script principal de actualización
- `scraping/daily_pipeline.py` - Pipeline de scraping y procesamiento  
- `extract_json.py` - Extractor de datos estructurados con LLM
- `template.json` - Plantilla de estructura de datos
- `streamlit_app.py` - Aplicación de visualización

#!/usr/bin/env python3
"""
Script para actualizar datos del SEN desde la última fecha disponible hasta la fecha actual.
Este script automáticamente detecta la última fecha con datos y ejecuta el pipeline
para obtener información nueva desde CubaDebate.
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Agregar el directorio del proyecto al path
project_dir = Path(__file__).parent
sys.path.append(str(project_dir))

from scraping.daily_pipeline import DailyPipeline


def obtener_ultima_fecha_disponible(data_dir="data"):
    """
    Obtiene la última fecha disponible en los datos.
    
    Args:
        data_dir (str): Directorio de datos
        
    Returns:
        str: Última fecha en formato YYYY-MM-DD, o None si no hay datos
    """
    # Verificar datos en el directorio daily
    daily_dir = Path(data_dir) / "daily"
    
    if not daily_dir.exists():
        logger.warning("No se encontró el directorio de datos diarios")
        return None
    
    # Buscar directorios de fechas (formato YYYY-MM-DD)
    fecha_dirs = []
    for item in daily_dir.iterdir():
        if item.is_dir() and len(item.name) == 10 and item.name.count('-') == 2:
            try:
                # Validar que sea una fecha válida
                datetime.strptime(item.name, '%Y-%m-%d')
                fecha_dirs.append(item.name)
            except ValueError:
                continue
    
    if not fecha_dirs:
        logger.warning("No se encontraron directorios de fechas válidos")
        return None
    
    # Ordenar y obtener la última fecha
    fecha_dirs.sort()
    ultima_fecha = fecha_dirs[-1]
    
    logger.info(f"Última fecha disponible: {ultima_fecha}")
    return ultima_fecha


def calcular_paginas_necesarias(ultima_fecha, fecha_actual=None):
    """
    Calcula el número de páginas necesarias para buscar artículos.
    
    Args:
        ultima_fecha (str): Última fecha disponible en formato YYYY-MM-DD
        fecha_actual (str): Fecha actual (opcional)
        
    Returns:
        int: Número de páginas a revisar
    """
    if fecha_actual is None:
        fecha_actual = datetime.now().strftime('%Y-%m-%d')
    
    try:
        fecha_ultimo = datetime.strptime(ultima_fecha, '%Y-%m-%d')
        fecha_hoy = datetime.strptime(fecha_actual, '%Y-%m-%d')
        
        # Calcular días de diferencia
        diferencia_dias = (fecha_hoy - fecha_ultimo).days
        
        # Calcular páginas necesarias (aproximadamente 1-2 artículos por día)
        # Agregamos margen de seguridad
        paginas_necesarias = max(1, min(diferencia_dias + 2, 10))
        
        logger.info(f"Diferencia de días: {diferencia_dias}")
        logger.info(f"Páginas necesarias: {paginas_necesarias}")
        
        return paginas_necesarias
        
    except ValueError as e:
        logger.error(f"Error calculando páginas necesarias: {e}")
        return 3  # Valor por defecto


def ejecutar_actualizacion(api_key, paginas_necesarias=None, modelo=None, force_all=False):
    """
    Ejecuta el pipeline de actualización de datos.
    
    Args:
        api_key (str): API key de Fireworks.ai
        paginas_necesarias (int): Número de páginas a revisar
        modelo (str): Modelo de LLM a utilizar
        force_all (bool): Si True, procesa todos los artículos disponibles
        
    Returns:
        bool: True si la actualización fue exitosa
    """
    try:
        # Configurar valores por defecto
        if modelo is None:
            modelo = "accounts/fireworks/models/llama-v3p1-8b-instruct"
        
        if paginas_necesarias is None:
            paginas_necesarias = 3
        
        logger.info("Iniciando pipeline de actualización de datos")
        logger.info(f"Modelo: {modelo}")
        logger.info(f"Páginas a revisar: {paginas_necesarias}")
        logger.info(f"Procesar todos los artículos: {force_all}")
        
        # Crear instancia del pipeline
        pipeline = DailyPipeline(
            api_key=api_key,
            model=modelo,
            template_path="template.json",
            data_dir="data",
            days_lookback=paginas_necesarias
        )
        
        # Ejecutar pipeline
        resultado = pipeline.run(analize_all=force_all)
        
        if isinstance(resultado, int) and resultado == 2:
            logger.info("✅ No hay nuevos artículos para procesar")
            return True
        elif resultado:
            logger.info("✅ Actualización completada exitosamente")
            return True
        else:
            logger.error("❌ Error durante la actualización")
            return False
            
    except Exception as e:
        logger.error(f"Error ejecutando actualización: {e}")
        return False


def main():
    """Función principal"""
    parser = argparse.ArgumentParser(
        description="Actualizar datos del SEN desde la última fecha disponible"
    )
    parser.add_argument(
        "--api-key", 
        type=str, 
        help="API key de Fireworks.ai (también se puede usar la variable FIREWORKS_API_KEY)"
    )
    parser.add_argument(
        "--modelo", 
        type=str, 
        default="accounts/fireworks/models/llama-v3p1-8b-instruct",
        help="Modelo de LLM a utilizar"
    )
    parser.add_argument(
        "--paginas", 
        type=int, 
        help="Número específico de páginas a revisar (opcional)"
    )
    parser.add_argument(
        "--force-all", 
        action="store_true",
        help="Procesar todos los artículos disponibles (recrear JSON completo)"
    )
    parser.add_argument(
        "--data-dir", 
        type=str, 
        default="data",
        help="Directorio de datos"
    )
    
    args = parser.parse_args()
    
    # Obtener API key
    api_key = args.api_key or os.getenv("FIREWORKS_API_KEY")
    if not api_key:
        logger.error("❌ No se encontró API key. Use --api-key o configure FIREWORKS_API_KEY")
        sys.exit(1)
    
    # Verificar que el directorio de datos existe
    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        logger.error(f"❌ No se encontró el directorio de datos: {data_dir}")
        sys.exit(1)
    
    # Si se especifica force-all, procesar todos los artículos
    if args.force_all:
        logger.info("🔄 Modo force-all activado: procesando todos los artículos")
        success = ejecutar_actualizacion(
            api_key=api_key,
            modelo=args.modelo,
            force_all=True
        )
        sys.exit(0 if success else 1)
    
    # Obtener última fecha disponible
    ultima_fecha = obtener_ultima_fecha_disponible(args.data_dir)
    
    if ultima_fecha is None:
        logger.warning("⚠️  No se encontraron datos previos. Ejecutando búsqueda inicial...")
        paginas_necesarias = args.paginas or 5
    else:
        # Calcular páginas necesarias basado en la última fecha
        paginas_necesarias = args.paginas or calcular_paginas_necesarias(ultima_fecha)
    
    # Ejecutar actualización
    logger.info(f"🚀 Iniciando actualización desde {ultima_fecha or 'inicio'}")
    success = ejecutar_actualizacion(
        api_key=api_key,
        paginas_necesarias=paginas_necesarias,
        modelo=args.modelo,
        force_all=False
    )
    
    if success:
        logger.info("✅ Actualización completada exitosamente")
        logger.info("📊 Los datos están listos para visualización en Streamlit")
        sys.exit(0)
    else:
        logger.error("❌ Error durante la actualización")
        sys.exit(1)


if __name__ == "__main__":
    main()

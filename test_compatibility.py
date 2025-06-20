"""
Script para probar la compatibilidad de datos entre local y deploy
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'Visualizacion'))
from utils import cargar_datos, preparar_dataframe_basico, filtrar_datos_por_metrica

def test_carga_datos():
    print("🔄 Probando carga de datos...")
    try:
        entradas = cargar_datos()
        print(f"✅ Datos cargados: {len(entradas)} entradas")
        
        # Probar preparación de dataframe básico
        df_basico = preparar_dataframe_basico(entradas)
        print(f"✅ DataFrame básico: {df_basico.shape}")
        print(f"   Tipos de datos: {dict(df_basico.dtypes)}")
        
        # Probar filtrado por déficit
        df_deficit = filtrar_datos_por_metrica(entradas, "deficit")
        print(f"✅ DataFrame déficit: {df_deficit.shape}")
        
        # Verificar datos nulos
        print("\n📊 Análisis de datos nulos:")
        for col in df_deficit.columns:
            nulos = df_deficit[col].isnull().sum()
            total = len(df_deficit)
            porcentaje = (nulos / total) * 100 if total > 0 else 0
            print(f"   {col}: {nulos}/{total} ({porcentaje:.1f}%)")
        
        # Verificar tipos problemáticos
        print("\n🔍 Verificando tipos problemáticos:")
        for col in df_deficit.columns:
            if col != 'enlace':
                dtype = df_deficit[col].dtype
                if dtype == 'object':
                    valores_ejemplo = df_deficit[col].dropna().head(3).tolist()
                    print(f"   {col} (object): {valores_ejemplo}")
                elif 'float' in str(dtype) or 'int' in str(dtype):
                    valores_ejemplo = df_deficit[col].dropna().head(3).tolist()
                    print(f"   {col} ({dtype}): {valores_ejemplo}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en carga de datos: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_graficos():
    print("\n🔄 Probando generación de gráficos...")
    try:
        from utils import crear_grafico_linea_plotly
        entradas = cargar_datos()
        df_deficit = filtrar_datos_por_metrica(entradas, "deficit")
        
        # Crear gráfico de prueba
        df_test = df_deficit.head(100).reset_index()
        fig = crear_grafico_linea_plotly(
            df_test, 
            'fecha', 
            'deficit', 
            title="Prueba de gráfico"
        )
        
        print("✅ Gráfico creado exitosamente")
        print(f"   Tipo de figura: {type(fig)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en generación de gráficos: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 Ejecutando pruebas de compatibilidad...")
    print("=" * 50)
    
    success = True
    success &= test_carga_datos()
    success &= test_graficos()
    
    print("=" * 50)
    if success:
        print("✅ Todas las pruebas pasaron correctamente")
    else:
        print("❌ Algunas pruebas fallaron")
        sys.exit(1)

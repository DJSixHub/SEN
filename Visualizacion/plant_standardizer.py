


PLANTAS_CANONICAS = [
    "Antonio Guiteras, Matanzas",                    # CTE Antonio Guiteras
    "Lidio Ramón Pérez (Felton), Holguín",         # CTE Felton
    "Antonio Maceo (Renté), Santiago de Cuba",      # CTE Renté
    "Ernesto Guevara (Santa Cruz), Mayabeque",     # CTE Santa Cruz
    "Carlos Manuel de Céspedes (Cienfuegos), Cienfuegos",  # CTE Cienfuegos
    "Máximo Gómez (Mariel), Artemisa",             # CTE Mariel    "10 de Octubre (Nuevitas), Camagüey",          # CTE Nuevitas
    "Otto Parellada (Tallapiedra), La Habana",     # CTE Tallapiedra/Otto Parellada/CTE Habana
    
    # Otras plantas o centrales de generación
    "Energas Boca de Jaruco, Mayabeque",           # Generación con gas (incluye Energas Jaruco)
    "Energas Varadero, Matanzas",                  # Generación con gas
    "Boca de Jaruco, Mayabeque",                   # Central eléctrica
]

# Mapeo de todas las variantes de nombres a su forma canónica
PLANT_NAME_MAPPING = {    # Antonio Guiteras (Matanzas)
    "Antonio Guiteras": "Antonio Guiteras, Matanzas",
    "CTE Antonio Guiteras": "Antonio Guiteras, Matanzas",
    "CTE Guiteras": "Antonio Guiteras, Matanzas",
    "Guiteras": "Antonio Guiteras, Matanzas",
    "Central Termoeléctrica Antonio Guiteras": "Antonio Guiteras, Matanzas",
    "termoeléctrica Antonio Guiteras": "Antonio Guiteras, Matanzas",
    "Central Termoeléctrica (CTE) Antonio Guiteras": "Antonio Guiteras, Matanzas",
    "CTE de Matanzas": "Antonio Guiteras, Matanzas",
    "CTE Matanzas": "Antonio Guiteras, Matanzas",
      # Felton (Lidio Ramón Pérez, Holguín)
    "Felton": "Lidio Ramón Pérez (Felton), Holguín",
    "CTE Felton": "Lidio Ramón Pérez (Felton), Holguín",
    "CTE de Felton": "Lidio Ramón Pérez (Felton), Holguín",
    "CTE Felto": "Lidio Ramón Pérez (Felton), Holguín",
    "Lidio Ramón Pérez": "Lidio Ramón Pérez (Felton), Holguín",
    "CTE Lidio Ramón Pérez": "Lidio Ramón Pérez (Felton), Holguín",
    "CTE Lidio Ramón Pérez (Felton)": "Lidio Ramón Pérez (Felton), Holguín",
    "Central Termoeléctrica (CTE) Felton": "Lidio Ramón Pérez (Felton), Holguín",
    "Central Termoeléctrica Felton 1": "Lidio Ramón Pérez (Felton), Holguín",
    "Feltón 2": "Lidio Ramón Pérez (Felton), Holguín",
    "CTE ETE Lidio Ramón Pérez Felton": "Lidio Ramón Pérez (Felton), Holguín",
    "Lidio Ramón Pérez (Holguín)": "Lidio Ramón Pérez (Felton), Holguín",
      # Renté (Antonio Maceo, Santiago de Cuba)
    "Renté": "Antonio Maceo (Renté), Santiago de Cuba",
    "Rente": "Antonio Maceo (Renté), Santiago de Cuba",
    "CTE Renté": "Antonio Maceo (Renté), Santiago de Cuba",
    "CTE Rente": "Antonio Maceo (Renté), Santiago de Cuba",
    "termoeléctrica Renté": "Antonio Maceo (Renté), Santiago de Cuba", 
    "Antonio Maceo": "Antonio Maceo (Renté), Santiago de Cuba",
    "CTE Antonio Maceo": "Antonio Maceo (Renté), Santiago de Cuba",
    "CTE Antonio Maceo (Rente)": "Antonio Maceo (Renté), Santiago de Cuba",
    "CTE Antonio Maceo ( Rente)": "Antonio Maceo (Renté), Santiago de Cuba",
    "CTE René": "Antonio Maceo (Renté), Santiago de Cuba",
      # Santa Cruz (Ernesto Guevara, Mayabeque)
    "Santa Cruz": "Ernesto Guevara (Santa Cruz), Mayabeque",
    "CTE Santa Cruz": "Ernesto Guevara (Santa Cruz), Mayabeque",
    "Ernesto Guevara": "Ernesto Guevara (Santa Cruz), Mayabeque",
    "CTE Ernesto Guevara": "Ernesto Guevara (Santa Cruz), Mayabeque",
    "CTE Ernesto Guevara (Santa Cruz)": "Ernesto Guevara (Santa Cruz), Mayabeque",
    "CTE Ernesto Che Guevara": "Ernesto Guevara (Santa Cruz), Mayabeque",
      # Cienfuegos (Carlos Manuel de Céspedes)
    "Cienfuegos": "Carlos Manuel de Céspedes (Cienfuegos), Cienfuegos",
    "CTE Cienfuegos": "Carlos Manuel de Céspedes (Cienfuegos), Cienfuegos",
    "CTE de Cienfuegos": "Carlos Manuel de Céspedes (Cienfuegos), Cienfuegos",
    "termoeléctrica Cienfuegos": "Carlos Manuel de Céspedes (Cienfuegos), Cienfuegos",
    "Carlos Manuel de Céspedes": "Carlos Manuel de Céspedes (Cienfuegos), Cienfuegos",
    "termoeléctrica Carlos Manuel de Céspedes": "Carlos Manuel de Céspedes (Cienfuegos), Cienfuegos",
    "CTE Carlos Manuel de Céspedes": "Cienfuegos",
    "CTE Carlos Manuel de Cespedes": "Cienfuegos",    "CTE Carlos M. de Céspedes": "Carlos Manuel de Céspedes (Cienfuegos), Cienfuegos",
    "CTE Céspedes": "Carlos Manuel de Céspedes (Cienfuegos), Cienfuegos",
    "Céspedes": "Carlos Manuel de Céspedes (Cienfuegos), Cienfuegos",
    "Central Termoeléctrica de Cienfuegos Carlos Manuel de Céspedes": "Carlos Manuel de Céspedes (Cienfuegos), Cienfuegos",
    "CTE Empresa Eléctrica Cienfuegos": "Carlos Manuel de Céspedes (Cienfuegos), Cienfuegos",
    
    # Mariel (Máximo Gómez, Artemisa)
    "Mariel": "Máximo Gómez (Mariel), Artemisa",
    "CTE Mariel": "Máximo Gómez (Mariel), Artemisa",
    "termoeléctrica Mariel": "Máximo Gómez (Mariel), Artemisa",
    "Máximo Gómez": "Máximo Gómez (Mariel), Artemisa",
    "CTE Máximo Gómez": "Máximo Gómez (Mariel), Artemisa",
    "CTE Máximo Gómez (Mariel)": "Máximo Gómez (Mariel), Artemisa",
    "Máximo Gómez (Mariel)": "Máximo Gómez (Mariel), Artemisa",
    "Mariel 8": "Máximo Gómez (Mariel), Artemisa",
    "termoeléctrica del Mariel": "Máximo Gómez (Mariel), Artemisa",
      # Nuevitas (10 de Octubre, Camagüey)
    "Nuevitas": "10 de Octubre (Nuevitas), Camagüey",
    "CTE Nuevitas": "10 de Octubre (Nuevitas), Camagüey",
    "Nuevitas (Camagüey)": "10 de Octubre (Nuevitas), Camagüey",
    "Diez de Octubre": "10 de Octubre (Nuevitas), Camagüey",
    "CTE Diez de Octubre": "10 de Octubre (Nuevitas), Camagüey", 
    "CTE Diez de Octubre ( Nuevitas)": "10 de Octubre (Nuevitas), Camagüey",
    "CTE 10 de Octubre": "10 de Octubre (Nuevitas), Camagüey",
    
    # Tallapiedra y Otto Parellada (unificadas, La Habana)
    "Tallapiedra": "Otto Parellada (Tallapiedra), La Habana",
    "CTE Tallapiedra": "Otto Parellada (Tallapiedra), La Habana",
    "Talla Piedra": "Otto Parellada (Tallapiedra), La Habana",
    "CTE Talla Piedra": "Otto Parellada (Tallapiedra), La Habana",
    "Talla piedra": "Otto Parellada (Tallapiedra), La Habana",
    "Otto Parellada": "Otto Parellada (Tallapiedra), La Habana",
    "CTE Otto Parellada": "Otto Parellada (Tallapiedra), La Habana",
    
    # Otras plantas termoeléctricas
    "CTE Habana": "Otto Parellada (Tallapiedra), La Habana",
    "Habana": "Otto Parellada (Tallapiedra), La Habana",
    
    # Otras plantas o centrales
    "Energas Boca de Jaruco": "Energas Boca de Jaruco, Mayabeque",
    "Energás Boca de Jaruco": "Energas Boca de Jaruco, Mayabeque",    "Boca de Jaruco": "Boca de Jaruco, Mayabeque",
    "Energas Jaruco": "Energas Boca de Jaruco, Mayabeque",
    "Energas Varadero": "Energas Varadero, Matanzas",
    "Energas": "Energas Boca de Jaruco, Mayabeque",  # Asumimos que Energas genérico se refiere a Boca de Jaruco
    
    # Entradas problemáticas - Ignorar o tratar especialmente
    "CTE Para": None,  # No es una central real, parece ser un error
    "CTE": None,  # Demasiado genérico para ser útil
    
    # Agrupaciones que no son plantas individuales
    "CTE Santa Cruz, Cienfuegos y Renté": None,
    "Santa Cruz, Cienfuegos y Renté": None,
}

def get_canonical_plant_name(plant_name):
    """
    Convierte cualquier variante de nombre de planta termoeléctrica a su forma canónica.
    
    Args:
        plant_name (str): Nombre original de la planta termoeléctrica
        
    Returns:
        str: Nombre canónico de la planta, o el original si no hay mapeo
    """
    if not plant_name:
        return plant_name
    
    # Buscar el nombre canónico en el mapeo
    return PLANT_NAME_MAPPING.get(plant_name, plant_name)

def get_valid_plant_names():
    """
    Devuelve la lista de nombres canónicos de plantas termoeléctricas.
    
    Returns:
        list: Lista de nombres canónicos
    """
    return [p for p in PLANTAS_CANONICAS if p is not None]

def standardize_plant_data(data):
    """
    Estandariza todos los nombres de plantas en una estructura de datos.
    
    Args:
        data (dict): Estructura de datos con información de plantas
        
    Returns:
        dict: La misma estructura con nombres estandarizados
    """
    if not data:
        return data
    
    # Copia para no modificar el original
    result = data.copy()
    
    # Procesar sección 'plantas' (avería, mantenimiento)
    if 'plantas' in result:
        plantas_data = result['plantas']
        
        # Procesar avería
        if 'averia' in plantas_data and plantas_data['averia']:
            for planta in plantas_data['averia']:
                if 'planta' in planta and planta['planta']:
                    canonical = get_canonical_plant_name(planta['planta'])
                    if canonical:  # Solo actualizar si hay un nombre canónico válido
                        planta['planta'] = canonical
        
        # Procesar mantenimiento
        if 'mantenimiento' in plantas_data and plantas_data['mantenimiento']:
            for planta in plantas_data['mantenimiento']:
                if 'planta' in planta and planta['planta']:
                    canonical = get_canonical_plant_name(planta['planta'])
                    if canonical:  # Solo actualizar si hay un nombre canónico válido
                        planta['planta'] = canonical
    
    # Procesar sección 'termoelectricas' si existe
    if 'termoelectricas' in result and result['termoelectricas']:
        for planta in result['termoelectricas']:
            if 'nombre' in planta and planta['nombre']:
                canonical = get_canonical_plant_name(planta['nombre'])
                if canonical:  # Solo actualizar si hay un nombre canónico válido
                    planta['nombre'] = canonical
    
    return result

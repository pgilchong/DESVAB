
"""
    explicar módulo
"""

# ----------------------------------------------
# MÓDULOS
# ----------------------------------------------
import geopandas as gpd
import os
import pandas as pd
import time
from geo import get_poligonos_barrios
from typing import List


# ----------------------------------------------
# VALORES DE VECTORES
# ----------------------------------------------
U1 = [0, .25, .5, .75, 1] # suelo a parque, proporción


# ----------------------------------------------
# CONSTANTES
# ----------------------------------------------
# Caso base
NOMENCLATURA_CODE18 = { # nomenclatura adaptando de las tipologías de CORINE Land Cover
    'l1': ['111', '112', '121', '122', '123', '124', '142',
           '133', '331', '333', '511', '512', '523'],
    'l2': ['312',
           '231', '321', '324', '323'],
    'l3': ['212',
           '222', '242', '243'],
    'l4': ['213'],
    'l5': ['522',
           '421', '521'],
    'l6': ['141']
}
CAPTACION_CO2 = { # valores de captación de tCO2e / ha / año
    'l1': 0.0,
    'l2': 5.8,
    'l3': {
        'cítricos': 18.21,
        'no cítricos': 22.91
        },
    'l4': 7.34,
    'l5': 20.7,
    'l6': 5.9,
    'l7': 4.4
}


# ----------------------------------------------
# RUTAS Y NOMBRES DE ARCHIVOS
# ----------------------------------------------
base_path = os.path.abspath(__file__)
desvab_root = os.path.dirname(os.path.dirname(base_path))
data_path = os.path.join(desvab_root, 'datos')
urbanismo_path = os.path.join(data_path, 'urbanismo')

# Caso base
areas_path = os.path.join(urbanismo_path, 'CLC_Barris', 'CLC_Barris.shp')
barrios_path = os.path.join(data_path, 'demografia', 'barrios.xlsx')


# ----------------------------------------------
# CLASE ÁREA URBANISMO
# ----------------------------------------------
class AreaUrbanismo:
    """
    explicar clase
    """
    def __init__(
            self,
            valores_u1: List[float] = U1,
            verbose: bool = False
    ):
        """
        explicar método
        """
        # Inicializar atributos con caso base
        if verbose:
            print('Inicializando Área Urbanismo...')
            print('Calculando caso base...')
            start_time = time.time()
        self._get_caso_base()
        if verbose:
            print(f'Caso base calculado en {time.time() - start_time:.2f} s')

        # Calcular vector U1 para valores dados
        if verbose:
            print('Calculando vector U1...')
            start_time = time.time()
        self.vector_u1 = {}
        for suelo_a_parque in valores_u1:
            self.get_vector_u1(suelo_a_parque)
        if verbose:
            print(f'Vector U1 calculado en {time.time() - start_time:.2f} s')
        
        # Guardar vectores en atributo vectores
        self.vectores = {
            'U1': self.vector_u1
        }

        if verbose:
            print('Área Urbanismo inicializada.')


    # ----------------------------------------------
    # MÉTODOS PARA CÁLCULO DE CASO BASE
    # ----------------------------------------------
    def _get_areas_corine(self):
        """
        explicar método
        """
        # Leer archivo de áreas urbanas
        gdf_areas = gpd.read_file(areas_path)[['CODE_18', 'geometry']]

        # Recodificar tipologías
        gdf_areas['CODE_Area'] = gdf_areas['CODE_18'].replace(
            {v: k for k, vs in NOMENCLATURA_CODE18.items() for v in vs}
        )

        # Obtener los polígonos de los barrios y convertir a sistema de coordenadas proyectado
        gdf_barrios = get_poligonos_barrios()
        gdf_barrios.set_crs('EPSG:4326', inplace=True)
        gdf_barrios.to_crs('EPSG:25830', inplace=True)

        ### Crear dataframe con áreas por tipología y barrio
        # Spatial join entre áreas y barrios
        joined = gpd.sjoin(gdf_barrios, gdf_areas, how='inner', predicate='intersects')
        # Calcular área de intersección
        joined['intersection_area'] = joined.apply(
            lambda row: row['geometry'].intersection(gdf_areas.loc[row['index_right'], 'geometry']).area,
            axis=1
        )
        # Agrupar por ID de barrio y tipología y sumar áreas de intersección
        areas = joined.groupby(['ID', 'CODE_Area'])['intersection_area'].sum().unstack(fill_value=0)
        self.areas = areas


    def _get_demografia(self):
        """
        explicar método
        """
        # Leer archivo de datos demográficos
        barrios = pd.read_excel(barrios_path, index_col=0, skipfooter=2)
        barrios.index = barrios.index.astype(str)

        # Guardar datos
        self.barrios = barrios

    
    def _get_areas_l7(self):
        """
        explicar método
        """
        # Calcular áreas de l7 a partir de Zonas Verdes por habitante, población y áreas de l6
        self.areas['l7'] = self.barrios['ZV/hab / m2'] * self.barrios['Población'] - self.areas['l6']

        # Clip a 0 si es negativo
        self.areas['l7'] = self.areas['l7'].clip(lower=0)


    def _get_captacion(self):
        """
        explicar método
        """
        # Aplanar diccionario para simplificar operaciones
        valores_co2 = {
            k: (v['no cítricos'] if isinstance(v, dict) else v) for k, v in CAPTACION_CO2.items()
        }
        # Pasar a tCO2e / m2 / año
        valores_co2 = {k: v / 10000 for k, v in valores_co2.items()}

        # Computar captación de CO2 por tipología y barrio multiplicando áreas por valores de captación
        captacion = self.areas.multiply(pd.Series(valores_co2))

        # Ajustar l3 para 'cítricos',  barrios dels Poblats del Nord (17)
        barrios_citricos = self.areas.index.str.startswith('17')
        captacion.loc[barrios_citricos, 'l3'] = (
            self.areas.loc[barrios_citricos, 'l3'] * CAPTACION_CO2['l3']['cítricos'] / 10000
        )

        # Agrupar por barrio y sumar captación de CO2
        captacion = captacion.sum(axis=1)

        # Almacenar captación
        self.captacion = captacion
        self.huella = -captacion


    def _get_caso_base(self):
        """
        explicar método
        wrapper
        """
        self._get_areas_corine()
        self._get_demografia()
        self._get_areas_l7()
        self._get_captacion()

    
    # ----------------------------------------------
    # MÉTODOS PARA CÁLCULO DE VECTOR U1, AUMENTO DE PARQUE URBANO
    # ----------------------------------------------
    def get_vector_u1(self, suelo_a_parque: float):
        """
        explicar método
        """
        ### Recalcular áreas a partir del aumento propuesto
        # Copiar áreas originales
        areas = self.areas.copy()
        # Calcular aumento propuesto de l7
        zv_hab = self.barrios['ZV/hab / m2'] + suelo_a_parque * (self.barrios['Propuesta ZV/hab / m2'] - self.barrios['ZV/hab / m2'])
        areas['l7'] = zv_hab * self.barrios['Población'] - self.areas['l6']
        areas['l7'] = areas['l7'].clip(lower=0)
        # Calcular reducción propuesta de l1
        areas['l1'] = self.areas['l1'] - (areas['l7'] - self.areas['l7'])
        areas['l1'] = areas['l1'].clip(lower=0)

        ### Recalcular captación de CO2 para nuevo caso (ver _get_captacion)
        valores_co2 = {
            k: (v['no cítricos'] if isinstance(v, dict) else v) for k, v in CAPTACION_CO2.items()
        }
        valores_co2 = {k: v / 10000 for k, v in valores_co2.items()}
        captacion = areas.multiply(pd.Series(valores_co2))
        barrios_citricos = areas.index.str.startswith('17')
        captacion.loc[barrios_citricos, 'l3'] = (
            areas.loc[barrios_citricos, 'l3'] * CAPTACION_CO2['l3']['cítricos'] / 10000
        )
        captacion = captacion.sum(axis=1)

        # Almacenar resultado
        self.vector_u1[suelo_a_parque] = captacion

        # Devolver resultado
        return captacion
    
    
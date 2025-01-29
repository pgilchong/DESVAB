# urbanismo.py

"""
MÓDULO ÁREA URBANISMO

Este módulo contiene la clase `AreaUrbanismo`, una herramienta para gestionar
y calcular la captación de CO2 mediante el análisis de usos del suelo urbano
y espacios verdes. Permite evaluar escenarios de transformación de suelo
urbanizado a zonas verdes, calculando el potencial de secuestro de carbono
por barrio según tipologías de cobertura terrestre (CORINE Land Cover).
Incluye modelos de captación de CO2 para diferentes tipos de vegetación
y usos del terreno en el contexto urbano de València.
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
U1 = [0., .25, .5, .75, 1.] # suelo a parque, proporción


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
BASE_PATH = os.path.abspath(__file__)
DESVAB_ROOT = os.path.dirname(os.path.dirname(BASE_PATH))
DATA_PATH = os.path.join(DESVAB_ROOT, 'datos')
URBANISMO_PATH = os.path.join(DATA_PATH, 'urbanismo')

# Caso base
AREAS_PATH = os.path.join(URBANISMO_PATH, 'CLC_Barris', 'CLC_Barris.shp')
BARRIOS_PATH = os.path.join(DATA_PATH, 'demografia', 'barrios.xlsx')


# ----------------------------------------------
# CLASE ÁREA URBANISMO
# ----------------------------------------------
class AreaUrbanismo:
    """
    Clase para gestionar y calcular el impacto ambiental de la planificación
    urbana mediante el análisis de usos del suelo. Permite cuantificar la
    capacidad de secuestro de carbono de las áreas verdes existentes y
    proyectadas, evaluando escenarios de renaturalización urbana y expansión
    de infraestructura verde.
    """
    def __init__(
            self,
            valores_u1: List[float] = U1,
            verbose: bool = False
            ) -> None:
        """
        Inicializa una instancia de la clase AreaUrbanismo, calculando el caso base
        y el vector U1 para los valores especificados.

        Args:
            - valores_u1 (list, opcional):
                Lista de porcentajes de conversión de suelo urbanizado a parques
                urbanos a evaluar. Por defecto, [0, .25, .5, .75, 1].
            - verbose (bool, opcional):
                Indica si se deben imprimir mensajes informativos.
                Por defecto, False.
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
        Procesa los datos CORINE Land Cover para calcular la distribución de
        usos del suelo por barrio.

        Este método realiza un análisis espacial de superposición entre las
        áreas de cobertura terrestre y los límites de barrios, calculando la
        superficie de cada tipología de uso del suelo en cada barrio.
        """
        # Leer archivo de áreas urbanas
        gdf_areas = gpd.read_file(AREAS_PATH)[['CODE_18', 'geometry']]

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
        Carga y procesa los datos demográficos por barrio, incluyendo población
        y métricas de zonas verdes por habitante.

        Establece la base para el cálculo de necesidades y potencial de
        expansión de áreas verdes urbanas.
        """
        # Leer archivo de datos demográficos
        barrios = pd.read_excel(BARRIOS_PATH, index_col=0, skipfooter=2)
        barrios.index = barrios.index.astype(str)

        # Guardar datos
        self.barrios = barrios

    
    def _get_areas_l7(self):
        """
        Calcula las áreas de zonas verdes (l7) a partir de indicadores
        urbanísticos y demográficos.

        Considera los estándares actuales y propuestos de metros cuadrados
        de zona verde por habitante, ajustando las superficies existentes
        de áreas naturales (l6).
        """
        # Calcular áreas de l7 a partir de Zonas Verdes por habitante, población y áreas de l6
        self.areas['l7'] = self.barrios['ZV/hab / m2'] * self.barrios['Población'] - self.areas['l6']

        # Clip a 0 si es negativo
        self.areas['l7'] = self.areas['l7'].clip(lower=0)


    def _get_captacion(self):
        """
        Calcula la captación neta de CO2 por barrio basada en los usos del suelo.

        Aplica tasas específicas de secuestro de carbono por tipología de
        cobertura terrestre, considerando variaciones regionales (ej. cultivos
        cítricos en Poblats del Nord) y ajustando unidades de superficie.
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
        Coordina el cálculo completo del caso base integrando datos de usos
        del suelo, información demográfica y modelos de captación de CO2.
        """
        self._get_areas_corine()
        self._get_demografia()
        self._get_areas_l7()
        self._get_captacion()

    
    # ----------------------------------------------
    # MÉTODOS PARA CÁLCULO DE VECTOR U1, AUMENTO DE PARQUE URBANO
    # ----------------------------------------------
    def get_vector_u1(
            self,
            suelo_a_parque: float
            ) -> pd.Series:
        """
        Calcula el impacto ambiental para un escenario específico de conversión
        de suelo urbanizado a zonas verdes.

        Args:
            - suelo_a_parque (float):
                Proporción de conversión de áreas urbanas a parques (entre 0 y 1),
                donde 1 representa el cumplimiento total de la propuesta de
                zonas verdes por habitante.

        Devuelve:
            - huella (pd.Series):
                Huella de carbono negativa (secuestro) por barrio en tCO2e,
                resultante del aumento de superficie verde y reducción de
                áreas urbanizadas.
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
        huella = -captacion

        # Almacenar resultado
        self.vector_u1[suelo_a_parque] = huella

        # Devolver resultado
        return huella
    
    
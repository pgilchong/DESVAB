# residuos.py

"""
MÓDULO ÁREA RESIDUOS

Este módulo contiene la clase `AreaResiduos`, una herramienta para gestionar
y calcular las emisiones de CO2 asociadas a la generación y tratamiento de
residuos urbanos. Permite analizar el impacto ambiental de diferentes estrategias
de reducción de residuos y mejora de tasas de reciclaje, considerando la
distribución demográfica y socioeconómica por barrio. Incluye modelos para
evaluar escenarios de economía circular y cumplimiento de objetivos europeos
de gestión de residuos en la ciudad de València.
"""


# ----------------------------------------------
# MÓDULOS
# ----------------------------------------------
import geopandas as gpd
import numpy as np
import os
import pandas as pd
import time

from math import e
from typing import List


# ----------------------------------------------
# VALORES DE VECTORES
# ----------------------------------------------
R1 = [0., .25, .5, .75, 1.] # reducción de residuos generados, proporción
R2 = [0., .25, .5, .75, 1.] # aumento de reciclaje desde caso base hasta estándar ue, proporción


# ----------------------------------------------
# CONSTANTES
# ----------------------------------------------
# Caso base
RESIDUOS_HAB = { # residuos generados por habitante y año, kg/hab/año
    'Resto': 314.42,
    'FORS': 32.99,
    'Vidrio': 18.7,
    'Papel y cartón': 26.73,
    'Envases': 20.89
}
RESIDUOS_PROP = {
    'Resto': 0.76,
    'FORS': 0.08,
    'Vidrio': 0.045,
    'Papel y cartón': 0.065,
    'Envases': 0.05

}
RESIDUOS_HAB = {k: v / 1000 for k, v in RESIDUOS_HAB.items()} # pasar a t/hab/año
TRATAMIENTO = pd.DataFrame( # % de residuos tratados por tipo de residuo y tratamiento
    [[0.08, 0.1 , 0.67, 0.15],
     [0.6 , 0.  , 0.3 , 0.1 ],
     [0.  , 0.71, 0.27, 0.02],
     [0.  , 0.6 , 0.4 , 0.  ],
     [0.  , 0.68, 0.16, 0.16]],
    index=['FORS', 'Resto', 'Envases', 'Papel y cartón', 'Vidrio'],
    columns=['Reciclaje', 'Compostaje', 'Vertido', 'Incineración']
)
FACTORES_EMISION = pd.DataFrame( # factores de emisión de CO2 por tratamiento de residuos, tCO2e/t
    [[0.17, 0.17, 0.58, 0.05],
     [0.05, 0.17, 0.52, 0.43],
     [0.22, np.nan, 0.02, 2.38],
     [0.07, np.nan, 0.89, 0.05],
     [0.05, np.nan, 0.02, 0.01]],
    index=['FORS', 'Resto', 'Envases', 'Papel y cartón', 'Vidrio'],
    columns=['Reciclaje', 'Compostaje', 'Vertido', 'Incineración']
)

# Vector R1
MAXIMO_R1 = 0.4 # reducción máxima de residuos generados, proporción

# Vector R2
ESCENARIOS_R2 = {
    0: TRATAMIENTO,
    .25: pd.DataFrame( # % de residuos tratados por tipo de residuo y tratamiento
        [[0.12, 0.22, 0.51, 0.15],
         [0.6 , 0.  , 0.3 , 0.1 ],
         [0.  , 0.75, 0.23, 0.02],
         [0.  , 0.67, 0.33, 0.  ],
         [0.  , 0.75, 0.09, 0.16]],
        index=['FORS', 'Resto', 'Envases', 'Papel y cartón', 'Vidrio'],
        columns=['Reciclaje', 'Compostaje', 'Vertido', 'Incineración']
    ),
    .5: pd.DataFrame( # % de residuos tratados por tipo de residuo y tratamiento
        [[0.12, 0.38, 0.35, 0.15],
         [0.6 , 0.  , 0.3 , 0.1 ],
         [0.  , 0.8 , 0.18, 0.02],
         [0.77, 0.23, 0.  , 0.  ],
         [0.8 , 0.04, 0.16, 0.  ]],
        index=['FORS', 'Resto', 'Envases', 'Papel y cartón', 'Vidrio'],
        columns=['Reciclaje', 'Compostaje', 'Vertido', 'Incineración']
    ),
    .75: pd.DataFrame( # % de residuos tratados por tipo de residuo y tratamiento
        [[0.12, 0.51, 0.22, 0.15],
         [0.6 , 0.  , 0.3 , 0.1 ],
         [0.  , 0.85, 0.13, 0.02],
         [0.85, 0.15, 0.  , 0.  ],
         [0.85, 0.  , 0.15, 0.  ]],
        index=['FORS', 'Resto', 'Envases', 'Papel y cartón', 'Vidrio'],
        columns=['Reciclaje', 'Compostaje', 'Vertido', 'Incineración']
    ),
    1: pd.DataFrame( # % de residuos tratados por tipo de residuo y tratamiento
        [[0.12, 0.65, 0.08, 0.15],
         [0.6 , 0.  , 0.3 , 0.1 ],
         [0.  , 0.99, 0.  , 0.01],
         [0.99, 0.01, 0.  , 0.  ],
         [0.99, 0.  , 0.01, 0.  ]],
        index=['FORS', 'Resto', 'Envases', 'Papel y cartón', 'Vidrio'],
        columns=['Reciclaje', 'Compostaje', 'Vertido', 'Incineración']
    )
}


# ----------------------------------------------
# RUTAS Y NOMBRES DE ARCHIVOS
# ----------------------------------------------
BASE_PATH = os.path.abspath(__file__)
DESVAB_ROOT = os.path.dirname(os.path.dirname(BASE_PATH))
DATA_PATH = os.path.join(DESVAB_ROOT, 'datos')
RESIDUOS_PATH = os.path.join(DATA_PATH, 'residuos')

# Caso base
BARRIOS_PATH = os.path.join(DATA_PATH, 'demografia', 'barrios.xlsx')
BETAS_PATH = os.path.join(RESIDUOS_PATH, 'betas_residuos.xlsx')


# ----------------------------------------------
# CLASE ÁREA RESIDUOS
# ----------------------------------------------
class AreaResiduos:
    """
    Clase para gestionar y calcular las emisiones asociadas a la gestión de
    residuos urbanos. Permite cuantificar la huella de carbono de diferentes
    tipos de residuos y tratamientos, evaluando escenarios de prevención en
    la generación de residuos y mejora de los sistemas de reciclaje y
    valorización material.
    """
    def __init__(
            self,
            valores_r1: List[float] = R1,
            valores_r2: List[float] = R2,
            verbose: bool = False
            ) -> None:
        """
        Inicializa una instancia de la clase AreaResiduos, calculando el caso base
        y los vectores R1 y R2 para los valores especificados.

        Args:
            - valores_r1 (list, opcional):
                Lista de porcentajes de reducción de generación de residuos a evaluar.
                Por defecto, [0, .25, .5, .75, 1].
            - valores_r2 (list, opcional):
                Lista de porcentajes de mejora en tasas de reciclaje a evaluar.
                Por defecto, [0, .25, .5, .75, 1].
            - verbose (bool, opcional):
                Indica si se deben imprimir mensajes informativos.
                Por defecto, False.
        """
        # Inicializar atributos con caso base
        if verbose:
            print('Inicializando Área Residuos...')
            print('Calculando caso base...')
            start_time = time.time()
        self._get_caso_base()
        if verbose:
            print(f'Caso base calculado en {time.time() - start_time:.2f} s')

        # Calcular vector R1 para valores dados
        if verbose:
            print('Calculando vector R1...')
            start_time = time.time()
        self.vector_r1 = {}
        for residuos_hab in valores_r1:
            self.get_vector_r1(residuos_hab)
        if verbose:
            print(f'Vector R1 calculado en {time.time() - start_time:.2f} s')

        # Calcular vector R2 para valores dados
        if verbose:
            print('Calculando vector R2...')
            start_time = time.time()
        self.vector_r2 = {}
        for tratamiento in valores_r2:
            self.get_vector_r2(tratamiento)
        if verbose:
            print(f'Vector R2 calculado en {time.time() - start_time:.2f} s')

        # Guardar vectores en atributo vectores
        self.vectores = {
            'R1': self.vector_r1,
            'R2': self.vector_r2
        }

        if verbose:
            print('Área Residuos inicializada.')

    
    # ----------------------------------------------
    # MÉTODOS PARA CÁLCULO DE CASO BASE
    # ----------------------------------------------
    def _get_demografia(self) -> None:
        """
        Carga y procesa los datos demográficos y socioeconómicos por barrio.

        Este método lee los archivos de población y renta per cápita,
        estableciendo las bases para el cálculo de coeficientes de generación
        de residuos ajustados a las características de cada zona.
        """
        # Leer archivo de datos demográficos
        barrios = pd.read_excel(BARRIOS_PATH, index_col=0, skipfooter=2)
        barrios.index = barrios.index.astype(str)

        # Guardar datos
        self.poblacion = barrios['Población']
        self.renta = barrios['Renta per cápita / €']


    def _get_betas(self) -> None:
        """
        Calcula los coeficientes beta de generación de residuos por barrio.

        Utiliza un modelo exponencial basado en la renta per cápita para
        estimar la relación entre nivel socioeconómico y producción de
        residuos, según datos históricos y estudios de referencia.
        """
        self.betas = 2.88 * 0.1 * e**(6 * 10**(-5) * self.renta)


    def _get_huella(self) -> None:
        """
        Calcula la huella de carbono total por barrio considerando todos los
        tipos de residuos y tratamientos.

        Combina datos de generación de residuos, distribución de tratamientos
        y factores de emisión específicos para cada flujo de residuos,
        aplicando los coeficientes beta de generación por barrio.
        """
        ### Calcular huella de carbono promedio
        # Inicializar huella a 0
        huella_av = 0
        for r in RESIDUOS_HAB:
            for t in TRATAMIENTO.columns:
                # Si el tratamiento existe para el residuo, sumar a la huella
                if not np.isnan(FACTORES_EMISION.loc[r, t]):
                    huella_av += TRATAMIENTO.loc[r, t] * RESIDUOS_HAB[r] * FACTORES_EMISION.loc[r, t]

        # Calcular huella de carbono por barrio
        huella = huella_av * self.poblacion * self.betas

        # Guardar atributos
        self.huella_promedio = huella_av
        self.huella = huella

    
    def _get_caso_base(self) -> None:
        """
        Coordina el cálculo completo del caso base integrando datos
        demográficos, coeficientes de generación y modelos de emisiones.
        """
        self._get_demografia()
        self._get_betas()
        self._get_huella()


    # ----------------------------------------------
    # MÉTODOS PARA CÁLCULO DE VECTOR R1, REDUCCIÓN DE RESIDUOS GENERADOS
    # ----------------------------------------------
    def get_vector_r1(
            self,
            reduccion: float
            ) -> float:
        """
        Calcula la huella de carbono para un escenario específico de reducción
        en la generación de residuos.

        Args:
            - reduccion (float):
                Proporción de reducción en generación de residuos (entre 0 y 1).

        Devuelve:
            - huella (pd.Series):
                Huella de carbono por barrio en tCO2e, aplicando una reducción
                lineal sobre el caso base según el porcentaje especificado.
        """
        # Calcular huella de carbono reducida
        huella = self.huella * (1 - reduccion * MAXIMO_R1)

        # Almacenar resultado
        self.vector_r1[reduccion] = huella

        # Devolver resultado
        return huella
    

    # ----------------------------------------------
    # MÉTODOS PARA CÁLCULO DE VECTOR R2, AUMENTO DE RECICLAJE
    # ----------------------------------------------
    def get_vector_r2(
            self,
            reciclado: float
            ) -> float:
        """
        Calcula la huella de carbono para un escenario específico de mejora
        en las tasas de reciclaje y valorización de residuos.

        Args:
            - reciclado (float):
                Proporción de avance hacia los objetivos europeos de tratamiento
                de residuos (entre 0 y 1), donde 1 representa el cumplimiento
                total de los estándares UE.

        Devuelve:
            - huella (pd.Series):
                Huella de carbono por barrio en tCO2e, considerando la
                reasignación de flujos de residuos hacia tratamientos menos
                emisores según los escenarios definidos.
        """
        # Recalcular huella con tabla de tratamiento pertinente
        huella_av = 0
        for r in RESIDUOS_HAB:
            for t in ESCENARIOS_R2[reciclado].columns:
                # Si el tratamiento existe para el residuo, sumar a la huella
                if not np.isnan(FACTORES_EMISION.loc[r, t]):
                    huella_av += ESCENARIOS_R2[reciclado].loc[r, t] * RESIDUOS_HAB[r] * FACTORES_EMISION.loc[r, t]

        # Calcular huella de carbono por barrio
        huella = huella_av * self.poblacion * self.betas

        # Almacenar resultado
        self.vector_r2[reciclado] = huella

        # Devolver resultado
        return huella
    

"""
    explicar módulo
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
base_path = os.path.abspath(__file__)
desvab_root = os.path.dirname(os.path.dirname(base_path))
data_path = os.path.join(desvab_root, 'datos')
residuos_path = os.path.join(data_path, 'residuos')

# Caso base
barrios_path = os.path.join(data_path, 'demografia', 'barrios.xlsx')
betas_path = os.path.join(residuos_path, 'betas_residuos.xlsx')


# ----------------------------------------------
# CLASE ÁREA RESIDUOS
# ----------------------------------------------
class AreaResiduos:
    """
    explicar clase
    """
    def __init__(
            self,
            valores_r1: List[float] = R1,
            valores_r2: List[float] = R2,
            verbose: bool = False
            ):
        """
        explicar método
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
    def _get_demografia(self):
        """
        explicar método
        """
        # Leer archivo de datos demográficos
        barrios = pd.read_excel(barrios_path, index_col=0, skipfooter=2)
        barrios.index = barrios.index.astype(str)

        # Guardar datos
        self.poblacion = barrios['Población']
        self.renta = barrios['Renta per cápita / €']


    def _get_betas(self):
        """
        explicar método
        """
        self.betas = 2.88 * 0.1 * e**(6 * 10**(-5) * self.renta)


    def _get_huella(self):
        """
        explicar método
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

    
    def _get_caso_base(self):
        """
        explicar método
        wrapper
        """
        self._get_demografia()
        self._get_betas()
        self._get_huella()


    # ----------------------------------------------
    # MÉTODOS PARA CÁLCULO DE VECTOR R1, REDUCCIÓN DE RESIDUOS GENERADOS
    # ----------------------------------------------
    def get_vector_r1(self, reduccion: float):
        """
        explicar método
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
    def get_vector_r2(self, reciclado: float):
        """
        explicar método
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
    
    
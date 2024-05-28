
"""
    explicar módulo
"""

# ----------------------------------------------
# MÓDULOS
# ----------------------------------------------
import os
import pandas as pd
import time
from geo import get_barrios_ids
from typing import List


# ----------------------------------------------
# VALORES DE VECTORES
# ----------------------------------------------
V2 = [.002, .0015, .001, .0005, 0] # construcción de nuevas viviendas, proporción
V3 = [0, .25, .5, .75, 1] # nuevas viviendas sostenibles, proporción


# ----------------------------------------------
# CONSTANTES
# ----------------------------------------------
# Caso base
CONSTRUCCION_ANUAL = 863 # viviendas nuevas al año
CONSTRUCCION_ANUAL_PCT = 0.2 # % de viviendas nuevas al año
SUPERFICIE_PROMEDIO = 90 # m2
EMISIONES_NUEVA_CONSTRUCCION = 0.06458 # tCO2e/m2

# Vector V3
REDUCCION_SOSTENIBILIDAD = 0.69 # % de reducción de emisiones en viviendas sostenibles


# ----------------------------------------------
# RUTAS Y NOMBRES DE ARCHIVOS
# ----------------------------------------------
base_path = os.path.abspath(__file__)
desvab_root = os.path.dirname(os.path.dirname(base_path))
data_path = os.path.join(desvab_root, 'datos')
vivienda_path = os.path.join(data_path, 'vivienda')

# Caso base
distribucion_nueva_construccion_path = os.path.join(vivienda_path, 'distribución_nueva_construcción.xlsx')


# ----------------------------------------------
# CLASE ÁREA VIVIENDA
# ----------------------------------------------
class AreaVivienda:
    """
    explicar clase
    """
    def __init__(
            self,
            valores_v2: List[float] = V2,
            valores_v3: List[float] = V3,
            verbose: bool = False
            ):
        """
        explicar método
        """
        # Inicializar atributos con caso base
        if verbose:
            print('Inicializando Área Vivienda...')
            print('Calculando caso base...')
            start_time = time.time()
        self._get_caso_base()
        if verbose:
            print(f'Caso base calculado en {time.time() - start_time:.2f} s')

        # Calcular vector V2 para valores dados
        if verbose:
            print('Calculando vector V2...')
            start_time = time.time()
        self.vector_v2 = {}
        for construccion in valores_v2:
            self.get_vector_v2(construccion)
        if verbose:
            print(f'Vector V2 calculado en {time.time() - start_time:.2f} s')

        # Calcular vector V3 para valores dados
        if verbose:
            print('Calculando vector V3...')
            start_time = time.time()
        self.vector_v3 = {}
        for nuevas_sostenibles in valores_v3:
            self.get_vector_v3(nuevas_sostenibles)
        if verbose:
            print(f'Vector V3 calculado en {time.time() - start_time:.2f} s')

        # Guardar vectores en atributo vectores
        self.vectores = {
            'V2': self.vector_v2,
            'V3': self.vector_v3
        }

        if verbose:
            print('Área Vivienda inicializada.')


    # ----------------------------------------------
    # MÉTODOS PARA CÁLCULO DE CASO BASE
    # ----------------------------------------------
    def _get_nueva_construccion(self):
        """
        explicar método
        """
        # Leer archivo de distribución de nueva construcción
        distribucion = pd.read_excel(distribucion_nueva_construccion_path,
                                     usecols=[0, 1, 2, 3], index_col=0, skipfooter=1)
        distribucion.index = distribucion.index.astype(str)

        # Crear serie vacía para almacenar viviendas nuevas por barrio
        viviendas_nuevas = pd.Series(0, index=get_barrios_ids())

        # Calcular viviendas nuevas por barrio
        viviendas_nuevas.loc[distribucion.index] = CONSTRUCCION_ANUAL * distribucion['Porcentaje']

        # Guardar atributo
        self.viviendas_nuevas = viviendas_nuevas


    def _get_huella(self):
        """
        explicar método
        """
        # Calcular huella de carbono de nueva construcción
        huella = self.viviendas_nuevas * SUPERFICIE_PROMEDIO * EMISIONES_NUEVA_CONSTRUCCION

        # Guardar atributo
        self.huella = huella


    def _get_caso_base(self):
        """
        explicar método
        wrapper
        """
        self._get_nueva_construccion()
        self._get_huella()


    # ----------------------------------------------
    # MÉTODOS PARA CÁLCULO DE VECTOR V2, REDUCCIÓN DE NUEVA CONSTRUCCIÓN
    # ----------------------------------------------
    def get_vector_v2(self, construccion: float):
        """
        explicar método
        """
        # Calcular huella de carbono para valor de construcción
        viviendas_nuevas = self.viviendas_nuevas * (construccion*100 / CONSTRUCCION_ANUAL_PCT)
        huella = viviendas_nuevas * SUPERFICIE_PROMEDIO * EMISIONES_NUEVA_CONSTRUCCION
        # Almacenar resultado
        self.vector_v2[construccion] = huella
        # Devolver resultado
        return huella
    

    # ----------------------------------------------
    # MÉTODOS PARA CÁLCULO DE VECTOR V3, VIVIENDAS SOSTENIBLES
    # ----------------------------------------------
    def get_vector_v3(self, nuevas_sostenibles: float):
        """
        explicar método
        """
        # Calcular huella de carbono a partir del caso base, reduciendo emisiones por vivienda sostenible
        huella = self.huella - self.huella * nuevas_sostenibles * REDUCCION_SOSTENIBILIDAD
        # Almacenar resultado
        self.vector_v3[nuevas_sostenibles] = huella
        # Devolver resultado
        return huella
    

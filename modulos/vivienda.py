
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
V1 = [0., .25, .5, .75, 1.] # construcción de nuevas viviendas, proporción
V2 = [0., .25, .5, .75, 1.] # nuevas viviendas sostenibles, proporción


# ----------------------------------------------
# CONSTANTES
# ----------------------------------------------
# Caso base
CONSTRUCCION_ANUAL = 863 # viviendas nuevas al año
CONSTRUCCION_ANUAL_PCT = 0.2 # % de viviendas nuevas al año
SUPERFICIE_PROMEDIO = 90 # m2
EMISIONES_NUEVA_CONSTRUCCION = 0.06458 # tCO2e/m2

# Vector V2
REDUCCION_SOSTENIBILIDAD = 0.69 # % de reducción de emisiones en viviendas sostenibles


# ----------------------------------------------
# RUTAS Y NOMBRES DE ARCHIVOS
# ----------------------------------------------
base_path = os.path.abspath(__file__)
desvab_root = os.path.dirname(os.path.dirname(base_path))
data_path = os.path.join(desvab_root, 'datos')
vivienda_path = os.path.join(data_path, 'vivienda')

# Caso base
distribucion_nueva_construccion_path = os.path.join(vivienda_path, 'distribución_nueva_construcción_.xlsx')


# ----------------------------------------------
# CLASE ÁREA VIVIENDA
# ----------------------------------------------
class AreaVivienda:
    """
    explicar clase
    """
    def __init__(
            self,
            valores_v1: List[float] = V1,
            valores_v2: List[float] = V2,
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

        # Calcular vector V1 para valores dados
        if verbose:
            print('Calculando vector V1...')
            start_time = time.time()
        self.vector_v1 = {}
        for construccion in valores_v1:
            self.get_vector_v1(construccion)
        if verbose:
            print(f'Vector V1 calculado en {time.time() - start_time:.2f} s')

        # Calcular vector V2 para valores dados
        if verbose:
            print('Calculando vector V2...')
            start_time = time.time()
        self.vector_v2 = {}
        for nuevas_sostenibles in valores_v2:
            self.get_vector_v2(nuevas_sostenibles)
        if verbose:
            print(f'Vector V2 calculado en {time.time() - start_time:.2f} s')

        # Guardar vectores en atributo vectores
        self.vectores = {
            'V1': self.vector_v1,
            'V2': self.vector_v2
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
                                     usecols=[0, 1, 3, 4], index_col=0)
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
    # MÉTODOS PARA CÁLCULO DE VECTOR V1, REDUCCIÓN DE NUEVA CONSTRUCCIÓN
    # ----------------------------------------------
    def get_vector_v1(self, construccion: float):
        """
        explicar método
        """
        # Calcular huella de carbono para valor de construcción
        viviendas_nuevas = self.viviendas_nuevas * (1 - construccion)
        huella = viviendas_nuevas * SUPERFICIE_PROMEDIO * EMISIONES_NUEVA_CONSTRUCCION
        # Almacenar resultado
        self.vector_v1[construccion] = huella
        # Devolver resultado
        return huella
    

    # ----------------------------------------------
    # MÉTODOS PARA CÁLCULO DE VECTOR V2, VIVIENDAS SOSTENIBLES
    # ----------------------------------------------
    def get_vector_v2(self, nuevas_sostenibles: float):
        """
        explicar método
        """
        # Calcular huella de carbono a partir del caso base, reduciendo emisiones por vivienda sostenible
        huella = self.huella - self.huella * nuevas_sostenibles * REDUCCION_SOSTENIBILIDAD
        # Almacenar resultado
        self.vector_v2[nuevas_sostenibles] = huella
        # Devolver resultado
        return huella
    

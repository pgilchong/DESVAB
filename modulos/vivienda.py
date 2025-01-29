# vivienda.py

"""
MÓDULO ÁREA VIVIENDA

Este módulo contiene la clase `AreaVivienda`, una herramienta para gestionar
y calcular la huella de carbono asociada a la construcción de nuevas viviendas
en diferentes escenarios urbanísticos. Permite analizar el impacto ambiental
de la nueva construcción considerando diferentes ratios de desarrollo urbano
y la implementación de criterios de sostenibilidad en las edificaciones.
Incluye funcionalidades para distribuir las emisiones por barrio y evaluar
escenarios de reducción de nueva construcción y promoción de viviendas
ecoeficientes en la ciudad de València.
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
BASE_PATH = os.path.abspath(__file__)
DESVAB_ROOT = os.path.dirname(os.path.dirname(BASE_PATH))
DATA_PATH = os.path.join(DESVAB_ROOT, 'datos')
VIVIENDA_PATH = os.path.join(DATA_PATH, 'vivienda')

# Caso base
DISTRIBUCION_NUEVA_CONSTRUCCION_PATH = os.path.join(VIVIENDA_PATH, 'distribución_nueva_construcción_.xlsx')


# ----------------------------------------------
# CLASE ÁREA VIVIENDA
# ----------------------------------------------
class AreaVivienda:
    """
    Clase para gestionar y calcular el impacto ambiental de la construcción
    residencial. Permite cuantificar las emisiones de CO2 asociadas a la nueva
    construcción distribuida por barrios, y evaluar escenarios de reducción
    del desarrollo urbanístico y de implementación de prácticas constructivas
    sostenibles.
    """
    def __init__(
            self,
            valores_v1: List[float] = V1,
            valores_v2: List[float] = V2,
            verbose: bool = False
            ):
        """
        Inicializa una instancia de la clase AreaVivienda, calculando el caso base
        y los vectores V1 y V2 para los valores especificados.

        Args:
            - valores_v1 (list, opcional):
                Lista de porcentajes de reducción de nueva construcción a evaluar.
                Por defecto, [0, .25, .5, .75, 1].
            - valores_v2 (list, opcional):
                Lista de porcentajes de viviendas sostenibles a evaluar.
                Por defecto, [0, .25, .5, .75, 1].
            - verbose (bool, opcional):
                Indica si se deben imprimir mensajes informativos.
                Por defecto, False.
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
        Calcula la distribución de nuevas viviendas por barrio a partir de
        los datos históricos de construcción.

        Este método lee el archivo de distribución de nueva construcción,
        procesa los porcentajes por barrio y calcula el número absoluto de
        viviendas nuevas basado en la media anual de construcción.
        """
        # Leer archivo de distribución de nueva construcción
        distribucion = pd.read_excel(DISTRIBUCION_NUEVA_CONSTRUCCION_PATH,
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
        Calcula la huella de carbono asociada a la construcción de nuevas
        viviendas.

        Este método utiliza el número de viviendas nuevas por barrio, la
        superficie promedio por vivienda y las emisiones por m2 para
        determinar las emisiones totales de CO2e.
        """
        # Calcular huella de carbono de nueva construcción
        huella = self.viviendas_nuevas * SUPERFICIE_PROMEDIO * EMISIONES_NUEVA_CONSTRUCCION

        # Guardar atributo
        self.huella = huella


    def _get_caso_base(self):
        """
        Calcula todos los componentes del caso base: distribución de nuevas
        construcciones y huella de carbono asociada.

        Este método coordina la ejecución de los métodos de cálculo de
        nueva construcción y emisiones correspondientes.
        """
        self._get_nueva_construccion()
        self._get_huella()


    # ----------------------------------------------
    # MÉTODOS PARA CÁLCULO DE VECTOR V1, REDUCCIÓN DE NUEVA CONSTRUCCIÓN
    # ----------------------------------------------
    def get_vector_v1(
            self,
            construccion: float
            ) -> pd.Series:
        """
        Calcula la huella de carbono para un escenario específico de reducción
        en la nueva construcción.

        Args:
            - construccion (float):
                Proporción de reducción en nueva construcción (entre 0 y 1).

        Devuelve:
            - huella (pd.Series):
                Huella de carbono por barrio en tCO2e, considerando la reducción
                en el número de viviendas construidas.
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
    def get_vector_v2(
            self,
            nuevas_sostenibles: float
            ) -> pd.Series:
        """
        Calcula la huella de carbono para un escenario específico de
        implementación de viviendas sostenibles.

        Args:
            - nuevas_sostenibles (float):
                Proporción de viviendas nuevas construidas con criterios
                sostenibles (entre 0 y 1).

        Devuelve:
            - huella (pd.Series):
                Huella de carbono por barrio en tCO2e, aplicando la reducción
                de emisiones asociada a las prácticas constructivas sostenibles.
        """
        # Calcular huella de carbono a partir del caso base, reduciendo emisiones por vivienda sostenible
        huella = self.huella - self.huella * nuevas_sostenibles * REDUCCION_SOSTENIBILIDAD
        # Almacenar resultado
        self.vector_v2[nuevas_sostenibles] = huella
        # Devolver resultado
        return huella
    

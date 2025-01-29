# energia.py

"""
MÓDULO ÁREA ENERGÍA

Este módulo contiene la clase `AreaEnergia`, una herramienta
para gestionar y calcular el consumo de energía eléctrica y de gas,
así como la huella de carbono asociada en diferentes sectores
(Residencial, Comercial e Industrial) por Código Postal (CP) y
barrio. Además, permite evaluar diferentes escenarios de autoconsumo,
electrificación, reducción de consumo y mejora del parque de edificios,
facilitando el análisis de impacto ambiental y energético en la ciudad
de València.
"""


# ----------------------------------------------
# MÓDULOS
# ----------------------------------------------
import numpy as np
import os
import pandas as pd
import time

from geo import get_matriz_cp
from itertools import product
from typing import List


# ----------------------------------------------
# VALORES DE VECTORES
# ----------------------------------------------
E1 = [0., .25, .5, .75, 1.] # autoconsumo, proporción
E2 = [0., .25, .5, .75, 1.] # electrificación, proporción
E3 = [0., .25, .5, .75, 1.] # reducción de consumo, proporción
V3 = [0., .25, .5, .75, 1.] # mejora parque edificios E-G, proporción


# ----------------------------------------------
# CONSTANTES
# ----------------------------------------------
# Caso base
RATIOS_ELEC_GAS = { # ratio de consumo de gas respecto a eléctrico
    'Residencial': 0.7,
    'Comercial': 0.44,
    'Industrial': 1.37
}
CALEFACCION = { # consumo de energía por calefacción como fracción de consumo residencial
    'Electricidad': 0.27,
    'Gas': 0.14
}
FACTOR_EMISION_MIX = { # factores de emisión de la red eléctrica
    'Actual': 0.12, # tCO2e/MWh
    'PNIEC': 0.068, # tCO2e/MWh
    'Borrador PNIEC': 0.03 # tCO2e/MWh
}
FACTOR_EMISION_GAS = 0.18 # tCO2e/MWh

# Vector E1
EFICIENCIA_PANELES_SOLARES = 0.224 # proporción
RENDIMIENTO_INSTALACIONES_SOLARES = 0.86 # proporción

# Vector E2
EFICIENCIA_ELECTRIFICACION = 0.3 # proporción

# Vector E3
MAXIMO_E3 = 0.16 # proporción

# Vector V3
REDUCCION_DEMANDA_REHABILITACION = 0.51 # proporción
CALEFACCION_SATISFECHA_GAS = 0.27 # proporción
CALEFACCION_SATISFECHA_ELECTRICIDAD = 0.14 # proporción


# ----------------------------------------------
# RUTAS Y NOMBRES DE ARCHIVOS
# ----------------------------------------------
BASE_PATH = os.path.abspath(__file__)
DESVAB_ROOT = os.path.dirname(os.path.dirname(BASE_PATH))
DATA_PATH = os.path.join(DESVAB_ROOT, 'datos')
ENERGIA_PATH = os.path.join(DATA_PATH, 'energia')

# Caso base
CONSUMOS_DATADIS_PATH = os.path.join(ENERGIA_PATH, 'consumos_datadis.csv') # consumos eléctricos por CP

# Vector E1
POTENCIAL_RADIACION_PATH = os.path.join(ENERGIA_PATH, 'potencial_PV') # carpeta con archivos de potencial de radiación por barrio (catastros)

# Vector V3
VIVIENDA_PATH = os.path.join(DATA_PATH, 'vivienda')
CERTIFICADOS_PATH = os.path.join(VIVIENDA_PATH, 'inmuebles_certificacion_energetica.xlsx') # certificados energéticos
ANTIGUEDADES_PATH = os.path.join(VIVIENDA_PATH, 'inmuebles_antiguedad.xlsx') # distribución de antigüedad de edificios


# ----------------------------------------------
# CLASE ÁREA ENERGÍA
# ----------------------------------------------
class AreaEnergia:
    """
    Clase para gestionar y calcular el consumo energético y la
    huella de carbono en diferentes sectores y escenarios.
    Permite calcular los consumos eléctricos y de gas por barrio,
    así como la huella de carbono asociada. Incluye distintos escenarios
    de autoconsumo, electrificación, reducción de consumo y mejora del
    parque de edificios.
    """
    def __init__(
            self,
            valores_e1: List[float] = E1,
            valores_e2: List[float] = E2,
            valores_e3: List[float] = E3,
            valores_v3: List[float] = V3,
            verbose: bool = False
            ) -> None:
        """
        Inicializa una instancia de la clase AreaEnergia,
        calculando el caso base y los vectores E1, E2, E3 y V3
        para los valores especificados.

        Args:
            - valores_e1 (list, opcional):
                Lista de porcentajes de autoconsumo a evaluar.
                Por defecto, [0, .25, .5, .75, 1].
            - valores_e2 (list, opcional):
                Lista de porcentajes de electrificación a evaluar.
                Por defecto, [0, .25, .5, .75, 1].
            - valores_e3 (list, opcional):
                Lista de porcentajes de reducción de consumo a evaluar.
                Por defecto, [0, .04, .08, .12, .16].
            - verbose (bool, opcional):
                Indica si se deben imprimir mensajes informativos.
                Por defecto, False.
        """
        # Inicializar atributos con caso base
        if verbose:
            print('Inicializando Área Energía...')
            print('Calculando caso base...')
            start_time = time.time()
        self._get_caso_base()
        if verbose:
            print(f'Caso base calculado en {time.time() - start_time:.2f} s')

        # Calcular vector E1 para valores dados
        if verbose:
            print('Calculando vector E1...')
            start_time = time.time()
        self._get_potencial_pv()
        self.vector_e1 = {}
        for autoconsumo, escenario in product(valores_e1, FACTOR_EMISION_MIX.keys()):
            self.get_vector_e1(autoconsumo, escenario)            
        if verbose:
            print(f'Vector E1 calculado en {time.time() - start_time:.2f} s')
        
        # Calcular vector E2 para valores dados
        if verbose:
            print('Calculando vector E2...')
            start_time = time.time()
        self.vector_e2 = {}
        for electrificacion, escenario in product(valores_e2, FACTOR_EMISION_MIX.keys()):
            self.get_vector_e2(electrificacion, escenario)
        if verbose:
            print(f'Vector E2 calculado en {time.time() - start_time:.2f} s')

        # Calcular vector E3 para valores dados
        if verbose:
            print('Calculando vector E3...')
            start_time = time.time()
        self.vector_e3 = {}
        for reduccion, escenario in product(valores_e3, FACTOR_EMISION_MIX.keys()):
            self.get_vector_e3(reduccion, escenario)
        if verbose:
            print(f'Vector E3 calculado en {time.time() - start_time:.2f} s')
        
        # Calcular vector V3 para valores dados
        if verbose:
            print('Calculando vector V3...')
            start_time = time.time()
        self._wrap_v3()
        self.vector_v3 = {}
        for mejora, escenario in product(valores_v3, FACTOR_EMISION_MIX.keys()):
            self.get_vector_v3(mejora, escenario)
        if verbose:
            print(f'Vector V3 calculado en {time.time() - start_time:.2f} s')

        # Guardar vectores en atributo vectores
        self.vectores = {
            'E1': self.vector_e1,
            'E2': self.vector_e2,
            'E3': self.vector_e3,
            'V3': self.vector_v3
        }

        if verbose:
            print('Área Energía inicializada.')
        
    
    # ----------------------------------------------
    # MÉTODOS PARA CÁLCULO DE CASO BASE
    # ----------------------------------------------
    def _get_consumos_electricos(self) -> None:
        """
        Calcula los consumos eléctricos por barrio a partir
        de los datos de consumo por CP.

        Este método lee el archivo de consumos eléctricos por
        CP, renombra y procesa las columnas, calcula el consumo
        total por CP y luego distribuye estos consumos a los
        barrios utilizando una matriz de superposición barrio-CP.
        """
        ### Consumos por CP
        # Leer archivo de datos de consumo
        consumos_cp = pd.read_csv(CONSUMOS_DATADIS_PATH, sep=',',
                                  usecols=[0, 6, 7, 8], encoding='utf-8',
                                  skiprows=5, skipfooter=3,
                                  na_values='-', engine='python')
        # Renombrar columnas y establecer CP como índice
        consumos_cp.columns = [
            'CP', 'Residencial', 'Comercial', 'Industrial'
        ]
        consumos_cp = consumos_cp.set_index('CP').replace(
            ',', '', regex=True).fillna(0).drop('Total').astype(float)
        # Calcular consumo total
        consumos_cp['Total'] = consumos_cp.sum(axis=1)

        ### Consumos por barrio
        # Calcular matriz de superposición barrio-CP
        matriz_cp = get_matriz_cp()
        # Inicializar DataFrame vacío
        consumos_barrio = pd.DataFrame(0, index=matriz_cp.columns,
                                       columns=consumos_cp.columns)
        # Calcular consumos por barrio
        for barrio in consumos_barrio.index:
            cps = matriz_cp.loc[:, barrio]
            cps = cps[cps > 0]
            for cp in cps.index:
                consumos_barrio.loc[barrio] += (
                    matriz_cp.loc[cp, barrio] * consumos_cp.loc[cp])
        
        # Guardar consumos por barrio
        self.consumos_electricos = consumos_barrio


    def _get_consumos_gas(self) -> None:
        """
        Calcula los consumos de gas por barrio a partir de los
        consumos eléctricos.

        Este método utiliza los ratios de consumo de gas respecto a
        eléctrico para cada sector y calcula el consumo de gas total por barrio.
        """
        consumos_gas = self.consumos_electricos.copy()
        consumos_gas['Residencial'] *= RATIOS_ELEC_GAS['Residencial']
        consumos_gas['Comercial'] *= RATIOS_ELEC_GAS['Comercial']
        consumos_gas['Industrial'] *= RATIOS_ELEC_GAS['Industrial']
        consumos_gas['Total'] = consumos_gas[
            ['Residencial', 'Comercial', 'Industrial']].sum(axis=1)
        self.consumos_gas = consumos_gas

    
    def _get_consumo_calefaccion(self) -> None:
        """
        Calcula el consumo energético destinado a calefacción en el
        sector residencial.

        Este método combina los consumos eléctricos y de gas residenciales
        multiplicados por sus respectivos factores de calefacción.
        """
        consumo_calefaccion = (
            self.consumos_electricos['Residencial'] * CALEFACCION['Electricidad']) + (
            self.consumos_gas['Residencial'] * CALEFACCION['Gas'])
        
        self.consumo_calefaccion = consumo_calefaccion

    
    def _get_huella(self) -> None:
        """
        Calcula la huella de carbono total por barrio.

        Este método suma las emisiones de carbono de los consumos
        eléctricos y de gas utilizando los factores de emisión correspondientes.
        """
        huella = (
            self.consumos_electricos['Total'] * FACTOR_EMISION_MIX['Actual']) + (
            self.consumos_gas['Total'] * FACTOR_EMISION_GAS)
        self.huella = huella

    
    def _get_caso_base(self) -> None:
        """
        Calcula todos los componentes del caso base: consumos
        eléctricos, consumos de gas, consumo de calefacción y huella de
        carbono.

        Este método es un wrapper que llama a los métodos internos
        necesarios para calcular el caso base.
        """
        self._get_consumos_electricos()
        self._get_consumos_gas()
        self._get_consumo_calefaccion()
        self._get_huella()

    
    # ----------------------------------------------
    # MÉTODOS PARA CÁLCULO DE VECTOR E1, AUTOCONSUMO
    # ----------------------------------------------
    def _get_potencial_pv(self) -> None:
        """
        Genera y almacena un dataframe con el potencial de radiación
        solar por tipo de edificio y barrio de València y otro dataframe
        con el número de edificios por tipo de uso y barrio.
        """
        
        # Crear dataframes
        potencial = pd.DataFrame(columns=['Residencial',
                                          'Comercial',
                                          'Industrial',
                                          'ServiciosPúblicos',
                                          'Agricultura'])

        # Crear diccionario de mapeo de usos
        usos = {
            '1_residential': 'Residencial',
            '2_agriculture': 'Agricultura',
            '3_industrial': 'Industrial',
            '4_1_office': 'Comercial',
            '4_2_retail': 'Comercial',
            '4_3_publicServices': 'ServiciosPúblicos'
        }

        # Recorrer archivos
        for file in os.listdir(POTENCIAL_RADIACION_PATH):
            # Si el archivo es un csv
            if file.endswith('.csv'):
                # Extraer ID de barrio del nombre de archivo
                id_barrio = file.split('.')[0][-3:]
                id_barrio = (
                    str(int(id_barrio[:2])) + '.' + str(int(id_barrio[2])))
                # Leer archivo
                catastros = pd.read_csv(
                    os.path.join(POTENCIAL_RADIACION_PATH, file), sep=',',
                    encoding='latin-1')
                # Eliminar filas con currentUse == ' ' (espacio)
                catastros = catastros[catastros['currentUse'] != ' ']
                # Renombrar tipos de uso
                catastros['currentUse'] = catastros['currentUse'].apply(lambda x: usos[x])
                # Calcular potencial (entre 1000 para pasar kWh a MWh)
                potencial_barrio = (
                    catastros['AREA']) * (
                    catastros['MEAN'] / 1000) * (
                    EFICIENCIA_PANELES_SOLARES) * (
                    RENDIMIENTO_INSTALACIONES_SOLARES)
                # Agrupar por uso y sumar
                potencial_barrio = potencial_barrio.groupby(
                    catastros['currentUse']).sum()
                potencial_barrio.name = id_barrio
                # Agrupar por uso y sumar
                potencial_barrio = potencial_barrio.groupby('currentUse').sum()
                # Añadir a dataframes
                potencial.loc[id_barrio] = potencial_barrio

        # Convertir NaN (ausentes en este caso) a 0
        potencial = potencial.fillna(0)

        # Guardar dataframe
        self.potencial_pv = potencial.sort_index()


    def get_vector_e1(
            self,
            autoconsumo: float,
            escenario: str
            ) -> pd.Series:
        """
        Genera y almacena el potencial de radiación solar por
        tipo de edificio y barrio, así como el número de
        edificios por tipo de uso y barrio.

        Este método lee los archivos de potencial de radiación
        solar, calcula el potencial de generación fotovoltaica
        ajustado por eficiencia y rendimiento, y agrupa los
        datos por tipo de uso y barrio.

        Args:
            - autoconsumo (float):
                Proporción de autoconsumo (entre 0 y 1).
            - escenario (str):
                Escenario de factor de emisión a utilizar;
                'Actual', 'PNIEC' o 'Borrador PNIEC'.

        Devuelve:
            - huella (pd.Series):
                Huella de carbono por barrio en tCO2e.
        
        """
        ### Comprobar valores de parámetros
        # Comprobar que el autoconsumo está entre 0 y 1
        if autoconsumo < 0 or autoconsumo > 1:
            raise ValueError('El autoconsumo debe ser un valor entre 0 y 1.')
        # Comprobar que el escenario es uno de los valores válidos
        if escenario not in FACTOR_EMISION_MIX.keys():
            raise ValueError('El escenario debe ser uno de los valores válidos.')

        ### Ejecutar vector
        # Calcular consumos eléctricos con autoconsumo
        consumos_electricos = (self.consumos_electricos['Total'] - self.potencial_pv.sum(axis=1) * autoconsumo)
        # Fijar a 0 consumos negativos
        consumos_electricos = consumos_electricos.clip(lower=0)
        # Calcular huella de carbono
        huella = (
            consumos_electricos * FACTOR_EMISION_MIX[escenario]) + (
            self.consumos_gas['Total'] * FACTOR_EMISION_GAS)
        # Almacenar resultado
        self.vector_e1[(autoconsumo, escenario)] = huella
        # Devolver resultado
        return huella
    

    # ----------------------------------------------
    # MÉTODOS PARA CÁLCULO DE VECTOR E2, ELECTRIFICACIÓN
    # ----------------------------------------------
    def get_vector_e2(
            self,
            electrificacion: float,
            escenario: str
            ) -> pd.Series:
        """
        Calcula la huella de carbono para un escenario específico
        de electrificación y factor de emisión.

        Este método ajusta los consumos eléctricos y de gas en
        función del grado de electrificación y calcula la huella de
        carbono resultante.

        Args:
            - electrificacion (float):
                Proporción de electrificación (entre 0 y 1).
            - escenario (str): 
                Escenario de factor de emisión a utilizar;
                'Actual', 'PNIEC' o 'Borrador PNIEC'.

        Devuelve:
            - huella (pd.Series):
                Huella de carbono por barrio en tCO2e.
        """
        ### Comprobar valores de parámetros
        # Comprobar que la electrificación está entre 0 y 1
        if electrificacion < 0 or electrificacion > 1:
            raise ValueError('La electrificación debe ser un valor entre 0 y 1.')
        # Comprobar que el escenario es uno de los valores válidos
        if escenario not in FACTOR_EMISION_MIX.keys():
            raise ValueError('El escenario debe ser uno de los valores válidos.')
        
        ### Ejecutar vector
        # Calcular consumos de gas con electrificación
        consumos_gas = self.consumos_gas['Total'] * (1 - electrificacion)
        # Calcular consumos eléctricos con electrificación
        consumos_electricos = self.consumos_electricos['Total'] * (1 + electrificacion * EFICIENCIA_ELECTRIFICACION)
        # Calcular huella de carbono
        huella = (
            consumos_electricos * FACTOR_EMISION_MIX[escenario]) + (
            consumos_gas * FACTOR_EMISION_GAS)
        # Almacenar resultado
        self.vector_e2[(electrificacion, escenario)] = huella
        # Devolver resultado
        return huella
    

    # ----------------------------------------------
    # MÉTODOS PARA CÁLCULO DE VECTOR E3, REDUCCIÓN DE CONSUMO
    # ----------------------------------------------
    def get_vector_e3(
            self,
            reduccion: float,
            escenario: str
            ) -> pd.Series:
        """
        Calcula la huella de carbono para un escenario específico
        de reducción de consumo y factor de emisión.

        Este método ajusta los consumos eléctricos y de gas en
        función de la reducción de demanda y calcula la huella de
        carbono resultante.

        Args:
            - reduccion (float):
                Proporción de reducción de consumo (entre 0 y 1).
            - escenario (str):
                Escenario de factor de emisión a utilizar;
                'Actual', 'PNIEC' o 'Borrador PNIEC'.

        Devuelve:
            - huella (pd.Series):
                Huella de carbono por barrio en tCO2e.
        
        """
        ### Comprobar valores de parámetros
        # Comprobar que la reducción está entre 0 y 1
        if reduccion < 0 or reduccion > 1:
            raise ValueError('La reducción debe ser un valor entre 0 y 1.')
        # Comprobar que el escenario es uno de los valores válidos
        if escenario not in FACTOR_EMISION_MIX.keys():
            raise ValueError('El escenario debe ser uno de los valores válidos.')
        
        ### Ejecutar vector
        # Calcular consumos de gas con reducción
        consumos_gas = self.consumos_gas[['Residencial', 'Comercial']].sum(axis=1) * (1 - reduccion * MAXIMO_E3) + self.consumos_gas['Industrial']
        # Calcular consumos eléctricos con reducción
        consumos_electricos = self.consumos_electricos[['Residencial', 'Comercial']].sum(axis=1) * (1 - reduccion * MAXIMO_E3) + self.consumos_electricos['Industrial']
        # Calcular huella de carbono
        huella = (
            consumos_electricos * FACTOR_EMISION_MIX[escenario]) + (
            consumos_gas * FACTOR_EMISION_GAS)
        # Almacenar resultado
        self.vector_e3[(reduccion, escenario)] = huella
        # Devolver resultado
        return huella


    # ----------------------------------------------
    # MÉTODOS PARA CÁLCULO DE VECTOR V3, MEJORA PARQUE EDIFICIOS
    # ----------------------------------------------
    def _get_certificados(self) -> None:
        """
        Lee el archivo de certificados energéticos y genera los
        atributos certificados_consumo y certificados_emisiones.

        Este método procesa los certificados energéticos de los
        inmuebles, corrige datos erróneos, clasifica por
        antigüedad y calcula estadísticas de consumo y emisiones
        por barrio y antigüedad.
        """        
        # Leer archivo
        df_certificados = pd.read_excel(CERTIFICADOS_PATH)

        # Cambiar número de distrito 0 por 5 (es error de la fuente de datos,
        # son todo edificios de La Saïdia)
        df_certificados['NUMERO_DISTRITO'] = (
            df_certificados['NUMERO_DISTRITO'].replace(0, 5))

        # Eliminar filas con barrio no etiquetado - ETIQUETAR MANUAL
        df_certificados = df_certificados[df_certificados['Codigo_barrio'] != 0]

        # Eliminar filas con letras 0
        df_certificados = (
            df_certificados[df_certificados['CONSUMO_EP_LETRA'] != 0])

        # Crear columna de ID de barrio
        df_certificados['ID'] = (
            df_certificados['NUMERO_DISTRITO'].astype(str)) + '.' + (
            df_certificados['Codigo_barrio'].astype(str))

        # Crear columna de rangos de antigüedad (<1800, 1801-1900,
        # 1901-1920, 1921-1940, 1941-1960, 1961-1980, 1981-2000,
        # 2001-2010, >2011)
        df_certificados['Antigüedad'] = pd.cut(
            df_certificados['ANYO_CONSTRUCCION'],
            bins=[0, 1800, 1900, 1920, 1940, 1960, 1980, 2000, 2010, 2021],
            labels=['<= 1800', '1801-1900', '1901-20', '1921-40', '1941-60',
                    '1961-80', '1981-00', '2001-10', '2011-21'])
        
        # Contar número de certificados y calcular media de consumo y
        # emisiones por barrio y antigüedad
        df_consumo = df_certificados.groupby(
            ['ID', 'Antigüedad', 'CONSUMO_EP_LETRA']).agg(
            {'Energy_Consumption': ['count', 'mean']}).reset_index()
        df_emisiones = df_certificados.groupby(
            ['ID', 'Antigüedad', 'EMISIONES_CO2_LETRA']).agg(
            {'EMISIONES_CO2_VALOR': ['count', 'mean']}).reset_index()

        # Renombrar columnas
        df_consumo.columns = [
            'ID', 'Antigüedad', 'Letra', 'Total Certificados', 'Media Consumo']
        df_emisiones.columns = [
            'ID', 'Antigüedad', 'Letra', 'Total Certificados', 'Media Emisiones']
        
        # Reemplazar NaN por 0
        df_consumo['Media Consumo'].fillna(0, inplace=True)
        df_emisiones['Media Emisiones'].fillna(0, inplace=True)
        
        # Guardar distribuciones de certificados
        self.certificados_consumo = df_consumo
        self.certificados_emisiones = df_emisiones


    def _get_antiguedades(self) -> None:
        """
        Lee el archivo de antigüedad de edificios y genera el atributo
        antiguedades.

        Este método procesa los datos de antigüedad de los edificios,
        asigna IDs de barrio y limpia los datos eliminando filas y
        columnas innecesarias.
        """
        # Leer archivo
        df_edificios = pd.read_excel(ANTIGUEDADES_PATH, skiprows=2, skipfooter=2)

        # Eliminar últimas 5 columnas
        df_edificios.drop(df_edificios.columns[-5:], axis=1, inplace=True)

        # Renombrar primera columna a 'Zona'
        df_edificios.rename(columns={df_edificios.columns[0]: 'Zona'},
                            inplace=True)

        # Eliminar total ciudad (primera fila) y distritos (filas indicadas)
        df_edificios.drop([0,1,8,12,17,22,28,33,39,45,51,59,65,71,77,80,84,87,95,98],
                          inplace=True)

        # Crear columna de ID
        df_edificios['ID'] = ''

        # Inicializar variables para recorrer filas
        filas_distrito, distrito = [], 0

        # Recorrer filas para asignar ID
        for i, row in df_edificios.iterrows():
            area = int(row['Zona'].strip().split('.')[0])
            if area == 1:
                distrito += 1
            df_edificios.loc[i, 'ID'] = str(distrito) + '.' + str(area)

        # Eliminar filas de totales y columnas de zona y edad media
        df_edificios.drop(filas_distrito, inplace=True)
        df_edificios.drop(['Zona', 'Edad media'], axis=1, inplace=True)

        # Establecer ID como índice
        df_edificios.set_index('ID', inplace=True)

        # Guardar distribución de antigüedad de edificios
        self.antiguedades = df_edificios
        
    
    def _get_distribuciones(self) -> None:
        """
        Genera los atributos distribucion_certificados_consumo y
        distribucion_certificados_emisiones.

        Este método ajusta las distribuciones de certificados de
        consumo y emisiones en función de la antigüedad de los
        edificios en cada barrio.
        """
        # Sacar aproximación de distribución de letras para cada barrio
        # Sumar total de certificados por barrio, antigüedad y letra y
        # multiplicar por proporción de antigüedad
        
        consumo = self.certificados_consumo.copy()
        emisiones = self.certificados_emisiones.copy()

        for barrio in self.antiguedades.index:
            # Sumar total de certificados por barrio separando por
            # antigüedad
            certificados_consumo = self.certificados_consumo[
                self.certificados_consumo['ID'] == barrio].groupby(
                'Antigüedad')['Total Certificados'].sum()
            certificados_emisiones = self.certificados_emisiones[
                self.certificados_emisiones['ID'] == barrio].groupby(
                'Antigüedad')['Total Certificados'].sum()
            for antiguedad in self.antiguedades.columns[1:]:
                for letra in ['A', 'B', 'C', 'D', 'E', 'F', 'G']:
                    loc = (
                        consumo['ID'] == barrio) & (
                        consumo['Antigüedad'] == antiguedad) & (
                        consumo['Letra'] == letra)
                    consumo.loc[loc, 'Total Certificados'] = (
                        consumo.loc[loc, 'Total Certificados']) / (
                        certificados_consumo[antiguedad]) * (
                        self.antiguedades.loc[barrio, antiguedad])
                    loc = (
                        emisiones['ID'] == barrio) & (
                        emisiones['Antigüedad'] == antiguedad) & (
                        emisiones['Letra'] == letra)
                    emisiones.loc[loc, 'Total Certificados'] = (
                        emisiones.loc[loc, 'Total Certificados']) / (
                        certificados_emisiones[antiguedad]) * (
                        self.antiguedades.loc[barrio, antiguedad])
        
        # Guardar distribuciones
        self.distribucion_certificados_consumo = consumo
        self.distribucion_certificados_emisiones = emisiones

    
    def _get_ahorro(self) -> None:
        """
        Calcula el potencial de ahorro energético y de emisiones mediante
        la rehabilitación de edificios certificados con letras E, F y G.

        Este método determina el porcentaje de certificados con bajas
        calificaciones energéticas y calcula el ahorro potencial en
        consumo de gas y electricidad.
        """
        # Calcular porcentaje de certificados con letras E-G
        cert_EFG = self.certificados_consumo[
            self.certificados_consumo['Letra'].isin(['E', 'F', 'G'])
            ].groupby(['ID']).sum(numeric_only=True)['Total Certificados'] / (
                self.certificados_consumo.groupby(['ID']).sum(numeric_only=True)['Total Certificados']
            )
        
        # Calcular ahorro energético
        ahorro = self.consumo_calefaccion * cert_EFG * REDUCCION_DEMANDA_REHABILITACION
        self.potencial_ahorro_gas = ahorro * CALEFACCION_SATISFECHA_GAS
        self.potencial_ahorro_electricidad = ahorro * CALEFACCION_SATISFECHA_ELECTRICIDAD

    
    def _wrap_v3(self) -> None:
        """
        Envuelve los métodos necesarios para calcular las mejoras del
        parque de edificios (V3).

        Este método ejecuta en secuencia los métodos para obtener certificados,
        antigüedades, distribuciones y ahorro energético.
        """
        self._get_certificados()
        self._get_antiguedades()
        self._get_distribuciones()
        self._get_ahorro()

    
    def get_vector_v3(
            self,
            mejora: float,
            escenario: str
            ) -> pd.Series:
        """
        Calcula la huella de carbono para un escenario específico de
        mejora del parque de edificios y factor de emisión.

        Este método ajusta los consumos eléctricos y de gas en función de
        las mejoras implementadas en el parque de edificios y calcula
        la huella de carbono resultante.

        Args:
            - mejora (float):
                Proporción de mejora del parque de edificios (entre 0 y 1).
            - escenario (str):
                Escenario de factor de emisión a utilizar;
                'Actual', 'PNIEC' o 'Borrador PNIEC'.

        Returns:
            - huella (pd.Series):
                Huella de carbono por barrio en toneladas de CO2 equivalente.
        """
        ### Comprobar valores de parámetros
        # Comprobar que la mejora está entre 0 y 1
        if mejora < 0 or mejora > 1:
            raise ValueError('La mejora debe ser un valor entre 0 y 1.')
        # Comprobar que el escenario es uno de los valores válidos
        if escenario not in FACTOR_EMISION_MIX.keys():
            raise ValueError('El escenario debe ser uno de los valores válidos.')
        
        ### Ejecutar vector
        # Calcular consumo energético
        consumo_gas = self.consumos_gas['Total'] - self.potencial_ahorro_gas * mejora
        consumo_electricidad = self.consumos_electricos['Total'] - self.potencial_ahorro_electricidad * mejora
        # Calcular huella de carbono
        huella = (
            consumo_electricidad * FACTOR_EMISION_MIX[escenario]) + (
            consumo_gas * FACTOR_EMISION_GAS)
        # Almacenar resultado
        self.vector_v3[(mejora, escenario)] = huella
        # Devolver resultado
        return huella
    

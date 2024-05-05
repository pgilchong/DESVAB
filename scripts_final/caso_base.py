"""
blablabla
"""


import numpy as np
import pandas as pd
import geopandas as gpd
import os
import copy
from typing import List, Dict, Tuple
import warnings
from geo import get_areas_barrios, get_matriz_overlap_poligonos


class AreaEnergiaVivienda:

    def __init__(
            self
    ):
        self.areas_barrios = get_areas_barrios()
        self.matriz_overlap = get_matriz_overlap_poligonos()


    def _calc_consumo_electrico(self):
        # Leer y preparar los datos de electricidad
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            CARPETA_DATOS, CARPETA_ENERGIA, ARCHIVO_ELECTRICIDAD_CP)
        electricidad_cp = pd.read_csv(path, sep=',', encoding='utf-8', skiprows=5, skipfooter=3,
                                      na_values='-', engine='python')
        electricidad_cp.columns = [
            'CP', 'Contratos_Total', 'Contratos_Residencial',
            'Contratos_Comercial', 'Contratos_Industrial',
            'Electricidad_Total', 'Electricidad_Residencial',
            'Electricidad_Comercial', 'Electricidad_Industrial',
            'Electricidad_Otro']
        electricidad_cp = electricidad_cp.set_index('CP').replace(',', '', regex=True).fillna(0).drop('Total').astype(float)
        
        # Calcular consumo medio por sector
        sectores = ['Total', 'Residencial', 'Comercial', 'Industrial']
        for sector in sectores:
            electricidad_cp[f'Electricidad_Media_{sector}'] = electricidad_cp[f'Electricidad_{sector}'] / electricidad_cp[f'Contratos_{sector}']
        electricidad_cp.fillna(0, inplace=True)
        
        # Inicializar DataFrame de consumos eléctricos por barrio
        columnas_electricidad = [f'Electricidad_{x}' for x in sectores + [f'Media_{s}' for s in sectores]]
        electricidad_barrios = pd.DataFrame(0, index=self.matriz_overlap.columns, columns=columnas_electricidad)

        # Calcular consumos por barrio
        for barrio in electricidad_barrios.index:
            for cp in electricidad_cp.index:
                overlap_factor = self.matriz_overlap.loc[cp, barrio]
                if overlap_factor > 0:
                    for columna in columnas_electricidad[:4]:
                        electricidad_barrios.loc[barrio, columna] += electricidad_cp.loc[cp, columna] * overlap_factor
                    for columna in columnas_electricidad[4:]:
                        electricidad_barrios.loc[barrio, columna] += electricidad_cp.loc[cp, columna] * (overlap_factor / self.areas_barrios[barrio])

        # Guardar DataFrame de consumo
        self.consumo_electricidad = electricidad_barrios.sort_index()
        
        # Calcular y guardar contratos por sector
        contratos = electricidad_barrios[[f'Electricidad_{s}' for s in sectores]].div(electricidad_barrios[[f'Electricidad_Media_{s}' for s in sectores]].values)
        self.contratos = contratos.rename(columns={col: col.split('_')[-1] for col in contratos.columns})


    def _calc_consumo_gas(self):
        """
        Genera y almacena un dataframe con los consumos de gas, totales
        y medios, por barrio.
        """
        ### GAS RESIDENCIAL
        # Calcular potencial de gas residencial
        gas_residencial = self.consumo_electricidad[
            ['Electricidad_Residencial', 'Electricidad_Media_Residencial']]
        gas_residencial *= RATIO_GAS_ELECTRICIDAD['Residencial']

        # Renombrar columnas
        gas_residencial.columns = ['Gas_Residencial', 'Gas_Medio_Residencial']

        # Obtener el path del archivo y leerlo
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            CARPETA_DATOS, CARPETA_ENERGIA, ARCHIVO_ACCESO_GAS)
        acceso_gas = pd.read_csv(
            path, sep=',', encoding='utf-8', skiprows=4, skipfooter=2,
            engine='python')
        
        # Filtrar y renombrar columnas
        acceso_gas = acceso_gas.iloc[1:, [0, 3]]
        acceso_gas.columns = ['ID', 'Acceso_Gas']

        # Coger solo el número antes del punto (dar formato a ID)
        acceso_gas['ID'] = acceso_gas['ID'].apply(lambda x: x.split('.')[0].strip())

        # Establecer ID como índice
        acceso_gas.set_index('ID', inplace=True)

        # Convertir % a float
        acceso_gas['Acceso_Gas'] = acceso_gas['Acceso_Gas'].apply(lambda x: float(x.replace('%', '')) / 100)

        # Calcular consumo de gas residencial según el % de acceso
        for barrio in gas_residencial.index:
            gas_residencial.loc[barrio] = gas_residencial.loc[barrio] * (
                acceso_gas.loc[barrio.split('.')[0], 'Acceso_Gas'])

        ### GAS COMERCIAL
        # Calcular potencial de gas comercial
        gas_comercial = self.consumo_electricidad[
            ['Electricidad_Comercial', 'Electricidad_Media_Comercial']]
        gas_comercial *= RATIO_GAS_ELECTRICIDAD['Comercial']

        # Renombrar columnas
        gas_comercial.columns = ['Gas_Comercial', 'Gas_Medio_Comercial']

        ### GAS INDUSTRIAL
        # Calcular potencial de gas industrial
        gas_industrial = self.consumo_electricidad[
            ['Electricidad_Industrial', 'Electricidad_Media_Industrial']]
        gas_industrial *= RATIO_GAS_ELECTRICIDAD['Industrial']

        # Renombrar columnas
        gas_industrial.columns = ['Gas_Industrial', 'Gas_Medio_Industrial']

        ### GAS TOTAL
        # Calcular potencial de gas total
        electricidad_otros = (
            self.consumo_electricidad['Electricidad_Total']) - (
            self.consumo_electricidad['Electricidad_Residencial']) - (
            self.consumo_electricidad['Electricidad_Comercial']) - (
            self.consumo_electricidad['Electricidad_Industrial'])
        gas_total = pd.DataFrame(0, index=self.consumo_electricidad.index,
                                 columns=['Gas_Total', 'Gas_Medio_Total'])
        gas_total['Gas_Total'] = (
            gas_residencial['Gas_Residencial']) + (
            gas_comercial['Gas_Comercial']) + (
            gas_industrial['Gas_Industrial']) + (
            electricidad_otros * RATIO_GAS_ELECTRICIDAD['Global'])
        gas_total['Gas_Medio_Total'] = (
            gas_total['Gas_Total'] / self.contratos['Total'])
        
        # Juntar resultados en un solo dataframe y guardarlo
        self.consumo_gas = pd.concat([
            gas_total, gas_residencial, gas_comercial, gas_industrial], axis=1)


    def _get_factores_emision(self):
        """
        Genera y almacena un diccionario con los factores de emisión de
        tCO2e/MWh para fuentes de energía no renovables.
        """
        ### EMISIONES
        # Obtener el path del archivo y leerlo
        path_emisiones = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            CARPETA_DATOS, CARPETA_ENERGIA, ARCHIVO_EMISIONES_RED)
        emisiones = pd.read_csv(path_emisiones, sep=',', encoding='utf-8',
                                skiprows=5, skipfooter=14, engine='python')
        
        # Filtrar columnas (2021) y renombrarlas
        emisiones = emisiones.iloc[:, [0, 1]]
        emisiones.columns = ['Fuente', 'Emisiones']

        # Establecer Fuente como índice
        emisiones.set_index('Fuente', inplace=True)

        # Convertir emisiones a float
        emisiones['Emisiones'] = emisiones['Emisiones'].apply(lambda x: float(x.replace(',', '.')))

        ### GENERACIÓN
        # Obtener el path del archivo y leerlo
        path_generacion = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            CARPETA_DATOS, CARPETA_ENERGIA, ARCHIVO_GENERACION_RED)
        generacion = pd.read_csv(
            path_generacion, sep=',', encoding='latin-1', skiprows=4,
            skipfooter=10, na_values='-', engine='python')
        
        # Filtrar columnas (2021) y renombrarlas
        generacion = generacion.iloc[:, [0, 2]]
        generacion.columns = ['Fuente', 'Generación']

        # Establecer Fuente como índice
        generacion.set_index('Fuente', inplace=True)

        # Convertir generación a float y GWh a MWh
        generacion['Generación'] = generacion['Generación'].apply(lambda x: float(x.replace(',', '.')) * 1000)

        ### FACTORES DE EMISIÓN
        # Definir fuentes no renovables
        fuentes_no_renovables = ['Carbón', 'Fuel + Gas', 'Ciclo combinado', 'Cogeneración', 'Residuos no renovables']

        # Calcular factores de emisión
        factores = {fuente: emisiones.loc[fuente, 'Emisiones'] / (
            generacion.loc[fuente, 'Generación']) for fuente in fuentes_no_renovables}
        
        # Guardar factores de emisión
        self.factores_emision = factores


    def _get_certificados(self):
        """
        Lee el archivo de certificados energéticos y genera los
        atributos certificados_consumo y certificados_emisiones.
        """
        # Obtener path del archivo
        path_certificados = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            CARPETA_DATOS, CARPETA_VIVIENDA, ARCHIVO_CERTIFICADOS)
        
        # Leer archivo
        df_certificados = pd.read_excel(path_certificados)

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

    
        def _get_antiguedades(self):
        """
        Lee el archivo de antigüedad de edificios y genera el atributo
        antiguedades.
        """
        # Obtener path del archivo
        path_edificios = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            CARPETA_DATOS, CARPETA_VIVIENDA, ARCHIVO_EDIFICIOS)
        
        # Leer archivo
        df_edificios = pd.read_excel(path_edificios, skiprows=2, skipfooter=2)

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

        # Cambiar a proporción respecto al total (dividir por columna total)
        #df_edificios[df_edificios.columns[1:]] = df_edificios.iloc[:, 1:].div(df_edificios['Total'], axis=1)

        # Guardar distribución de antigüedad de edificios
        self.antiguedades = df_edificios
        
    
    def _calc_distribuciones_certificados(self):
        """
        Genera los atributos distribucion_certificados_consumo y
        distribucion_certificados_emisiones.
        """
        # Sacar aproximación de distribución de letras para cada barrio
        # Sumar total de certificados por barrio, antigüedad y letra y
        # multiplicar por proporción de antigüedad
        
        consumo = copy.deepcopy(self.certificados_consumo)
        emisiones = copy.deepcopy(self.certificados_emisiones)

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
        

    def _calc_demanda_energetica(self):
        """
        Genera y almacena una serie con la demanda de energía por
        barrio.
        """
        # Crear serie de demanda de energía por barrio
        demanda = pd.Series(index=self.antiguedades.index, dtype=float)
        # Sumar total de certificados por barrio y multiplicar por media
        # de consumo
        for barrio in demanda.index:
            demanda[barrio] = (
                self.distribucion_certificados_consumo[
                    self.distribucion_certificados_consumo['ID'] == barrio][
                        'Total Certificados'] * (
                self.distribucion_certificados_consumo[
                    self.distribucion_certificados_consumo['ID'] == barrio][
                        'Media Consumo'])
                ).sum()
        # Guardar serie
        self.demanda = demanda

    
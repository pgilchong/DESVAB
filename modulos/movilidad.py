
"""
    explicar módulo

    ya vienen los datos procesados en excel, hay que recodificarlos
    a barrios
"""

# ----------------------------------------------
# MÓDULOS
# ----------------------------------------------
import geopandas as gpd
import os
import pandas as pd
import time
import warnings
from geo import get_matriz_cuadrantes, get_poligonos_barrios, get_poligonos_cuadrantes
from math import isclose


# ----------------------------------------------
# VALORES DE VECTORES
# ----------------------------------------------
M1 = [0, .25, .5, .75, 1]
M2 = [0, .25, .5, .75, 1]
M3 = [0, .25, .5, .75, 1]
U2 = [0, .05, .1, .15, .2]


# ----------------------------------------------
# CONSTANTES
# ----------------------------------------------
# Caso base


# Vectores M1 y M2
FACTOR_EMISION_MIX = { # factores de emisión de la red eléctrica
    'Actual': 0.12, # tCO2e/MWh
    'PNIEC': 0.068, # tCO2e/MWh
    'Borrador PNIEC': 0.03 # tCO2e/MWh
}

# Vector U2
MAXIMO_U2 = 0.2


# ----------------------------------------------
# RUTAS Y NOMBRES DE ARCHIVOS
# ----------------------------------------------
base_path = os.path.abspath(__file__)
desvab_root = os.path.dirname(os.path.dirname(base_path))
data_path = os.path.join(desvab_root, 'datos')
movilidad_path = os.path.join(data_path, 'movilidad')

excel_path = os.path.join(movilidad_path, 'contaminacion_trafico_2021_v3.xlsx')


# ----------------------------------------------
# CLASE ÁREA MOVILIDAD
# ----------------------------------------------
class AreaMovilidad:
    """
    explicar clase
    """
    def __init__(
            self,
            valores_m1 = M1,
            valores_m2 = M2,
            valores_m3 = M3,
            verbose = False
        ):
        """
        explicar método
        """
        if verbose:
            print('Inicializando Área Movilidad...')
            print('Calculando caso base...')
            start_time = time.time()

        # Cargar datos de excel
        excel = pd.ExcelFile(excel_path)
        
        # Cargar datos de cuadrantes y barrios
        matriz_overlap = get_matriz_cuadrantes()
        gdf_cuad = get_poligonos_cuadrantes()
        gdf_barrios = get_poligonos_barrios()

        def cargar_datos(
                sheet_name: str,
                gdf_cuad: gpd.GeoDataFrame = gdf_cuad,
                gdf_barrios: gpd.GeoDataFrame = gdf_barrios,
                ) -> pd.DataFrame:
            with warnings.catch_warnings(record=True):
                warnings.simplefilter('ignore', UserWarning)
                df_cuad = excel.parse(
                    sheet_name, usecols=['num_cuadrante', 'CO2_real_kg', 'publico_kWh', 'privado_kWh'],
                    index_col='num_cuadrante'
                    )
            df_cuad['CO2_real_kg'] = df_cuad['CO2_real_kg'] / (10**6)  # Convertir a toneladas desde g, datos pone kg pero son g
            df_cuad['FE'] = df_cuad['publico_kWh'] + df_cuad['privado_kWh'] # Sumar kWh de públicos y privados
            df_cuad['FE'] = df_cuad['FE'] / (10**6)  # Convertir a MWh
            df_cuad = df_cuad.drop(columns=['publico_kWh', 'privado_kWh'])
            cols = ['CO2_real_kg', 'FE']
            df_barrios = pd.DataFrame(0, index=matriz_overlap.columns, columns=df_cuad.columns)

            gdf_cuad = gdf_cuad.join(df_cuad)
            gdf_barrios = gdf_barrios.join(df_barrios, on='ID')

            # Asignar emisiones a partir del solapamiento de cuadrantes y barrios
            for barrio in gdf_barrios.index:
                for cuad in gdf_cuad.index:
                    if matriz_overlap.loc[cuad, barrio]:
                        overlap_area = matriz_overlap.loc[cuad, barrio]
                        gdf_barrios.loc[barrio, cols] += gdf_cuad.loc[cuad, cols] * overlap_area
            
            # Ajustar emisiones para barrios no completamente contenidos en cuadrantes
            for neighborhood, fila in gdf_barrios.iterrows():
                if not gdf_cuad.intersects(fila.geometry).any():
                    continue
                neighborhood_area = fila.geometry.area
                overlap_area = gdf_cuad[gdf_cuad.intersects(fila.geometry)].intersection(fila.geometry).area.sum()
                if overlap_area < neighborhood_area:
                    correction_factor = neighborhood_area / overlap_area
                    gdf_barrios.loc[neighborhood, cols] *= correction_factor

            # Asignar emisiones a barrios sin solapamiento
            neighborhoods_with_data = gdf_barrios[(gdf_barrios['CO2_real_kg'] > 0)]
            for neighborhood, fila in gdf_barrios.iterrows():
                if not neighborhood == '17.5' and not gdf_cuad.intersects(fila.geometry).any():
                    # Buscar el barrio más cercano con datos disponibles
                    center_point = fila.geometry.centroid
                    nearest_neighborhood = neighborhoods_with_data.distance(center_point).idxmin()
                    gdf_barrios.loc[neighborhood, cols] = gdf_barrios.loc[nearest_neighborhood, cols] * 0.5

            # Distribuir emisiones sobrantes de cuadrantes sin asignar a barrios
            for cuad, fila in gdf_cuad.iterrows():
                # Si el cuadrante no tiene emisiones o no tiene área sobrante (suma aprox. 1), no hacer nada
                if (fila['CO2_real_kg'] == 0) or (isclose(matriz_overlap.loc[cuad].sum(), 1, abs_tol=1e-5)):
                    continue
                # Comprobar si el cuadrante se solapa con algún barrio
                overlapping_neighborhoods = gdf_barrios[gdf_barrios.intersects(fila.geometry)]
                if overlapping_neighborhoods.empty:
                    # Asignar a barrio más cercano si no hay solapamiento
                    # Encontrar el barrio más cercano al centro del cuadrante
                    center_point = fila.geometry.centroid
                    nearest_neighborhood = gdf_barrios.distance(center_point).idxmin()
                    gdf_barrios.loc[nearest_neighborhood, cols] += fila[cols]
                elif len(overlapping_neighborhoods) == 1:
                    # Asignar todas las emisiones sobrantes al único barrio con solapamiento
                    neighborhood = overlapping_neighborhoods.iloc[0].name
                    factor = 1 - matriz_overlap.loc[cuad, neighborhood].sum()
                    gdf_barrios.loc[neighborhood, cols] += fila[cols] * factor
                else:
                    # Distribuir emisiones a barrios con solapamiento
                    total_overlap_area = overlapping_neighborhoods.intersection(fila.geometry).area.sum()
                    leftover_proportion = 1 - matriz_overlap.loc[cuad].sum()
                    for _, neighborhood in overlapping_neighborhoods.iterrows():
                        overlap_area = neighborhood.geometry.intersection(fila.geometry).area
                        proportion = overlap_area / total_overlap_area
                        gdf_barrios.loc[neighborhood.name, cols] += fila[cols] * proportion * leftover_proportion

            co2 = gdf_barrios['CO2_real_kg'].groupby(gdf_barrios.index).sum()
            fe = gdf_barrios['FE'].groupby(gdf_barrios.index).sum()
            return co2, fe
        

        self.co2_base, self.fe_base = cargar_datos(0)
        self.huella = self.co2_base + self.fe_base * FACTOR_EMISION_MIX['Actual']
        if verbose: print('Caso base calculado.')

        self.vector_m1, self.vector_m2, self.vector_m3, self.vector_u2 = {}, {}, {}, {}
        for vector in [self.vector_m1, self.vector_m2, self.vector_m3, self.vector_u2]:
            for escenario in FACTOR_EMISION_MIX:
                vector[(0, escenario)] = self.co2_base + self.fe_base * FACTOR_EMISION_MIX[escenario]

        nombres_excel = excel.sheet_names[1:]
        for hoja in nombres_excel:
            vector, valor = hoja.split('_')[0], hoja.split('_')[-1]
            valor = float(valor) / 100
            co2, fe = cargar_datos(hoja)
            if vector == 'M1':
                self.vector_m1[(valor, 'Actual')] = co2 + fe * FACTOR_EMISION_MIX['Actual']
                self.vector_m1[(valor, 'PNIEC')] = co2 + fe * FACTOR_EMISION_MIX['PNIEC']
                self.vector_m1[(valor, 'Borrador PNIEC')] = co2 + fe * FACTOR_EMISION_MIX['Borrador PNIEC']
            elif vector == 'M2':
                self.vector_m2[(valor, 'Actual')] = co2 + fe * FACTOR_EMISION_MIX['Actual']
                self.vector_m2[(valor, 'PNIEC')] = co2 + fe * FACTOR_EMISION_MIX['PNIEC']
                self.vector_m2[(valor, 'Borrador PNIEC')] = co2 + fe * FACTOR_EMISION_MIX['Borrador PNIEC']
            elif vector == 'M3':
                self.vector_m3[(valor, 'Actual')] = co2 + fe * FACTOR_EMISION_MIX['Actual']
                self.vector_m3[(valor, 'PNIEC')] = co2 + fe * FACTOR_EMISION_MIX['PNIEC']
                self.vector_m3[(valor, 'Borrador PNIEC')] = co2 + fe * FACTOR_EMISION_MIX['Borrador PNIEC']
            elif vector == 'U2':
                self.vector_u2[(valor / MAXIMO_U2, 'Actual')] = co2 + fe * FACTOR_EMISION_MIX['Actual']
                self.vector_u2[(valor / MAXIMO_U2, 'PNIEC')] = co2 + fe * FACTOR_EMISION_MIX['PNIEC']
                self.vector_u2[(valor / MAXIMO_U2, 'Borrador PNIEC')] = co2 + fe * FACTOR_EMISION_MIX['Borrador PNIEC']
            if verbose: print(f'Valor {valor} para {vector} calculado.')

        # Guardar vectores en atributo vectores
        self.vectores = {
            'M1': self.vector_m1,
            'M2': self.vector_m2,
            'M3': self.vector_m3,
            'U2': self.vector_u2
        }

        if verbose:
            print(f'Área Movilidad inicializada en {time.time() - start_time:.2f} s')


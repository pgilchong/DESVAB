# geo.py

"""
MÓDULO PARA LA GESTIÓN DE DATOS GEOGRÁFICOS

Este módulo contiene funciones para trabajar con datos geográficos
o geoespaciales con la idea de importarlas en otros módulos.

Funciones:
    - get_cps_valencia():
        Obtiene una lista de los códigos postales de Valencia desde el archivo de consumos eléctricos.

    - get_poligonos_cp():
        Devuelve un GeoDataFrame con los polígonos de los códigos postales de Valencia.

    - get_barrios_ids():
        Obtiene una lista con los IDs de los barrios de Valencia.

    - parse_geometry():
        Función auxiliar para convertir representaciones GeoJSON en objetos Polygon.

    - get_poligonos_barrios():
        Devuelve un GeoDataFrame con los polígonos de los barrios de Valencia.

    - get_areas_barrios():
        Calcula el área total de cada barrio sumando sus polígonos asociados.

    - get_areas_cp():
        Calcula el área total de cada código postal sumando sus polígonos asociados.

    - get_matriz_cp():
        Genera una matriz de superposición entre los códigos postales y los barrios de Valencia.

    - ids_a_nombre():
        Devuelve un diccionario que mapea el ID de cada barrio a su nombre correspondiente.

    - get_poligonos_cuadrantes():
        Devuelve un GeoDataFrame con los polígonos de los cuadrantes de Valencia.

    - get_areas_cuadrantes():
        Calcula el área total de cada cuadrante sumando sus polígonos asociados.

    - get_matriz_cuadrantes():
        Genera una matriz de superposición entre los cuadrantes y los barrios de Valencia.

    - get_poligonos_areas_censales():
        Devuelve un GeoDataFrame con los polígonos de las áreas censales de Valencia.

    - get_areas_censales():
        Calcula el área total de cada área censal sumando sus polígonos asociados.

    - get_matriz_overlap_censales():
        Genera una matriz de superposición entre las áreas censales y los barrios de Valencia.

    - get_poligonos_distritos():
        Obtiene los polígonos de los distritos de Valencia combinando los de los barrios.

    - get_poligonos_distritos_alt():
        Método alternativo para obtener los polígonos de los distritos desde un archivo JSON.

"""


# LIBRERÍAS
import ast
import os
import pandas as pd
import geopandas as gpd
import json
from typing import List
import warnings

from shapely.geometry import Polygon, MultiPolygon


# -------------------------------------------------
# CONSTANTES
# -------------------------------------------------
# NOMBRES DE CARPETAS Y ARCHIVOS
BASE_PATH = os.path.abspath(__file__)
DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(BASE_PATH)), 'datos')
ENERGIA_PATH = os.path.join(DATA_PATH, 'energia')
GEO_PATH = os.path.join(DATA_PATH, 'geo')
MOVILIDAD_PATH = os.path.join(DATA_PATH, 'movilidad')
CONSUMOS_PATH = os.path.join(ENERGIA_PATH, 'consumos_datadis.csv')
POLIGONOS_PATH = os.path.join(GEO_PATH, 'codigos_postales.geojson')
BARRIOS_PATH = os.path.join(GEO_PATH, 'barris-barrios.xlsx')
CUADRANTES_PATH = os.path.join(MOVILIDAD_PATH, 'contaminacion_trafico_2021_v3.xlsx')
CENSALES_PATH = os.path.join(GEO_PATH, 'seccions-censals-secciones-censales.xlsx')
DISTRITOS_PATH = os.path.join(GEO_PATH, 'districtes-distritos.json')


# -------------------------------------------------
# CÓDIGO / FUNCIONES GEOGRÁFICAS
# -------------------------------------------------
def get_cps_valencia() -> List[int]:
    """
    Devuelve los códigos postales de Valencia a partir de los CPs
    registrados en el fichero de consumos eléctricos del anuario.

    Devuelve:
        - cps (List[int]):
            Lista de códigos postales.
    """
    # Leer el archivo
    df_from_file = pd.read_csv(
        CONSUMOS_PATH, sep=',', encoding='utf-8', 
        skiprows=5, skipfooter=3, na_values='-', engine='python')
    # Obtener los códigos postales
    cps = df_from_file.iloc[1:, 0].astype(str).values
    # Devolver los códigos postales
    return cps


def get_poligonos_cp(
        cps: list = get_cps_valencia()
        ) -> gpd.GeoDataFrame:
    """
    Devuelve un GeoDataFrame con los polígonos de cada código postal de
    València a partir del archivo de códigos postales de la Comunidad
    Valenciana.

    Args:
        - cps (List[str], opcional):
            Lista de códigos postales de la ciudad de València.
            Por defecto, get_cps_valencia().
    
    Devuelve:
        - poligonos_cp (gpd.GeoDataFrame):
            GeoDataFrame con índice CP y columna 'geometry' con los polígonos
            de cada CP.
    """
    # Leer el archivo
    with open(POLIGONOS_PATH) as f:
        json_cps = json.load(f)
    
    # Crear una lista para almacenar los polígonos y los códigos postales
    geometries = []
    cp_values = []
    
    # Recorrer los polígonos
    for feature in json_cps['features']:
        cp = feature['properties']['COD_POSTAL']
        # Si el CP está en la lista de CPs de Valencia
        if cp in cps:
            # Crear polígono a partir de las coordenadas
            polygon = Polygon(feature['geometry']['coordinates'][0])
            geometries.append(polygon)
            cp_values.append(cp)
    
    # Crear un GeoDataFrame con los polígonos de cada CP
    poligonos_cp = gpd.GeoDataFrame({'CP': cp_values, 'geometry': geometries})
    poligonos_cp.set_index('CP', inplace=True)
    poligonos_cp.sort_index(inplace=True)
    
    # Devolver el GeoDataFrame con los polígonos de cada CP
    return poligonos_cp


def get_barrios_ids() -> List[str]:
    """
    Devuelve una lista con los IDs de los barrios de València.

    Devuelve:
        - barrios_ids (List[str]):
            Lista con los IDs de los barrios de València.
    """
    # Leer el archivo
    poligonos_barrios = pd.read_excel(BARRIOS_PATH)
    # Crear el ID (formato distrito.barrio)
    poligonos_barrios['ID'] = (
        poligonos_barrios['Codigo distrito'].astype(str)) + '.' + (
        poligonos_barrios['Codigo barrio'].astype(str))
    # Crear la lista de IDs, ordenada
    barrios_ids = poligonos_barrios['ID'].sort_values().unique().tolist()
    # Devolver la lista de IDs de los barrios
    return barrios_ids


def parse_geometry(geo_shape_str: str) -> Polygon:
    """
    Función de ayuda para parsear la columna 'geo_shape' de los
    archivos de datos geográficos.

    Args:
        - geo_shape_str (str):
            String con la representación de un polígono en formato
            GeoJSON.

    Devuelve:
        - Polygon:
            Polígono creado a partir de la representación GeoJSON.
    """
    geo_dict = ast.literal_eval(geo_shape_str)
    return Polygon(geo_dict['coordinates'][0])


def get_poligonos_barrios() -> gpd.GeoDataFrame:
    """
    Devuelve un GeoDataFrame con los polígonos de cada barrio de València
    a partir del archivo de polígonos de la ciudad.

    Devuelve:
        - poligonos_barrios (gpd.GeoDataFrame):
            GeoDataFrame con índice ID y columna 'geometry' con los polígonos
            de cada barrio.
    """
    # Leer el archivo
    poligonos_barrios = pd.read_excel(BARRIOS_PATH)
    # Crear el ID (formato distrito.barrio)
    poligonos_barrios['ID'] = (
        poligonos_barrios['Codigo distrito'].astype(str)) + '.' + (
        poligonos_barrios['Codigo barrio'].astype(str))
    # Evaluar la columna geo_shape para obtener el polígono de cada barrio
    poligonos_barrios['geometry'] = poligonos_barrios['geo_shape'].apply(parse_geometry)
    # Filtrar las columnas y preparar para GeoDataFrame
    poligonos_barrios = poligonos_barrios[['ID', 'geometry']]

    # Crear un GeoDataFrame
    poligonos_barrios_gdf = gpd.GeoDataFrame(poligonos_barrios, geometry='geometry')
    # Establecer el ID como índice
    poligonos_barrios_gdf = poligonos_barrios_gdf.set_index('ID')
    # Ordenar el índice
    poligonos_barrios_gdf = poligonos_barrios_gdf.sort_index()

    # Devolver el GeoDataFrame con los polígonos de cada barrio
    return poligonos_barrios_gdf


def get_areas_barrios(
        poligonos_barrios: gpd.GeoDataFrame = None
        ) -> dict:
    """
    Calcula la suma de las áreas de los polígonos asociados a cada
    barrio devueltos por get_poligonos_barrios y devuelve un
    diccionario con los barrios como claves y la suma de las áreas de
    sus polígonos como valores.
    
    Devuelve:
        - areas_barrios_sum (dict):
            Diccionario con barrios como claves y la suma de las áreas
            de sus polígonos como valores.
    """
    # Obtener el GeoDataFrame con los polígonos de cada barrio
    poligonos_barrios = get_poligonos_barrios() if poligonos_barrios is None else poligonos_barrios
    
    # Agrupar los polígonos por barrio y sumar las áreas de cada grupo
    #poligonos_barrios['geometry'] = poligonos_barrios['geometry'].to_crs({'proj': 'cea'})
    areas_sum = poligonos_barrios.groupby('ID')['geometry'].apply(
        lambda x: x.area.sum())
    
    # Devolver el resultado como un diccionario
    return areas_sum.to_dict()


def get_areas_cp(
        poligonos_cp: gpd.GeoDataFrame = None
        ) -> dict:
    """
    Calcula la suma de las áreas de los polígonos asociados a cada
    código postal devueltos por get_poligonos_cp y devuelve un
    diccionario con los códigos postales como claves y la suma de las
    áreas de sus polígonos como valores.
    
    Devuelve:
        - areas_cp_sum (dict):
            Diccionario con códigos postales como claves y la suma de
            las áreas de sus polígonos como valores.
    """
    # Obtener el GeoDataFrame con los polígonos de cada código postal
    poligonos_cp = get_poligonos_cp() if poligonos_cp is None else poligonos_cp
    
    # Agrupar los polígonos por código postal y sumar las áreas de cada grupo
    #poligonos_cp['geometry'] = poligonos_cp['geometry'].to_crs({'proj': 'cea'})
    areas_sum = poligonos_cp.groupby('CP')['geometry'].apply(
        lambda x: x.area.sum())
    
    # Devolver el resultado como un diccionario
    return areas_sum.to_dict()


def get_matriz_cp(
        poligonos_cp: gpd.GeoDataFrame = None,
        poligonos_barrios: gpd.GeoDataFrame = None,
        porcentaje: bool = True
        ) -> pd.DataFrame:
    """
    Devuelve un DataFrame con la matriz de overlap entre los polígonos de los
    CPs y los polígonos de los barrios de València.
    
    Args:
        - porcentaje (bool, opcional):
            Si True, devuelve el porcentaje de overlap. Por defecto, True.
        - poligonos_cp (gpd.GeoDataFrame, opcional):
            GeoDataFrame con los polígonos de los códigos postales. Por defecto, get_poligonos_cp().
        - poligonos_barrios (gpd.GeoDataFrame, opcional):
            GeoDataFrame con los polígonos de los barrios. Por defecto, get_poligonos_barrios().
    
    Devuelve:
        - matriz_overlap (pd.DataFrame): DataFrame con índice CP y columnas barrio con el overlap entre el CP y el barrio.
    """
    # Obtener los GeoDataFrames con los polígonos de CPs y barrios
    poligonos_cp = get_poligonos_cp() if poligonos_cp is None else poligonos_cp
    poligonos_barrios = get_poligonos_barrios() if poligonos_barrios is None else poligonos_barrios

    # Inicializar el DataFrame de la matriz de overlap
    matriz_overlap = pd.DataFrame(0, index=poligonos_cp.index.unique(), columns=poligonos_barrios.index.unique())
    areas_cp = get_areas_cp(poligonos_cp)
    
    # Recorrer los CPs
    for cp_index, cp_row in poligonos_cp.iterrows():
        # Recorrer los barrios
        for barrio_index, barrio_row in poligonos_barrios.iterrows():
            if cp_row['geometry'].intersects(barrio_row['geometry']):
                # Calcular intersección
                intersection = cp_row['geometry'].intersection(barrio_row['geometry'])
                # Pasar a Cylindrical equal-area projection para calcular el área
                #intersection = intersection.to_crs({'proj': 'cea'})
                # Calcular el área de intersección
                intersection_area = intersection.area
                if porcentaje:
                    # Calcular el porcentaje del área de intersección respecto al área total del CP
                    porcentaje_overlap = (intersection_area / areas_cp[cp_index])
                    matriz_overlap.loc[cp_index, barrio_index] += porcentaje_overlap
                else:
                    matriz_overlap.loc[cp_index, barrio_index] += intersection_area
    
    return matriz_overlap


def ids_a_nombre() -> dict:
    """
    Devuelve un diccionario con el ID de cada barrio como clave y el
    nombre del barrio como valor.

    Devuelve:
        - dict_id_a_nombre (dict):
            Diccionario con el ID de cada barrio como clave y el nombre
            del barrio como valor.
    """
    # Leer el archivo
    poligonos_barrios = pd.read_excel(BARRIOS_PATH)
    # Crear el ID (formato distrito.barrio)
    poligonos_barrios['ID'] = (
        poligonos_barrios['Codigo distrito'].astype(str)) + '.' + (
            poligonos_barrios['Codigo barrio'].astype(str))
    # Crear el diccionario
    dict_id_a_nombre = poligonos_barrios.set_index('ID')['Nombre']
    # Cambiar nombres a título (str.title())
    dict_id_a_nombre = dict_id_a_nombre.apply(lambda x: x.title())
    # Devolver el diccionario
    return dict_id_a_nombre.to_dict()

ID_A_NOMBRE = ids_a_nombre()


def get_poligonos_cuadrantes() -> gpd.GeoDataFrame:
    """
    Devuelve un GeoDataFrame con los polígonos de cada cuadrante de
    València a partir del archivo de límites de cuadrantes.

    Devuelve:
        - gdf_poligonos_cuadrantes (gpd.GeoDataFrame):
            GeoDataFrame con índice cuadrante y columna 'geometry' con los
            polígonos de cada cuadrante.
    """
    with warnings.catch_warnings(record=True):
        warnings.simplefilter('ignore', UserWarning)
        poligonos_cuadrantes = (
            pd.read_excel(CUADRANTES_PATH).set_index('num_cuadrante').iloc[:, :4])
    # Renombrar las columnas
    poligonos_cuadrantes.columns = ['lon_min', 'lon_max', 'lat_min', 'lat_max']
    # Crear la columna 'geometry' con los polígonos
    poligonos_cuadrantes['geometry'] = poligonos_cuadrantes.apply(
        lambda x: Polygon([
            (x['lon_min'], x['lat_min']), (x['lon_min'], x['lat_max']),
            (x['lon_max'], x['lat_max']), (x['lon_max'], x['lat_min']),
            (x['lon_min'], x['lat_min'])  # Cerrar el polígono
        ]), axis=1)
    # Convertir a GeoDataFrame
    gdf_poligonos_cuadrantes = gpd.GeoDataFrame(poligonos_cuadrantes, geometry='geometry')
    
    return gdf_poligonos_cuadrantes


def get_areas_cuadrantes(
        poligonos_cuadrantes: gpd.GeoDataFrame = get_poligonos_cuadrantes()
        ) -> dict:
    """
    Devuelve un diccionario con el área de cada cuadrante a partir del
    archivo de límites de cuadrantes.

    Devuelve:
        - areas_cuadrantes (pd.Series):
            Serie con el índice representando el número del cuadrante y
            el valor representando el área de cada cuadrante.
    """
    # Utilizar la función modificada para obtener los polígonos de cuadrantes como un GeoDataFrame
    gdf_poligonos_cuadrantes = get_poligonos_cuadrantes() if poligonos_cuadrantes is None else poligonos_cuadrantes
    
    # Calcular el área de cada polígono directamente
    areas_cuadrantes = gdf_poligonos_cuadrantes['geometry'].area
    
    return areas_cuadrantes.to_dict()


def get_matriz_cuadrantes() -> pd.DataFrame:
    """
    Devuelve un DataFrame con la matriz de overlap entre los polígonos
    de los cuadrantes y los polígonos de los barrios de València.
    
    Devuelve:
        - matriz_overlap (pd.DataFrame):
            DataFrame con índice cuadrante y columnas barrio con el
            overlap entre el cuadrante y el barrio, expresado como
            porcentaje del área del cuadrante que cada barrio ocupa.
    """
    # Obtener los polígonos de cuadrantes y barrios como GeoDataFrames
    poligonos_cuadrantes = get_poligonos_cuadrantes()
    poligonos_barrios = get_poligonos_barrios()

    areas_cuadrantes = get_areas_cuadrantes(poligonos_cuadrantes)

    # Crear el DataFrame de la matriz de overlap
    matriz_overlap = pd.DataFrame(0, index=poligonos_cuadrantes.index,
                                  columns=poligonos_barrios.index.unique(), dtype=float)

    # Iterar sobre cada cuadrante y barrio para calcular el overlap
    for cuadrante_idx, cuadrante_row in poligonos_cuadrantes.iterrows():
        for barrio_idx, barrio_row in poligonos_barrios.iterrows():
            if cuadrante_row['geometry'].intersects(barrio_row['geometry']):
                # Calcular el área de intersección
                intersection_area = cuadrante_row['geometry'].intersection(barrio_row['geometry']).area
                # Calcular porcentaje de overlap respecto al área del cuadrante
                porcentaje_overlap = (intersection_area / areas_cuadrantes[cuadrante_idx])
                matriz_overlap.loc[cuadrante_idx, barrio_idx] = porcentaje_overlap

    return matriz_overlap


def get_poligonos_areas_censales() -> gpd.GeoDataFrame:
    """
    Devuelve un GeoDataFrame con los polígonos de cada área censal
    de València a partir del archivo de límites de áreas censales.

    Devuelve:
        - gdf_poligonos_censales (gpd.GeoDataFrame):
            GeoDataFrame con índice ID y columna 'geometry' con los
            polígonos de cada área censal.
    """
    # Leer el archivo
    poligonos_censales = pd.read_excel(CENSALES_PATH)
    # Crear el ID (renombrar Código Distrito Sección a ID)
    poligonos_censales = poligonos_censales.rename(
        columns={'Código Distrito Sección': 'ID'})
    # Recodificar a string el ID y añadir un 0 al principio si la longitud es 3
    poligonos_censales['ID'] = poligonos_censales['ID'].astype(int).astype(str).apply(
        lambda x: '0' + x if len(x) == 3 else x)
    # Evaluar la columna geo_shape para obtener el polígono de cada área censal
    poligonos_censales['geometry'] = poligonos_censales['geo_shape'].apply(parse_geometry)
    # Convertir a GeoDataFrame
    gdf_poligonos_censales = gpd.GeoDataFrame(poligonos_censales, geometry='geometry')
    # Establecer el ID como índice y ordenarlo
    gdf_poligonos_censales = gdf_poligonos_censales.set_index('ID').sort_index()

    # Devolver el GeoDataFrame con los polígonos de cada área censal
    return gdf_poligonos_censales


def get_areas_censales(
        poligonos_censales: gpd.GeoDataFrame = get_poligonos_areas_censales()
        ) -> dict:
    """
    Calcula la suma de las áreas de los polígonos asociados a cada
    área censal devueltos por get_poligonos_areas_censales y devuelve
    un diccionario con los códigos postales como claves y la suma de
    las áreas de sus polígonos como valores.

    Devuelve:
        - areas_censales_sum (dict):
            Diccionario con áreas censales como claves y la suma de las
            áreas de sus polígonos como valores.
    """
    # Obtener el GeoDataFrame con los polígonos de cada área censal
    poligonos_censales = get_poligonos_areas_censales() if poligonos_censales is None else poligonos_censales

    # Agrupar los polígonos por área censal y sumar las áreas de cada grupo
    areas_sum = poligonos_censales.groupby('ID')['geometry'].apply(
        lambda x: x.area.sum())
    
    # Devolver el resultado como un diccionario
    return areas_sum.to_dict()


def get_matriz_overlap_censales() -> pd.DataFrame:
    """
    Devuelve un DataFrame con la matriz de overlap entre los polígonos
    de las áreas censales y los polígonos de los barrios de València.

    Devuelve:
        - matriz_overlap (pd.DataFrame):
            DataFrame con índice área censal y columnas barrio con el
            overlap entre el área censal y el barrio, expresado como
            porcentaje del área del área censal que cada barrio ocupa.
    """
    # Definir poligonos utilizando las funciones actualizadas que devuelven GeoDataFrames
    poligonos_censales = get_poligonos_areas_censales()
    poligonos_barrios = get_poligonos_barrios()

    areas_censales = get_areas_censales(poligonos_censales)

    # Crear el DataFrame de la matriz de overlap
    matriz_overlap = pd.DataFrame(0, index=poligonos_censales.index.unique(),
                                  columns=poligonos_barrios.index.unique(), dtype=float)

    # Iterar sobre cada área censal y barrio para calcular el overlap
    for censal_index, censal_row in poligonos_censales.iterrows():
        for barrio_index, barrio_row in poligonos_barrios.iterrows():
            if censal_row['geometry'].intersects(barrio_row['geometry']):
                # Calcular el área de intersección
                intersection_area = censal_row['geometry'].intersection(barrio_row['geometry']).area
                # Normalizar el área de intersección por el área total del área censal para obtener el porcentaje de overlap
                porcentaje_overlap = (intersection_area / areas_censales[censal_index])
                matriz_overlap.loc[censal_index, barrio_index] = porcentaje_overlap

    return matriz_overlap


def get_poligonos_distritos(
        paper: bool = False
        ) -> gpd.GeoDataFrame:
    """
    Combina los polígonos de los barrios para obtener los polígonos de los distritos.

    Args:
        - paper (bool, opcional):
            Si True, elimina los barrios 17.5, 19.3, 19.4, 19.5 y 19.6 (para el paper).
            Por defecto, False.

    Devuelve:
        - poligonos_distritos_gdf (gpd.GeoDataFrame):
            GeoDataFrame con índice ID y columna 'geometry' con los polígonos de cada distrito.
    """
    # a partir de get_poligonos_barrios(), combina los polígonos de los barrios para obtener los polígonos de los distritos
    # se sabe los distritos a partir de la primera parte del índice de los barrios (antes del punto)
    poligonos_barrios = get_poligonos_barrios()
    poligonos_distritos = poligonos_barrios.copy()
    if paper:
        # remove indices 17.5, 19.3, 19.4, 19.5, 19.6
        poligonos_distritos = poligonos_distritos.drop(['17.5', '19.3', '19.4', '19.5', '19.6'])
    poligonos_distritos.index = poligonos_distritos.index.str.split('.').str[0]
    poligonos_distritos = poligonos_distritos.dissolve(by=poligonos_distritos.index)
    poligonos_distritos = poligonos_distritos.buffer(0.0000000000000000000000000000000001)
    
    poli_aux = get_poligonos_distritos_()
    poli_aux.reset_index(inplace=True)
    geom0 = poli_aux.loc[poli_aux[poli_aux['ID'] == '17'].geometry.area.idxmax()].geometry
    geom1 = poligonos_distritos.loc['17'].geoms[0]
    poligonos_distritos.loc['17'] = MultiPolygon([geom0, geom1])
    
    return poligonos_distritos


def get_poligonos_distritos_alt(
        paper: bool = False
        ) -> gpd.GeoDataFrame:
    """
    Combina los polígonos de los barrios para obtener los polígonos de los distritos (método alternativo).

    Args:
        - paper (bool, opcional):
            Si True, elimina los barrios 17.5, 19.3, 19.4, 19.5 y 19.6 (para el paper).
            Por defecto, False.

    Devuelve:
        - poligonos_distritos_gdf (gpd.GeoDataFrame):
            GeoDataFrame con índice ID y columna 'geometry' con los polígonos de cada distrito.
    """    
    # Leer el archivo json
    poligonos_distritos = pd.read_json(DISTRITOS_PATH, encoding='utf-8')

    # identificador Código distrito
    poligonos_distritos = poligonos_distritos.rename(columns={'coddistrit': 'ID'})
    poligonos_distritos['ID'] = poligonos_distritos['ID'].astype(str)

    # Evaluar la columna geo_shape para obtener el polígono de cada distrito
    poligonos_distritos['geometry'] = poligonos_distritos['geo_shape'].apply(
        lambda x: Polygon(x['geometry']['coordinates'][0]))
    
    # Filtrar las columnas y preparar para GeoDataFrame
    poligonos_distritos = poligonos_distritos[['ID', 'geometry']]

    # Crear un GeoDataFrame
    poligonos_distritos_gdf = gpd.GeoDataFrame(poligonos_distritos, geometry='geometry')
    # Establecer el ID como índice
    poligonos_distritos_gdf = poligonos_distritos_gdf.set_index('ID')
    # Ordenar el índice
    poligonos_distritos_gdf = poligonos_distritos_gdf.sort_index()

    
    if paper:
        # remove neighborhoods 17.5, 19.3, 19.4, 19.5, 19.6 using difference function
        poligonos_barrios = get_poligonos_barrios()
        poligonos_distritos_gdf = poligonos_distritos_gdf.difference(poligonos_barrios.loc[['17.5', '19.3', '19.4', '19.5', '19.6']].unary_union)
        # remove None rows
        poligonos_distritos_gdf = poligonos_distritos_gdf[poligonos_distritos_gdf.geometry.notna()]
    
    # Devolver el GeoDataFrame con los polígonos de cada distrito
    return poligonos_distritos_gdf


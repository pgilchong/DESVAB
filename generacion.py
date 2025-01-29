# generacion.py

"""
MÓDULO DE GENERACIÓN/EJECUCIÓN

Este módulo se encarga de ejecutar los cálculos a partir de los módulos de las áreas.
Se inicializan las áreas, cargando los datos y calculando los vectores.
Se combinan los resultados en un solo DataFrame y se guardan en archivos CSV, JSON y Excel.
"""


# ----------------------------------------------
# MÓDULOS
# ----------------------------------------------
import ast
import os
import pandas as pd
import sys
import time

from modulos.energia import AreaEnergia
from modulos.movilidad import AreaMovilidad
from modulos.residuos import AreaResiduos
from modulos.urbanismo import AreaUrbanismo
from modulos.vivienda import AreaVivienda


# ----------------------------------------------
# RUTAS Y NOMBRES DE ARCHIVOS
# ----------------------------------------------
BASE_PATH = os.path.abspath(__file__) # Path: generacion.py
DESVAB_ROOT = os.path.dirname(BASE_PATH) # Path: desvab
DATA_PATH = os.path.join(DESVAB_ROOT, 'datos') # Path: desvab/datos
RESULTADOS_PATH = os.path.join(DESVAB_ROOT, 'resultados') # Path: desvab/resultados

BARRIOS_PATH = os.path.join(DATA_PATH, 'demografia', 'barrios.xlsx') # Path: desvab/datos/demografia/barrios.xlsx


# ----------------------------------------------
# FUNCIONES
# ----------------------------------------------
def clean_value(x: float) -> float:
    """
    Redondea a 0 los valores cercanos a 0.

    Args:
        x (float): Valor a redondear.

    Devuelve:
        float: Valor redondeado a 0 si es cercano a 0.
    """
    return 0 if abs(x) < 1e-8 else x


def main(verbose: bool = False) -> None:
    """
    Ejecuta el proceso principal de cálculo de huellas de carbono por área.

    Args:
        verbose (bool): Si es True, imprime mensajes de estado durante la ejecución. Por defecto es False.

    Proceso:
        1. Inicializa las áreas de Energía, Vivienda, Movilidad, Urbanismo y Residuos.
        2. Carga los datos demográficos de los barrios desde un archivo Excel.
        3. Combina los resultados de las diferentes áreas en un único DataFrame.
        4. Genera y guarda archivos Excel por vector y por área.
        5. Guarda los resultados consolidados en formatos CSV y JSON.
    """
    # Inicializar áreas
    if verbose:
        print('Inicializando áreas y cargando datos...')
        start_time = time.time()
    energia = AreaEnergia(verbose=verbose)
    vivienda = AreaVivienda(verbose=verbose)
    movilidad = AreaMovilidad(verbose=verbose)
    urbanismo = AreaUrbanismo(verbose=verbose)
    residuos = AreaResiduos(verbose=verbose)
    barrios = pd.read_excel(BARRIOS_PATH, usecols=['ID', 'Nombre', 'Población'], skipfooter=2)
    barrios.set_index('ID', inplace=True)
    barrios.index = barrios.index.astype(str)
    nombre_barrios = barrios['Nombre']
    poblacion = barrios['Población']
    if verbose:
        print(f'Áreas inicializadas en {time.time() - start_time:.2f} s')

    ### Combinar resultados en un solo DataFrame
    if verbose:
        print('Combinando resultados...')
        start_time = time.time()
    # Crear DataFrame vacío
    df = pd.DataFrame(columns=['id', 'vector', 'valor_vector', 'huella', 'reduccion', 'huella/capita'])
    # Crear excel de resultados por área
    with pd.ExcelWriter(os.path.join(RESULTADOS_PATH, 'resultados.xlsx'), engine='xlsxwriter') as writer_a:
        # Iterar sobre áreas y vectores
        areas = [energia, vivienda, urbanismo, movilidad, residuos]
        sheets_a = {
            'E': {},
            'V': {},
            'M': {},
            'U': {},
            'R': {}
        }
        for area in areas:
            for nombre_vector, vector in area.vectores.items():
                # Crear excel
                with pd.ExcelWriter(os.path.join(RESULTADOS_PATH, 'por_area', f'{area.nombre}.xlsx'), engine='xlsxwriter') as writer_v:
                    for valor_vector, huella in vector.items():
                        # Formato a valor_vector
                        if type(valor_vector) == tuple:
                            valor_vector = (str(round(valor_vector[0]*100))+'%', valor_vector[1])
                        else:
                            valor_vector = str(round(valor_vector*100))+'%'
                        # Calcular reducción y huella per cápita
                        reduccion = area.huella - huella
                        huella_capita = huella / poblacion
                        # Redondear a 0 valores cercanos a 0
                        huella = huella.apply(clean_value)
                        reduccion = reduccion.apply(clean_value)
                        huella_capita = huella_capita.apply(clean_value)
                        # Crear registros para el DataFrame
                        df_concat = pd.DataFrame({
                            'id': huella.index,
                            'vector': nombre_vector,
                            'valor_vector': str(valor_vector),
                            'huella': huella,
                            'reduccion': reduccion,
                            'huella/capita': huella_capita
                        })
                        # Concatenar registros al DataFrame
                        df = pd.concat([df, df_concat])
                        # Guardar para excel de áreas
                        nombre_vector_a = '*'+nombre_vector if nombre_vector in ['V1', 'U2'] else nombre_vector
                        valor_vector_a = ', Mix Red '.join([str(v) for v in valor_vector]) if type(valor_vector) == tuple else valor_vector
                        sheets_a[nombre_vector[0]][(nombre_vector, valor_vector_a)] = pd.DataFrame({
                            'ID.': huella.index,
                            f'{nombre_vector_a}, {valor_vector_a}. Huella / tCO2e': huella,
                            f'{nombre_vector_a}, {valor_vector_a}. Reducción / tCO2e': reduccion,
                            f'{nombre_vector_a}, {valor_vector_a}. Huella/cápita / tCO2e': huella_capita
                        })
                        # Escribir a excel de vector
                        sheetname_v = f'{nombre_vector}_{valor_vector}'
                        sheet_v = pd.DataFrame({
                            'ID': huella.index,
                            'Barrio': nombre_barrios,
                            'Huella / tCO2e': huella,
                            'Reducción / tCO2e': reduccion,
                            'Huella/cápita / tCO2e': huella_capita
                        })
                        sheet_v.to_excel(writer_v, sheet_name=sheetname_v, index=False)

        # Guardar resultados, excel
        if verbose:
            print('Guardando resultados...')
            start_time = time.time()
        sheet_base = pd.DataFrame({
            'ID.': barrios.index,
            'Barrio': nombre_barrios,
            'Población': poblacion
        })
        sheet = sheet_base.copy()
        sheet['Base. Huella / tCO2e'] = energia.huella + vivienda.huella + movilidad.huella + urbanismo.huella + residuos.huella
        sheet['Base. Huella/cápita / tCO2e'] = sheet['Base. Huella / tCO2e'] / poblacion
        sheet.to_excel(writer_a, sheet_name='General', index=False)
        for letra, combinacion in sheets_a.items():
            sheetname = {'E': 'Energía', 'V': 'Vivienda', 'M': 'Movilidad', 'U': 'Urbanismo', 'R': 'Residuos'}[letra]
            sheet = sheet_base.copy()
            # añadir caso base
            area = {'E': energia, 'V': vivienda, 'M': movilidad, 'U': urbanismo, 'R': residuos}[letra]
            huella = area.huella.apply(clean_value)
            huella_capita = huella / poblacion.apply(clean_value)
            sheet['Base. Huella / tCO2e'] = huella
            sheet['Base. Huella/cápita / tCO2e'] = huella_capita
            for (nombre_vector, valor_vector), columnas in combinacion.items():
                sheet = pd.merge(sheet, columnas, on='ID.', how='left')
                # añadir notas específicas para V3 y U2
                if letra == 'V':
                    nota = '*Nota: el vector V3 se ha calculado a partir del caso base de Energía.'
                elif letra == 'U':
                    nota = '*Nota: el vector U2 se ha calculado a partir del caso base de Movilidad.'
                else:
                    nota = ''
                if nota:
                    fila_aclaracion = {col: '' for col in sheet.columns}
                    fila_aclaracion['ID.'] = nota
                    sheet = pd.concat([sheet, pd.DataFrame(fila_aclaracion, index=[0])], ignore_index=True)
            sheet.to_excel(writer_a, sheet_name=sheetname, index=False)
    
    # Guardar resultados, CSV y JSON
    csv_path = os.path.join(RESULTADOS_PATH, 'resultados.csv')
    df.to_csv(csv_path, index=False)
    json_path = os.path.join(RESULTADOS_PATH, 'resultados.json')
    json_file = df.to_json(orient='table')
    with open(json_path, 'w') as f:
        f.write(json_file)
    json_2col_path = os.path.join(RESULTADOS_PATH, 'resultados_2col.json')
    df[['valor_vector', 'valor_mix']] = df['valor_vector'].apply(
        lambda x: pd.Series(ast.literal_eval(x) if isinstance(x, str) and x.startswith('(') and x.endswith(')') else (x, ''))
    )
    json_file = df.to_json(orient='table')
    with open(json_2col_path, 'w') as f:
        f.write(json_file)
    if verbose:
        print(f'Resultados guardados en {time.time() - start_time:.2f} s')


# ----------------------------------------------
# EJECUCIÓN
# ----------------------------------------------
if __name__ == '__main__':
    main(verbose=True)


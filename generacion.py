
"""
explicar módulo
"""

# ----------------------------------------------
# MÓDULOS
# ----------------------------------------------
import os
import pandas as pd
import sys
import time

# añadir el path a la carpeta "scripts_final" para importar los módulos
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'modulos'))
from modulo_energia import AreaEnergia
from modulo_movilidad import AreaMovilidad
from modulo_residuos import AreaResiduos
from modulo_urbanismo import AreaUrbanismo
from modulo_vivienda import AreaVivienda


# ----------------------------------------------
# RUTAS Y NOMBRES DE ARCHIVOS
# ----------------------------------------------
base_path = os.path.abspath(__file__)
desvab_root = os.path.dirname(base_path)
data_path = os.path.join(desvab_root, 'datos')
resultados_path = os.path.join(desvab_root, 'resultados')

barrios_path = os.path.join(data_path, 'demografia', 'barrios.xlsx')


# ----------------------------------------------
# FUNCIONES
# ----------------------------------------------
def main(
        verbose: bool = False
        ):
    """
    explicar función
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
    barrios = pd.read_excel(barrios_path, usecols=['ID', 'Nombre', 'Población'], skipfooter=2)
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
    # Iterar sobre áreas y vectores
    areas = [energia, vivienda, movilidad, urbanismo, residuos]
    for area in areas:
        for nombre_vector, vector in area.vectores.items():
            if nombre_vector not in ['R2']: # no implementados
                # Crear excel
                writer = pd.ExcelWriter(os.path.join(resultados_path, 'por_vector', f'{nombre_vector}.xlsx'), engine='xlsxwriter')
                for valor_vector, huella in vector.items():
                    # Calcular reducción y huella per cápita
                    reduccion = ((area.huella - huella) / area.huella).fillna(0)
                    huella_capita = huella / poblacion
                    # Redondear valores cercanos a 0 a 0
                    huella = huella.apply(lambda x: 0 if abs(x) < 1e-8 else x)
                    reduccion = reduccion.apply(lambda x: 0 if abs(x) < 1e-8 else x)
                    huella_capita = huella_capita.apply(lambda x: 0 if abs(x) < 1e-8 else x)
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
                    # Escribir a excel
                    sheetname = f'{nombre_vector}_{valor_vector}'
                    sheet = pd.DataFrame({
                        'ID': huella.index,
                        'Barrio': nombre_barrios,
                        'Huella / tCO2e': huella,
                        'Reducción / %': reduccion,
                        'Huella/cápita / tCO2e': huella_capita
                    })
                    sheet.to_excel(writer, sheet_name=sheetname, index=False)
                # Guardar excel
                writer.close()
    if verbose:
        print(f'Resultados combinados en {time.time() - start_time:.2f} s')
    
    # Guardar resultados
    if verbose:
        print('Guardando resultados...')
        start_time = time.time()
    csv_path = os.path.join(resultados_path, 'resultados.csv')
    df.to_csv(csv_path, index=False)ç
    json_path = os.path.join(resultados_path, 'resultados.json')
    json_file = df.to_json(orient='table')
    with open(json_path, 'w') as f:
        f.write(json_file)
    if verbose:
        print(f'Resultados guardados en {time.time() - start_time:.2f} s')


# ----------------------------------------------
# EJECUCIÓN
# ----------------------------------------------
if __name__ == '__main__':
    main(verbose=True)

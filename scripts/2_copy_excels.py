import os
import shutil

# Carpeta raíz desde donde se empieza a buscar
carpeta_raiz = r"Y:\CELL_PAINTING_2024_EXPORT\IIG\ESFERAS PAPER\2. CLUSTERING 3D"
# Carpeta destino para los excels reunidos
carpeta_destino = os.path.join(carpeta_raiz, "EXCELS esferas_completo")
os.makedirs(carpeta_destino, exist_ok=True)

# Nombre esperado del archivo Excel
nombre_excel = "spheroid_features.xlsx"

# Parámetros conocidos
horas = ["72H", "96H", "120H"]
replicas = ["R1", "R2", "R3"]
lineas = ["BT549", "MDA468", "HCC1806"]

# Buscar y copiar los archivos
for hora in horas:
    for replica in replicas:
        for linea in lineas:
            encontrado = False

            # Buscar rutas posibles dentro del patrón esperado
            subcarpeta_hora = os.path.join(carpeta_raiz, hora)
            subcarpeta_replica = os.path.join(subcarpeta_hora, replica)

            # Buscar dentro de carpetas que contienen el nombre de la línea celular
            if os.path.isdir(subcarpeta_replica):
                for sub in os.listdir(subcarpeta_replica):
                    if linea in sub:
                        ruta_carpeta_linea = os.path.join(subcarpeta_replica, sub)
                        ruta_excel = os.path.join(ruta_carpeta_linea, nombre_excel)

                        if os.path.exists(ruta_excel):
                            nuevo_nombre = f"{linea}_{replica}_{hora}_{nombre_excel}"
                            destino = os.path.join(carpeta_destino, nuevo_nombre)
                            shutil.copy2(ruta_excel, destino)
                            print(f"✅ Copiado: {ruta_excel} → {destino}")
                            encontrado = True
                            break  # Ya lo encontramos, no seguimos buscando en más subcarpetas

            if not encontrado:
                print(f"❌ No encontrado: {linea} - {replica} - {hora}")
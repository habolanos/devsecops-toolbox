import os
import pandas as pd
import sys
from openpyxl.styles import Font, Alignment
import openpyxl

# --- Directorio de salida centralizado (DEVSECOPS_OUTPUT_DIR) ---
try:
    from utils import get_output_dir
except ImportError:
    import os as _os
    from pathlib import Path as _Path
    def get_output_dir(default="."):
        env = _os.getenv("DEVSECOPS_OUTPUT_DIR")
        if env:
            p = _Path(env)
            p.mkdir(parents=True, exist_ok=True)
            return p
        p = _Path(default)
        p.mkdir(parents=True, exist_ok=True)
        return p
# -------------------------------------------------------------------

if len(sys.argv) > 1:
    csv_file = os.path.expanduser(sys.argv[1])  # Expandir ~ a ruta completa
    file_ne = os.path.splitext(os.path.basename(csv_file))[0]
else:
    print("Error: Se requiere la ruta al archivo CSV como argumento.")
    print("Uso: python tag_filter.py <ruta_archivo.csv>")
    sys.exit(1)

if not os.path.isfile(csv_file):
    print(f"Error: El archivo '{csv_file}' no existe o no es un archivo válido.")
    sys.exit(1)

df = pd.read_csv(csv_file)
df_filtrado = df[~((df['version'] == 'version') & (df['tag'] == 'tag'))]

pattern = r'^\d+(\.\d+)*-[a-zA-Z]+$'
df_filtrado = df[df['tag'].astype(str).str.match(pattern)]
df_filtrado = df[
    df['tag'].astype(str).str.match(pattern) & 
    ~df['tag'].astype(str).str.contains('-master', case=False)
].copy()

df_filtrado.loc[:, 'fecha_creacion'] = pd.to_datetime(df_filtrado['fecha_creacion'], errors='coerce')
df_ordenado = df_filtrado.sort_values(by='fecha_creacion', ascending=False)

with pd.ExcelWriter(f'{file_ne}.xlsx', engine='openpyxl') as writer:
    df_ordenado.to_excel(writer, sheet_name='Imagenes', index=False)

    workbook = writer.book
    worksheet = writer.sheets['Imagenes']

    for col in worksheet.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(cell.value)
            except:
                pass
        adjusted_width = (max_length + 6)
        worksheet.column_dimensions[column].width = adjusted_width

    for cell in worksheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.fill = openpyxl.styles.PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")

    fecha_column = 'D'
    for cell in worksheet[fecha_column]:
        cell.number_format = 'YYYY-MM-DD HH:MM:SS'

print(f"Archivo guardado en {file_ne}.xlsx")

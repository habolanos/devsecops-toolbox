import os
import pandas as pd
import sys
from openpyxl.styles import Font, Alignment
import openpyxl

if len(sys.argv) > 1:
    csv_file = sys.argv[1]
    file_ne = os.path.splitext(os.path.basename(csv_file))[0]

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

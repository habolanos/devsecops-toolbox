# 🔨 Instrucciones de Compilación - DevSecOps Toolbox

Guía completa para compilar ejecutables de DevSecOps Toolbox para Windows y Linux.

---

## 📋 Requisitos Previos

### Para Compilar en Windows

- **Python 3.11+** (descarga desde https://www.python.org/)
- **Git** (descarga desde https://git-scm.com/)
- **Espacio en disco**: Mínimo 2 GB

### Para Compilar en Linux

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install python3.11 python3.11-venv git

# CentOS/RHEL
sudo yum install python311 git

# macOS
brew install python@3.11 git
```

---

## 🚀 Pasos de Compilación

### Paso 1: Clonar Repositorio

```bash
git clone https://github.com/habolanos/devsecops-toolbox.git
cd devsecops-toolbox
```

### Paso 2: Crear Entorno Virtual (Opcional pero Recomendado)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

### Paso 3: Instalar Dependencias

```bash
# Instalar dependencias del proyecto
pip install -r requirements.txt

# Instalar PyInstaller
pip install pyinstaller
```

### Paso 4: Compilar Ejecutables

```bash
# Windows
python build_executables.py

# Linux/macOS
python3 build_executables.py
```

### Paso 5: Verificar Compilación

```bash
# Windows
dir dist\

# Linux/macOS
ls -lh dist/
```

Deberías ver:
- `toolbox.exe` (Windows)
- `toolbox` (Linux/macOS)

---

## 📊 Salida Esperada

```
╔════════════════════════════════════════════════════════════════╗
║         DevSecOps Toolbox - Compilador de Ejecutables         ║
╚════════════════════════════════════════════════════════════════╝

✅ PyInstaller encontrado
📦 Compilando ejecutable para win32...
   Origen: C:\...\devsecops-toolbox\scm\main.py
   Destino: C:\...\devsecops-toolbox\dist

✅ Compilación exitosa
✅ Ejecutable creado: C:\...\devsecops-toolbox\dist\toolbox.exe
   Tamaño: 65.43 MB

✅ Script wrapper creado: C:\...\devsecops-toolbox\toolbox.bat

╔════════════════════════════════════════════════════════════════╗
║                    ✅ COMPILACIÓN COMPLETADA                   ║
╚════════════════════════════════════════════════════════════════╝

📦 Ejecutables generados:
   Windows: dist/toolbox.exe
   Linux:   dist/toolbox

🚀 Uso:
   Windows: toolbox.bat
   Linux:   ./toolbox
```

---

## ✅ Verificar Ejecutable

### Windows

```bash
# Ejecutar directamente
dist\toolbox.exe

# O usar el wrapper
toolbox.bat
```

### Linux

```bash
# Dar permisos de ejecución
chmod +x dist/toolbox

# Ejecutar
./dist/toolbox
```

---

## 📦 Contenido del Ejecutable

Los ejecutables compilados incluyen:

```
toolbox.exe / toolbox
├── Python 3.11 (runtime)
├── Todas las dependencias Python
│   ├── rich (UI)
│   ├── pyyaml (templates)
│   ├── google-cloud-* (GCP)
│   ├── azure-* (Azure)
│   ├── boto3 (AWS)
│   └── más...
├── Código fuente (scm/)
└── Configuración
```

---

## 🔧 Opciones Avanzadas

### Compilar con Icono Personalizado

```bash
# Editar build_executables.py y agregar:
# --icon=path/to/icon.ico
```

### Compilar para Arquitectura Específica

```bash
# x86-64 (predeterminado)
python build_executables.py

# ARM64 (requiere compilación cruzada)
# Más complejo, requiere configuración especial
```

### Compilar en Modo Debug

```bash
# Editar build_executables.py y cambiar:
# --console a --windowed (para ocultar consola)
```

---

## 🐛 Troubleshooting

### Error: "PyInstaller no encontrado"

```bash
pip install pyinstaller
```

### Error: "No se encontró main.py"

Asegúrate de estar en el directorio raíz del proyecto:
```bash
cd devsecops-toolbox
python build_executables.py
```

### Error: "Permiso denegado" en Linux

```bash
chmod +x build_executables.py
python3 build_executables.py
```

### El ejecutable es muy grande (>100 MB)

Es normal. PyInstaller incluye todo lo necesario. Para reducir tamaño:
1. Usar UPX (compresión)
2. Eliminar módulos no usados
3. Usar `--onedir` en lugar de `--onefile`

---

## 📈 Optimizaciones

### Reducir Tamaño del Ejecutable

```bash
# Instalar UPX
# Windows: descarga desde https://upx.github.io/
# Linux: sudo apt-get install upx

# Editar build_executables.py y agregar:
# --upx-dir=/path/to/upx
```

### Mejorar Velocidad de Inicio

```bash
# Usar --onedir en lugar de --onefile
# Más rápido pero genera carpeta
```

---

## 🚀 Distribución

### Preparar para Distribución

```bash
# 1. Compilar
python build_executables.py

# 2. Crear ZIP
# Windows
tar -czf devsecops-toolbox-windows.tar.gz dist/toolbox.exe

# Linux
tar -czf devsecops-toolbox-linux.tar.gz dist/toolbox

# 3. Subir a GitHub Releases
# O distribuir por otro medio
```

### Crear Instalador (Windows)

```bash
# Instalar NSIS
# https://nsis.sourceforge.io/

# Crear script NSIS
# Compilar instalador
```

---

## 📋 Checklist de Compilación

- [ ] Python 3.11+ instalado
- [ ] Repositorio clonado
- [ ] Dependencias instaladas (`pip install -r requirements.txt`)
- [ ] PyInstaller instalado (`pip install pyinstaller`)
- [ ] Script `build_executables.py` presente
- [ ] Ejecutar `python build_executables.py`
- [ ] Verificar que `dist/toolbox.exe` o `dist/toolbox` existe
- [ ] Probar ejecutable: `./dist/toolbox`
- [ ] Verificar que se abre el menú principal
- [ ] Listo para distribución

---

## 📞 Soporte

Si tienes problemas durante la compilación:

1. Verifica que Python 3.11+ está instalado: `python --version`
2. Verifica que PyInstaller está instalado: `pip list | grep PyInstaller`
3. Revisa los logs de compilación
4. Abre un issue en GitHub con los detalles del error

---

**Versión**: 1.0  
**Última actualización**: 15 de Julio de 2026  
**Estado**: ✅ Completo


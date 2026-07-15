# 📦 Ejecutables Compilados - DevSecOps Toolbox

Esta carpeta contiene los ejecutables compilados de DevSecOps Toolbox para Windows y Linux.

---

## 🚀 Uso Rápido

### Windows 🪟

```bash
# Opción 1: Ejecutar directamente
toolbox.exe

# Opción 2: Usar script wrapper
toolbox.bat
```

### Linux 🐧

```bash
# Opción 1: Ejecutar directamente
./toolbox

# Opción 2: Usar script wrapper
./toolbox
```

---

## 📋 Archivos Incluidos

| Archivo | Descripción | Tamaño |
|---------|-------------|--------|
| `toolbox.exe` | Ejecutable para Windows | ~50-80 MB |
| `toolbox` | Ejecutable para Linux | ~50-80 MB |

---

## ✅ Requisitos

**Ninguno.** Los ejecutables incluyen todo lo necesario:
- ✅ Python 3.11+ (incluido)
- ✅ Todas las dependencias (incluidas)
- ✅ Herramientas CLI (gcloud, az, aws, kubectl)

---

## 🎯 Primer Uso

### 1. Descargar Ejecutable

Descarga el ejecutable correspondiente a tu sistema operativo.

### 2. Ejecutar

```bash
# Windows
toolbox.exe

# Linux
./toolbox
```

### 3. Seleccionar Opción

Se abrirá un menú interactivo:

```
╔═══════════════════════════════════════════════════════════════╗
║          🔐 DevSecOps Toolbox - Launcher Principal           ║
╚═══════════════════════════════════════════════════════════════╝

[1] ☁️  GCP (Google Cloud Platform)
[2] ☁️  AZURE (Azure Cloud Platform)
[3] 🔷 AZDO (Azure DevOps)
[4] 🟠 AWS (Amazon Web Services)
[5] 🐧 Terminal (Scripts Universales)
[6] 📊 KPI Analyzer Pro

[A] 🚀 Ejecutar Todas las Herramientas
[Q] 🚪 Salir

Selecciona una opción [1-6, A, Q]:
```

---

## 📚 Documentación

Para más información, consulta:

- `README.md` - Documentación principal
- `scm/templates/README.md` - Guía de templates
- `docs/` - Documentación completa

---

## 🔄 Actualizar Ejecutables

Si necesitas actualizar los ejecutables a una versión más nueva:

```bash
# 1. Clonar/actualizar repositorio
git pull origin master

# 2. Compilar nuevos ejecutables
python build_executables.py

# 3. Los nuevos ejecutables estarán en dist/
```

---

## 🐛 Troubleshooting

### "Archivo no encontrado" en Windows

Si ves este error, asegúrate de:
1. Descargar `toolbox.exe` (no `toolbox`)
2. Estar en el directorio correcto
3. Tener permisos de lectura

### "Permiso denegado" en Linux

```bash
# Dar permisos de ejecución
chmod +x toolbox

# Luego ejecutar
./toolbox
```

### El ejecutable no abre

Verifica que:
1. Tienes espacio en disco (mínimo 100 MB)
2. Tu sistema operativo es compatible (Windows 7+ o Linux)
3. No hay antivirus bloqueando la ejecución

---

## 📊 Especificaciones Técnicas

### Windows

- **Requisitos**: Windows 7 o superior
- **Arquitectura**: x86-64
- **Tamaño**: ~50-80 MB
- **Dependencias**: Ninguna (todo incluido)

### Linux

- **Requisitos**: Linux kernel 2.6.32+
- **Arquitectura**: x86-64
- **Tamaño**: ~50-80 MB
- **Dependencias**: glibc 2.17+

---

## 🔐 Seguridad

✅ Los ejecutables son:
- Compilados desde código fuente verificado
- Firmados digitalmente (en versiones de producción)
- Escaneados por antivirus
- Incluyen todas las dependencias necesarias

---

## 📞 Soporte

Si tienes problemas:

1. Consulta la documentación: `README.md`
2. Revisa los logs: `outcome/`
3. Abre un issue en GitHub

---

**Versión**: 1.7.0  
**Última actualización**: 15 de Julio de 2026  
**Estado**: ✅ Listo para usar


# GCP Certificate Manager Checker

Herramienta SRE para monitorear certificados en Google Cloud Certificate Manager.

## 🔐 Características

- **Monitoreo de certificados** - Lista todos los certificados del proyecto
- **Control de expiración** - Calcula días restantes hasta la expiración
- **Sistema de Semáforo SRE** - Indicadores visuales de estado:
  - 🟢 **HEALTHY** - Más de 60 días para expirar
  - 🔵 **ATTENTION** - Entre 30 y 60 días para expirar
  - 🟡 **WARNING** - Menos de 30 días para expirar
  - 🔴 **CRITICAL** - Menos de 7 días para expirar
  - ⏸️ **INACTIVE** - Certificado no activo
- **Resumen ejecutivo** - Panel con conteo de estados
- **Exportación CSV/JSON** - Genera reportes en carpeta `outcome/`
- **Solo gcloud** - No requiere librerías de Google Cloud Python

## 📋 Requisitos

- Python 3.8+
- `gcloud` CLI instalado y autenticado
- Permisos IAM requeridos:
  - `certificatemanager.certificates.list`
  - `certificatemanager.locations.list`

## 🛠️ Instalación

```bash
pip install rich
```

## 🚀 Uso

```bash
# Proyecto por defecto
python gcp_certificate_checker.py

# Especificar proyecto
python gcp_certificate_checker.py --project YOUR_PROJECT_ID

# Modo debug (muestra comandos ejecutados)
python gcp_certificate_checker.py --debug

# Exportar a CSV
python gcp_certificate_checker.py --output csv

# Exportar a JSON
python gcp_certificate_checker.py -o json
```

## 📝 Argumentos

| Argumento | Descripción | Default |
|-----------|-------------|---------|
| `--project` | ID del proyecto GCP | `cpl-xxxx-yyyy-zzzz-99999999` |
| `--debug` | Activa modo debug para diagnóstico | `False` |
| `--output`, `-o` | Exporta resultados (`csv` o `json`) | `None` |
| `--timezone`, `-tz` | Zona horaria para mostrar fechas | `America/Mazatlan` (Culiacán) |
| `--help`, `-h` | Muestra documentación completa | - |

## 📊 Ejemplo de Salida

```
🔐 Iniciando escaneo de Certificate Manager en: my-project
🕐 Fecha y hora de revisión: 2026-02-16 14:45:30 (America/Mazatlan)

                    🔒 Certificate Manager: my-project
┏━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ Certificado          ┃   Tipo    ┃ Dominios          ┃ Estado  ┃ Expiración ┃ Días Rest.┃ Semáforo SRE ┃
┡━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ cert-api-prod        │  MANAGED  │ api.example.com   │ ACTIVE  │ 2026-06-15 │       138 │  HEALTHY ✅  │
│ cert-web-staging     │  MANAGED  │ web.example.com   │ ACTIVE  │ 2026-02-20 │        23 │  WARNING ⚠️  │
│ cert-old-service     │  MANAGED  │ old.example.com   │ ACTIVE  │ 2026-02-01 │         4 │  CRITICAL 🚨 │
└──────────────────────┴───────────┴───────────────────┴─────────┴────────────┴───────────┴──────────────┘
╭─────────────────────────── 📊 Resumen Ejecutivo ───────────────────────────╮
│ 🚨 CRITICAL: 1  ⚠️ WARNING: 1  👁️ ATTENTION: 0  ✅ HEALTHY: 1  | Total: 3  │
╰────────────────────────────────────────────────────────────────────────────╯

Tip: Los certificados con menos de 30 días para expirar requieren atención.
```

## 🔧 Cómo Funciona

1. Usa `gcloud certificate-manager certificates list` para obtener los certificados
2. Extrae información de dominios, tipo y estado
3. Calcula días restantes hasta la expiración
4. Aplica lógica de semáforo SRE basada en días restantes
5. Muestra resultados en tabla formateada con Rich

## 📁 Formato de Exportación

**CSV** - Columnas: `project`, `certificate`, `type`, `domains`, `state`, `expire_time`, `days_to_expiry`, `status`, `revision_time`

**JSON** - Array de objetos con los mismos campos

---

## 📜 Historial de Cambios

| Fecha | Versión | Descripción |
|-------|---------|-------------|
| 2026-02-20 | 1.2.0 | Reporte JSON mejorado con metadatos (timestamp, timezone, summary) |
| 2026-02-19 | 1.1.1 | Validación de conexión GCP al inicio (check_gcp_connection) |
| 2026-02-16 | 1.1.0 | Timezone configurable con Culiacán (America/Mazatlan) como default, tabla de tiempos de ejecución |
| 2026-01-28 | 1.0.0 | Versión inicial con monitoreo de certificados |

---

## Autor

**Harold Adrian**

---

## Licencia

Internal SRE Tool - Softtek

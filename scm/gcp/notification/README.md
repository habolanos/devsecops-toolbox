# GCP Notification Tools

Herramientas para enviar notificaciones y reportes de monitoreo de servicios GKE a Google Chat mediante webhooks.

## 📋 Contenido

| Archivo | Descripción |
|---------|-------------|
| `webhooks.sh` | Script principal con configuración JSON, descubrimiento dinámico de namespaces y validación de dependencias |
| `webhooks_optimized.sh` | Versión optimizada del script de webhooks |
| `template-webhooks.sh` | Plantilla base para crear nuevos webhooks |
| `config/webhooks_config.json` | **Archivo de configuración** con webhook URL y contextos a monitorear |

## 🚀 webhooks.sh

Script principal de monitoreo con mejores prácticas de desarrollo.

### Características

| Mejora | Descripción |
|--------|-------------|
| **Configuración externa JSON** | Webhook URL y proyectos en archivo JSON separado |
| **Funciones reutilizables** | Eliminación de código duplicado mediante `calculate_stats()`, `preview_and_send()` |
| **Validación de dependencias** | Verifica `kubectl`, `jq`, `curl` antes de ejecutar |
| **Variables de entorno** | Soporte para `CONFIG_FILE`, `WEBHOOK_URL` y `TIMEZONE` |
| **Manejo de errores mejorado** | Validación de JSON y respuesta HTTP del webhook |
| **Código organizado** | Estructura modular con secciones claras (config, funciones, handlers, main) |
| **Ejecución paralela** | Descubrimiento de namespaces y procesamiento de deployments en paralelo |

### Archivo de Configuración JSON

Ubicación por defecto: `config/webhooks_config.json`

```json
{
  "webhook": {
    "url": "https://chat.googleapis.com/v1/spaces/.../messages?key=...&token=...",
    "description": "Descripción del webhook"
  },
  "settings": {
    "timezone": "America/Mazatlan",
    "reporter": "SRE Equipo Softtek - Harold Adrian",
    "excluded_namespace_prefixes": ["gke-", "datadog", "kube-", "default"]
  },
  "contexts": [
    {
      "name": "COMERCIAL",
      "context": "gke_cpl-corp-cial-prod-17042024_us-central1_gke-corp-cial-prod-01",
      "description": "Cluster Comercial Producción"
    }
  ]
}
```

### Descubrimiento Dinámico de Namespaces

El script descubre automáticamente todos los namespaces en cada contexto configurado, excluyendo los que coincidan con los prefijos definidos en `excluded_namespace_prefixes`:

| Prefijo excluido | Descripción |
|------------------|-------------|
| `gke-` | Namespaces del sistema GKE |
| `datadog` | Namespaces de Datadog |
| `kube-` | Namespaces del sistema Kubernetes |
| `default` | Namespace default |

### Variables de Entorno

| Variable | Descripción | Prioridad |
|----------|-------------|----------|
| `CONFIG_FILE` | Ruta al archivo JSON de configuración | - |
| `WEBHOOK_URL` | URL del webhook (sobrescribe JSON) | Alta |
| `TIMEZONE` | Zona horaria (sobrescribe JSON) | Alta |
| `PARALLEL_ENABLED` | Habilitar ejecución paralela (default: `true`) | - |

### Uso

```bash
# Usar configuración por defecto (config/webhooks_config.json)
./webhooks.sh --summary

# Usar archivo de configuración personalizado
CONFIG_FILE="/path/to/mi_config.json" ./webhooks.sh --simple-estable

# Sobrescribir webhook desde variable de entorno
WEBHOOK_URL="https://..." ./webhooks.sh --summary
```

---

##  Requisitos

- **kubectl**: Configurado con acceso a los clusters GKE
- **jq**: Para formateo de JSON
- **curl**: Para envío de webhooks
- **Bash 4+**: Para arrays asociativos y funciones avanzadas

### Instalación de dependencias

```bash
# En sistemas basados en Debian/Ubuntu
sudo apt-get install jq curl

# En macOS con Homebrew
brew install jq curl
```

## 🔐 Seguridad

> ⚠️ **Importante**: Las URLs de webhook contienen tokens de autenticación. No las compartas públicamente ni las incluyas en repositorios públicos.

### Recomendaciones

1. Usar variables de entorno para las URLs de webhook
2. Almacenar credenciales en un gestor de secretos
3. Restringir permisos del archivo (`chmod 700 webhooks.sh`)

## 📊 Ejemplo de Salida

```
📣 Reporte Monitoreo Soporte Temprano COMERCIAL

Servicios monitoreados: 45 de 10 namespaces
• Operando normalmente: 45 ✅
🥷 SRE Equipo Softtek
```

## 🔗 Referencias

- [Google Chat Webhooks](https://developers.google.com/chat/how-tos/webhooks)
- [Kubectl Cheat Sheet](https://kubernetes.io/docs/reference/kubectl/cheatsheet/)

---

## 📜 Historial de Cambios

| Fecha | Versión | Descripción |
|-------|---------|-------------|
| 2026-02-14 | 2.3.0 | Ejecución paralela: descubrimiento de namespaces y procesamiento de deployments con background jobs |
| 2026-02-14 | 2.2.1 | Consolidación: eliminado `webhooks_v2.sh`, toda la funcionalidad en `webhooks.sh` |
| 2026-02-14 | 2.2.0 | Descubrimiento dinámico de namespaces por contexto, filtro de prefijos excluidos |
| 2026-02-14 | 2.1.0 | Configuración externa JSON: webhook URL y contextos en `config/webhooks_config.json` |
| 2026-02-14 | 2.0.0 | Mejoras: funciones reutilizables, validación de dependencias, variables de entorno |
| 2026-01-12 | 1.1.0 | Actualización de documentación: añadida tabla de historial de cambios |
| 2025-01-01 | 1.0.0 | Versión inicial con scripts de webhooks para Google Chat |

---

## Autor

**Harold Adrian**

# 🔐 Opciones de Acceso - Dashboard Matutino DevSecOps

**Fecha:** 22 de Junio de 2026  
**Versión:** 1.0  
**Objetivo:** Documentar todas las opciones de acceso y autenticación

---

## 📋 Resumen de Opciones de Acceso

El Dashboard Matutino DevSecOps requiere acceso a través de dos canales principales:

```
1. Azure DevOps API (Datos)
   └─ Autenticación: Personal Access Token (PAT)

2. Microsoft Teams (Notificaciones)
   └─ Autenticación: Webhook URL
```

---

## 🔑 Opción 1: Azure DevOps API - Personal Access Token (PAT)

### ¿Qué es?
Un token de autenticación que permite acceder a la API de Azure DevOps sin usar contraseña.

### ¿Dónde obtenerlo?

**Paso 1: Ir a Azure DevOps**
```
https://dev.azure.com/Coppel-Retail
```

**Paso 2: Acceder a Configuración de Usuario**
```
1. Click en tu avatar (esquina superior derecha)
2. Seleccionar "Personal access tokens"
3. Click en "New Token"
```

**Paso 3: Crear Token**
```
Nombre: "Dashboard Matutino DevSecOps"
Organización: "Coppel-Retail"
Expiración: 90 días (recomendado)
Alcance: "Code (Read)"
```

**Paso 4: Copiar Token**
```
El token aparecerá UNA SOLA VEZ
Copiar y guardar en lugar seguro
```

### Formato
```
Personal Access Token (PAT):
xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Uso en Dashboard
```bash
export AZDO_PAT="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

python scm/dashboard/dashboard_consolidator.py \
  --org "Coppel-Retail" \
  --project "Cadena_de_Suministros" \
  --pat "$AZDO_PAT"
```

### Permisos Requeridos
```
✅ Code (Read) - Leer PRs y commits
✅ Release (Read) - Leer releases
✅ Build (Read) - Leer pipelines
✅ Project & Team (Read) - Leer proyectos
```

### Seguridad
```
⚠️ NUNCA compartir el PAT
⚠️ NUNCA commitear el PAT al repositorio
⚠️ Usar variables de entorno
⚠️ Rotar cada 90 días
⚠️ Revocar si se expone
```

---

## 📱 Opción 2: Microsoft Teams - Webhook URL

### ¿Qué es?
Una URL especial que permite enviar mensajes automáticamente a un canal de Teams.

### ¿Dónde obtenerlo?

**Paso 1: Abrir Microsoft Teams**
```
Aplicación de Teams o web.teams.microsoft.com
```

**Paso 2: Ir al Grupo "Equipo Comercial/CDS"**
```
1. Seleccionar el equipo
2. Ir al canal donde recibirán notificaciones
```

**Paso 3: Configurar Connector**
```
1. Click en "..." (More options) en la esquina superior derecha
2. Seleccionar "Connectors"
3. Buscar "Incoming Webhook"
4. Click en "Configure"
```

**Paso 4: Crear Webhook**
```
Nombre: "Dashboard Matutino DevSecOps"
Imagen: [Logo DevSecOps]
Click en "Create"
```

**Paso 5: Copiar URL**
```
La URL aparecerá en la pantalla
Copiar URL completa
```

### Formato
```
Webhook URL:
https://outlook.webhook.office.com/webhookb2/xxxxx@xxxxx/IncomingWebhook/xxxxx/xxxxx
```

### Uso en Dashboard
```bash
export TEAMS_WEBHOOK_URL="https://outlook.webhook.office.com/webhookb2/..."

python scm/dashboard/dashboard_scheduler.py \
  --org "Coppel-Retail" \
  --project "Cadena_de_Suministros" \
  --pat "$AZDO_PAT" \
  --webhook "$TEAMS_WEBHOOK_URL" \
  --run-once
```

### Seguridad
```
⚠️ NUNCA compartir la URL
⚠️ NUNCA commitear la URL al repositorio
⚠️ Usar variables de entorno
⚠️ Revocar si se expone
⚠️ Cambiar si se compromete
```

---

## 🔧 Configuración de Variables de Entorno

### Windows PowerShell
```powershell
$env:AZDO_ORG = "Coppel-Retail"
$env:AZDO_PROJECT = "Cadena_de_Suministros"
$env:AZDO_PAT = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
$env:TEAMS_WEBHOOK_URL = "https://outlook.webhook.office.com/webhookb2/..."
```

### Linux/Mac Bash
```bash
export AZDO_ORG="Coppel-Retail"
export AZDO_PROJECT="Cadena_de_Suministros"
export AZDO_PAT="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export TEAMS_WEBHOOK_URL="https://outlook.webhook.office.com/webhookb2/..."
```

### Archivo .env (NO commitear)
```
AZDO_ORG=Coppel-Retail
AZDO_PROJECT=Cadena_de_Suministros
AZDO_PAT=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TEAMS_WEBHOOK_URL=https://outlook.webhook.office.com/webhookb2/...
```

---

## 📊 Matriz de Acceso

| Componente | Tipo de Acceso | Credencial | Requerido |
|-----------|:---------------:|:----------:|:---------:|
| **Azure DevOps API** | Token | PAT | ✅ Sí |
| **Microsoft Teams** | Webhook | URL | ✅ Sí |
| **Archivo HTML** | Local | N/A | ✅ Sí |
| **Histórico** | Local | N/A | ✅ Sí |

---

## 🚀 Flujo de Autenticación

### Consolidator (Tool 26)
```
1. Recibe PAT como parámetro
2. Crea cliente Azure DevOps
3. Autentica con PAT
4. Accede a APIs
5. Consolida datos
```

### Generator (Tool 27)
```
1. Lee dashboard_data.json
2. No requiere autenticación
3. Genera HTML
4. Guarda archivo
```

### Scheduler (Tool 29)
```
1. Recibe PAT para ejecutar Consolidator
2. Recibe Webhook URL para Teams
3. Ejecuta Consolidator (con PAT)
4. Ejecuta Generator
5. Envía notificación a Teams (con Webhook)
```

---

## ✅ Checklist de Acceso

### Antes de Ejecutar

- [ ] Crear PAT en Azure DevOps
  - [ ] Ir a dev.azure.com/Coppel-Retail
  - [ ] Personal access tokens
  - [ ] New Token
  - [ ] Copiar token

- [ ] Crear Webhook en Teams
  - [ ] Abrir Teams
  - [ ] Ir a "Equipo Comercial/CDS"
  - [ ] Connectors → Incoming Webhook
  - [ ] Configure
  - [ ] Copiar URL

- [ ] Configurar Variables de Entorno
  - [ ] AZDO_ORG
  - [ ] AZDO_PROJECT
  - [ ] AZDO_PAT
  - [ ] TEAMS_WEBHOOK_URL

- [ ] Validar Acceso
  - [ ] Probar PAT con curl
  - [ ] Probar Webhook con curl
  - [ ] Ejecutar test_dashboard.py

---

## 🧪 Validar Acceso

### Validar PAT
```bash
# Probar acceso a Azure DevOps API
curl -u :$AZDO_PAT \
  "https://dev.azure.com/Coppel-Retail/Cadena_de_Suministros/_apis/git/repositories?api-version=7.0"

# Respuesta esperada:
# {"value": [...], "count": N}
```

### Validar Webhook
```bash
# Probar envío a Teams
curl -X POST "$TEAMS_WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "@type": "MessageCard",
    "@context": "https://schema.org/extensions",
    "summary": "Test",
    "themeColor": "0078D4",
    "sections": [{
      "activityTitle": "Test Webhook",
      "text": "Si ves este mensaje, el webhook funciona ✅"
    }]
  }'

# Respuesta esperada:
# 1
```

---

## 🔄 Rotación de Credenciales

### Cada 90 días: Rotar PAT
```
1. Crear nuevo PAT en Azure DevOps
2. Actualizar variable de entorno
3. Probar con nuevo PAT
4. Revocar PAT antiguo
```

### Si se Expone: Revocar Inmediatamente
```
1. Ir a dev.azure.com/Coppel-Retail
2. Personal access tokens
3. Revocar token expuesto
4. Crear nuevo token
5. Actualizar variable de entorno
```

---

## 📞 Solución de Problemas

### Error: "401 Unauthorized"
```
❌ PAT inválido o expirado
✅ Solución:
   1. Verificar PAT en Azure DevOps
   2. Crear nuevo PAT si está expirado
   3. Actualizar variable de entorno
```

### Error: "403 Forbidden"
```
❌ PAT sin permisos suficientes
✅ Solución:
   1. Verificar alcance del PAT
   2. Crear nuevo PAT con alcance "Code (Read)"
   3. Actualizar variable de entorno
```

### Error: "Webhook URL invalid"
```
❌ Webhook URL incorrecta o revocada
✅ Solución:
   1. Crear nuevo Webhook en Teams
   2. Copiar URL completa
   3. Actualizar variable de entorno
```

### Error: "Connection timeout"
```
❌ Problemas de conectividad
✅ Solución:
   1. Verificar conexión a internet
   2. Verificar firewall
   3. Probar con curl
   4. Contactar a IT
```

---

## 🎯 Resumen Rápido

### Opción 1: Azure DevOps API (PAT)
```
Obtener: dev.azure.com → Personal access tokens → New Token
Formato: Token de 52 caracteres
Uso: --pat "$AZDO_PAT"
Seguridad: Rotar cada 90 días
```

### Opción 2: Microsoft Teams (Webhook)
```
Obtener: Teams → Equipo → Connectors → Incoming Webhook
Formato: https://outlook.webhook.office.com/webhookb2/...
Uso: --webhook "$TEAMS_WEBHOOK_URL"
Seguridad: Revocar si se expone
```

---

## 📚 Referencias

- [Azure DevOps Personal Access Tokens](https://docs.microsoft.com/en-us/azure/devops/organizations/accounts/use-personal-access-tokens-to-authenticate)
- [Microsoft Teams Webhooks](https://docs.microsoft.com/en-us/microsoftteams/platform/webhooks-and-connectors/how-to/connectors-using)
- [Azure DevOps API v7.0](https://docs.microsoft.com/en-us/rest/api/azure/devops)

---

**Preparado por:** Harold Adrian  
**Fecha:** 22 de Junio de 2026  
**Versión:** 1.0  
**Estado:** ✅ DOCUMENTADO

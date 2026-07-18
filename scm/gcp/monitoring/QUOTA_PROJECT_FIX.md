# 🔧 Solución: Warning de Quota Project

**Problema**: Warning de Google Cloud SDK sobre "quota project"  
**Severidad**: ⚠️ Warning (no es error)  
**Solución**: 3 opciones

---

## 📋 El Warning

```
UserWarning: Your application has authenticated using end user credentials 
from Google Cloud SDK without a quota project. You might receive a 
"quota exceeded" or "API not enabled" error.
```

---

## ✅ Solución 1: Configurar Quota Project (Recomendado)

### **Paso 1: Identificar tu proyecto GCP**

```bash
gcloud config list --format='value(core.project)'
```

### **Paso 2: Configurar como quota project**

```bash
gcloud config set project PROJECT_ID
gcloud auth application-default set-quota-project PROJECT_ID
```

### **Paso 3: Verificar**

```bash
gcloud auth application-default print-access-token
```

---

## ✅ Solución 2: Usar Variable de Entorno

### **Windows (PowerShell)**

```powershell
$env:GOOGLE_CLOUD_QUOTA_PROJECT = "PROJECT_ID"
python gcp_monitor.py --project=PROJECT_ID
```

### **Windows (CMD)**

```cmd
set GOOGLE_CLOUD_QUOTA_PROJECT=PROJECT_ID
python gcp_monitor.py --project=PROJECT_ID
```

### **Linux/Mac**

```bash
export GOOGLE_CLOUD_QUOTA_PROJECT=PROJECT_ID
python gcp_monitor.py --project=PROJECT_ID
```

---

## ✅ Solución 3: Suprimir Warning en Código

Si no quieres ver el warning, agrega esto al inicio de `gcp_monitor.py`:

```python
import warnings
warnings.filterwarnings('ignore', message='.*quota project.*')
```

---

## 🔍 Verificar que Funciona

Ejecuta y verifica que:

1. ✅ El warning desaparece
2. ✅ Las métricas se obtienen correctamente
3. ✅ No hay errores de "quota exceeded"

```bash
python gcp_monitor.py --project=PROJECT_ID
```

---

## 📊 Comparación de Soluciones

| Solución | Ventaja | Desventaja |
|----------|---------|-----------|
| **1. Quota Project** | Permanente, recomendado | Requiere configuración inicial |
| **2. Variable Entorno** | Temporal, flexible | Requiere configurar cada vez |
| **3. Suprimir Warning** | Rápido | Solo oculta, no resuelve |

---

## 🎯 Recomendación

**Usa Solución 1** (Quota Project) porque:
- ✅ Es permanente
- ✅ Resuelve el problema de raíz
- ✅ Evita futuros errores de quota
- ✅ Recomendado por Google Cloud

---

## ⚠️ Nota Importante

El warning **NO impide que funcione** el código. Es solo una advertencia de Google Cloud SDK.

Si ves este error (diferente del warning):
```
API not enabled
quota exceeded
```

Entonces sí hay un problema real que necesita solución.

---

**Implementación**: Aplica Solución 1 o 2 según tu preferencia  
**Status**: ✅ Resuelto

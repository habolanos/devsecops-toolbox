# ✅ SOLUCIÓN - Error de ListTopicsRequest y ListSubscriptionsRequest

**Fecha**: 16 de Julio de 2026  
**Problema**: `module 'google.cloud.pubsub_v1' has no attribute 'ListTopicsRequest'`  
**Estado**: ✅ RESUELTO

---

## 🔴 Problema Original

```
Error listando topics: module 'google.cloud.pubsub_v1' has no attribute 'ListTopicsRequest'
Error listando subscriptions: module 'google.cloud.pubsub_v1' has no attribute 'ListSubscriptionsRequest'
```

**Causa**: Las clases `ListTopicsRequest` y `ListSubscriptionsRequest` no están en el módulo raíz `pubsub_v1`, sino en el submódulo `pubsub_v1.types`.

---

## ✅ Solución Implementada

Se corrigieron los imports en `scm/gcp/pubsub_monitor/pubsub_collector.py`:

### Cambio 1: Agregar imports correctos

**Antes**:
```python
from google.cloud import pubsub_v1
```

**Después**:
```python
from google.cloud import pubsub_v1
from google.cloud.pubsub_v1.types import ListTopicsRequest, ListSubscriptionsRequest
```

---

### Cambio 2: Usar las clases importadas en `_collect_topics()`

**Antes**:
```python
request = pubsub_v1.ListTopicsRequest(project=project_path)
```

**Después**:
```python
request = ListTopicsRequest(project=project_path)
```

---

### Cambio 3: Usar las clases importadas en `_collect_subscriptions()`

**Antes**:
```python
request = pubsub_v1.ListSubscriptionsRequest(project=project_path)
```

**Después**:
```python
request = ListSubscriptionsRequest(project=project_path)
```

---

## 🔧 Explicación Técnica

### ¿Por qué ocurrió el error?

En `google-cloud-pubsub`, las clases de request están organizadas en submódulos:
- `google.cloud.pubsub_v1` - Cliente principal
- `google.cloud.pubsub_v1.types` - Tipos de datos (requests, responses, etc.)

El código intentaba acceder a `ListTopicsRequest` desde `pubsub_v1` directamente, pero está en `pubsub_v1.types`.

### ¿Cómo lo resolvimos?

Importamos las clases directamente desde el submódulo correcto:

```python
from google.cloud.pubsub_v1.types import ListTopicsRequest, ListSubscriptionsRequest
```

Esto permite usar las clases sin el prefijo `pubsub_v1.`:

```python
request = ListTopicsRequest(project=project_path)
```

---

## 📊 Cambios Realizados

| Archivo | Línea | Cambio |
|---------|-------|--------|
| `pubsub_collector.py` | 21 | Agregar import de ListTopicsRequest y ListSubscriptionsRequest |
| `pubsub_collector.py` | 150 | Cambiar `pubsub_v1.ListTopicsRequest` a `ListTopicsRequest` |
| `pubsub_collector.py` | 184 | Cambiar `pubsub_v1.ListSubscriptionsRequest` a `ListSubscriptionsRequest` |

---

## ✅ Verificación

### Antes (Error)
```
Error listando topics en cpl-cmanager-dev-13072023: 
module 'google.cloud.pubsub_v1' has no attribute 'ListTopicsRequest'
```

### Después (Funcionando)
```
✅ Topics recopilados correctamente
✅ Subscriptions recopiladas correctamente
```

---

## 🔗 Commit

- `e768e82` - fix: Importar ListTopicsRequest y ListSubscriptionsRequest desde google.cloud.pubsub_v1.types

---

## 📝 Notas Importantes

### Estructura de google-cloud-pubsub

```
google.cloud.pubsub_v1
├── PublisherClient
├── SubscriberClient
└── types
    ├── ListTopicsRequest
    ├── ListSubscriptionsRequest
    ├── Topic
    ├── Subscription
    └── ...
```

### Alternativas

Si se prefiere no importar las clases directamente, se puede usar:

```python
from google.cloud.pubsub_v1 import types

request = types.ListTopicsRequest(project=project_path)
```

Pero la solución actual (importar directamente) es más limpia.

---

## ✨ Estado Final

✅ **PROBLEMA RESUELTO**

- ✅ Topics se recopilan correctamente
- ✅ Subscriptions se recopilan correctamente
- ✅ Imports están en el lugar correcto
- ✅ Código es más limpio y legible

---

**Versión**: 1.0.0  
**Última actualización**: 16 de Julio de 2026  
**Estado**: ✅ RESUELTO


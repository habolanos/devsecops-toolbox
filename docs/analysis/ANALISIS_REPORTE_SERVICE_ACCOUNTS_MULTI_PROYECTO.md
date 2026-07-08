# 📊 Análisis Profesional: Reporte de Service Accounts Multi-Proyecto GCP

**Fecha:** 8 de Julio de 2026  
**Versión:** 1.0.0  
**Nivel:** Profesional (SRE/DevSecOps)  
**Estado:** ✅ ANÁLISIS COMPLETO

---

## 📋 Tabla de Contenidos

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Análisis Técnico](#análisis-técnico)
3. [Arquitectura Propuesta](#arquitectura-propuesta)
4. [Implementación Detallada](#implementación-detallada)
5. [Casos de Uso](#casos-de-uso)
6. [Consideraciones de Seguridad](#consideraciones-de-seguridad)
7. [Roadmap de Implementación](#roadmap-de-implementación)

---

## 🎯 Resumen Ejecutivo

### Objetivo
Crear una herramienta profesional para extraer, consolidar y reportar service accounts de múltiples proyectos GCP con análisis de seguridad, uso y cumplimiento.

### Alcance
- ✅ Extracción de service accounts desde múltiples proyectos
- ✅ Análisis de permisos IAM (roles, bindings)
- ✅ Análisis de claves (edad, rotación, seguridad)
- ✅ Análisis de uso (últimas actividades, logs)
- ✅ Análisis de seguridad (públicos, permisos excesivos)
- ✅ Reportes consolidados (JSON, CSV, Excel)
- ✅ Comparativa entre proyectos
- ✅ Alertas de riesgos

### Impacto
- **Visibilidad:** 100% de service accounts en múltiples proyectos
- **Seguridad:** Identificación de riesgos IAM
- **Cumplimiento:** Validación de políticas de rotación
- **Eficiencia:** Automatización de auditoría

---

## 🔍 Análisis Técnico

### 1. Análisis de Roles y Permisos Temporales

#### A. Estructura de Datos Extendida para Roles

```python
# Service Account con análisis detallado de roles
ServiceAccountWithRoles = {
    "project_id": "mi-proyecto",
    "email": "sa-name@mi-proyecto.iam.gserviceaccount.com",
    
    "iam_bindings": [
        {
            "role": "roles/compute.admin",
            "role_title": "Compute Admin",
            "role_description": "Acceso completo a Compute Engine",
            "permission_count": 127,
            "granted_at": "2024-01-15T10:30:00Z",
            "granted_by": "user@example.com",
            "requested_duration_days": 90,
            "expiration_date": "2024-04-15T10:30:00Z",
            "days_remaining": 45,
            "is_temporary": True,
            "is_expired": False,
            "condition": {
                "expression": "resource.name.startsWith('projects/_/buckets/my-bucket')",
                "title": "Acceso limitado a bucket específico",
                "description": "Solo acceso a mi-bucket"
            },
            "risk_level": "HIGH",
            "risk_factors": [
                "Permiso administrativo",
                "Acceso a múltiples servicios",
                "Sin restricción de recursos"
            ]
        },
        {
            "role": "roles/storage.objectViewer",
            "role_title": "Storage Object Viewer",
            "role_description": "Lectura de objetos en Cloud Storage",
            "permission_count": 2,
            "granted_at": "2024-06-01T14:20:00Z",
            "granted_by": "admin@example.com",
            "requested_duration_days": 365,
            "expiration_date": "2025-06-01T14:20:00Z",
            "days_remaining": 358,
            "is_temporary": True,
            "is_expired": False,
            "condition": {
                "expression": "resource.matchTag('env', 'prod')",
                "title": "Solo ambiente producción",
                "description": "Acceso limitado a recursos con tag env=prod"
            },
            "risk_level": "LOW",
            "risk_factors": []
        },
        {
            "role": "roles/viewer",
            "role_title": "Viewer",
            "role_description": "Acceso de lectura a todos los recursos",
            "permission_count": 5000,
            "granted_at": "2023-01-01T00:00:00Z",
            "granted_by": "owner@example.com",
            "requested_duration_days": None,  # Permanente
            "expiration_date": None,
            "days_remaining": None,
            "is_temporary": False,
            "is_expired": False,
            "condition": None,
            "risk_level": "MEDIUM",
            "risk_factors": [
                "Permiso permanente sin fecha de expiración",
                "Acceso de lectura a todos los recursos"
            ]
        }
    ],
    
    "role_summary": {
        "total_roles": 3,
        "temporary_roles": 2,
        "permanent_roles": 1,
        "expired_roles": 0,
        "expiring_soon": [
            {
                "role": "roles/compute.admin",
                "days_remaining": 45,
                "expiration_date": "2024-04-15T10:30:00Z"
            }
        ],
        "highest_risk_role": "roles/compute.admin",
        "total_permissions": 5127,
        "average_days_remaining": 201
    }
}
```

---

### 2. Fuentes de Datos

#### A. Service Accounts
```bash
gcloud iam service-accounts list --project=PROJECT_ID --format=json
```
**Datos extraídos:**
- Email
- Display Name
- Disabled status
- Creation time
- Description

#### B. IAM Bindings
```bash
gcloud projects get-iam-policy PROJECT_ID --format=json
```
**Datos extraídos:**
- Roles asignados
- Members (service accounts)
- Conditions (si existen)

#### C. Service Account Keys
```bash
gcloud iam service-accounts keys list --iam-account=SA_EMAIL --format=json
```
**Datos extraídos:**
- Key ID
- Key type (USER_MANAGED, SYSTEM_MANAGED)
- Valid after
- Valid before
- Key algorithm

#### D. Activity Logs
```bash
gcloud logging read "protoPayload.authenticationInfo.principalEmail=SA_EMAIL" \
  --project=PROJECT_ID --format=json --limit=1000
```
**Datos extraídos:**
- Última actividad
- Servicios utilizados
- Frecuencia de uso
- Errores/fallos

#### E. Metadata (Opcional)
```bash
gcloud compute instances list --project=PROJECT_ID --format=json
gcloud container clusters list --project=PROJECT_ID --format=json
```
**Datos extraídos:**
- Service accounts en uso en VMs
- Service accounts en GKE

---

### 2. Desafíos Técnicos

| Desafío | Solución |
|---------|----------|
| **Múltiples proyectos** | Iteración con lista de proyectos, paralelización con ThreadPoolExecutor |
| **Permisos limitados** | Validación de permisos, fallback graceful, reportes parciales |
| **Volumen de datos** | Paginación, caché, filtros, compresión |
| **Latencia** | Paralelización, timeout, reintentos con backoff |
| **Análisis de logs** | Límite de 1000 registros, agregación, muestreo |
| **Formato de salida** | Múltiples formatos (JSON, CSV, Excel, HTML) |

---

### 3. Permisos Requeridos

```yaml
Permisos Mínimos:
  - iam.serviceAccounts.list
  - iam.serviceAccounts.get
  - iam.serviceAccounts.getIamPolicy
  - iam.serviceAccountKeys.list
  - resourcemanager.projects.getIamPolicy
  - logging.logEntries.list (para análisis de actividad)

Roles Recomendados:
  - roles/iam.securityReviewer (lectura de IAM)
  - roles/logging.viewer (lectura de logs)
  - roles/resourcemanager.organizationViewer (múltiples proyectos)
```

---

## 🏗️ Arquitectura Propuesta

### Componentes Principales

```
┌─────────────────────────────────────────────────────────────┐
│                    GCP Multi-Project SA Reporter              │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  CLI Interface (gcp_sa_multi_project_reporter.py)    │   │
│  │  - Argumentos: --projects, --org, --format, --output │   │
│  │  - Modo: all, security, compliance, usage            │   │
│  └──────────────────────────────────────────────────────┘   │
│                           ↓                                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Orchestrator (sa_multi_project_orchestrator.py)     │   │
│  │  - Validación de proyectos                           │   │
│  │  - Paralelización de extracción                      │   │
│  │  - Consolidación de datos                           │   │
│  │  - Análisis cruzado                                 │   │
│  └──────────────────────────────────────────────────────┘   │
│                           ↓                                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Extractors (sa_extractors.py)                       │   │
│  │  ├─ ServiceAccountExtractor                          │   │
│  │  ├─ IAMBindingsExtractor                             │   │
│  │  ├─ KeysExtractor                                    │   │
│  │  ├─ ActivityExtractor                                │   │
│  │  └─ MetadataExtractor                                │   │
│  └──────────────────────────────────────────────────────┘   │
│                           ↓                                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Analyzers (sa_analyzers.py)                         │   │
│  │  ├─ SecurityAnalyzer                                 │   │
│  │  ├─ ComplianceAnalyzer                               │   │
│  │  ├─ UsageAnalyzer                                    │   │
│  │  ├─ RiskAnalyzer                                     │   │
│  │  └─ TrendAnalyzer                                    │   │
│  └──────────────────────────────────────────────────────┘   │
│                           ↓                                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Report Generators (sa_report_generators.py)         │   │
│  │  ├─ JSONReportGenerator                              │   │
│  │  ├─ CSVReportGenerator                               │   │
│  │  ├─ ExcelReportGenerator                             │   │
│  │  ├─ HTMLReportGenerator                              │   │
│  │  └─ SummaryReportGenerator                           │   │
│  └──────────────────────────────────────────────────────┘   │
│                           ↓                                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Output (outcome/)                                   │   │
│  │  ├─ sa_report_YYYYMMDD_HHMMSS.json                   │   │
│  │  ├─ sa_report_YYYYMMDD_HHMMSS.csv                    │   │
│  │  ├─ sa_report_YYYYMMDD_HHMMSS.xlsx                   │   │
│  │  ├─ sa_report_YYYYMMDD_HHMMSS.html                   │   │
│  │  └─ sa_summary_YYYYMMDD_HHMMSS.txt                   │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 💻 Implementación Detallada

### 1. Estructura de Datos

```python
# Service Account Completo
ServiceAccount = {
    "project_id": "mi-proyecto",
    "email": "sa-name@mi-proyecto.iam.gserviceaccount.com",
    "display_name": "Mi Service Account",
    "disabled": False,
    "created_at": "2024-01-15T10:30:00Z",
    "description": "Service account para aplicación X",
    
    # IAM Bindings
    "iam_bindings": [
        {
            "role": "roles/compute.admin",
            "condition": None,
            "granted_by": "user@example.com"
        }
    ],
    
    # Keys
    "keys": [
        {
            "key_id": "abc123def456",
            "key_type": "USER_MANAGED",
            "created_at": "2024-01-15T10:30:00Z",
            "valid_after": "2024-01-15T10:30:00Z",
            "valid_before": "2025-01-15T10:30:00Z",
            "algorithm": "KEY_ALG_RSA_2048",
            "age_days": 180,
            "days_until_expiry": 185
        }
    ],
    
    # Activity
    "activity": {
        "last_activity": "2026-07-08T09:15:00Z",
        "days_since_last_activity": 0,
        "total_activities_30d": 1250,
        "services_used": ["compute.googleapis.com", "storage.googleapis.com"],
        "error_rate": 0.02
    },
    
    # Security Analysis
    "security": {
        "has_user_managed_keys": True,
        "key_rotation_compliant": False,
        "excessive_permissions": True,
        "risk_level": "HIGH",
        "risk_factors": [
            "User-managed keys older than 90 days",
            "Has compute.admin role",
            "No activity in last 30 days"
        ]
    },
    
    # Compliance
    "compliance": {
        "key_rotation_policy": "90 days",
        "compliant": False,
        "violations": [
            "Key age exceeds 90 days"
        ]
    }
}
```

### 2. Configuración en config.json

**Ubicación:** `scm/config.json`

```json
{
  "gcp": {
    "_info": "Configuración de Google Cloud Platform",
    "enabled": true,
    "project_id": "<TU_PROJECT_ID>",
    "region": "us-central1",
    
    "service_accounts_reporter": {
      "_info": "Configuración para el reporte multi-proyecto de service accounts",
      "enabled": true,
      "projects": [
        "proyecto-produccion-001",
        "proyecto-staging-002",
        "proyecto-desarrollo-003",
        "proyecto-qa-004",
        "proyecto-backup-005"
      ],
      "defaults": {
        "mode": "all",
        "output_format": "json",
        "include_activity": true,
        "activity_days": 30,
        "key_rotation_policy_days": 90,
        "parallel_workers": 5,
        "timeout_seconds": 300,
        "cache_enabled": true,
        "cache_ttl_minutes": 60
      },
      "security": {
        "dangerous_roles": [
          "roles/editor",
          "roles/owner",
          "roles/compute.admin",
          "roles/iam.securityAdmin",
          "roles/resourcemanager.organizationAdmin"
        ],
        "alert_on_risk_level": ["HIGH", "CRITICAL"],
        "encrypt_reports": true
      },
      "compliance": {
        "policies": [
          {
            "name": "key_rotation_90days",
            "description": "Rotación de claves cada 90 días",
            "enabled": true,
            "threshold_days": 90
          },
          {
            "name": "no_user_managed_keys",
            "description": "No permitir claves user-managed",
            "enabled": false
          },
          {
            "name": "no_excessive_permissions",
            "description": "No permitir roles peligrosos",
            "enabled": true
          }
        ]
      },
      "notifications": {
        "enabled": true,
        "on_high_risk": true,
        "on_compliance_violation": true,
        "webhook_url": "<TU_TEAMS_WEBHOOK_URL>"
      }
    },
    
    "credentials": {
      "_info": "Opciones: 'adc' (Application Default Credentials), 'service_account', 'oauth'",
      "type": "adc",
      "service_account_key_path": "",
      "impersonate_service_account": ""
    },
    
    "defaults": {
      "timezone": "America/Mazatlan",
      "output_format": "json"
    }
  }
}
```

**Campos Principales:**

| Campo | Descripción | Ejemplo |
|-------|-------------|---------|
| `projects` | Array de nombres de proyectos GCP | `["proyecto-prod", "proyecto-staging"]` |
| `mode` | Modo de reporte (all, security, compliance, usage) | `all` |
| `output_format` | Formato de salida (json, csv, excel, html) | `json` |
| `include_activity` | Incluir análisis de actividad | `true` |
| `activity_days` | Días de actividad a analizar | `30` |
| `key_rotation_policy_days` | Días para rotación de claves | `90` |
| `parallel_workers` | Número de workers para paralelización | `5` |
| `dangerous_roles` | Roles considerados peligrosos | Array de roles |
| `alert_on_risk_level` | Niveles de riesgo para alertas | `["HIGH", "CRITICAL"]` |

---

### 3. Módulos Principales

#### A. Config Loader (Cargar desde config.json)

```python
import json
from pathlib import Path
from typing import Dict, List

class ConfigLoader:
    """Carga configuración desde config.json."""
    
    def __init__(self, config_path: str = "config.json"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        """Carga el archivo config.json."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"config.json no encontrado en {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            return json.load(f)
    
    def get_projects(self) -> List[str]:
        """Obtiene lista de proyectos desde config.json."""
        return self.config.get('gcp', {}).get('service_accounts_reporter', {}).get('projects', [])
    
    def get_sa_reporter_config(self) -> Dict:
        """Obtiene configuración del reporte de service accounts."""
        return self.config.get('gcp', {}).get('service_accounts_reporter', {})
    
    def get_defaults(self) -> Dict:
        """Obtiene valores por defecto."""
        reporter_config = self.get_sa_reporter_config()
        return reporter_config.get('defaults', {})
    
    def get_security_config(self) -> Dict:
        """Obtiene configuración de seguridad."""
        reporter_config = self.get_sa_reporter_config()
        return reporter_config.get('security', {})
    
    def get_compliance_policies(self) -> List[Dict]:
        """Obtiene políticas de cumplimiento."""
        reporter_config = self.get_sa_reporter_config()
        return reporter_config.get('compliance', {}).get('policies', [])
```

**Uso en CLI:**

```python
def main():
    # Cargar configuración
    config_loader = ConfigLoader('config.json')
    
    # Obtener proyectos por defecto
    projects = config_loader.get_projects()
    defaults = config_loader.get_defaults()
    
    # Permitir override desde línea de comandos
    parser = argparse.ArgumentParser()
    parser.add_argument('--projects', 
                       default=','.join(projects),
                       help='Proyectos a analizar (default: desde config.json)')
    parser.add_argument('--mode', 
                       default=defaults.get('mode', 'all'),
                       help='Modo de reporte (default: desde config.json)')
    parser.add_argument('--output', 
                       default=defaults.get('output_format', 'json'),
                       help='Formato de salida (default: desde config.json)')
    
    args = parser.parse_args()
    
    # Usar configuración
    projects_to_analyze = args.projects.split(',')
    # ... resto del código
```

---

#### B. Extractor Base

```python
class ServiceAccountExtractor:
    """Extrae service accounts de un proyecto."""
    
    def __init__(self, project_id: str, debug: bool = False):
        self.project_id = project_id
        self.debug = debug
    
    def extract_all(self) -> Dict:
        """Extrae todos los datos de service accounts."""
        return {
            'service_accounts': self.get_service_accounts(),
            'iam_bindings': self.get_iam_bindings(),
            'keys': self.get_keys(),
            'activity': self.get_activity(),
            'metadata': self.get_metadata()
        }
    
    def get_service_accounts(self) -> List[Dict]:
        """Obtiene lista de service accounts."""
        cmd = f'gcloud iam service-accounts list --project={self.project_id} --format=json'
        return run_gcloud_command(cmd, self.debug) or []
    
    def get_iam_bindings(self) -> Dict:
        """Obtiene bindings IAM del proyecto."""
        cmd = f'gcloud projects get-iam-policy {self.project_id} --format=json'
        return run_gcloud_command(cmd, self.debug) or {}
    
    def get_keys(self, sa_email: str) -> List[Dict]:
        """Obtiene claves de un service account."""
        cmd = f'gcloud iam service-accounts keys list --iam-account={sa_email} --format=json'
        return run_gcloud_command(cmd, self.debug) or []
    
    def get_activity(self, sa_email: str, days: int = 30) -> Dict:
        """Obtiene actividad reciente del service account."""
        cmd = f'''gcloud logging read "protoPayload.authenticationInfo.principalEmail={sa_email}" \
                  --project={self.project_id} --format=json --limit=1000'''
        logs = run_gcloud_command(cmd, self.debug) or []
        return self._analyze_activity(logs, days)
```

#### B. Roles and Permissions Analyzer

```python
from datetime import datetime, timedelta
from typing import Dict, List

class RolesAndPermissionsAnalyzer:
    """Analiza roles, permisos temporales y días restantes."""
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.role_metadata = self._load_role_metadata()
    
    def analyze_roles(self, sa: Dict, iam_bindings: List[Dict]) -> Dict:
        """Analiza roles de un service account."""
        analyzed_bindings = []
        
        for binding in iam_bindings:
            if self._is_sa_in_binding(sa['email'], binding):
                analyzed_binding = self._analyze_single_binding(binding)
                analyzed_bindings.append(analyzed_binding)
        
        return {
            'iam_bindings': analyzed_bindings,
            'role_summary': self._generate_role_summary(analyzed_bindings)
        }
    
    def _analyze_single_binding(self, binding: Dict) -> Dict:
        """Analiza un binding individual."""
        role = binding.get('role', '')
        condition = binding.get('condition', {})
        
        # Extraer información de la condición (si existe)
        granted_at = self._extract_grant_date(condition)
        requested_duration = self._extract_duration(condition)
        expiration_date = self._calculate_expiration(granted_at, requested_duration)
        days_remaining = self._calculate_days_remaining(expiration_date)
        
        return {
            'role': role,
            'role_title': self._get_role_title(role),
            'role_description': self._get_role_description(role),
            'permission_count': self._get_permission_count(role),
            'granted_at': granted_at,
            'granted_by': self._extract_granted_by(binding),
            'requested_duration_days': requested_duration,
            'expiration_date': expiration_date,
            'days_remaining': days_remaining,
            'is_temporary': requested_duration is not None,
            'is_expired': days_remaining is not None and days_remaining < 0,
            'condition': condition if condition else None,
            'risk_level': self._calculate_role_risk(role, days_remaining),
            'risk_factors': self._identify_role_risks(role, days_remaining)
        }
    
    def _calculate_days_remaining(self, expiration_date: str) -> int:
        """Calcula días restantes hasta expiración."""
        if not expiration_date:
            return None
        
        try:
            exp_date = datetime.fromisoformat(expiration_date.replace('Z', '+00:00'))
            today = datetime.now(exp_date.tzinfo)
            delta = (exp_date - today).days
            return delta
        except:
            return None
    
    def _calculate_expiration(self, granted_at: str, duration_days: int) -> str:
        """Calcula fecha de expiración."""
        if not granted_at or not duration_days:
            return None
        
        try:
            grant_date = datetime.fromisoformat(granted_at.replace('Z', '+00:00'))
            expiration = grant_date + timedelta(days=duration_days)
            return expiration.isoformat()
        except:
            return None
    
    def _calculate_role_risk(self, role: str, days_remaining: int) -> str:
        """Calcula nivel de riesgo del rol."""
        risk_score = 0
        
        # Riesgo por tipo de rol
        dangerous_roles = {
            'roles/editor': 50,
            'roles/owner': 60,
            'roles/compute.admin': 40,
            'roles/iam.securityAdmin': 50,
            'roles/resourcemanager.organizationAdmin': 60
        }
        
        risk_score += dangerous_roles.get(role, 0)
        
        # Riesgo por expiración
        if days_remaining is not None:
            if days_remaining < 0:
                risk_score += 30  # Expirado
            elif days_remaining < 7:
                risk_score += 20  # Expira pronto
            elif days_remaining < 30:
                risk_score += 10  # Expira en menos de 30 días
        else:
            risk_score += 15  # Permanente sin expiración
        
        if risk_score >= 70:
            return 'CRITICAL'
        elif risk_score >= 50:
            return 'HIGH'
        elif risk_score >= 30:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def _identify_role_risks(self, role: str, days_remaining: int) -> List[str]:
        """Identifica factores de riesgo."""
        risks = []
        
        dangerous_roles = [
            'roles/editor', 'roles/owner', 'roles/compute.admin',
            'roles/iam.securityAdmin', 'roles/resourcemanager.organizationAdmin'
        ]
        
        if role in dangerous_roles:
            risks.append(f"Rol administrativo: {role}")
        
        if days_remaining is None:
            risks.append("Permiso permanente sin fecha de expiración")
        elif days_remaining < 0:
            risks.append(f"Permiso expirado hace {abs(days_remaining)} días")
        elif days_remaining < 7:
            risks.append(f"Permiso expira en {days_remaining} días")
        elif days_remaining < 30:
            risks.append(f"Permiso expira en {days_remaining} días (menos de 30)")
        
        return risks
    
    def _generate_role_summary(self, bindings: List[Dict]) -> Dict:
        """Genera resumen de roles."""
        temporary = [b for b in bindings if b['is_temporary']]
        expired = [b for b in bindings if b['is_expired']]
        expiring_soon = [b for b in bindings 
                        if b['days_remaining'] and 0 <= b['days_remaining'] < 30]
        
        return {
            'total_roles': len(bindings),
            'temporary_roles': len(temporary),
            'permanent_roles': len(bindings) - len(temporary),
            'expired_roles': len(expired),
            'expiring_soon': [
                {
                    'role': b['role'],
                    'days_remaining': b['days_remaining'],
                    'expiration_date': b['expiration_date']
                }
                for b in expiring_soon
            ],
            'highest_risk_role': max(bindings, key=lambda x: self._risk_score(x['risk_level']))['role'] if bindings else None,
            'total_permissions': sum(b['permission_count'] for b in bindings),
            'average_days_remaining': self._calculate_average_days_remaining(bindings)
        }
    
    def _calculate_average_days_remaining(self, bindings: List[Dict]) -> int:
        """Calcula promedio de días restantes."""
        days_list = [b['days_remaining'] for b in bindings if b['days_remaining'] is not None]
        return int(sum(days_list) / len(days_list)) if days_list else None
    
    def _risk_score(self, risk_level: str) -> int:
        """Convierte nivel de riesgo a puntuación."""
        scores = {'CRITICAL': 4, 'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}
        return scores.get(risk_level, 0)
    
    def _get_role_title(self, role: str) -> str:
        """Obtiene título del rol."""
        role_titles = {
            'roles/editor': 'Editor',
            'roles/owner': 'Owner',
            'roles/viewer': 'Viewer',
            'roles/compute.admin': 'Compute Admin',
            'roles/storage.admin': 'Storage Admin',
            'roles/iam.securityAdmin': 'Security Admin',
            'roles/resourcemanager.organizationAdmin': 'Organization Admin'
        }
        return role_titles.get(role, role.replace('roles/', ''))
    
    def _get_role_description(self, role: str) -> str:
        """Obtiene descripción del rol."""
        # En implementación real, usar GCP API para obtener descripciones
        descriptions = {
            'roles/editor': 'Acceso completo de lectura y escritura',
            'roles/owner': 'Acceso completo incluyendo gestión de permisos',
            'roles/viewer': 'Acceso de lectura a todos los recursos',
            'roles/compute.admin': 'Acceso completo a Compute Engine'
        }
        return descriptions.get(role, 'Descripción no disponible')
    
    def _get_permission_count(self, role: str) -> int:
        """Obtiene cantidad de permisos del rol."""
        # En implementación real, usar GCP API
        permission_counts = {
            'roles/editor': 5000,
            'roles/owner': 5000,
            'roles/viewer': 5000,
            'roles/compute.admin': 127,
            'roles/storage.admin': 50
        }
        return permission_counts.get(role, 0)
```

---

#### C. Security Analyzer
```python
class SecurityAnalyzer:
    """Analiza riesgos de seguridad de service accounts."""
    
    DANGEROUS_ROLES = [
        'roles/editor',
        'roles/owner',
        'roles/compute.admin',
        'roles/iam.securityAdmin',
        'roles/resourcemanager.organizationAdmin'
    ]
    
    def analyze(self, sa: Dict) -> Dict:
        """Analiza seguridad de un service account."""
        return {
            'has_user_managed_keys': self._check_user_managed_keys(sa),
            'key_rotation_compliant': self._check_key_rotation(sa),
            'excessive_permissions': self._check_excessive_permissions(sa),
            'risk_level': self._calculate_risk_level(sa),
            'risk_factors': self._identify_risk_factors(sa)
        }
    
    def _check_excessive_permissions(self, sa: Dict) -> bool:
        """Verifica si tiene permisos excesivos."""
        roles = [binding['role'] for binding in sa.get('iam_bindings', [])]
        return any(role in self.DANGEROUS_ROLES for role in roles)
    
    def _check_key_rotation(self, sa: Dict) -> bool:
        """Verifica cumplimiento de rotación de claves."""
        for key in sa.get('keys', []):
            if key['key_type'] == 'USER_MANAGED':
                age_days = key.get('age_days', 0)
                if age_days > 90:  # Política estándar
                    return False
        return True
    
    def _calculate_risk_level(self, sa: Dict) -> str:
        """Calcula nivel de riesgo (LOW, MEDIUM, HIGH, CRITICAL)."""
        risk_score = 0
        
        # Puntuación por factores
        if self._check_excessive_permissions(sa):
            risk_score += 40
        if not self._check_key_rotation(sa):
            risk_score += 30
        if sa.get('activity', {}).get('days_since_last_activity', 0) > 30:
            risk_score += 20
        if sa.get('disabled', False):
            risk_score += 10
        
        if risk_score >= 70:
            return 'CRITICAL'
        elif risk_score >= 50:
            return 'HIGH'
        elif risk_score >= 30:
            return 'MEDIUM'
        else:
            return 'LOW'
```

#### C. Multi-Project Orchestrator
```python
class MultiProjectOrchestrator:
    """Orquesta extracción y análisis de múltiples proyectos."""
    
    def __init__(self, projects: List[str], max_workers: int = 5):
        self.projects = projects
        self.max_workers = max_workers
    
    def extract_all(self) -> Dict:
        """Extrae datos de todos los proyectos en paralelo."""
        results = {}
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self._extract_project, proj): proj
                for proj in self.projects
            }
            
            for future in as_completed(futures):
                project = futures[future]
                try:
                    results[project] = future.result()
                except Exception as e:
                    results[project] = {'error': str(e)}
        
        return results
    
    def _extract_project(self, project_id: str) -> Dict:
        """Extrae datos de un proyecto específico."""
        extractor = ServiceAccountExtractor(project_id)
        return extractor.extract_all()
    
    def consolidate(self, data: Dict) -> Dict:
        """Consolida datos de múltiples proyectos."""
        return {
            'summary': self._generate_summary(data),
            'by_project': data,
            'cross_project_analysis': self._cross_project_analysis(data),
            'risk_matrix': self._generate_risk_matrix(data)
        }
    
    def _cross_project_analysis(self, data: Dict) -> Dict:
        """Análisis cruzado entre proyectos."""
        return {
            'total_service_accounts': sum(
                len(proj.get('service_accounts', []))
                for proj in data.values()
            ),
            'total_high_risk': sum(
                len([sa for sa in proj.get('service_accounts', [])
                     if sa.get('security', {}).get('risk_level') in ['HIGH', 'CRITICAL']])
                for proj in data.values()
            ),
            'projects_with_issues': [
                proj for proj, data in data.items()
                if any(sa.get('security', {}).get('risk_level') in ['HIGH', 'CRITICAL']
                       for sa in data.get('service_accounts', []))
            ]
        }
```

---

## � Formatos de Reporte con Análisis de Roles

### 1. Reporte JSON (Estructura Completa)

```json
{
  "report_metadata": {
    "generated_at": "2026-07-08T11:00:00Z",
    "projects_analyzed": 5,
    "total_service_accounts": 45,
    "total_roles": 120
  },
  "service_accounts": [
    {
      "project_id": "proyecto-prod",
      "email": "app-sa@proyecto-prod.iam.gserviceaccount.com",
      "roles_analysis": {
        "iam_bindings": [
          {
            "role": "roles/compute.admin",
            "role_title": "Compute Admin",
            "permission_count": 127,
            "granted_at": "2024-01-15T10:30:00Z",
            "granted_by": "admin@example.com",
            "requested_duration_days": 90,
            "expiration_date": "2024-04-15T10:30:00Z",
            "days_remaining": 45,
            "is_temporary": true,
            "is_expired": false,
            "risk_level": "HIGH"
          }
        ],
        "role_summary": {
          "total_roles": 3,
          "temporary_roles": 2,
          "permanent_roles": 1,
          "expired_roles": 0,
          "expiring_soon": [
            {
              "role": "roles/compute.admin",
              "days_remaining": 45,
              "expiration_date": "2024-04-15T10:30:00Z"
            }
          ]
        }
      }
    }
  ]
}
```

### 2. Reporte CSV (Tabla Plana)

```csv
Proyecto,Service Account,Rol,Título Rol,Permisos,Otorgado En,Otorgado Por,Duración Solicitada (días),Fecha Expiración,Días Restantes,Es Temporal,Expirado,Nivel Riesgo
proyecto-prod,app-sa@proyecto-prod.iam.gserviceaccount.com,roles/compute.admin,Compute Admin,127,2024-01-15T10:30:00Z,admin@example.com,90,2024-04-15T10:30:00Z,45,true,false,HIGH
proyecto-prod,app-sa@proyecto-prod.iam.gserviceaccount.com,roles/storage.objectViewer,Storage Object Viewer,2,2024-06-01T14:20:00Z,admin@example.com,365,2025-06-01T14:20:00Z,358,true,false,LOW
proyecto-staging,ci-cd-sa@proyecto-staging.iam.gserviceaccount.com,roles/viewer,Viewer,5000,2023-01-01T00:00:00Z,owner@example.com,,,,false,false,MEDIUM
```

### 3. Reporte Excel (Múltiples Tabs)

**Tab 1: Resumen Ejecutivo**
```
┌────────────────────────────────────────────────┐
│ RESUMEN DE SERVICE ACCOUNTS MULTI-PROYECTO      │
├────────────────────────────────────────────────┤
│ Total Proyectos:                             5 │
│ Total Service Accounts:                      45 │
│ Total Roles:                                120 │
│ Roles Temporales:                            78 │
│ Roles Permanentes:                           42 │
│ Roles Expirados:                              3 │
│ Roles Expirando Pronto (< 30 días):          12 │
│ Promedio Días Restantes:                    201 │
│ Roles de Alto Riesgo:                        18 │
└────────────────────────────────────────────────┘
```

**Tab 2: Roles por Service Account**
```
┌──────────────────────────────────────────────────────────────────┐
│ SA │ Rol │ Duración │ Expiración │ Días Rest. │ Riesgo │ Acción │
├──────────────────────────────────────────────────────────────────┤
│ app-sa │ compute.admin │ 90d │ 2024-04-15 │ 45 │ HIGH │ Revisar │
│ app-sa │ storage.viewer │ 365d │ 2025-06-01 │ 358 │ LOW │ OK │
│ ci-cd │ viewer │ Perm. │ - │ - │ MEDIUM │ Revisar │
└──────────────────────────────────────────────────────────────────┘
```

**Tab 3: Roles Expirando Pronto**
```
┌────────────────────────────────────────────────────────────────┐
│ Proyecto │ Service Account │ Rol │ Expira En │ Acción Requerida │
├────────────────────────────────────────────────────────────────┤
│ p-prod │ app-sa │ compute.admin │ 45 días │ Renovar o revocar │
│ p-staging │ ci-cd-sa │ editor │ 15 días │ Renovar urgente │
│ p-dev │ test-sa │ owner │ 3 días │ CRÍTICO: Renovar YA │
└────────────────────────────────────────────────────────────────┘
```

**Tab 4: Análisis de Riesgos**
```
┌──────────────────────────────────────────────────────────────┐
│ Proyecto │ SA │ Rol │ Riesgo │ Días Rest. │ Recomendación │
├──────────────────────────────────────────────────────────────┤
│ p-prod │ app-sa │ compute.admin │ HIGH │ 45 │ Revisar │
│ p-prod │ app-sa │ storage.viewer │ LOW │ 358 │ OK │
│ p-staging │ ci-cd │ viewer │ MEDIUM │ - │ Revisar │
└──────────────────────────────────────────────────────────────┘
```

### 4. Reporte HTML (Interactivo)

```html
<section class="roles-by-sa">
  <h2>Roles por Service Account</h2>
  <table class="interactive-table">
    <thead>
      <tr>
        <th>Proyecto</th>
        <th>Service Account</th>
        <th>Rol</th>
        <th>Duración Solicitada</th>
        <th>Fecha Expiración</th>
        <th>Días Restantes</th>
        <th>Nivel Riesgo</th>
      </tr>
    </thead>
    <tbody>
      <tr class="risk-high">
        <td>proyecto-prod</td>
        <td>app-sa@proyecto-prod.iam.gserviceaccount.com</td>
        <td>roles/compute.admin</td>
        <td>90 días</td>
        <td>2024-04-15</td>
        <td class="warning">45</td>
        <td><span class="badge high">HIGH</span></td>
      </tr>
    </tbody>
  </table>
</section>
```

---

## �📋 Casos de Uso

### 1. Auditoría de Seguridad
```bash
python gcp_sa_multi_project_reporter.py \
  --projects=proyecto1,proyecto2,proyecto3 \
  --mode=security \
  --output=excel \
  --format=detailed
```

**Salida:**
- Reporte Excel con tabs: Resumen, Alto Riesgo, Claves Vencidas, Permisos Excesivos
- Gráficos de distribución de riesgo
- Recomendaciones accionables

### 2. Cumplimiento Normativo
```bash
python gcp_sa_multi_project_reporter.py \
  --org=mi-organizacion \
  --mode=compliance \
  --output=json \
  --policy=key_rotation_90days
```

**Salida:**
- JSON con estado de cumplimiento por proyecto
- Violaciones detectadas
- Plan de remediación

### 3. Análisis de Uso
```bash
python gcp_sa_multi_project_reporter.py \
  --projects=proyecto1,proyecto2 \
  --mode=usage \
  --output=csv \
  --period=30days
```

**Salida:**
- CSV con actividad de últimos 30 días
- Servicios más utilizados
- Service accounts inactivos

### 4. Comparativa Entre Proyectos
```bash
python gcp_sa_multi_project_reporter.py \
  --projects=proyecto1,proyecto2,proyecto3 \
  --mode=all \
  --output=html \
  --compare=true
```

**Salida:**
- HTML interactivo con comparativas
- Gráficos de tendencias
- Matriz de riesgos

---

## 🔐 Consideraciones de Seguridad

### 1. Autenticación
```yaml
Opciones:
  - gcloud CLI (recomendado para desarrollo)
  - Service Account JSON (para automatización)
  - Application Default Credentials (para GCP)

Implementación:
  - Validar credenciales antes de ejecutar
  - Usar service account con permisos mínimos
  - Rotar credenciales regularmente
```

### 2. Autorización
```yaml
Permisos Mínimos:
  - iam.serviceAccounts.list
  - iam.serviceAccounts.get
  - iam.serviceAccountKeys.list
  - resourcemanager.projects.getIamPolicy
  - logging.logEntries.list

Crear rol personalizado:
  gcloud iam roles create saReporter --permissions=...
```

### 3. Protección de Datos
```yaml
Medidas:
  - Encriptar reportes en tránsito (HTTPS)
  - Encriptar reportes en reposo (AES-256)
  - Limitar acceso a reportes (ACLs)
  - Auditar acceso a reportes (Cloud Audit Logs)
  - Sanitizar datos sensibles en logs
```

### 4. Privacidad
```yaml
Consideraciones:
  - No incluir claves privadas en reportes
  - Enmascarar emails parcialmente
  - Limitar historial de actividad
  - Cumplir con políticas de retención
```

---

## 🛣️ Roadmap de Implementación

### Fase 1: MVP (2 semanas)
**Objetivo:** Herramienta básica funcional

```
Semana 1:
  - [ ] Extractor de service accounts
  - [ ] Extractor de IAM bindings
  - [ ] Extractor de claves
  - [ ] Generador de reporte JSON
  - [ ] Tests unitarios (20+)

Semana 2:
  - [ ] Multi-proyecto (paralelización)
  - [ ] Security analyzer básico
  - [ ] Generador de reporte CSV
  - [ ] Documentación
  - [ ] Tests de integración (10+)
```

**Entregables:**
- `gcp_sa_multi_project_reporter.py` (CLI)
- `sa_extractors.py` (módulo base)
- `sa_analyzers.py` (análisis básico)
- `sa_report_generators.py` (JSON, CSV)
- Documentación de uso

### Fase 2: Análisis Avanzado (2 semanas)
**Objetivo:** Análisis profundo de seguridad y cumplimiento

```
Semana 3:
  - [ ] Activity analyzer (logs)
  - [ ] Compliance analyzer
  - [ ] Risk scoring avanzado
  - [ ] Trend analysis
  - [ ] Tests (15+)

Semana 4:
  - [ ] Excel report generator
  - [ ] HTML report generator
  - [ ] Alertas automáticas
  - [ ] Caché de datos
  - [ ] Optimización de performance
```

**Entregables:**
- Análisis de actividad
- Reportes Excel/HTML
- Sistema de alertas
- Caché distribuido

### Fase 3: Integración (1 semana)
**Objetivo:** Integración con toolbox

```
- [ ] Integración en GCP tools.py (Tool 38)
- [ ] Integración en menú principal
- [ ] Validación de permisos
- [ ] Manejo de errores
- [ ] Tests finales (20+)
```

**Entregables:**
- Tool 38 en GCP launcher
- Documentación completa
- 50+ tests unitarios

---

## 📊 Métricas de Éxito

| Métrica | Target |
|---------|--------|
| **Cobertura de Proyectos** | 100% |
| **Tiempo de Extracción** | < 5 min (10 proyectos) |
| **Precisión de Análisis** | > 95% |
| **Tasa de Éxito** | > 99% |
| **Cobertura de Tests** | > 80% |
| **Documentación** | 100% |

---

## 💡 Recomendaciones

### 1. Corto Plazo (MVP)
- ✅ Implementar extractor básico
- ✅ Crear reportes JSON/CSV
- ✅ Validar con 2-3 proyectos
- ✅ Documentar uso

### 2. Mediano Plazo
- ✅ Agregar análisis de seguridad
- ✅ Crear reportes Excel/HTML
- ✅ Implementar alertas
- ✅ Integrar en toolbox

### 3. Largo Plazo
- ✅ Machine Learning para detección de anomalías
- ✅ Dashboard interactivo
- ✅ Integración con SIEM
- ✅ Automatización de remediación

---

## 📚 Referencias

### Documentación GCP
- [Service Accounts](https://cloud.google.com/iam/docs/service-accounts)
- [IAM Roles](https://cloud.google.com/iam/docs/understanding-roles)
- [Cloud Logging](https://cloud.google.com/logging/docs)
- [gcloud CLI](https://cloud.google.com/sdk/gcloud)

### Estándares de Seguridad
- [CIS Google Cloud Platform Foundation Benchmark](https://www.cisecurity.org/benchmark/google_cloud_platform)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [ISO 27001](https://www.iso.org/isoiec-27001-information-security-management.html)

---

## 🎯 Conclusión

La implementación de una herramienta de reporte de service accounts multi-proyecto es **viable, necesaria y altamente beneficiosa** para:

1. **Seguridad:** Identificar y mitigar riesgos IAM
2. **Cumplimiento:** Validar políticas de rotación y permisos
3. **Operaciones:** Automatizar auditoría y análisis
4. **Visibilidad:** Consolidar información dispersa

**Recomendación:** Proceder con Fase 1 (MVP) inmediatamente, con timeline de 2 semanas.

---

**Versión:** 1.0.0  
**Fecha:** 8 de Julio de 2026  
**Autor:** Harold Adrian Bolanos Rodriguez  
**Estado:** ✅ ANÁLISIS COMPLETADO


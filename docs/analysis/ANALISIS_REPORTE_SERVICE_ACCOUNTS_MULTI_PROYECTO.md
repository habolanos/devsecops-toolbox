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

### 1. Fuentes de Datos

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

### 2. Módulos Principales

#### A. Extractor Base
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

#### B. Security Analyzer
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

## 📋 Casos de Uso

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


# 🔐 GCP Secret Manager Integration

## Highlights

Esta versión introduce **soporte completo para GCP Secret Manager** en las herramientas de conectividad de Kubernetes, permitiendo validar conexiones a bases de datos cuyos credenciales están almacenados de forma segura en Secret Manager.

## ✨ What's New

### 🔐 Secret Manager Support
- **Deploy Dependency Checker** (v1.0.5) y **Deployment Validator** (v1.0.4) ahora detectan y procesan referencias a GCP Secret Manager
- Obtención automática de secretos vía `gcloud secrets versions access`
- Extracción de conexiones DB desde JSON (`host`, `port`, `type`)
- Nueva columna **Source** en resultados: 🔐 SM / 🔑 K8s / 📋 CM

### 🎨 Rich Console Improvements
- Forzado de Rich terminal mode para ejecuciones desde menú
- Tablas formateadas, colores, iconos y progress spinners en todas las ejecuciones
- Instalación automática de Rich en venv

### 🔧 Technical Improvements
- Type hints con `from __future__ import annotations`
- Directorio de salida centralizado (`scm/outcome/`)
- Export CSV/JSON con metadata de Secret Manager
- Debug mejorado para troubleshooting

## 📊 Example Output

```
╭─────────────────┬──────────────┬──────────┬──────────────┬────────────┬──────────┬────────╮
│ Origen          │ Recurso      │  Source  │ Conexión     │ Tipo DB    │ Host     │ Puerto │
├─────────────────┼──────────────┼──────────┼──────────────┼────────────┼──────────┼────────┤
│ ConfigMap       │ app-config   │  🔐 SM   │ TCP          │ postgresql │ 10.1.2.3 │  5432  │
│ ConfigMap       │ app-config   │  📋 CM   │ TCP          │ redis      │ 10.1.2.4 │  6379  │
│ Secret          │ db-creds     │  🔑 K8s  │ TCP          │ mysql      │ 10.1.2.5 │  3306  │
╰─────────────────┴──────────────┴──────────┴──────────────┴────────────┴──────────┴────────╯
```

## 🚀 Installation

```bash
git clone <repo-url>
cd devsecops-toolbox
python scm/gcp/tools.py
```

## 📝 Full Changelog

### Features
- `7f6ea91` feat(gcp/connectivity): Add GCP Secret Manager support to deploy_dependency_checker v1.0.5
- `6de7618` feat(gcp/connectivity): Add GCP Secret Manager support to deployment_validator v1.0.4

### Fixes
- `7e12d76` fix(gcp/tools): Add Rich requirements to connectivity tools
- `f9179e1` fix(gcp/connectivity): Force Rich terminal mode for subprocess execution
- `2d31ecd` fix(gcp/connectivity): Use centralized output directory for exports
- `cd7aa72` fix(gcp/connectivity): Use __future__ annotations for type hints
- `8d6f65f` fix(gcp/connectivity): Improve Console fallback for type hints

### Chores
- `7bdd239` chore: Bump version to 1.9.4
- `8d10b55` docs: Add release notes for v1.9.4

## 📦 Assets

- **Source code** (zip)
- **Source code** (tar.gz)
- **Distribution**: `devsecops-toolbox_dist_20260616_132218.zip` (1.294 MB, 201 files)

## 🔄 Migration from v1.9.3

100% backward compatible. No breaking changes.

---

**Full release notes:** [RELEASE_v1.9.4.md](./RELEASE_v1.9.4.md)

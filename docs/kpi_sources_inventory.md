# Inventario de Fuentes JSON — DevSecOps Toolbox

> **Última actualización**: 2026-06-09  
> **Herramientas catalogadas**: 67 scripts  
> **Salidas JSON identificadas**: 67 archivos

---

## Resumen por Plataforma

| Plataforma | Scripts | Salidas JSON | Dimensiones Cubiertas |
|------------|---------|--------------|----------------------|
| **GCP** | 25 | 25 | Seguridad, Observabilidad, Confiabilidad, Eficiencia |
| **AZDO** | 17 | 17 | Entrega Continua, Cumplimiento, Confiabilidad |
| **AWS** | 19 | 19 | Seguridad, Observabilidad, Eficiencia |
| **Terminal** | 6 | 6 | Observabilidad, Confiabilidad |

---

## GCP — Google Cloud Platform (25 herramientas)

### Seguridad

| Script | Salida JSON | Campos Clave | Dimensión KPI | Periodicidad |
|--------|-------------|--------------|---------------|--------------|
| `gcp/certificate-manager/gcp_certificate_checker.py` | `outcome/gcp_certificates_YYYYMMDD_HHMMSS.json` | `certificates[].days_to_expiry`, `certificates[].status`, `certificates[].domains` | Seguridad | Diaria |
| `gcp/rolesypermisos/gcp_iam_roles_report.py` | `outcome/gcp_iam_roles_YYYYMMDD_HHMMSS.json` | `bindings[].role`, `bindings[].members`, `bindings[].has_wildcard` | Seguridad | Semanal |
| `gcp/service-account/gcp_service_account_checker.py` | `outcome/gcp_service_accounts_YYYYMMDD_HHMMSS.json` | `service_accounts[].email`, `service_accounts[].keys_count`, `service_accounts[].last_used` | Seguridad | Semanal |
| `gcp/secrets-configmaps/gcp_secrets_configmaps_checker.py` | `outcome/gcp_secrets_configmaps_YYYYMMDD_HHMMSS.json` | `secrets[].name`, `secrets[].last_modified`, `secrets[].rotation_days` | Seguridad | Diaria |
| `gcp/cloud-armor/gcp_cloud_armor_checker.py` | `outcome/gcp_cloud_armor_YYYYMMDD_HHMMSS.json` | `policies[].name`, `policies[].rules_count`, `policies[].enabled` | Seguridad | Semanal |

### Observabilidad

| Script | Salida JSON | Campos Clave | Dimensión KPI | Periodicidad |
|--------|-------------|--------------|---------------|--------------|
| `gcp/monitoring/gcp_monitor.py` | `outcome/gcp_monitoring_YYYYMMDD_HHMMSS.json` | `resources[].type`, `resources[].cpu_usage`, `resources[].memory_usage`, `resources[].status` | Observabilidad | Horaria |
| `gcp/monitoring/gke_deployments_report.py` | `outcome/gke_deployments_YYYYMMDD_HHMMSS.json` | `deployments[].name`, `deployments[].replicas`, `deployments[].ready_replicas`, `deployments[].conditions` | Observabilidad | Diaria |
| `gcp/monitoring/gke_node_monitor.py` | `outcome/gke_nodes_YYYYMMDD_HHMMSS.json` | `nodes[].name`, `nodes[].cpu_allocatable`, `nodes[].memory_allocatable`, `nodes[].pods_count` | Observabilidad | Horaria |
| `gcp/monitoring/gke_pod_monitor.py` | `outcome/gke_pods_YYYYMMDD_HHMMSS.json` | `pods[].name`, `pods[].cpu_request`, `pods[].cpu_limit`, `pods[].memory_request`, `pods[].memory_limit` | Observabilidad | Horaria |

### Confiabilidad

| Script | Salida JSON | Campos Clave | Dimensión KPI | Periodicidad |
|--------|-------------|--------------|---------------|--------------|
| `gcp/connectivity/pod_connectivity_checker.py` | `outcome/pod_connectivity_YYYYMMDD_HHMMSS.json` | `results[].status`, `results[].message`, `results[].latency_ms` | Confiabilidad | Diaria |
| `gcp/connectivity/deploy_dependency_checker.py` | `outcome/deploy_dependencies_YYYYMMDD_HHMMSS.json` | `dependencies[].name`, `dependencies[].status`, `dependencies[].health_check` | Confiabilidad | Diaria |
| `gcp/connectivity/deployment_validator.py` | `outcome/deployment_validation_YYYYMMDD_HHMMSS.json` | `validations[].deployment`, `validations[].configmaps_ok`, `validations[].secrets_ok`, `validations[].connectivity_ok` | Confiabilidad | Diaria |
| `gcp/load-balancer/gcp_load_balancer_checker.py` | `outcome/gcp_load_balancers_YYYYMMDD_HHMMSS.json` | `load_balancers[].name`, `load_balancers[].backends[].healthy_count`, `load_balancers[].backends[].unhealthy_count` | Confiabilidad | Horaria |

### Eficiencia Operativa

| Script | Salida JSON | Campos Clave | Dimensión KPI | Periodicidad |
|--------|-------------|--------------|---------------|--------------|
| `gcp/cluster-gke/gcp_cluster_checker.py` | `outcome/gcp_gke_clusters_YYYYMMDD_HHMMSS.json` | `clusters[].name`, `clusters[].node_count`, `clusters[].version`, `clusters[].autoscaling_enabled` | Eficiencia | Diaria |
| `gcp/cloud-sql/gcp_disk_checker.py` | `outcome/gcp_cloudsql_disk_YYYYMMDD_HHMMSS.json` | `instances[].name`, `instances[].disk_size_gb`, `instances[].disk_used_gb`, `instances[].disk_usage_percent` | Eficiencia | Diaria |
| `gcp/cloud-sql/gcp_database_checker.py` | `outcome/gcp_cloudsql_databases_YYYYMMDD_HHMMSS.json` | `databases[].instance`, `databases[].name`, `databases[].size_mb` | Eficiencia | Semanal |
| `gcp/vpc-networks/gcp_vpc_networks_checker.py` | `outcome/gcp_vpc_networks_YYYYMMDD_HHMMSS.json` | `networks[].name`, `networks[].subnets_count`, `networks[].firewall_rules_count` | Eficiencia | Semanal |
| `gcp/vpc-networks/gcp_ip_addresses_checker.py` | `outcome/gcp_ip_addresses_YYYYMMDD_HHMMSS.json` | `addresses[].name`, `addresses[].status`, `addresses[].in_use` | Eficiencia | Diaria |
| `gcp/gateway-services/gcp_gateway_checker.py` | `outcome/gcp_gateways_YYYYMMDD_HHMMSS.json` | `gateways[].name`, `gateways[].routes_count`, `gateways[].services_count` | Eficiencia | Semanal |
| `gcp/artifact-registry/gcp_artifact_registry_tag_filter.py` | `outcome/gcp_artifact_registry_YYYYMMDD_HHMMSS.json` | `images[].name`, `images[].tags_count`, `images[].size_mb`, `images[].last_updated` | Eficiencia | Semanal |
| `gcp/cloud-run/gcp_cloudrun_checker.py` | `outcome/gcp_cloudrun_YYYYMMDD_HHMMSS.json` | `services[].name`, `services[].traffic`, `services[].revisions_count`, `services[].min_instances` | Eficiencia | Diaria |
| `gcp/cloud-sql/gcp_sql_comparator.py` | `outcome/gcp_cloudsql_comparison_YYYYMMDD_HHMMSS.json` | `comparison[].instance`, `comparison[].differences[]` | Eficiencia | Semanal |
| `gcp/inventory/generar-inventario-csv.py` | `outcome/gcp_inventory_YYYYMMDD_HHMMSS.json` | `inventory[].resource_type`, `inventory[].count`, `inventory[].status` | Eficiencia | Mensual |
| `gcp/reports-viewer/gcp_reports_viewer.py` | `outcome/gcp_reports_dashboard_YYYYMMDD_HHMMSS.json` | `metrics.by_tool`, `metrics.by_status`, `metrics.total_resources` | Observabilidad | Diaria |

---

## AZDO — Azure DevOps (17 herramientas)

### Entrega Continua

| Script | Salida JSON | Campos Clave | Dimensión KPI | Periodicidad |
|--------|-------------|--------------|---------------|--------------|
| `azdo/cicd_inventory.py` | `outcome/cicd_inventory_YYYYMMDD_HHMMSS.json` | `repos[].name`, `repos[].ci_pipeline`, `repos[].cd_pipeline`, `repos[].last_commit_date` | Entrega Continua | Diaria |
| `azdo/cicd_inventory_prod_deploy.py` | `outcome/prod_deployments_YYYYMMDD_HHMMSS.json` | `deployments[].pipeline`, `deployments[].environment`, `deployments[].status`, `deployments[].timestamp` | Entrega Continua | Diaria |
| `azdo/cicd_inventory_ci_detailed.py` | `outcome/ci_pipelines_detailed_YYYYMMDD_HHMMSS.json` | `pipelines[].name`, `pipelines[].runs_count_30d`, `pipelines[].success_rate`, `pipelines[].avg_duration_minutes` | Entrega Continua | Diaria |
| `azdo/cicd_inventory_cd_detailed.py` | `outcome/cd_pipelines_detailed_YYYYMMDD_HHMMSS.json` | `pipelines[].name`, `pipelines[].deployments_count_30d`, `pipelines[].success_rate`, `pipelines[].avg_duration_minutes` | Entrega Continua | Diaria |
| `azdo/cicd_pipeline_status.py` | `outcome/pipeline_status_YYYYMMDD_HHMMSS.json` | `pipelines[].name`, `pipelines[].status`, `pipelines[].last_run`, `pipelines[].failure_count_7d` | Entrega Continua | Horaria |

### Confiabilidad

| Script | Salida JSON | Campos Clave | Dimensión KPI | Periodicidad |
|--------|-------------|--------------|---------------|--------------|
| `azdo/cicd_inventory_health_score.py` | `outcome/pipeline_health_score_YYYYMMDD_HHMMSS.json` | `pipelines[].health_score`, `pipelines[].mttr_minutes`, `pipelines[].rating`, `pipelines[].dimensions` | Confiabilidad | Diaria |
| `azdo/azdo_release_cd_health.py` | `outcome/release_cd_health_YYYYMMDD_HHMMSS.json` | `releases[].name`, `releases[].success_rate`, `releases[].avg_duration`, `releases[].failure_count` | Confiabilidad | Diaria |
| `azdo/azdo_release_deep_dive.py` | `outcome/release_deep_dive_YYYYMMDD_HHMMSS.json` | `releases[].name`, `releases[].stages[]`, `releases[].approvals[]`, `releases[].artifacts[]` | Confiabilidad | Semanal |

### Cumplimiento

| Script | Salida JSON | Campos Clave | Dimensión KPI | Periodicidad |
|--------|-------------|--------------|---------------|--------------|
| `azdo/azdo_branch_policy_checker.py` | `outcome/branch_policies_YYYYMMDD_HHMMSS.json` | `repos[].name`, `repos[].policies[].type`, `repos[].policies[].enabled`, `repos[].policies[].compliant` | Cumplimiento | Semanal |
| `azdo/azdo_branch_lock_checker.py` | `outcome/branch_locks_YYYYMMDD_HHMMSS.json` | `repos[].name`, `repos[].branches[].name`, `repos[].branches[].locked`, `repos[].branches[].lock_reason` | Cumplimiento | Diaria |
| `azdo/azdo_pipeline_drift.py` | `outcome/pipeline_drift_YYYYMMDD_HHMMSS.json` | `pipelines[].name`, `pipelines[].has_drift`, `pipelines[].drift_type`, `pipelines[].last_modified` | Cumplimiento | Semanal |
| `azdo/azdo_pr_master_checker.py` | `outcome/pr_master_check_YYYYMMDD_HHMMSS.json` | `prs[].id`, `prs[].title`, `prs[].approvals_count`, `prs[].required_approvals`, `prs[].compliant` | Cumplimiento | Diaria |
| `azdo/azdo_pr_pipeline_analyzer.py` | `outcome/pr_pipeline_analysis_YYYYMMDD_HHMMSS.json` | `prs[].id`, `prs[].pipeline_runs[]`, `prs[].validation_status` | Cumplimiento | Diaria |
| `azdo/azdo_task_validator.py` | `outcome/task_validation_YYYYMMDD_HHMMSS.json` | `pipelines[].name`, `pipelines[].tasks[].name`, `pipelines[].tasks[].version`, `pipelines[].tasks[].deprecated` | Cumplimiento | Semanal |
| `azdo/cicd_inventory_pending_approvals.py` | `outcome/pending_approvals_YYYYMMDD_HHMMSS.json` | `approvals[].release`, `approvals[].environment`, `approvals[].approver`, `approvals[].pending_since` | Cumplimiento | Diaria |

### Eficiencia Operativa

| Script | Salida JSON | Campos Clave | Dimensión KPI | Periodicidad |
|--------|-------------|--------------|---------------|--------------|
| `azdo/cicd_inventory_branches_created.py` | `outcome/branches_created_YYYYMMDD_HHMMSS.json` | `branches[].repo`, `branches[].name`, `branches[].creator`, `branches[].created_date` | Eficiencia | Semanal |
| `azdo/cicd_inventory_hotfix_branches.py` | `outcome/hotfix_branches_YYYYMMDD_HHMMSS.json` | `branches[].repo`, `branches[].name`, `branches[].creator`, `branches[].age_days` | Eficiencia | Diaria |
| `azdo/cicd_inventory_gke_pipelines.py` | `outcome/gke_pipelines_YYYYMMDD_HHMMSS.json` | `pipelines[].name`, `pipelines[].gke_clusters[]`, `pipelines[].last_run` | Eficiencia | Semanal |

---

## AWS — Amazon Web Services (19 herramientas)

### Seguridad

| Script | Salida JSON | Campos Clave | Dimensión KPI | Periodicidad |
|--------|-------------|--------------|---------------|--------------|
| `aws/iam/aws_iam_checker.py` | `outcome/aws_iam_users_YYYYMMDD_HHMMSS.json` | `users[].name`, `users[].mfa_enabled`, `users[].access_keys_count`, `users[].last_activity` | Seguridad | Diaria |
| `aws/iam/aws_roles_checker.py` | `outcome/aws_iam_roles_YYYYMMDD_HHMMSS.json` | `roles[].name`, `roles[].policies_count`, `roles[].has_wildcard`, `roles[].last_used` | Seguridad | Semanal |
| `aws/acm/aws_acm_checker.py` | `outcome/aws_acm_certificates_YYYYMMDD_HHMMSS.json` | `certificates[].domain`, `certificates[].days_to_expiry`, `certificates[].status`, `certificates[].in_use` | Seguridad | Diaria |
| `aws/secretsmanager/aws_secrets_checker.py` | `outcome/aws_secrets_YYYYMMDD_HHMMSS.json` | `secrets[].name`, `secrets[].last_rotated`, `secrets[].rotation_enabled`, `secrets[].days_since_rotation` | Seguridad | Diaria |
| `aws/waf/aws_waf_checker.py` | `outcome/aws_waf_YYYYMMDD_HHMMSS.json` | `web_acls[].name`, `web_acls[].rules_count`, `web_acls[].associated_resources[]` | Seguridad | Semanal |

### Observabilidad

| Script | Salida JSON | Campos Clave | Dimensión KPI | Periodicidad |
|--------|-------------|--------------|---------------|--------------|
| `aws/cloudwatch/aws_cloudwatch_checker.py` | `outcome/aws_cloudwatch_alarms_YYYYMMDD_HHMMSS.json` | `alarms[].name`, `alarms[].state`, `alarms[].metric`, `alarms[].threshold` | Observabilidad | Horaria |
| `aws/eks/aws_eks_pod_checker.py` | `outcome/aws_eks_pods_YYYYMMDD_HHMMSS.json` | `pods[].name`, `pods[].cpu_request`, `pods[].memory_request`, `pods[].status` | Observabilidad | Horaria |
| `aws/eks/aws_eks_node_checker.py` | `outcome/aws_eks_nodes_YYYYMMDD_HHMMSS.json` | `nodes[].name`, `nodes[].cpu_allocatable`, `nodes[].memory_allocatable`, `nodes[].pods_count` | Observabilidad | Horaria |

### Confiabilidad

| Script | Salida JSON | Campos Clave | Dimensión KPI | Periodicidad |
|--------|-------------|--------------|---------------|--------------|
| `aws/rds/aws_rds_checker.py` | `outcome/aws_rds_instances_YYYYMMDD_HHMMSS.json` | `instances[].name`, `instances[].status`, `instances[].multi_az`, `instances[].backup_retention_days` | Confiabilidad | Diaria |
| `aws/elb/aws_load_balancer_checker.py` | `outcome/aws_load_balancers_YYYYMMDD_HHMMSS.json` | `load_balancers[].name`, `load_balancers[].healthy_targets`, `load_balancers[].unhealthy_targets` | Confiabilidad | Horaria |
| `aws/eks/aws_eks_checker.py` | `outcome/aws_eks_clusters_YYYYMMDD_HHMMSS.json` | `clusters[].name`, `clusters[].status`, `clusters[].version`, `clusters[].endpoint` | Confiabilidad | Diaria |

### Eficiencia Operativa

| Script | Salida JSON | Campos Clave | Dimensión KPI | Periodicidad |
|--------|-------------|--------------|---------------|--------------|
| `aws/ec2/aws_ec2_checker.py` | `outcome/aws_ec2_instances_YYYYMMDD_HHMMSS.json` | `instances[].id`, `instances[].type`, `instances[].state`, `instances[].cpu_utilization` | Eficiencia | Diaria |
| `aws/ec2/aws_ebs_checker.py` | `outcome/aws_ebs_volumes_YYYYMMDD_HHMMSS.json` | `volumes[].id`, `volumes[].size_gb`, `volumes[].iops`, `volumes[].attached` | Eficiencia | Diaria |
| `aws/rds/aws_rds_storage_checker.py` | `outcome/aws_rds_storage_YYYYMMDD_HHMMSS.json` | `instances[].name`, `instances[].allocated_storage_gb`, `instances[].storage_used_percent` | Eficiencia | Diaria |
| `aws/lambda/aws_lambda_checker.py` | `outcome/aws_lambda_functions_YYYYMMDD_HHMMSS.json` | `functions[].name`, `functions[].runtime`, `functions[].memory_mb`, `functions[].invocations_30d` | Eficiencia | Diaria |
| `aws/ecr/aws_ecr_checker.py` | `outcome/aws_ecr_repositories_YYYYMMDD_HHMMSS.json` | `repositories[].name`, `repositories[].images_count`, `repositories[].size_mb` | Eficiencia | Semanal |
| `aws/vpc/aws_vpc_checker.py` | `outcome/aws_vpcs_YYYYMMDD_HHMMSS.json` | `vpcs[].id`, `vpcs[].cidr_block`, `vpcs[].subnets_count` | Eficiencia | Semanal |
| `aws/vpc/aws_security_groups_checker.py` | `outcome/aws_security_groups_YYYYMMDD_HHMMSS.json` | `security_groups[].id`, `security_groups[].rules_count`, `security_groups[].has_overly_permissive_rules` | Eficiencia | Semanal |
| `aws/inventory/aws_inventory_generator.py` | `outcome/aws_inventory_YYYYMMDD_HHMMSS.json` | `inventory[].resource_type`, `inventory[].count`, `inventory[].region` | Eficiencia | Mensual |

---

## Terminal — Scripts Universales (6 herramientas)

### Observabilidad

| Script | Salida JSON | Campos Clave | Dimensión KPI | Periodicidad |
|--------|-------------|--------------|---------------|--------------|
| `terminal/certificate-tls-report.sh` | `outcome/certificate_tls_report_YYYYMMDD_HHMMSS.json` | `certificates[].host`, `certificates[].expiry_date`, `certificates[].days_remaining`, `certificates[].tls_version` | Observabilidad | Diaria |
| `terminal/db-connections-checker.sh` | `outcome/db_connections_YYYYMMDD_HHMMSS.json` | `connections[].host`, `connections[].port`, `connections[].status`, `connections[].latency_ms` | Observabilidad | Horaria |

### Confiabilidad

| Script | Salida JSON | Campos Clave | Dimensión KPI | Periodicidad |
|--------|-------------|--------------|---------------|--------------|
| `terminal/deployments-last-news.sh` | `outcome/deployments_last_news_YYYYMMDD_HHMMSS.json` | `deployments[].name`, `deployments[].created_date`, `deployments[].replicas` | Confiabilidad | Diaria |
| `terminal/deployments-last-update.sh` | `outcome/deployments_last_update_YYYYMMDD_HHMMSS.json` | `deployments[].name`, `deployments[].last_rollout`, `deployments[].revision` | Confiabilidad | Diaria |
| `terminal/deployments-recent-events.sh` | `outcome/deployments_recent_events_YYYYMMDD_HHMMSS.json` | `events[].deployment`, `events[].type`, `events[].reason`, `events[].message`, `events[].timestamp` | Confiabilidad | Horaria |
| `terminal/k8s-deploy-manifest-diff.sh` | `outcome/k8s_manifest_diff_YYYYMMDD_HHMMSS.json` | `diffs[].deployment`, `diffs[].changes[]`, `diffs[].severity`, `diffs[].recommendations[]` | Confiabilidad | Por demanda |

---

## Notas Técnicas

### Convenciones de Nombres de Archivos

Todos los archivos JSON siguen el patrón:
```
outcome/<tool_name>_YYYYMMDD_HHMMSS.json
```

### Estructura Común de JSON

Todos los archivos JSON incluyen metadata estándar:
```json
{
  "metadata": {
    "script": "nombre_script.py",
    "version": "x.y.z",
    "generated_at": "YYYY-MM-DDTHH:MM:SS.sssZ",
    "platform": "gcp|azdo|aws|terminal",
    "project_id": "...",
    "region": "..."
  },
  "summary": {
    "total_resources": 0,
    "healthy": 0,
    "warning": 0,
    "critical": 0
  },
  "data": [...]
}
```

### Campos Comunes para KPIs

Los siguientes campos son críticos para el cálculo de KPIs y aparecen en múltiples salidas:

- **Timestamps**: `generated_at`, `last_modified`, `created_date`, `last_run`
- **Estados**: `status`, `state`, `health`, `rating`
- **Contadores**: `count`, `total`, `success_count`, `failure_count`
- **Métricas de tiempo**: `duration_minutes`, `mttr_minutes`, `days_since_*`, `days_to_expiry`
- **Porcentajes**: `success_rate`, `usage_percent`, `cpu_usage`, `memory_usage`
- **Booleanos de compliance**: `enabled`, `compliant`, `has_drift`, `mfa_enabled`, `rotation_enabled`

---

## Próximos Pasos

1. **Mapeo a KPIs**: Cada campo clave se mapeará a uno o más KPIs en `kpi_schema.yaml`.
2. **Fórmulas de cálculo**: Definir operaciones matemáticas para agregar datos de múltiples fuentes.
3. **Benchmarks**: Asociar cada KPI con valores de referencia de industria (DORA, SRE, ITIL).
4. **Dashboards**: Visualizar KPIs en tiempo real usando las salidas JSON como fuente de datos.

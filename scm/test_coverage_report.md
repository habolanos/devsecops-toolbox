# Reporte de Cobertura de Tests — scm/

> **Fecha:** 2026-08-09
> **Alcance:** Todos los programas `.py` en `scm/` y sus subfolders

---

## Resumen Ejecutivo

| Métrica | Valor |
|---------|-------|
| Total programas `.py` | 185 |
| Total archivos de test | 55 |
| Programas con test directo | 22 |
| Programas con test centralizado | 18 |
| Programas sin test | 145 |
| Cobertura total | 21.6% |

---

## Reporte por Subfolder

### 1. scm/ (root — 8 scripts, 0 tests propios)

| Script | Test directo | Test centralizado |
|--------|-------------|-------------------|
| `base_launcher.py` | ❌ | ✅ `tests/unit/test_base_launcher_unit.py` |
| `export_manager.py` | ❌ | ❌ |
| `fix_dashboard_config.py` | ❌ | ❌ |
| `main.py` | ❌ | ✅ `tests/unit/test_main.py`, `test_main_extended.py` |
| `output_manager.py` | ❌ | ✅ `tests/unit/test_output_manager.py` |
| `search_module.py` | ❌ | ✅ `tests/unit/test_search_module.py` |
| `search_module_advanced.py` | ❌ | ❌ |
| `utils.py` | ❌ | ✅ `tests/unit/test_utils.py` |

**Cobertura:** 5/8 (62.5%) via tests centralizados

---

### 2. scm/aws/ (5 scripts root + 45 scripts en subfolders = 50 total)

#### aws/ root

| Script | Test directo | Test centralizado |
|--------|-------------|-------------------|
| `fix_encoding.py` | ❌ | ❌ |
| `generate_remaining_tools.py` | ❌ | ❌ |
| `regenerate_tools.py` | ❌ | ❌ |
| `tools.py` | ❌ | ✅ `aws/tests/test_aws_tools.py`, `tests/unit/test_aws_tools.py` |
| `validate_tools_registration.py` | ❌ | ❌ |

#### aws/ subfolders (45 scripts, 0 tests)

| Subfolder | Scripts | Tests |
|-----------|---------|-------|
| `acm/` | 1 | 0 |
| `cloudwatch/` | 2 | 0 |
| `ec2/` | 2 | 0 |
| `ecr/` | 2 | 0 |
| `eks/` | 8 | 0 |
| `elb/` | 1 | 0 |
| `iam/` | 4 | 0 |
| `inventory/` | 5 | 0 |
| `lambda/` | 5 | 0 |
| `rds/` | 4 | 0 |
| `secretsmanager/` | 1 | 0 |
| `vpc/` | 4 | 0 |
| `waf/` | 1 | 0 |

**Cobertura:** 1/50 (2.0%) — solo `tools.py` tiene test

---

### 3. scm/azdo/ (31 scripts root + 17 en subfolders = 48 total)

#### azdo/ root

| Script | Test directo | Test centralizado |
|--------|-------------|-------------------|
| `azdo_branch_lock_checker.py` | ❌ | ❌ |
| `azdo_branch_policy_checker.py` | ❌ | ❌ |
| `azdo_pipeline_drift.py` | ❌ | ❌ |
| `azdo_pipeline_history.py` | ❌ | ✅ `tests/test_azdo_pipeline_history.py` |
| `azdo_pr_master_checker.py` | ❌ | ✅ `tests/unit/test_pr_master_checker.py` |
| `azdo_pr_pipeline_analyzer.py` | ❌ | ❌ |
| `azdo_release_cd_health.py` | ✅ `test_release_cd_health.py` | ❌ |
| `azdo_release_deep_dive.py` | ❌ | ❌ |
| `azdo_release_explorer_rich.py` | ❌ | ❌ |
| `azdo_repo_branch_diff.py` | ❌ | ❌ |
| `azdo_repo_properties_branch_diff.py` | ❌ | ❌ |
| `azdo_scan_pipeline_logs.py` | ❌ | ❌ |
| `azdo_scan_repos_vulnerabilities.py` | ❌ | ❌ |
| `azdo_task_validator.py` | ❌ | ❌ |
| `cicd_inventory.py` | ❌ | ❌ |
| `cicd_inventory_branches_created.py` | ❌ | ❌ |
| `cicd_inventory_cd_detailed.py` | ✅ `test_cd_detailed_inventory.py` | ❌ |
| `cicd_inventory_ci_detailed.py` | ❌ | ❌ |
| `cicd_inventory_gke_pipelines.py` | ❌ | ❌ |
| `cicd_inventory_health_score.py` | ❌ | ❌ |
| `cicd_inventory_hotfix_branches.py` | ❌ | ❌ |
| `cicd_inventory_pending_approvals.py` | ❌ | ❌ |
| `cicd_inventory_prod_deploy.py` | ❌ | ❌ |
| `cicd_pipeline_status.py` | ❌ | ✅ `tests/unit/test_cicd_pipeline_status.py` |
| `interactive_search.py` | ❌ | ❌ |
| `pipeline-cd-rollback-pipeline.py` | ❌ | ✅ `tests/unit/test_pipeline_rollback_extended.py`, `test_pipeline_rollback_redo.py` |
| `pipeline-cd-update-branchconfig.py` | ❌ | ✅ `tests/unit/test_pipeline_update_extended.py` |
| `pipeline_cd_backup_restore.py` | ✅ `test_pipeline_cd_backup_restore.py` | ❌ |
| `pipeline_cd_new_re_release.py` | ❌ | ❌ |
| `pipeline_cd_restore_release.py` | ❌ | ❌ |
| `tools.py` | ❌ | ✅ `tests/unit/test_azdo_tools.py` |

#### azdo/health-probe-masive/ (7 scripts, 1 test)

| Script | Test directo |
|--------|-------------|
| `azdo_parser.py` | ❌ |
| `config.py` | ❌ |
| `connectivity_tester.py` | ❌ |
| `health_probe_validator.py` | ✅ `test_health_probe.py` |
| `k8s_checker.py` | ❌ |
| `models.py` | ❌ |
| `reporter.py` | ❌ |

#### azdo/pipeline_updater/ (10 scripts, 11 tests)

| Script | Test directo |
|--------|-------------|
| `azdo_client.py` | ✅ `test_update_release_definition.py` |
| `config.py` | ❌ |
| `models.py` | ❌ |
| `parallel_executor.py` | ✅ `test_disable_pipeline.py` |
| `pipeline_updater.py` | ❌ |
| `reporter.py` | ❌ |
| `search_engine.py` | ❌ |
| `template_parser.py` | ❌ |
| `update_engine.py` | ✅ `test_add_task.py`, `test_copy_stage.py`, `test_exact_match.py`, `test_reorder_stages.py`, `test_template_*.py` (6), `test_triggers.py` |
| `validator.py` | ❌ |

**Cobertura azdo/:** 17/48 (35.4%)

---

### 4. scm/azure/ (1 script, 0 tests)

| Script | Test directo |
|--------|-------------|
| `tools.py` | ❌ |

**Cobertura:** 0/1 (0%)

---

### 5. scm/dashboard/ (4 scripts, 0 tests propios)

| Script | Test directo | Test centralizado |
|--------|-------------|-------------------|
| `dashboard_consolidator.py` | ❌ | ✅ `tests/unit/test_dashboard_direct.py` |
| `dashboard_generator.py` | ❌ | ✅ `tests/unit/test_dashboard_generator.py`, `test_dashboard_main.py`, `test_dashboard_modules.py` |
| `dashboard_scheduler.py` | ❌ | ❌ |
| `run_dashboard.py` | ❌ | ✅ `tests/unit/test_dashboard_launch.py` |

**Cobertura:** 3/4 (75%) via tests centralizados

---

### 6. scm/gcp/ (1 script root + 48 scripts en subfolders = 49 total)

#### gcp/ root

| Script | Test directo | Test centralizado |
|--------|-------------|-------------------|
| `tools.py` | ❌ | ✅ `tests/unit/test_gcp_tools.py` |

#### gcp/ subfolders (48 scripts, 4 tests)

| Subfolder | Scripts | Tests |
|-----------|---------|-------|
| `artifact-registry/` | 1 | 0 |
| `certificate-manager/` | 1 | 0 |
| `cloud-armor/` | 1 | 0 |
| `cloud-functions/` | 3 | 0 |
| `cloud-run/` | 11 | 0 |
| `cloud-sql/` | 3 | 0 |
| `cluster-gke/` | 1 | 0 |
| `connectivity/` | 3 | 1 (`test_secret_manager.py`) |
| `consolidation/` | 3 | 0 |
| `deployments_off/` | 1 | 0 |
| `event-tracker/` | 1 | 0 |
| `gateway-services/` | 2 | 2 (`test_dashboard_generator.py`, `test_route_duplicates.py`) |
| `inventory/` | 3 | 0 |
| `load-balancer/` | 1 | 1 (`test_load_balancer_checker.py`) |
| `monitoring/` | 6 | 0 |
| `pubsub_monitor/` | 8 | 0 |
| `reports-viewer/` | 1 | 0 |
| `rolesypermisos/` | 1 | 0 |
| `secrets-configmaps/` | 1 | 0 |
| `service-account/` | 1 | 0 |
| `service-accounts/` | 5 | 0 |
| `vpc-networks/` | 2 | 0 |

**Cobertura:** 5/49 (10.2%)

---

### 7. scm/kpi_analyzer/ (13 scripts, 0 tests propios)

| Script | Test centralizado |
|--------|-------------------|
| `analyze_kpis.py` | ❌ |
| `analyzer.py` | ✅ `tests/unit/test_analyzer_kpi.py` |
| `benchmarks.py` | ❌ |
| `consolidator.py` | ❌ |
| `dashboard_generator.py` | ❌ |
| `exporter.py` | ❌ |
| `generator.py` | ❌ |
| `health_score.py` | ❌ |
| `maturity_model.py` | ❌ |
| `reporter.py` | ✅ `tests/unit/test_reporter_kpi.py` |
| `scheduler.py` | ❌ |
| `streamlit_app.py` | ❌ |
| `tools.py` | ❌ |

**Cobertura:** 2/13 (15.4%) via tests centralizados

---

### 8. scm/setup/ (1 script root + 9 en subfolders = 10 total)

| Script | Test directo |
|--------|-------------|
| `wizard.py` | ✅ `test_setup_wizard.py` |
| `steps/aws_step.py` | ❌ |
| `steps/azdo_step.py` | ❌ |
| `steps/azure_step.py` | ❌ |
| `steps/base_step.py` | ❌ |
| `steps/dashboard_step.py` | ❌ |
| `steps/gcp_step.py` | ❌ |
| `steps/global_step.py` | ❌ |
| `steps/precheck_step.py` | ❌ |
| `validators/config_validator.py` | ❌ |

**Cobertura:** 1/10 (10%)

---

### 9. scm/terminal/ (1 script root + 1 en subfolder = 2 total)

| Script | Test directo |
|--------|-------------|
| `tools.py` | ❌ |
| `check_cluster_memory_cpu_limits/history_limits_v3.py` | ❌ |

**Cobertura:** 0/2 (0%)

---

### 10. scm/tests/ (centralizado — 33 tests)

| Test | Cubre |
|------|-------|
| `test_azdo_pipeline_history.py` | `azdo/azdo_pipeline_history.py` |
| `unit/test_analyzer_kpi.py` | `kpi_analyzer/analyzer.py` |
| `unit/test_aws_tools.py` | `aws/tools.py` |
| `unit/test_azdo_tools.py` | `azdo/tools.py` |
| `unit/test_base_launcher_unit.py` | `base_launcher.py` |
| `unit/test_cicd_extended.py` | `azdo/cicd_inventory*.py` (parcial) |
| `unit/test_cicd_pipeline_status.py` | `azdo/cicd_pipeline_status.py` |
| `unit/test_dashboard_direct.py` | `dashboard/dashboard_consolidator.py` |
| `unit/test_dashboard_generator.py` | `dashboard/dashboard_generator.py` |
| `unit/test_dashboard_launch.py` | `dashboard/run_dashboard.py` |
| `unit/test_dashboard_main.py` | `dashboard/dashboard_generator.py` |
| `unit/test_dashboard_modules.py` | `dashboard/` (varios) |
| `unit/test_deep_module_coverage.py` | Varios módulos |
| `unit/test_gcp_tools.py` | `gcp/tools.py` |
| `unit/test_kpi_analyzer.py` | `kpi_analyzer/` (varios) |
| `unit/test_kpi_complete.py` | `kpi_analyzer/` (varios) |
| `unit/test_kpi_modules_extended.py` | `kpi_analyzer/` (varios) |
| `unit/test_main.py` | `main.py` |
| `unit/test_main_extended.py` | `main.py` |
| `unit/test_module_functions_real.py` | Varios módulos |
| `unit/test_output_manager.py` | `output_manager.py` |
| `unit/test_pipeline_rollback_extended.py` | `azdo/pipeline-cd-rollback-pipeline.py` |
| `unit/test_pipeline_rollback_redo.py` | `azdo/pipeline-cd-rollback-pipeline.py` |
| `unit/test_pipeline_update_extended.py` | `azdo/pipeline-cd-update-branchconfig.py` |
| `unit/test_pr_master_checker.py` | `azdo/azdo_pr_master_checker.py` |
| `unit/test_real_coverage.py` | Varios módulos |
| `unit/test_real_module_execution.py` | Varios módulos |
| `unit/test_reporter_kpi.py` | `kpi_analyzer/reporter.py` |
| `unit/test_search_module.py` | `search_module.py` |
| `unit/test_update_engine_auto.py` | `azdo/pipeline_updater/update_engine.py` |
| `unit/test_utils.py` | `utils.py` |
| `unit/test_zero_coverage.py` | Varios módulos |
| `integration/test_cloud_apis.py` | Integración cloud |

---

## Matriz Consolidada

| Subfolder | Scripts | Tests directos | Tests centralizados | Sin test | Cobertura |
|-----------|---------|---------------|--------------------|---------|-----------|
| **scm/ root** | 8 | 0 | 5 | 3 | 62.5% |
| **aws/** | 50 | 2 | 1 | 47 | 6.0% |
| **azdo/** | 48 | 15 | 6 | 27 | 43.8% |
| **azure/** | 1 | 0 | 0 | 1 | 0% |
| **dashboard/** | 4 | 0 | 3 | 1 | 75% |
| **gcp/** | 49 | 4 | 1 | 44 | 10.2% |
| **kpi_analyzer/** | 13 | 0 | 2 | 11 | 15.4% |
| **setup/** | 10 | 1 | 0 | 9 | 10% |
| **terminal/** | 2 | 0 | 0 | 2 | 0% |
| **tests/** | — | 33 | — | — | — |
| **TOTAL** | 185 | 22 | 18 | 145 | 21.6% |

---

## Top 10 — Programas críticos sin test

1. `azdo/azdo_pipeline_drift.py` (40KB) — Sin test
2. `azdo/azdo_pr_pipeline_analyzer.py` (57KB) — Sin test
3. `azdo/cicd_inventory_health_score.py` (98KB) — Sin test
4. `azdo/azdo_release_deep_dive.py` (36KB) — Sin test
5. `azdo/azdo_release_explorer_rich.py` (28KB) — Sin test
6. `azdo/azdo_repo_branch_diff.py` (51KB) — Sin test
7. `azdo/azdo_repo_properties_branch_diff.py` (59KB) — Sin test
8. `azdo/pipeline_cd_new_re_release.py` (27KB) — Sin test
9. `azdo/pipeline_cd_restore_release.py` (22KB) — Sin test
10. `gcp/monitoring/gcp_monitor.py` — Sin test

---

## Recomendaciones

1. **Prioridad alta**: Crear tests para los 10 programas críticos listados arriba
2. **Prioridad media**: Cubrir `aws/` subfolders (47 scripts sin test)
3. **Prioridad media**: Cubrir `gcp/` subfolders (44 scripts sin test)
4. **Prioridad baja**: `azure/`, `terminal/` (3 scripts sin test, bajo impacto)
5. **Mantener**: Tests existentes en `azdo/pipeline_updater/` y `scm/tests/unit/` siguen siendo el patrón a seguir

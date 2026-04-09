#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GCP Cloud Armor Checker

Herramienta SCM para auditar y analizar Security Policies (Cloud Armor) en Google Cloud Platform.
Proporciona validaciones de seguridad profesionales para identificar configuraciones de riesgo.

Funcionalidades:
- Listado de Security Policies con detalle de reglas
- Análisis de cobertura de backends
- Modo auditoría con validaciones automáticas
- Detección de configuraciones de riesgo
- Comparación entre proyectos
- Exportación CSV/JSON

Autor: Harold Adrian
Versión: 1.0.0
"""

import subprocess
import json
import argparse
import sys
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, List, Dict, Any, Tuple

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

__version__ = "1.0.0"

# Constantes
DEFAULT_PROJECT_ID = "cpl-xxxx-yyyy-zzzz-99999999"
DEFAULT_TIMEZONE = "America/Mazatlan"

# Reglas WAF preconfiguradas conocidas (OWASP ModSecurity CRS)
KNOWN_WAF_RULES = {
    "sqli": "SQL Injection",
    "xss": "Cross-Site Scripting",
    "lfi": "Local File Inclusion",
    "rfi": "Remote File Inclusion",
    "rce": "Remote Code Execution",
    "sessionfixation": "Session Fixation",
    "scannerdetection": "Scanner Detection",
    "protocolattack": "Protocol Attack",
    "php": "PHP Injection",
    "nodejs": "Node.js Attack",
    "cve": "Known CVEs"
}


def get_args():
    parser = argparse.ArgumentParser(
        description="SCM Tool: GCP Cloud Armor Security Audit",
        add_help=False
    )
    parser.add_argument(
        "--project", "-p",
        type=str,
        default=DEFAULT_PROJECT_ID,
        help=f"ID del proyecto de GCP (Default: {DEFAULT_PROJECT_ID})"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Activa modo debug para ver comandos gcloud ejecutados"
    )
    parser.add_argument(
        "--help", "-h",
        action="store_true",
        help="Muestra documentación completa del script"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        choices=["csv", "json"],
        help="Exporta resultados a archivo (csv o json) en carpeta outcome/"
    )
    parser.add_argument(
        "--timezone", "-tz",
        type=str,
        default=DEFAULT_TIMEZONE,
        help=f"Timezone para mostrar timestamps (default: {DEFAULT_TIMEZONE})"
    )
    parser.add_argument(
        "--view", "-v",
        type=str,
        choices=["all", "policies", "rules", "backends", "gaps"],
        default="all",
        help="Vista específica: policies, rules, backends, gaps (backends sin protección), all"
    )
    parser.add_argument(
        "--audit", "-a",
        action="store_true",
        help="Ejecuta auditoría completa de seguridad con validaciones automáticas"
    )
    parser.add_argument(
        "--compare", "-c",
        type=str,
        help="Compara configuración con otro proyecto GCP"
    )
    parser.add_argument(
        "--severity", "-s",
        type=str,
        choices=["all", "critical", "warning", "info"],
        default="all",
        help="Filtra hallazgos por severidad (solo en modo --audit)"
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        default=True,
        help="Ejecuta consultas en paralelo (default: activado)"
    )
    parser.add_argument(
        "--no-parallel",
        action="store_true",
        help="Desactiva ejecución paralela"
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=4,
        help="Número máximo de workers para ejecución paralela (default: 4)"
    )
    
    return parser.parse_args()


def show_help(console):
    """Muestra documentación completa desde README.md."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    readme_path = os.path.join(script_dir, "README.md")
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            from rich.markdown import Markdown
            md = Markdown(f.read())
            console.print(md)
    else:
        console.print("[yellow]README.md no encontrado[/]")
    sys.exit(0)


def run_gcloud_command(cmd: str, debug: bool, console) -> Optional[Any]:
    """Ejecuta comando gcloud y retorna JSON parseado."""
    if debug:
        console.print(f"[dim]DEBUG: {cmd}[/]")
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode != 0:
            if debug:
                console.print(f"[red]Error: {result.stderr}[/]")
            return None
        if result.stdout.strip():
            return json.loads(result.stdout)
        return []
    except subprocess.TimeoutExpired:
        console.print("[red]Timeout ejecutando comando[/]")
        return None
    except json.JSONDecodeError:
        return None
    except Exception as e:
        if debug:
            console.print(f"[red]Exception: {e}[/]")
        return None


def check_gcp_connection(project_id: str, console) -> bool:
    """Verifica conexión activa con GCP."""
    cmd = f'gcloud config get-value account 2>/dev/null'
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and result.stdout.strip():
            return True
        console.print("[red]❌ No hay sesión activa de gcloud. Ejecuta: gcloud auth login[/]")
        return False
    except Exception:
        console.print("[red]❌ Error verificando conexión GCP[/]")
        return False


def extract_name_from_url(url: str) -> str:
    """Extrae el nombre de un recurso desde su URL."""
    if not url:
        return "N/A"
    return url.split('/')[-1] if '/' in url else url


# ============ DATA COLLECTION ============

def get_security_policies(project_id: str, debug: bool, console) -> List[Dict]:
    """Obtiene todas las Security Policies (Cloud Armor)."""
    cmd = f'gcloud compute security-policies list --project={project_id} --format=json'
    return run_gcloud_command(cmd, debug, console) or []


def get_security_policy_details(project_id: str, policy_name: str, debug: bool, console) -> Optional[Dict]:
    """Obtiene detalles completos de una Security Policy."""
    cmd = f'gcloud compute security-policies describe {policy_name} --project={project_id} --format=json'
    return run_gcloud_command(cmd, debug, console)


def get_security_policy_rules(project_id: str, policy_name: str, debug: bool, console) -> List[Dict]:
    """Obtiene las reglas de una Security Policy."""
    cmd = f'gcloud compute security-policies rules list --security-policy={policy_name} --project={project_id} --format=json'
    return run_gcloud_command(cmd, debug, console) or []


def get_backend_services_global(project_id: str, debug: bool, console) -> List[Dict]:
    """Obtiene backend services globales."""
    cmd = f'gcloud compute backend-services list --global --project={project_id} --format=json'
    return run_gcloud_command(cmd, debug, console) or []


def get_backend_services_regional(project_id: str, debug: bool, console) -> List[Dict]:
    """Obtiene backend services regionales."""
    cmd = f'gcloud compute backend-services list --filter="region:*" --project={project_id} --format=json'
    return run_gcloud_command(cmd, debug, console) or []


def get_forwarding_rules_global(project_id: str, debug: bool, console) -> List[Dict]:
    """Obtiene forwarding rules globales (para identificar backends expuestos)."""
    cmd = f'gcloud compute forwarding-rules list --global --project={project_id} --format=json'
    return run_gcloud_command(cmd, debug, console) or []


# ============ ANALYSIS FUNCTIONS ============

def analyze_policy_rules(rules: List[Dict]) -> Dict[str, Any]:
    """Analiza las reglas de una política y extrae estadísticas."""
    analysis = {
        "total_rules": len(rules),
        "allow_rules": 0,
        "deny_rules": 0,
        "throttle_rules": 0,
        "redirect_rules": 0,
        "preview_rules": 0,
        "waf_rules": [],
        "rate_limit_rules": 0,
        "default_action": None,
        "priorities": []
    }
    
    for rule in rules:
        action = rule.get('action', '').lower()
        priority = rule.get('priority', 0)
        analysis['priorities'].append(priority)
        
        if action == 'allow':
            analysis['allow_rules'] += 1
        elif action == 'deny(403)' or action == 'deny(404)' or action == 'deny(502)' or 'deny' in action:
            analysis['deny_rules'] += 1
        elif action == 'throttle':
            analysis['throttle_rules'] += 1
        elif action == 'redirect':
            analysis['redirect_rules'] += 1
        
        if rule.get('preview'):
            analysis['preview_rules'] += 1
        
        if rule.get('rateLimitOptions'):
            analysis['rate_limit_rules'] += 1
        
        # Detectar reglas WAF preconfiguradas
        match = rule.get('match', {})
        expr = match.get('expr', {}).get('expression', '')
        if 'evaluatePreconfiguredWaf' in expr or 'evaluatePreconfiguredExpr' in expr:
            analysis['waf_rules'].append({
                'priority': priority,
                'expression': expr,
                'action': action
            })
        
        # Default rule (priority 2147483647)
        if priority == 2147483647:
            analysis['default_action'] = action
    
    return analysis


def identify_security_gaps(data: Dict) -> List[Dict]:
    """Identifica brechas de seguridad en la configuración."""
    findings = []
    
    all_backends = data.get('backend_services_global', []) + data.get('backend_services_regional', [])
    policies = data.get('security_policies', [])
    policy_names = [p.get('name') for p in policies]
    
    # Gap 1: Backends sin Security Policy
    for backend in all_backends:
        security_policy = backend.get('securityPolicy')
        if not security_policy:
            # Verificar si es un backend expuesto externamente
            load_balancing_scheme = backend.get('loadBalancingScheme', '')
            if load_balancing_scheme in ['EXTERNAL', 'EXTERNAL_MANAGED']:
                findings.append({
                    'severity': 'critical',
                    'resource': backend.get('name'),
                    'resource_type': 'backend_service',
                    'finding': 'Backend expuesto a Internet sin Cloud Armor',
                    'recommendation': f"Asociar Security Policy: gcloud compute backend-services update {backend.get('name')} --security-policy=POLICY_NAME --global"
                })
            else:
                findings.append({
                    'severity': 'warning',
                    'resource': backend.get('name'),
                    'resource_type': 'backend_service',
                    'finding': 'Backend sin Security Policy asociada',
                    'recommendation': 'Considerar agregar Cloud Armor para defensa en profundidad'
                })
    
    # Gap 2: Análisis de políticas
    for policy in policies:
        policy_name = policy.get('name')
        rules = data.get(f'rules_{policy_name}', [])
        analysis = analyze_policy_rules(rules)
        
        # Default rule permite todo
        if analysis['default_action'] and 'allow' in analysis['default_action'].lower():
            findings.append({
                'severity': 'critical',
                'resource': policy_name,
                'resource_type': 'security_policy',
                'finding': 'Default rule permite todo el tráfico (action=allow)',
                'recommendation': 'Cambiar default rule a deny(403) y agregar reglas allow específicas'
            })
        
        # Sin reglas WAF preconfiguradas
        if not analysis['waf_rules']:
            findings.append({
                'severity': 'warning',
                'resource': policy_name,
                'resource_type': 'security_policy',
                'finding': 'Sin reglas WAF preconfiguradas (OWASP CRS)',
                'recommendation': 'Agregar reglas: evaluatePreconfiguredWaf("sqli-v33-stable"), evaluatePreconfiguredWaf("xss-v33-stable")'
            })
        
        # Sin rate limiting
        if analysis['rate_limit_rules'] == 0:
            findings.append({
                'severity': 'warning',
                'resource': policy_name,
                'resource_type': 'security_policy',
                'finding': 'Sin reglas de rate limiting configuradas',
                'recommendation': 'Considerar agregar throttle rules para prevenir ataques de fuerza bruta'
            })
        
        # Reglas en preview en producción
        if analysis['preview_rules'] > 0:
            findings.append({
                'severity': 'info',
                'resource': policy_name,
                'resource_type': 'security_policy',
                'finding': f"{analysis['preview_rules']} regla(s) en modo preview",
                'recommendation': 'Revisar y activar reglas en preview si ya fueron validadas'
            })
        
        # Adaptive Protection
        adaptive = policy.get('adaptiveProtectionConfig', {})
        if not adaptive.get('layer7DdosDefenseConfig', {}).get('enable'):
            findings.append({
                'severity': 'warning',
                'resource': policy_name,
                'resource_type': 'security_policy',
                'finding': 'Adaptive Protection (L7 DDoS) deshabilitado',
                'recommendation': 'Habilitar: gcloud compute security-policies update POLICY --enable-layer7-ddos-defense'
            })
    
    return findings


# ============ TABLE CREATION ============

def create_policies_table(policies: List[Dict], data: Dict, console) -> Table:
    """Crea tabla de Security Policies."""
    table = Table(
        title="🛡️ Security Policies (Cloud Armor)",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )
    
    table.add_column("#", style="dim", width=3)
    table.add_column("Policy Name", style="cyan")
    table.add_column("Type", style="yellow")
    table.add_column("Rules", style="green", justify="right")
    table.add_column("WAF Rules", style="magenta", justify="right")
    table.add_column("Default", style="white")
    table.add_column("Adaptive", style="blue")
    table.add_column("Backends", style="green", justify="right")
    
    all_backends = data.get('backend_services_global', []) + data.get('backend_services_regional', [])
    
    for idx, policy in enumerate(policies, 1):
        name = policy.get('name', 'N/A')
        policy_type = policy.get('type', 'CLOUD_ARMOR')
        
        # Contar reglas y WAF
        rules = data.get(f'rules_{name}', [])
        analysis = analyze_policy_rules(rules)
        
        default_action = analysis['default_action'] or 'N/A'
        if 'deny' in default_action.lower():
            default_display = f"[green]{default_action}[/green]"
        else:
            default_display = f"[red]{default_action}[/red]"
        
        # Adaptive Protection
        adaptive = policy.get('adaptiveProtectionConfig', {})
        l7_defense = adaptive.get('layer7DdosDefenseConfig', {}).get('enable', False)
        adaptive_display = "[green]✓[/green]" if l7_defense else "[red]✗[/red]"
        
        # Contar backends asociados
        backend_count = sum(1 for b in all_backends if name in str(b.get('securityPolicy', '')))
        
        table.add_row(
            str(idx),
            name,
            policy_type,
            str(analysis['total_rules']),
            str(len(analysis['waf_rules'])),
            default_display,
            adaptive_display,
            str(backend_count)
        )
    
    return table


def create_rules_table(policy_name: str, rules: List[Dict], console) -> Table:
    """Crea tabla de reglas de una política."""
    table = Table(
        title=f"📋 Rules: {policy_name}",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )
    
    table.add_column("Priority", style="cyan", justify="right", width=10)
    table.add_column("Action", style="yellow", width=12)
    table.add_column("Match", style="white", max_width=50)
    table.add_column("Rate Limit", style="blue", width=12)
    table.add_column("Preview", style="magenta", width=8)
    table.add_column("Description", style="dim", max_width=30)
    
    # Ordenar por prioridad
    sorted_rules = sorted(rules, key=lambda x: x.get('priority', 0))
    
    for rule in sorted_rules:
        priority = rule.get('priority', 0)
        action = rule.get('action', 'N/A')
        
        # Formatear match
        match = rule.get('match', {})
        if match.get('versionedExpr') == 'SRC_IPS_V1':
            match_display = f"IPs: {', '.join(match.get('config', {}).get('srcIpRanges', []))[:40]}..."
        elif match.get('expr'):
            expr = match.get('expr', {}).get('expression', '')[:45]
            match_display = f"Expr: {expr}..."
        else:
            match_display = "N/A"
        
        # Rate limit
        rate_limit = rule.get('rateLimitOptions')
        if rate_limit:
            rate_display = f"{rate_limit.get('rateLimitThreshold', {}).get('count', '-')}/min"
        else:
            rate_display = "-"
        
        preview = "[yellow]Preview[/yellow]" if rule.get('preview') else "-"
        description = (rule.get('description', '') or '-')[:28]
        
        # Color por action
        if 'deny' in action.lower():
            action_display = f"[red]{action}[/red]"
        elif action.lower() == 'allow':
            action_display = f"[green]{action}[/green]"
        elif action.lower() == 'throttle':
            action_display = f"[yellow]{action}[/yellow]"
        else:
            action_display = action
        
        # Highlight default rule
        if priority == 2147483647:
            priority_display = "[bold]DEFAULT[/bold]"
        else:
            priority_display = str(priority)
        
        table.add_row(
            priority_display,
            action_display,
            match_display,
            rate_display,
            preview,
            description
        )
    
    return table


def create_backends_coverage_table(data: Dict, console) -> Table:
    """Crea tabla de cobertura de backends."""
    table = Table(
        title="🔌 Backend Services - Cloud Armor Coverage",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )
    
    table.add_column("#", style="dim", width=3)
    table.add_column("Backend Service", style="cyan")
    table.add_column("Scope", style="blue")
    table.add_column("LB Scheme", style="yellow")
    table.add_column("Security Policy", style="green")
    table.add_column("CDN", style="magenta")
    table.add_column("IAP", style="white")
    table.add_column("Status", style="bold")
    
    all_backends = data.get('backend_services_global', []) + data.get('backend_services_regional', [])
    
    for idx, backend in enumerate(sorted(all_backends, key=lambda x: x.get('name', '')), 1):
        name = backend.get('name', 'N/A')
        
        # Determinar scope
        if 'region' in str(backend.get('selfLink', '')):
            scope = "Regional"
        else:
            scope = "Global"
        
        lb_scheme = backend.get('loadBalancingScheme', 'N/A')
        
        # Security Policy
        security_policy = extract_name_from_url(backend.get('securityPolicy', ''))
        if security_policy and security_policy != 'N/A':
            policy_display = f"[green]{security_policy}[/green]"
            status = "[green]✅ Protected[/green]"
        else:
            policy_display = "[dim]None[/dim]"
            if lb_scheme in ['EXTERNAL', 'EXTERNAL_MANAGED']:
                status = "[red]🔴 EXPOSED[/red]"
            else:
                status = "[yellow]⚠️ Unprotected[/yellow]"
        
        cdn = "[green]✓[/green]" if backend.get('enableCDN') else "[dim]✗[/dim]"
        iap = "[green]✓[/green]" if backend.get('iap', {}).get('enabled') else "[dim]✗[/dim]"
        
        table.add_row(
            str(idx),
            name,
            scope,
            lb_scheme,
            policy_display,
            cdn,
            iap,
            status
        )
    
    return table


def create_findings_table(findings: List[Dict], severity_filter: str, console) -> Table:
    """Crea tabla de hallazgos de auditoría."""
    table = Table(
        title="🔍 Security Audit Findings",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )
    
    table.add_column("Sev", style="bold", width=4)
    table.add_column("Resource", style="cyan", width=25)
    table.add_column("Type", style="blue", width=15)
    table.add_column("Finding", style="white", max_width=45)
    
    severity_icons = {
        'critical': '🔴',
        'warning': '🟡',
        'info': '🔵'
    }
    
    severity_order = {'critical': 0, 'warning': 1, 'info': 2}
    sorted_findings = sorted(findings, key=lambda x: severity_order.get(x['severity'], 3))
    
    for finding in sorted_findings:
        sev = finding['severity']
        
        if severity_filter != 'all' and sev != severity_filter:
            continue
        
        icon = severity_icons.get(sev, '❓')
        table.add_row(
            icon,
            finding['resource'][:23],
            finding['resource_type'],
            finding['finding'][:43]
        )
    
    return table


def create_summary_panel(data: Dict, findings: List[Dict], console) -> Panel:
    """Crea panel de resumen ejecutivo."""
    policies = data.get('security_policies', [])
    all_backends = data.get('backend_services_global', []) + data.get('backend_services_regional', [])
    
    protected_backends = sum(1 for b in all_backends if b.get('securityPolicy'))
    total_backends = len(all_backends)
    coverage_pct = (protected_backends / total_backends * 100) if total_backends > 0 else 0
    
    external_backends = [b for b in all_backends if b.get('loadBalancingScheme') in ['EXTERNAL', 'EXTERNAL_MANAGED']]
    external_protected = sum(1 for b in external_backends if b.get('securityPolicy'))
    
    critical_count = sum(1 for f in findings if f['severity'] == 'critical')
    warning_count = sum(1 for f in findings if f['severity'] == 'warning')
    info_count = sum(1 for f in findings if f['severity'] == 'info')
    
    # Contar WAF rules totales
    total_waf_rules = 0
    adaptive_enabled = 0
    for policy in policies:
        rules = data.get(f"rules_{policy.get('name')}", [])
        analysis = analyze_policy_rules(rules)
        total_waf_rules += len(analysis['waf_rules'])
        if policy.get('adaptiveProtectionConfig', {}).get('layer7DdosDefenseConfig', {}).get('enable'):
            adaptive_enabled += 1
    
    summary_text = f"""[bold]📊 Coverage[/bold]
Backends: {protected_backends}/{total_backends} ({coverage_pct:.0f}%) con Cloud Armor
External: {external_protected}/{len(external_backends)} backends externos protegidos

[bold]🛡️ Policies[/bold]
Total: {len(policies)} | WAF Rules: {total_waf_rules} | Adaptive Protection: {adaptive_enabled}/{len(policies)}

[bold]🔍 Findings[/bold]
🔴 Critical: {critical_count} | 🟡 Warning: {warning_count} | 🔵 Info: {info_count}"""
    
    return Panel(summary_text, title="📈 Resumen Ejecutivo", border_style="cyan")


def create_comparison_table(data_a: Dict, data_b: Dict, project_a: str, project_b: str, console) -> Table:
    """Crea tabla de comparación entre proyectos."""
    table = Table(
        title=f"⚖️ Comparación: {project_a} vs {project_b}",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )
    
    table.add_column("Métrica", style="white")
    table.add_column(project_a[:20], style="cyan", justify="right")
    table.add_column(project_b[:20], style="yellow", justify="right")
    table.add_column("Match", style="bold", justify="center")
    
    def get_icon(a, b):
        return "[green]✓[/green]" if a == b else "[yellow]⚠[/yellow]"
    
    # Security Policies
    sp_a = len(data_a.get('security_policies', []))
    sp_b = len(data_b.get('security_policies', []))
    table.add_row("Security Policies", str(sp_a), str(sp_b), get_icon(sp_a, sp_b))
    
    # Backends
    bs_a = data_a.get('backend_services_global', []) + data_a.get('backend_services_regional', [])
    bs_b = data_b.get('backend_services_global', []) + data_b.get('backend_services_regional', [])
    
    protected_a = sum(1 for b in bs_a if b.get('securityPolicy'))
    protected_b = sum(1 for b in bs_b if b.get('securityPolicy'))
    
    pct_a = f"{(protected_a/len(bs_a)*100):.0f}%" if bs_a else "0%"
    pct_b = f"{(protected_b/len(bs_b)*100):.0f}%" if bs_b else "0%"
    
    table.add_row("Backends Totales", str(len(bs_a)), str(len(bs_b)), get_icon(len(bs_a), len(bs_b)))
    table.add_row("Backends Protegidos", str(protected_a), str(protected_b), get_icon(protected_a, protected_b))
    table.add_row("Cobertura %", pct_a, pct_b, get_icon(pct_a, pct_b))
    
    return table


# ============ EXPORT FUNCTIONS ============

def export_to_json(data: Dict, findings: List[Dict], project_id: str, timezone_str: str, console):
    """Exporta datos a JSON."""
    outcome_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outcome")
    os.makedirs(outcome_dir, exist_ok=True)
    
    tz = ZoneInfo(timezone_str)
    now = datetime.now(tz)
    filename = f"cloud_armor_audit_{project_id}_{now.strftime('%Y%m%d_%H%M%S')}.json"
    filepath = os.path.join(outcome_dir, filename)
    
    export_data = {
        "metadata": {
            "project": project_id,
            "timestamp": now.isoformat(),
            "timezone": timezone_str,
            "version": __version__
        },
        "security_policies": data.get('security_policies', []),
        "backend_services": {
            "global": data.get('backend_services_global', []),
            "regional": data.get('backend_services_regional', [])
        },
        "audit_findings": findings,
        "summary": {
            "total_policies": len(data.get('security_policies', [])),
            "total_backends": len(data.get('backend_services_global', [])) + len(data.get('backend_services_regional', [])),
            "findings_critical": sum(1 for f in findings if f['severity'] == 'critical'),
            "findings_warning": sum(1 for f in findings if f['severity'] == 'warning'),
            "findings_info": sum(1 for f in findings if f['severity'] == 'info')
        }
    }
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)
    
    console.print(f"\n[green]📁 Exportado:[/green] {filepath}")


def export_to_csv(data: Dict, findings: List[Dict], project_id: str, timezone_str: str, console):
    """Exporta hallazgos a CSV."""
    import csv
    
    outcome_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outcome")
    os.makedirs(outcome_dir, exist_ok=True)
    
    tz = ZoneInfo(timezone_str)
    now = datetime.now(tz)
    filename = f"cloud_armor_audit_{project_id}_{now.strftime('%Y%m%d_%H%M%S')}.csv"
    filepath = os.path.join(outcome_dir, filename)
    
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['project', 'severity', 'resource', 'resource_type', 'finding', 'recommendation', 'timestamp'])
        
        for finding in findings:
            writer.writerow([
                project_id,
                finding['severity'],
                finding['resource'],
                finding['resource_type'],
                finding['finding'],
                finding.get('recommendation', ''),
                now.isoformat()
            ])
    
    console.print(f"\n[green]📁 Exportado:[/green] {filepath}")


# ============ MAIN ============

def main():
    if not RICH_AVAILABLE:
        print("Error: La librería 'rich' es requerida. Instala con: pip install rich")
        sys.exit(1)
    
    console = Console()
    args = get_args()
    
    if args.help:
        show_help(console)
    
    project_id = args.project
    debug = args.debug
    view = args.view
    timezone_str = args.timezone
    parallel = args.parallel and not args.no_parallel
    max_workers = args.max_workers
    
    # Verificar conexión
    if not check_gcp_connection(project_id, console):
        sys.exit(1)
    
    # Header
    tz = ZoneInfo(timezone_str)
    now = datetime.now(tz)
    
    console.print(Panel(
        f"[bold cyan]🛡️ Cloud Armor Security Audit[/bold cyan]\n"
        f"📌 Project: [yellow]{project_id}[/yellow]\n"
        f"🕐 {now.strftime('%Y-%m-%d %H:%M:%S')} ({timezone_str})",
        border_style="cyan"
    ))
    
    # Recolectar datos
    data = {}
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Recolectando datos de Cloud Armor...", total=None)
        
        if parallel:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(get_security_policies, project_id, debug, console): 'security_policies',
                    executor.submit(get_backend_services_global, project_id, debug, console): 'backend_services_global',
                    executor.submit(get_backend_services_regional, project_id, debug, console): 'backend_services_regional',
                    executor.submit(get_forwarding_rules_global, project_id, debug, console): 'forwarding_rules_global',
                }
                
                for future in as_completed(futures):
                    key = futures[future]
                    data[key] = future.result() or []
        else:
            data['security_policies'] = get_security_policies(project_id, debug, console)
            data['backend_services_global'] = get_backend_services_global(project_id, debug, console)
            data['backend_services_regional'] = get_backend_services_regional(project_id, debug, console)
            data['forwarding_rules_global'] = get_forwarding_rules_global(project_id, debug, console)
        
        # Obtener reglas de cada política
        for policy in data.get('security_policies', []):
            policy_name = policy.get('name')
            if policy_name:
                rules = get_security_policy_rules(project_id, policy_name, debug, console)
                data[f'rules_{policy_name}'] = rules
        
        progress.update(task, completed=True)
    
    # Ejecutar auditoría
    findings = identify_security_gaps(data)
    
    console.print()
    
    # Mostrar tablas según vista
    if view in ['all', 'policies']:
        if data.get('security_policies'):
            console.print(create_policies_table(data['security_policies'], data, console))
            console.print()
        else:
            console.print("[yellow]⚠️ No se encontraron Security Policies en este proyecto[/yellow]\n")
    
    if view in ['all', 'rules']:
        for policy in data.get('security_policies', []):
            policy_name = policy.get('name')
            rules = data.get(f'rules_{policy_name}', [])
            if rules:
                console.print(create_rules_table(policy_name, rules, console))
                console.print()
    
    if view in ['all', 'backends', 'gaps']:
        console.print(create_backends_coverage_table(data, console))
        console.print()
    
    # Mostrar hallazgos (siempre en audit mode, o si hay hallazgos críticos)
    if args.audit or any(f['severity'] == 'critical' for f in findings):
        console.print(create_findings_table(findings, args.severity, console))
        console.print()
    
    # Resumen ejecutivo
    console.print(create_summary_panel(data, findings, console))
    
    # Comparación con otro proyecto
    if args.compare:
        console.print(f"\n[cyan]Obteniendo datos de {args.compare}...[/cyan]")
        data_b = {}
        data_b['security_policies'] = get_security_policies(args.compare, debug, console)
        data_b['backend_services_global'] = get_backend_services_global(args.compare, debug, console)
        data_b['backend_services_regional'] = get_backend_services_regional(args.compare, debug, console)
        
        console.print()
        console.print(create_comparison_table(data, data_b, project_id, args.compare, console))
    
    # Exportar
    if args.output == 'json':
        export_to_json(data, findings, project_id, timezone_str, console)
    elif args.output == 'csv':
        export_to_csv(data, findings, project_id, timezone_str, console)
    
    # Tip final
    if not args.audit and findings:
        console.print(f"\n[dim]Tip: Usa --audit para ver todas las recomendaciones de seguridad[/dim]")


if __name__ == "__main__":
    main()

"""
Dashboard HTML Generator for GCP Gateway Services Checker.

Genera un dashboard HTML interactivo en un solo archivo con todos los
recursos escaneados (Gateways, HTTPRoutes, Services, Policies, Duplicates).
Usa los datos en memoria y opcionalmente los JSON de salida.
"""

import json
import os
from datetime import datetime
from html import escape


def generate_dashboard(all_results, project_id, revision_time, output_path, clusters_scanned=None):
    """Genera un dashboard HTML interactivo en un solo archivo.

    Args:
        all_results: dict con keys 'gateways', 'routes', 'services', 'policies', 'duplicates'
        project_id: ID del proyecto GCP escaneado
        revision_time: string con fecha/hora de revision
        output_path: ruta completa del archivo HTML a generar
        clusters_scanned: lista de nombres de clusters escaneados
    """
    gateways = all_results.get('gateways', [])
    routes = all_results.get('routes', [])
    services = all_results.get('services', [])
    policies = all_results.get('policies', [])
    duplicates = all_results.get('duplicates', [])

    gw_healthy = sum(1 for g in gateways if g.get('status') == 'Healthy')
    gw_unhealthy = sum(1 for g in gateways if g.get('status') == 'Unhealthy')
    gw_other = len(gateways) - gw_healthy - gw_unhealthy

    rt_healthy = sum(1 for r in routes if r.get('has_gateway') and r.get('rules_count', 0) > 0)
    rt_no_gw = sum(1 for r in routes if not r.get('has_gateway'))

    svc_healthy = sum(1 for s in services if s.get('status') == 'OK' and s.get('pods_ready', 0) == s.get('pods_total', 0) and s.get('pods_total', 0) > 0)
    svc_degraded = sum(1 for s in services if s.get('status') == 'OK' and s.get('pods_ready', 0) < s.get('pods_total', 0) and s.get('pods_total', 0) > 0)
    svc_no_pods = sum(1 for s in services if s.get('pods_total', 0) == 0)

    dup_critical = sum(1 for d in duplicates if d.get('severity') == 'CRITICAL')
    dup_high = sum(1 for d in duplicates if d.get('severity') == 'HIGH')
    dup_medium = sum(1 for d in duplicates if d.get('severity') == 'MEDIUM')

    clusters_list = clusters_scanned or sorted(set(
        g.get('cluster', '') for g in gateways
        if g.get('cluster')
    ) | set(
        r.get('cluster', '') for r in routes
        if r.get('cluster')
    ) | set(
        s.get('cluster', '') for s in services
        if s.get('cluster')
    ))

    html = _build_html(
        project_id=project_id,
        revision_time=revision_time,
        gateways=gateways, routes=routes, services=services, policies=policies, duplicates=duplicates,
        gw_healthy=gw_healthy, gw_unhealthy=gw_unhealthy, gw_other=gw_other,
        rt_healthy=rt_healthy, rt_no_gw=rt_no_gw,
        svc_healthy=svc_healthy, svc_degraded=svc_degraded, svc_no_pods=svc_no_pods,
        dup_critical=dup_critical, dup_high=dup_high, dup_medium=dup_medium,
        clusters_list=clusters_list,
    )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    return output_path


def _build_html(**ctx):
    project_id = ctx['project_id']
    revision_time = ctx['revision_time']
    gateways = ctx['gateways']
    routes = ctx['routes']
    services = ctx['services']
    policies = ctx['policies']
    duplicates = ctx['duplicates']
    clusters_list = ctx['clusters_list']

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Gateway Services Dashboard - {escape(project_id)}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Oxygen,Ubuntu,sans-serif;background:#0f172a;color:#e2e8f0;min-height:100vh;}}
.header{{background:linear-gradient(135deg,#1e293b 0%,#334155 100%);padding:24px 32px;border-bottom:1px solid #475569;}}
.header h1{{font-size:1.75rem;color:#38bdf8;display:flex;align-items:center;gap:10px;}}
.header .meta{{display:flex;gap:24px;margin-top:12px;flex-wrap:wrap;font-size:.875rem;color:#94a3b8;}}
.header .meta span{{display:flex;align-items:center;gap:6px;}}
.header .badge{{background:#1e293b;border:1px solid #475569;padding:4px 12px;border-radius:20px;font-size:.75rem;color:#38bdf8;}}
.container{{max-width:1400px;margin:0 auto;padding:24px;}}
.section{{margin-bottom:32px;}}
.section-title{{font-size:1.25rem;font-weight:600;margin-bottom:16px;display:flex;align-items:center;gap:8px;color:#f1f5f9;}}
.section-title .count{{background:#334155;color:#94a3b8;padding:2px 10px;border-radius:12px;font-size:.75rem;font-weight:400;}}

.cards{{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:16px;margin-bottom:32px;}}
.card{{background:#1e293b;border:1px solid #334155;border-radius:12px;padding:20px;transition:transform .15s,border-color .15s;}}
.card:hover{{transform:translateY(-2px);border-color:#475569;}}
.card .icon{{font-size:1.75rem;margin-bottom:8px;}}
.card .label{{font-size:.75rem;color:#94a3b8;text-transform:uppercase;letter-spacing:.5px;}}
.card .value{{font-size:2rem;font-weight:700;margin-top:4px;}}
.card.green .value{{color:#4ade80;}}
.card.red .value{{color:#f87171;}}
.card.yellow .value{{color:#facc15;}}
.card.blue .value{{color:#60a5fa;}}
.card.purple .value{{color:#c084fc;}}
.card .sub{{font-size:.75rem;color:#64748b;margin-top:6px;}}

.tabs{{display:flex;gap:4px;margin-bottom:16px;border-bottom:2px solid #334155;flex-wrap:wrap;}}
.tab{{padding:10px 20px;background:none;border:none;color:#94a3b8;cursor:pointer;font-size:.875rem;font-weight:500;border-bottom:2px solid transparent;margin-bottom:-2px;transition:color .15s,border-color .15s;}}
.tab:hover{{color:#e2e8f0;}}
.tab.active{{color:#38bdf8;border-bottom-color:#38bdf8;}}
.tab .badge-num{{background:#334155;padding:1px 8px;border-radius:10px;font-size:.7rem;margin-left:6px;}}
.tab.active .badge-num{{background:#0ea5e9;color:#0f172a;}}
.tab-content{{display:none;}}
.tab-content.active{{display:block;}}

table{{width:100%;border-collapse:collapse;font-size:.8125rem;}}
thead th{{text-align:left;padding:10px 14px;background:#1e293b;color:#94a3b8;font-weight:600;border-bottom:1px solid #334155;position:sticky;top:0;cursor:pointer;user-select:none;white-space:nowrap;}}
thead th:hover{{color:#38bdf8;}}
thead th .sort-arrow{{font-size:.6rem;margin-left:4px;opacity:.4;}}
tbody td{{padding:8px 14px;border-bottom:1px solid #1e293b;color:#cbd5e1;}}
tbody tr:hover{{background:#1e293b;}}
.table-wrap{{overflow-x:auto;border-radius:8px;border:1px solid #334155;}}

.pill{{display:inline-block;padding:2px 10px;border-radius:12px;font-size:.7rem;font-weight:600;}}
.pill-green{{background:#064e3b;color:#4ade80;}}
.pill-red{{background:#7f1d1d;color:#f87171;}}
.pill-yellow{{background:#78350f;color:#facc15;}}
.pill-blue{{background:#1e3a5f;color:#60a5fa;}}
.pill-gray{{background:#334155;color:#94a3b8;}}
.pill-critical{{background:#7f1d1d;color:#fff;font-weight:700;}}
.pill-high{{background:#78350f;color:#fff;font-weight:700;}}
.pill-medium{{background:#1e3a5f;color:#fff;font-weight:700;}}

.search-box{{margin-bottom:16px;}}
.search-box input{{width:100%;padding:10px 16px;background:#1e293b;border:1px solid #334155;border-radius:8px;color:#e2e8f0;font-size:.875rem;outline:none;}}
.search-box input:focus{{border-color:#38bdf8;}}
.search-box input::placeholder{{color:#64748b;}}

.empty{{text-align:center;padding:40px;color:#64748b;font-style:italic;}}
.footer{{text-align:center;padding:24px;color:#475569;font-size:.75rem;border-top:1px solid #334155;margin-top:32px;}}

.cluster-filter{{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px;}}
.cluster-chip{{padding:4px 14px;border-radius:20px;font-size:.75rem;cursor:pointer;border:1px solid #334155;background:#1e293b;color:#94a3b8;transition:all .15s;}}
.cluster-chip:hover{{border-color:#475569;}}
.cluster-chip.active{{background:#0ea5e9;color:#0f172a;border-color:#0ea5e9;font-weight:600;}}

@media(max-width:768px){{.cards{{grid-template-columns:1fr 1fr;}}.header h1{{font-size:1.25rem;}}}}
</style>
</head>
<body>

<div class="header">
  <h1>🌐 Gateway Services Dashboard</h1>
  <div class="meta">
    <span>📦 <strong>Proyecto:</strong> {escape(project_id)}</span>
    <span>🕐 <strong>Revisión:</strong> {escape(revision_time)}</span>
    <span>☸️ <strong>Clusters:</strong> {len(clusters_list)}</span>
    <span class="badge">v2.3.0</span>
  </div>
</div>

<div class="container">

  <div class="cards">
    <div class="card green"><div class="icon">🚪</div><div class="label">Gateways Healthy</div><div class="value">{ctx['gw_healthy']}</div><div class="sub">Unhealthy: {ctx['gw_unhealthy']} · Other: {ctx['gw_other']} · Total: {len(gateways)}</div></div>
    <div class="card blue"><div class="icon">🛤️</div><div class="label">HTTPRoutes Healthy</div><div class="value">{ctx['rt_healthy']}</div><div class="sub">No Gateway: {ctx['rt_no_gw']} · Total: {len(routes)}</div></div>
    <div class="card purple"><div class="icon">🔌</div><div class="label">Services Healthy</div><div class="value">{ctx['svc_healthy']}</div><div class="sub">Degraded: {ctx['svc_degraded']} · No Pods: {ctx['svc_no_pods']} · Total: {len(services)}</div></div>
    <div class="card yellow"><div class="icon">📋</div><div class="label">Policies</div><div class="value">{len(policies)}</div><div class="sub">Health Check + Backend</div></div>
    <div class="card red"><div class="icon">🚨</div><div class="label">Duplicates CRITICAL</div><div class="value">{ctx['dup_critical']}</div><div class="sub">High: {ctx['dup_high']} · Medium: {ctx['dup_medium']} · Total: {len(duplicates)}</div></div>
  </div>

  <div class="tabs">
    <button class="tab active" onclick="showTab('gateways')">🚪 Gateways <span class="badge-num">{len(gateways)}</span></button>
    <button class="tab" onclick="showTab('routes')">🛤️ HTTPRoutes <span class="badge-num">{len(routes)}</span></button>
    <button class="tab" onclick="showTab('services')">🔌 Services <span class="badge-num">{len(services)}</span></button>
    <button class="tab" onclick="showTab('policies')">📋 Policies <span class="badge-num">{len(policies)}</span></button>
    <button class="tab" onclick="showTab('duplicates')">🚨 Duplicates <span class="badge-num">{len(duplicates)}</span></button>
  </div>

  <div id="tab-gateways" class="tab-content active">
    <div class="search-box"><input type="text" placeholder="Buscar gateway..." onkeyup="filterTable('gw-table',this.value)"></div>
    <div class="table-wrap">
      <table id="gw-table"><thead><tr>
        <th onclick="sortTable('gw-table',0)">Cluster<span class="sort-arrow">▼</span></th>
        <th onclick="sortTable('gw-table',1)">Name<span class="sort-arrow"></span></th>
        <th onclick="sortTable('gw-table',2)">Namespace<span class="sort-arrow"></span></th>
        <th onclick="sortTable('gw-table',3)">Status<span class="sort-arrow"></span></th>
        <th onclick="sortTable('gw-table',4)">Class<span class="sort-arrow"></span></th>
        <th onclick="sortTable('gw-table',5)">Type<span class="sort-arrow"></span></th>
        <th onclick="sortTable('gw-table',6)">Load Balancer<span class="sort-arrow"></span></th>
        <th onclick="sortTable('gw-table',7)">IP Addresses<span class="sort-arrow"></span></th>
        <th onclick="sortTable('gw-table',8)">Ports<span class="sort-arrow"></span></th>
      </tr></thead><tbody>
{_render_gateway_rows(gateways)}
      </tbody></table>
    </div>
  </div>

  <div id="tab-routes" class="tab-content">
    <div class="search-box"><input type="text" placeholder="Buscar httproute..." onkeyup="filterTable('rt-table',this.value)"></div>
    <div class="table-wrap">
      <table id="rt-table"><thead><tr>
        <th onclick="sortTable('rt-table',0)">Cluster<span class="sort-arrow"></span></th>
        <th onclick="sortTable('rt-table',1)">Name<span class="sort-arrow"></span></th>
        <th onclick="sortTable('rt-table',2)">Namespace<span class="sort-arrow"></span></th>
        <th onclick="sortTable('rt-table',3)">Hostnames<span class="sort-arrow"></span></th>
        <th onclick="sortTable('rt-table',4)">Date Created<span class="sort-arrow"></span></th>
        <th onclick="sortTable('rt-table',5)">Rules<span class="sort-arrow"></span></th>
        <th onclick="sortTable('rt-table',6)">Attached Gateways<span class="sort-arrow"></span></th>
        <th onclick="sortTable('rt-table',7)">Status<span class="sort-arrow"></span></th>
      </tr></thead><tbody>
{_render_route_rows(routes)}
      </tbody></table>
    </div>
  </div>

  <div id="tab-services" class="tab-content">
    <div class="search-box"><input type="text" placeholder="Buscar service..." onkeyup="filterTable('svc-table',this.value)"></div>
    <div class="table-wrap">
      <table id="svc-table"><thead><tr>
        <th onclick="sortTable('svc-table',0)">Cluster<span class="sort-arrow"></span></th>
        <th onclick="sortTable('svc-table',1)">Name<span class="sort-arrow"></span></th>
        <th onclick="sortTable('svc-table',2)">Namespace<span class="sort-arrow"></span></th>
        <th onclick="sortTable('svc-table',3)">Status<span class="sort-arrow"></span></th>
        <th onclick="sortTable('svc-table',4)">Type<span class="sort-arrow"></span></th>
        <th onclick="sortTable('svc-table',5)">Endpoints<span class="sort-arrow"></span></th>
        <th onclick="sortTable('svc-table',6)">Pods<span class="sort-arrow"></span></th>
      </tr></thead><tbody>
{_render_service_rows(services)}
      </tbody></table>
    </div>
  </div>

  <div id="tab-policies" class="tab-content">
    <div class="search-box"><input type="text" placeholder="Buscar policy..." onkeyup="filterTable('pol-table',this.value)"></div>
    <div class="table-wrap">
      <table id="pol-table"><thead><tr>
        <th onclick="sortTable('pol-table',0)">Cluster<span class="sort-arrow"></span></th>
        <th onclick="sortTable('pol-table',1)">Name<span class="sort-arrow"></span></th>
        <th onclick="sortTable('pol-table',2)">Namespace<span class="sort-arrow"></span></th>
        <th onclick="sortTable('pol-table',3)">Kind<span class="sort-arrow"></span></th>
        <th onclick="sortTable('pol-table',4)">Policy Type<span class="sort-arrow"></span></th>
        <th onclick="sortTable('pol-table',5)">Target Kind<span class="sort-arrow"></span></th>
        <th onclick="sortTable('pol-table',6)">Target Name<span class="sort-arrow"></span></th>
        <th onclick="sortTable('pol-table',7)">Status<span class="sort-arrow"></span></th>
        <th onclick="sortTable('pol-table',8)">Date Created<span class="sort-arrow"></span></th>
      </tr></thead><tbody>
{_render_policy_rows(policies)}
      </tbody></table>
    </div>
  </div>

  <div id="tab-duplicates" class="tab-content">
    <div class="search-box"><input type="text" placeholder="Buscar conflicto..." onkeyup="filterTable('dup-table',this.value)"></div>
    <div class="table-wrap">
      <table id="dup-table"><thead><tr>
        <th onclick="sortTable('dup-table',0)">Severity<span class="sort-arrow"></span></th>
        <th onclick="sortTable('dup-table',1)">Cluster<span class="sort-arrow"></span></th>
        <th onclick="sortTable('dup-table',2)">Gateway<span class="sort-arrow"></span></th>
        <th onclick="sortTable('dup-table',3)">Listener<span class="sort-arrow"></span></th>
        <th onclick="sortTable('dup-table',4)">Hostname<span class="sort-arrow"></span></th>
        <th onclick="sortTable('dup-table',5)">Path<span class="sort-arrow"></span></th>
        <th onclick="sortTable('dup-table',6)">Method<span class="sort-arrow"></span></th>
        <th onclick="sortTable('dup-table',7)">Route 1<span class="sort-arrow"></span></th>
        <th onclick="sortTable('dup-table',8)">Route 2<span class="sort-arrow"></span></th>
        <th onclick="sortTable('dup-table',9)">Conflict Type<span class="sort-arrow"></span></th>
      </tr></thead><tbody>
{_render_duplicate_rows(duplicates)}
      </tbody></table>
    </div>
  </div>

</div>

<div class="footer">
  Generated by GCP Gateway Services Checker v2.3.0 · {escape(revision_time)}
</div>

<script>
function showTab(name){{
  document.querySelectorAll('.tab-content').forEach(el=>el.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(el=>el.classList.remove('active'));
  document.getElementById('tab-'+name).classList.add('active');
  event.target.closest('.tab').classList.add('active');
}}
function filterTable(tableId,query){{
  query=query.toLowerCase();
  const rows=document.querySelectorAll('#'+tableId+' tbody tr');
  rows.forEach(row=>{{
    const text=row.textContent.toLowerCase();
    row.style.display=text.includes(query)?'':'none';
  }});
}}
function sortTable(tableId,colIdx){{
  const table=document.getElementById(tableId);
  const tbody=table.querySelector('tbody');
  const rows=Array.from(tbody.querySelectorAll('tr'));
  const ths=table.querySelectorAll('thead th');
  const isAsc=ths[colIdx].classList.contains('sort-asc');
  rows.sort((a,b)=>{{
    const aText=a.cells[colIdx].textContent.trim();
    const bText=b.cells[colIdx].textContent.trim();
    const aNum=parseFloat(aText);
    const bNum=parseFloat(bText);
    if(!isNaN(aNum)&&!isNaN(bNum)) return isAsc?aNum-bNum:bNum-aNum;
    return isAsc?aText.localeCompare(bText):bText.localeCompare(aText);
  }});
  ths.forEach(th=>{{th.classList.remove('sort-asc','sort-desc');th.querySelector('.sort-arrow').textContent='';}});
  ths[colIdx].classList.add(isAsc?'sort-desc':'sort-asc');
  ths[colIdx].querySelector('.sort-arrow').textContent=isAsc?'▼':'▲';
  rows.forEach(r=>tbody.appendChild(r));
}}
</script>
</body>
</html>"""


def _pill(status):
    s = (status or '').lower()
    if s in ('healthy', 'ok'):
        return '<span class="pill pill-green">Healthy</span>'
    elif s in ('unhealthy', 'error'):
        return '<span class="pill pill-red">Unhealthy</span>'
    elif s in ('pending', 'degraded'):
        return '<span class="pill pill-yellow">Pending</span>'
    return f'<span class="pill pill-gray">{escape(status or "N/A")}</span>'


def _render_gateway_rows(gateways):
    if not gateways:
        return '        <tr><td colspan="9" class="empty">No se detectaron Gateways</td></tr>'
    rows = []
    for g in gateways:
        rows.append(f"""        <tr>
          <td>{escape(g.get('cluster',''))}</td>
          <td>{escape(g.get('name',''))}</td>
          <td>{escape(g.get('namespace',''))}</td>
          <td>{_pill(g.get('status',''))}</td>
          <td>{escape(g.get('gateway_class',''))}</td>
          <td>{escape(g.get('type',''))}</td>
          <td>{escape(g.get('load_balancer',''))}</td>
          <td>{escape(g.get('ip_addresses',''))}</td>
          <td>{escape(g.get('ports',''))}</td>
        </tr>""")
    return '\n'.join(rows)


def _render_route_rows(routes):
    if not routes:
        return '        <tr><td colspan="8" class="empty">No se detectaron HTTPRoutes</td></tr>'
    rows = []
    for r in routes:
        has_gw = r.get('has_gateway', False)
        rules = r.get('rules_count', 0)
        if has_gw and rules > 0:
            status_pill = '<span class="pill pill-green">Healthy</span>'
        elif not has_gw:
            status_pill = '<span class="pill pill-red">No Gateway</span>'
        else:
            status_pill = '<span class="pill pill-yellow">No Rules</span>'
        rows.append(f"""        <tr>
          <td>{escape(r.get('cluster',''))}</td>
          <td>{escape(r.get('name',''))}</td>
          <td>{escape(r.get('namespace',''))}</td>
          <td>{escape(r.get('hostnames',''))}</td>
          <td>{escape(r.get('date_created',''))}</td>
          <td>{escape(str(rules))}</td>
          <td>{escape(r.get('attached_gateways',''))}</td>
          <td>{status_pill}</td>
        </tr>""")
    return '\n'.join(rows)


def _render_service_rows(services):
    if not services:
        return '        <tr><td colspan="7" class="empty">No se detectaron Services</td></tr>'
    rows = []
    for s in services:
        pods_ready = s.get('pods_ready', 0)
        pods_total = s.get('pods_total', 0)
        if pods_total == 0:
            pods_pill = f'<span class="pill pill-red">{pods_ready}/{pods_total}</span>'
        elif pods_ready < pods_total:
            pods_pill = f'<span class="pill pill-yellow">{pods_ready}/{pods_total}</span>'
        else:
            pods_pill = f'<span class="pill pill-green">{pods_ready}/{pods_total}</span>'
        rows.append(f"""        <tr>
          <td>{escape(s.get('cluster',''))}</td>
          <td>{escape(s.get('name',''))}</td>
          <td>{escape(s.get('namespace',''))}</td>
          <td>{_pill(s.get('status',''))}</td>
          <td>{escape(s.get('type',''))}</td>
          <td>{escape(s.get('endpoints',''))}</td>
          <td>{pods_pill}</td>
        </tr>""")
    return '\n'.join(rows)


def _render_policy_rows(policies):
    if not policies:
        return '        <tr><td colspan="9" class="empty">No se detectaron Policies</td></tr>'
    rows = []
    for p in policies:
        rows.append(f"""        <tr>
          <td>{escape(p.get('cluster',''))}</td>
          <td>{escape(p.get('name',''))}</td>
          <td>{escape(p.get('namespace',''))}</td>
          <td>{escape(p.get('kind',''))}</td>
          <td>{escape(p.get('policy_type',''))}</td>
          <td>{escape(p.get('target_kind',''))}</td>
          <td>{escape(p.get('target_name',''))}</td>
          <td>{_pill(p.get('status',''))}</td>
          <td>{escape(p.get('date_created',''))}</td>
        </tr>""")
    return '\n'.join(rows)


def _render_duplicate_rows(duplicates):
    if not duplicates:
        return '        <tr><td colspan="10" class="empty">✅ No se detectaron duplicidades ni conflictos</td></tr>'
    sev_class = {'CRITICAL': 'pill-critical', 'HIGH': 'pill-high', 'MEDIUM': 'pill-medium'}
    rows = []
    for d in duplicates:
        sev = d.get('severity', 'MEDIUM')
        pill = f'<span class="pill {sev_class.get(sev, "pill-gray")}">{escape(sev)}</span>'
        rows.append(f"""        <tr>
          <td>{pill}</td>
          <td>{escape(d.get('cluster',''))}</td>
          <td>{escape(d.get('gateway',''))}</td>
          <td>{escape(d.get('listener',''))}</td>
          <td>{escape(d.get('hostname',''))}</td>
          <td>{escape(d.get('path',''))}</td>
          <td>{escape(d.get('method',''))}</td>
          <td>{escape(d.get('route_1',''))}</td>
          <td>{escape(d.get('route_2',''))}</td>
          <td>{escape(d.get('conflict_type',''))}</td>
        </tr>""")
    return '\n'.join(rows)

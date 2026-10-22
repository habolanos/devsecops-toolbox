#!/usr/bin/env python3
"""
Salida por defecto JSON + HTML para las herramientas de Azure DevOps.

Todas las opciones del launcher generan automáticamente, al finalizar:
  - <tool>_<timestamp>.json   (payload estándar: metadata + summary + data)
  - <tool>_<timestamp>.html   (reporte tabla tema oscuro auto-contenido)

en el directorio outcome/ (resolución: DEVSECOPS_OUTPUT_DIR >
config.json global.output_dir > scm/outcome).

Uso:
    from azdo_default_export import write_default_reports
    write_default_reports("mi_tool", __version__, rows,
                          metadata={...}, summary={...},
                          organization=org, project=project)
"""

import json
import os
import sys
import html as _html_mod
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

__version__ = "1.0.2"

# Asegurar que scm/ (padre de azdo/) está en sys.path para importar
# export_manager / utils cuando el script se ejecuta directo.
_SCM_DIR = Path(__file__).resolve().parent.parent
if str(_SCM_DIR) not in sys.path:
    sys.path.insert(0, str(_SCM_DIR))


def _resolve_outdir() -> Path:
    """outcome/: DEVSECOPS_OUTPUT_DIR > config.json global.output_dir > scm/outcome."""
    env = os.getenv("DEVSECOPS_OUTPUT_DIR")
    if env:
        p = Path(env)
    else:
        out = "outcome"
        cfg = _SCM_DIR / "config.json"
        try:
            if cfg.exists():
                out = json.loads(cfg.read_text(encoding="utf-8")) \
                    .get("global", {}).get("output_dir", "outcome")
        except Exception:
            pass
        p = Path(out) if Path(out).is_absolute() else _SCM_DIR / out
    p.mkdir(parents=True, exist_ok=True)
    return p


def _jsonable(v):
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    if isinstance(v, dict):
        return {str(k): _jsonable(x) for k, x in v.items()}
    if isinstance(v, (list, tuple, set)):
        return [_jsonable(x) for x in v]
    return str(v)


def _esc(v) -> str:
    return _html_mod.escape("" if v is None else str(v))


def _html_report(tool_name: str, version: str, rows: List[Dict],
                 meta_rows: Dict, sum_items: Dict, title: str) -> str:
    esc = _esc
    columns = list(dict.fromkeys(k for row in rows for k in row.keys()))
    meta_html = "".join(
        f'<div class="meta-item"><span class="meta-k">{esc(k)}</span>'
        f'<span class="meta-v">{esc(v)}</span></div>'
        for k, v in meta_rows.items())
    sum_html = "".join(
        f'<div class="stat"><div class="stat-v">{esc(v)}</div>'
        f'<div class="stat-k">{esc(k)}</div></div>'
        for k, v in sum_items.items())
    head_html = "".join(f"<th>{esc(c)}</th>" for c in columns)
    body_html = "".join(
        "<tr>" + "".join(f"<td>{esc(row.get(c))}</td>" for c in columns) + "</tr>"
        for row in rows)
    page_title = esc(title)
    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{page_title}</title>
<style>
:root{{--bg:#0f172a;--card:#1e293b;--line:#334155;--txt:#e2e8f0;--dim:#94a3b8;--acc:#38bdf8}}
*{{box-sizing:border-box;margin:0}}
body{{background:var(--bg);color:var(--txt);font-family:'Segoe UI',system-ui,sans-serif;padding:24px}}
h1{{font-size:22px;margin-bottom:4px}}
.sub{{color:var(--dim);font-size:13px;margin-bottom:16px}}
.meta{{display:flex;flex-wrap:wrap;gap:10px 24px;background:var(--card);border:1px solid var(--line);
border-radius:8px;padding:12px 16px;margin-bottom:16px;font-size:12px}}
.meta-item{{display:flex;gap:6px}}.meta-k{{color:var(--dim);font-weight:600}}
.meta-v{{color:var(--txt)}}
.stats{{display:flex;flex-wrap:wrap;gap:12px;margin-bottom:16px}}
.stat{{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px 18px;min-width:110px}}
.stat-v{{font-size:20px;font-weight:700;color:var(--acc)}}
.stat-k{{font-size:11px;color:var(--dim);text-transform:uppercase;letter-spacing:.5px}}
.wrap{{overflow-x:auto;border:1px solid var(--line);border-radius:8px}}
table{{border-collapse:collapse;width:100%;font-size:12px}}
th{{background:#0b1220;color:var(--acc);text-align:left;padding:10px 12px;position:sticky;top:0;
text-transform:uppercase;font-size:10px;letter-spacing:.5px;white-space:nowrap}}
td{{padding:8px 12px;border-top:1px solid var(--line);white-space:nowrap;max-width:420px;
overflow:hidden;text-overflow:ellipsis}}
tr:hover td{{background:#16213a}}
input#q{{background:var(--card);border:1px solid var(--line);color:var(--txt);border-radius:6px;
padding:8px 12px;width:320px;margin-bottom:12px;font-size:13px}}
</style></head><body>
<h1>{page_title}</h1>
<div class="sub">Generado automaticamente por DevSecOps Toolbox - {esc(tool_name)} v{esc(version)}</div>
<div class="meta">{meta_html}</div>
<div class="stats">{sum_html}</div>
<input id="q" placeholder="Filtrar..." onkeyup="filtrar()">
<div class="wrap"><table id="t"><thead><tr>{head_html}</tr></thead>
<tbody>{body_html}</tbody></table></div>
<script>
function filtrar(){{const q=document.getElementById('q').value.toLowerCase();
document.querySelectorAll('#t tbody tr').forEach(r=>{{
r.style.display=r.textContent.toLowerCase().includes(q)?'':'none';}});}}
</script></body></html>"""


def write_default_reports(
    tool_name: str,
    tool_version: str,
    rows: Union[List[Dict], Dict],
    metadata: Optional[Dict] = None,
    summary: Optional[Dict] = None,
    organization: Optional[str] = None,
    project: Optional[str] = None,
    title: Optional[str] = None,
    excel: bool = False,
    quiet: bool = False,
) -> Dict[str, Optional[str]]:
    """
    Genera siempre <tool>_<ts>.json y <tool>_<ts>.html en outcome/;
    con ``excel=True`` también <tool>_<ts>.xlsx (requiere pandas+openpyxl).

    Args:
        tool_name: nombre base del archivo (ej. "pr_master_checker")
        tool_version: __version__ del script
        rows: lista de dicts (datos del reporte) o reporte dict
        metadata: pares extra para la sección metadata
        summary: pares extra para el resumen (tarjetas en HTML)
        organization / project: contexto Azure DevOps
        title: título del reporte HTML
        excel: True para generar también .xlsx
        quiet: True para no imprimir las rutas generadas

    Returns:
        {"json": ruta, "html": ruta, ["excel": ruta]} — o "Error: ..." por formato
    """
    out: Dict[str, Optional[str]] = {}
    try:
        outdir = _resolve_outdir()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        gen_at = datetime.now().astimezone().isoformat(timespec="seconds")

        # Acepta lista de filas o un reporte dict (se guarda tal cual en JSON;
        # en HTML se muestra como tabla clave/valor de primer nivel).
        report_is_dict = isinstance(rows, dict)
        if report_is_dict:
            data_payload: Any = _jsonable(rows)
            table_rows: List[Dict] = [
                {"key": k, "value": v} for k, v in
                (_jsonable(rows) or {}).items()]
        else:
            table_rows = [_jsonable(r) if isinstance(r, dict)
                          else {"value": _jsonable(r)}
                          for r in (rows or [])]
            data_payload = table_rows

        meta = {"tool": tool_name, "version": tool_version,
                "generated_at": gen_at}
        if organization:
            meta["organization"] = organization
        if project:
            meta["project"] = project
        if metadata:
            meta.update(metadata)

        summ = {"total": len(rows) if rows else 0}
        if summary:
            summ.update(summary)

        # ── JSON ──
        json_path = outdir / f"{tool_name}_{ts}.json"
        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump({"metadata": meta, "summary": summ,
                           "data": data_payload},
                          f, indent=2, ensure_ascii=False, default=str)
            out["json"] = str(json_path)
        except Exception as e:
            out["json"] = f"Error: {e}"

        # ── HTML ──
        html_path = outdir / f"{tool_name}_{ts}.html"
        try:
            meta_rows = {"Tool": tool_name, "Version": tool_version,
                         "Generated": gen_at}
            if organization:
                meta_rows["Organization"] = organization
            if project:
                meta_rows["Project"] = project
            if metadata:
                meta_rows.update(metadata)
            page_title = title or tool_name.replace("_", " ").title()
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(_html_report(tool_name, tool_version, table_rows,
                                     meta_rows, summ, page_title))
            out["html"] = str(html_path)
        except Exception as e:
            out["html"] = f"Error: {e}"

        # ── Excel (opcional) ──
        if excel:
            xlsx_path = outdir / f"{tool_name}_{ts}.xlsx"
            try:
                import pandas as pd
                pd.DataFrame(table_rows).to_excel(
                    xlsx_path, index=False, engine="openpyxl")
                out["excel"] = str(xlsx_path)
            except ImportError:
                out["excel"] = "Error: pandas/openpyxl no instalados"
            except Exception as e:
                out["excel"] = f"Error: {e}"
    except Exception as e:
        out = {"json": f"Error: {e}", "html": f"Error: {e}"}

    if not quiet:
        try:
            print("📁 Archivos generados:")
        except UnicodeEncodeError:
            print("Archivos generados:")
        for fmt, path in out.items():
            ok = path and not str(path).startswith("Error")
            disp = path
            if ok:
                try:
                    disp = str(Path(path).resolve())
                except Exception:
                    pass
            try:
                print(f"   📄 {fmt.upper()}: {disp}" if ok
                      else f"   ⚠️  {fmt.upper()}: {disp}")
            except UnicodeEncodeError:
                # Consolas cp1252 (Windows) sin UTF-8
                print(f"   {'[OK]' if ok else '[!!]'} {fmt.upper()}: {disp}")
            except UnicodeEncodeError:
                # Consolas cp1252 (Windows) sin UTF-8
                print(f"{'[OK]' if ok else '[!!]'} {fmt.upper()}: {path}")
    return out


if __name__ == "__main__":
    demo = write_default_reports(
        "azdo_default_export_demo", __version__,
        [{"id": 1, "name": "demo", "status": "ok"}],
        summary={"ok": 1}, title="Demo Default Export")
    print(demo)

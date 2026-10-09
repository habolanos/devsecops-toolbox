#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Helpers compartidos del Dashboard Matutino DevSecOps.
Resolución de credenciales AZDO y webhook de Teams desde config.json.
"""

import json
import os
from pathlib import Path

SCM_CONFIG_FILE = Path(__file__).resolve().parent.parent / "config.json"


def load_config():
    """Carga scm/config.json. Retorna {} si no existe o falla."""
    try:
        if SCM_CONFIG_FILE.exists():
            cfg = json.loads(SCM_CONFIG_FILE.read_text(encoding="utf-8"))
            return cfg if isinstance(cfg, dict) else {}
    except Exception:
        pass
    return {}


def resolve_credentials(org=None, project=None, pat=None):
    """
    Resuelve credenciales de Azure DevOps.

    Orden de precedencia:
      1. Argumento explícito (--org / --project / --pat)
      2. Variables de entorno AZDO_ORG / AZDO_PROJECT / AZDO_PAT
      3. scm/config.json → azdo.organization / azdo.project / azdo.pat

    Retorna tupla (org, project, pat); elementos sin resolver quedan como "".
    """
    azdo = load_config().get("azdo", {})
    if not isinstance(azdo, dict):
        azdo = {}
    return (
        org or os.getenv("AZDO_ORG") or azdo.get("organization") or azdo.get("organization_url") or "",
        project or os.getenv("AZDO_PROJECT") or azdo.get("project") or "",
        pat or os.getenv("AZDO_PAT") or azdo.get("pat") or "",
    )


def resolve_webhook(webhook=None):
    """
    Resuelve webhook de Microsoft Teams.

    Orden de precedencia:
      1. Argumento explícito (--webhook)
      2. Variable de entorno TEAMS_WEBHOOK_URL
      3. scm/config.json → dashboard.webhook_url o
         dashboard.notifications.teams.webhook_url

    Retorna "" si no hay webhook configurado.
    """
    if webhook:
        return webhook
    env = os.getenv("TEAMS_WEBHOOK_URL")
    if env:
        return env
    dash = load_config().get("dashboard", {})
    if not isinstance(dash, dict):
        return ""
    url = dash.get("webhook_url")
    if url and url != "<TU_TEAMS_WEBHOOK_URL>":
        return url
    teams = dash.get("notifications", {}).get("teams", {})
    if isinstance(teams, dict):
        url = teams.get("webhook_url") or ""
        if url != "<TU_TEAMS_WEBHOOK_URL>":
            return url
    return ""


def resolve_cron(cron=None):
    """
    Resuelve expresión cron del scheduler.

    Orden: argumento > scm/config.json dashboard.schedule.cron > default 7 AM.
    """
    if cron:
        return cron
    dash = load_config().get("dashboard", {})
    if isinstance(dash, dict):
        sched = dash.get("schedule", {})
        if isinstance(sched, dict) and sched.get("cron"):
            return sched["cron"]
    return "0 7 * * *"

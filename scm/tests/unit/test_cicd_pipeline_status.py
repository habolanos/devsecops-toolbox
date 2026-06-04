"""
Tests unitarios para cicd_pipeline_status.py

Cubre las funciones puras y de cache del script de reporte de estado CI+CD.
"""

import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Asegurar que scm está importable como paquete
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scm.azdo.cicd_pipeline_status import (
    _bucket,
    parse_date,
    days_since,
    fmt_date,
    build_ci_row,
    classify_pipeline_group,
    _cache_is_fresh,
    _load_cache,
    _save_cache,
    make_headers,
    api_get_paginated,
    BUCKETS,
    DEPRECADO_SI,
    DEPRECADO_NO,
    GRUPO_SIN_COINCIDENCIA,
    SCRIPT_NAME,
    CACHE_TTL_HOURS,
    API_VERSION,
    DEFAULT_INACTIVE_DAYS,
)


# ═══════════════════════════════════════════════════════════════════════════════
# _bucket
# ═══════════════════════════════════════════════════════════════════════════════
class TestBucket:
    """Tests para la función _bucket()."""

    @pytest.mark.unit
    def test_bucket_nunca(self):
        assert _bucket("Nunca") == "Nunca"

    @pytest.mark.unit
    def test_bucket_cero_dias(self):
        assert _bucket("0") == "0-30d"

    @pytest.mark.unit
    def test_bucket_30_dias(self):
        assert _bucket("30") == "0-30d"

    @pytest.mark.unit
    def test_bucket_31_dias(self):
        assert _bucket("31") == "31-60d"

    @pytest.mark.unit
    def test_bucket_60_dias(self):
        assert _bucket("60") == "31-60d"

    @pytest.mark.unit
    def test_bucket_61_dias(self):
        assert _bucket("61") == "61-90d"

    @pytest.mark.unit
    def test_bucket_90_dias(self):
        assert _bucket("90") == "61-90d"

    @pytest.mark.unit
    def test_bucket_91_dias(self):
        assert _bucket("91") == "91-180d"

    @pytest.mark.unit
    def test_bucket_180_dias(self):
        assert _bucket("180") == "91-180d"

    @pytest.mark.unit
    def test_bucket_181_dias(self):
        assert _bucket("181") == ">180d"

    @pytest.mark.unit
    def test_bucket_grande(self):
        assert _bucket("999") == ">180d"

    @pytest.mark.unit
    def test_all_buckets_covered(self):
        """Verifica que todos los valores de BUCKETS son retornables."""
        results = {
            _bucket("15"), _bucket("45"), _bucket("75"),
            _bucket("120"), _bucket("200"), _bucket("Nunca"),
        }
        assert results == set(BUCKETS)


# ═══════════════════════════════════════════════════════════════════════════════
# parse_date
# ═══════════════════════════════════════════════════════════════════════════════
class TestParseDate:
    """Tests para la función parse_date()."""

    @pytest.mark.unit
    def test_none_returns_none(self):
        assert parse_date(None) is None

    @pytest.mark.unit
    def test_empty_string_returns_none(self):
        assert parse_date("") is None

    @pytest.mark.unit
    def test_iso_with_milliseconds(self):
        result = parse_date("2024-05-01T10:30:00.000Z")
        assert result is not None
        assert result.year == 2024
        assert result.month == 5
        assert result.day == 1

    @pytest.mark.unit
    def test_iso_without_milliseconds(self):
        result = parse_date("2024-05-01T10:30:00Z")
        assert result is not None
        assert result.hour == 10
        assert result.minute == 30

    @pytest.mark.unit
    def test_iso_without_z(self):
        result = parse_date("2024-05-01T10:30:00")
        assert result is not None
        assert result.year == 2024

    @pytest.mark.unit
    def test_invalid_format_returns_none(self):
        assert parse_date("not-a-date") is None

    @pytest.mark.unit
    def test_returns_utc_timezone(self):
        result = parse_date("2024-05-01T10:30:00Z")
        assert result.tzinfo == timezone.utc


# ═══════════════════════════════════════════════════════════════════════════════
# days_since
# ═══════════════════════════════════════════════════════════════════════════════
class TestDaysSince:
    """Tests para la función days_since()."""

    @pytest.mark.unit
    def test_none_returns_none(self):
        assert days_since(None) is None

    @pytest.mark.unit
    def test_today_returns_zero(self):
        now = datetime.now(timezone.utc)
        result = days_since(now)
        assert result == 0

    @pytest.mark.unit
    def test_one_day_ago(self):
        dt = datetime.now(timezone.utc) - timedelta(days=1)
        result = days_since(dt)
        assert result == 1

    @pytest.mark.unit
    def test_ninety_days_ago(self):
        dt = datetime.now(timezone.utc) - timedelta(days=90)
        result = days_since(dt)
        assert result == 90

    @pytest.mark.unit
    def test_returns_integer(self):
        dt = datetime.now(timezone.utc) - timedelta(days=45)
        result = days_since(dt)
        assert isinstance(result, int)


# ═══════════════════════════════════════════════════════════════════════════════
# fmt_date
# ═══════════════════════════════════════════════════════════════════════════════
class TestFmtDate:
    """Tests para la función fmt_date()."""

    @pytest.mark.unit
    def test_empty_returns_dash(self):
        assert fmt_date("", "UTC") == "—"

    @pytest.mark.unit
    def test_none_returns_dash(self):
        assert fmt_date(None, "UTC") == "—"

    @pytest.mark.unit
    def test_valid_date_returns_formatted(self):
        result = fmt_date("2024-05-01T10:30:00Z", "UTC")
        assert result != "—"
        assert "2024" in result

    @pytest.mark.unit
    def test_invalid_timezone_fallback(self):
        result = fmt_date("2024-05-01T10:30:00Z", "Invalid/Zone")
        assert result != "—"
        assert "2024" in result


# ═══════════════════════════════════════════════════════════════════════════════
# build_ci_row
# ═══════════════════════════════════════════════════════════════════════════════
class TestBuildCIRow:
    """Tests para la función build_ci_row()."""

    @pytest.mark.unit
    def _make_defn(self, queue_status="enabled", modified="2024-04-01T10:00:00Z",
                   finish_time="2024-04-20T09:00:00Z", name="pipeline-test", defn_id=1):
        """Helper: crea un diccionario de definición CI mock."""
        return {
            "id": defn_id,
            "name": name,
            "path": "\\",
            "queueStatus": queue_status,
            "modifiedDate": modified,
            "latestCompletedBuild": {"finishTime": finish_time} if finish_time else None,
            "url": f"https://dev.azure.com/org/proj/_apis/build/definitions/{defn_id}",
        }

    @pytest.mark.unit
    def test_enabled_pipeline_fields(self):
        """Pipeline enabled con ejecución reciente."""
        defn = self._make_defn(queue_status="enabled")
        row = build_ci_row(defn, inactive_days=90, tz_name="UTC")
        assert row["tipo"] == "CI"
        assert row["nombre"] == "pipeline-test"
        assert row["queue_status"] == "enabled"
        assert "Activo" in row["estado"]

    @pytest.mark.unit
    def test_disabled_pipeline_is_deprecated(self):
        """Pipeline disabled siempre es deprecado."""
        defn = self._make_defn(queue_status="disabled")
        row = build_ci_row(defn, inactive_days=90, tz_name="UTC")
        assert row["deprecado"] == DEPRECADO_SI
        assert "Deshabilitado" in row["estado"]

    @pytest.mark.unit
    def test_paused_pipeline_estado(self):
        """Pipeline pausado muestra estado correcto."""
        defn = self._make_defn(queue_status="paused")
        row = build_ci_row(defn, inactive_days=90, tz_name="UTC")
        assert "Pausado" in row["estado"]

    @pytest.mark.unit
    def test_never_executed_is_deprecated(self):
        """Pipeline sin ejecución alguna es deprecado."""
        defn = self._make_defn(finish_time=None)
        defn["latestCompletedBuild"] = None
        defn["latestBuild"] = None
        row = build_ci_row(defn, inactive_days=90, tz_name="UTC")
        assert row["deprecado"] == DEPRECADO_SI
        assert row["dias_inactivo"] == "Nunca"

    @pytest.mark.unit
    def test_inactive_pipeline_is_deprecated(self):
        """Pipeline inactivo por más de N días es deprecado."""
        old_date = (datetime.now(timezone.utc) - timedelta(days=100)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        defn = self._make_defn(finish_time=old_date)
        row = build_ci_row(defn, inactive_days=90, tz_name="UTC")
        assert row["deprecado"] == DEPRECADO_SI

    @pytest.mark.unit
    def test_active_recent_pipeline_not_deprecated(self):
        """Pipeline con ejecución reciente (dentro de inactive_days) no es deprecado."""
        recent_date = (datetime.now(timezone.utc) - timedelta(days=5)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        defn = self._make_defn(queue_status="enabled", finish_time=recent_date)
        row = build_ci_row(defn, inactive_days=90, tz_name="UTC")
        assert row["deprecado"] == DEPRECADO_NO

    @pytest.mark.unit
    def test_row_has_required_keys(self):
        """El row tiene todas las claves requeridas."""
        defn = self._make_defn()
        row = build_ci_row(defn, inactive_days=90, tz_name="UTC")
        required_keys = [
            "tipo", "id", "nombre", "path", "estado", "queue_status",
            "deprecado", "ultima_act", "ultima_act_raw", "ultimo_run",
            "ultimo_run_raw", "dias_inactivo", "url",
        ]
        for key in required_keys:
            assert key in row, f"Falta clave: {key}"

    @pytest.mark.unit
    def test_dias_inactivo_is_numeric_string(self):
        """dias_inactivo es un string numérico cuando hay ejecución."""
        recent = (datetime.now(timezone.utc) - timedelta(days=10)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        defn = self._make_defn(finish_time=recent)
        row = build_ci_row(defn, inactive_days=90, tz_name="UTC")
        assert row["dias_inactivo"].isdigit()


# ═══════════════════════════════════════════════════════════════════════════════
# Cache functions
# ═══════════════════════════════════════════════════════════════════════════════
class TestCacheFunctions:
    """Tests para las funciones de cache."""

    @pytest.mark.unit
    def test_cache_is_fresh_nonexistent(self, tmp_path):
        """Cache no fresco si el archivo no existe."""
        fake_path = tmp_path / "nonexistent.json"
        assert _cache_is_fresh(fake_path) is False

    @pytest.mark.unit
    def test_cache_is_fresh_none(self):
        """Cache no fresco si path es None."""
        assert _cache_is_fresh(None) is False

    @pytest.mark.unit
    def test_cache_is_fresh_recent_file(self, tmp_path):
        """Cache fresco si el archivo fue creado hace poco."""
        cache_file = tmp_path / f"{SCRIPT_NAME}_raw_20260506_010000.json"
        cache_file.write_text("{}", encoding="utf-8")
        assert _cache_is_fresh(cache_file) is True

    @pytest.mark.unit
    def test_cache_is_stale_old_file(self, tmp_path):
        """Cache caducado si el archivo tiene más de TTL horas."""
        cache_file = tmp_path / f"{SCRIPT_NAME}_raw_20240101_000000.json"
        cache_file.write_text("{}", encoding="utf-8")
        stale_mtime = time.time() - (CACHE_TTL_HOURS + 1) * 3600
        os.utime(cache_file, (stale_mtime, stale_mtime))
        assert _cache_is_fresh(cache_file) is False

    @pytest.mark.unit
    def test_load_cache_valid_json(self, tmp_path):
        """Cargar cache con JSON válido."""
        data = {"metadata": {"script": SCRIPT_NAME}, "rows": [{"tipo": "CI"}]}
        cache_file = tmp_path / "cache.json"
        cache_file.write_text(json.dumps(data), encoding="utf-8")
        result = _load_cache(cache_file)
        assert result["metadata"]["script"] == SCRIPT_NAME
        assert len(result["rows"]) == 1

    @pytest.mark.unit
    def test_load_cache_returns_dict(self, tmp_path):
        """_load_cache retorna un diccionario."""
        cache_file = tmp_path / "cache.json"
        cache_file.write_text('{"rows": []}', encoding="utf-8")
        result = _load_cache(cache_file)
        assert isinstance(result, dict)

    @pytest.mark.unit
    def test_save_cache_creates_file(self, tmp_path):
        """_save_cache crea un archivo JSON en outcome/.cache/."""
        rows = [{"tipo": "CI", "nombre": "test-pipeline"}]
        with patch("scm.azdo.cicd_pipeline_status.get_output_dir", return_value=tmp_path):
            saved_path = _save_cache(rows, "https://dev.azure.com/org", "TestProject", 90)
        assert saved_path.exists()
        with open(saved_path, encoding="utf-8") as f:
            data = json.load(f)
        assert data["metadata"]["script"] == SCRIPT_NAME
        assert data["metadata"]["org"] == "https://dev.azure.com/org"
        assert data["metadata"]["project"] == "TestProject"
        assert data["metadata"]["inactive_days"] == 90
        assert len(data["rows"]) == 1

    @pytest.mark.unit
    def test_save_cache_filename_format(self, tmp_path):
        """El nombre del archivo de cache sigue el patrón esperado."""
        rows = []
        with patch("scm.azdo.cicd_pipeline_status.get_output_dir", return_value=tmp_path):
            saved_path = _save_cache(rows, "org", "proj", 90)
        assert saved_path.name.startswith(f"{SCRIPT_NAME}_raw_")
        assert saved_path.suffix == ".json"

    @pytest.mark.unit
    def test_save_cache_creates_directory(self, tmp_path):
        """_save_cache crea el directorio .cache si no existe."""
        rows = []
        cache_dir = tmp_path / ".cache"
        assert not cache_dir.exists()
        with patch("scm.azdo.cicd_pipeline_status.get_output_dir", return_value=tmp_path):
            _save_cache(rows, "org", "proj", 90)
        assert cache_dir.exists()


# ═══════════════════════════════════════════════════════════════════════════════
# make_headers / api_get
# ═══════════════════════════════════════════════════════════════════════════════
class TestMakeHeaders:
    """Tests para make_headers()."""

    @pytest.mark.unit
    def test_returns_authorization_header(self):
        headers = make_headers("my-token")
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Basic ")

    @pytest.mark.unit
    def test_returns_content_type(self):
        headers = make_headers("my-token")
        assert headers["Content-Type"] == "application/json"

    @pytest.mark.unit
    def test_token_is_base64_encoded(self):
        import base64
        headers = make_headers("test-pat")
        encoded = headers["Authorization"].replace("Basic ", "")
        decoded = base64.b64decode(encoded).decode()
        assert decoded == ":test-pat"


class TestApiGetPaginated:
    """Tests para api_get_paginated() — paginación via x-ms-continuationtoken."""

    @pytest.mark.unit
    def test_single_page_no_token(self):
        """Una sola página sin token de continuación."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"value": [{"id": 1}, {"id": 2}]}
        mock_resp.headers = {}
        mock_resp.raise_for_status = MagicMock()
        with patch("scm.azdo.cicd_pipeline_status.requests.get", return_value=mock_resp):
            result = api_get_paginated("http://test.url", {}, {})
        assert len(result) == 2

    @pytest.mark.unit
    def test_two_pages_with_token(self):
        """Dos páginas: primera con token, segunda sin token."""
        resp_page1 = MagicMock()
        resp_page1.status_code = 200
        resp_page1.json.return_value = {"value": [{"id": i} for i in range(1, 1001)]}
        resp_page1.headers = {"x-ms-continuationtoken": "abc-token-123"}
        resp_page1.raise_for_status = MagicMock()

        resp_page2 = MagicMock()
        resp_page2.status_code = 200
        resp_page2.json.return_value = {"value": [{"id": i} for i in range(1001, 1693)]}
        resp_page2.headers = {}
        resp_page2.raise_for_status = MagicMock()

        with patch("scm.azdo.cicd_pipeline_status.requests.get",
                   side_effect=[resp_page1, resp_page2]):
            result = api_get_paginated("http://test.url", {}, {})

        assert len(result) == 1692

    @pytest.mark.unit
    def test_token_passed_in_second_request(self):
        """El continuationToken se incluye como parámetro en la segunda llamada."""
        resp_page1 = MagicMock()
        resp_page1.status_code = 200
        resp_page1.json.return_value = {"value": [{"id": 1}]}
        resp_page1.headers = {"x-ms-continuationtoken": "my-token"}
        resp_page1.raise_for_status = MagicMock()

        resp_page2 = MagicMock()
        resp_page2.status_code = 200
        resp_page2.json.return_value = {"value": [{"id": 2}]}
        resp_page2.headers = {}
        resp_page2.raise_for_status = MagicMock()

        with patch("scm.azdo.cicd_pipeline_status.requests.get",
                   side_effect=[resp_page1, resp_page2]) as mock_get:
            api_get_paginated("http://test.url", {}, {})

        second_call_params = mock_get.call_args_list[1][1]["params"]
        assert second_call_params["continuationToken"] == "my-token"

    @pytest.mark.unit
    def test_returns_empty_on_exception(self):
        """Devuelve lista vacía si la primera llamada lanza excepción."""
        with patch("scm.azdo.cicd_pipeline_status.requests.get",
                   side_effect=Exception("timeout")):
            result = api_get_paginated("http://test.url", {})
        assert result == []

    @pytest.mark.unit
    def test_partial_result_on_second_page_error(self):
        """Si la segunda página falla, devuelve los datos de la primera."""
        resp_page1 = MagicMock()
        resp_page1.status_code = 200
        resp_page1.json.return_value = {"value": [{"id": i} for i in range(10)]}
        resp_page1.headers = {"x-ms-continuationtoken": "token"}
        resp_page1.raise_for_status = MagicMock()

        with patch("scm.azdo.cicd_pipeline_status.requests.get",
                   side_effect=[resp_page1, Exception("timeout")]):
            result = api_get_paginated("http://test.url", {})

        assert len(result) == 10

    @pytest.mark.unit
    def test_makes_two_requests_for_two_pages(self):
        """Verifica que se hacen exactamente 2 llamadas HTTP para 2 páginas."""
        resp_p1 = MagicMock(status_code=200, headers={"x-ms-continuationtoken": "t"})
        resp_p1.json.return_value = {"value": [{"id": 1}]}
        resp_p1.raise_for_status = MagicMock()
        resp_p2 = MagicMock(status_code=200, headers={})
        resp_p2.json.return_value = {"value": [{"id": 2}]}
        resp_p2.raise_for_status = MagicMock()

        with patch("scm.azdo.cicd_pipeline_status.requests.get",
                   side_effect=[resp_p1, resp_p2]) as mock_get:
            api_get_paginated("http://url", {}, {})

        assert mock_get.call_count == 2


class TestClassifyPipelineGroup:
    """Tests para classify_pipeline_group() — clasificación por palabras clave en path."""

    @pytest.mark.unit
    def test_wms_by_wm(self):
        assert classify_pipeline_group("\\/WM\\pipeline") == "WMS"

    @pytest.mark.unit
    def test_wms_by_wms(self):
        assert classify_pipeline_group("\\/WMS\\pipeline") == "WMS"

    @pytest.mark.unit
    def test_wms_by_ayr(self):
        assert classify_pipeline_group("\\/AYR\\build") == "WMS"

    @pytest.mark.unit
    def test_wms_by_ims(self):
        assert classify_pipeline_group("\\/IMS\\deploy") == "WMS"

    @pytest.mark.unit
    def test_wms_by_rdm(self):
        assert classify_pipeline_group("\\/RDM\\service") == "WMS"

    @pytest.mark.unit
    def test_oms_keyword(self):
        assert classify_pipeline_group("\\/OMS\\checkout") == "OMS"

    @pytest.mark.unit
    def test_csc_keyword(self):
        assert classify_pipeline_group("\\/CSC\\api") == "CSC"

    @pytest.mark.unit
    def test_tms_by_tms(self):
        assert classify_pipeline_group("\\/TMS\\route") == "TMS"

    @pytest.mark.unit
    def test_tms_by_cmanager(self):
        assert classify_pipeline_group("\\/CManager\\deploy") == "TMS"

    @pytest.mark.unit
    def test_tms_by_torrecontrol(self):
        assert classify_pipeline_group("\\/TorreControl\\monitor") == "TMS"

    @pytest.mark.unit
    def test_sin_coincidencia_unrelated_path(self):
        assert classify_pipeline_group("\\/SharedLibs\\utils") == GRUPO_SIN_COINCIDENCIA

    @pytest.mark.unit
    def test_sin_coincidencia_empty_path(self):
        assert classify_pipeline_group("") == GRUPO_SIN_COINCIDENCIA

    @pytest.mark.unit
    def test_sin_coincidencia_root_only(self):
        assert classify_pipeline_group("\\\\") == GRUPO_SIN_COINCIDENCIA

    @pytest.mark.unit
    def test_case_insensitive_lowercase(self):
        assert classify_pipeline_group("\\/wms\\ci-build") == "WMS"

    @pytest.mark.unit
    def test_case_insensitive_mixed(self):
        assert classify_pipeline_group("\\/Oms\\order-api") == "OMS"

    @pytest.mark.unit
    def test_wms_takes_priority_over_later_groups(self):
        """Path con 'wms' y 'tms' juntos → WMS gana (primera regla)."""
        assert classify_pipeline_group("\\/wms-tms\\pipeline") == "WMS"

    @pytest.mark.unit
    def test_keyword_in_middle_of_path(self):
        """Palabra clave en el medio del path se detecta correctamente."""
        assert classify_pipeline_group("\\/Proyectos\\CSC\\api-gateway") == "CSC"

    @pytest.mark.unit
    def test_build_ci_row_includes_grupo(self):
        """build_ci_row agrega campo 'grupo' correctamente desde el path."""
        dt = datetime.now(timezone.utc) - timedelta(days=5)
        defn = {
            "id": 1, "name": "wms-build",
            "path": "\\/WMS\\Inventario",
            "queueStatus": "enabled",
            "modifiedDate": "2024-01-01T00:00:00Z",
            "latestCompletedBuild": {"finishTime": dt.strftime("%Y-%m-%dT%H:%M:%SZ")},
            "url": "https://dev.azure.com/org",
        }
        row = build_ci_row(defn, inactive_days=365, tz_name="UTC")
        assert row["grupo"] == "WMS"

    @pytest.mark.unit
    def test_none_path_returns_sin_coincidencia(self):
        """Path None no rompe la función."""
        assert classify_pipeline_group(None) == GRUPO_SIN_COINCIDENCIA


class TestDefaultDeprecationThreshold:
    """Verifica que el umbral de deprecación default es 1 año (365 días)."""

    @pytest.mark.unit
    def test_default_inactive_days_is_one_year(self):
        assert DEFAULT_INACTIVE_DAYS == 365

    @pytest.mark.unit
    def test_pipeline_at_364_days_not_deprecated(self):
        """Pipeline con 364 días inactivo NO debe ser deprecado (< 365)."""
        dt = datetime.now(timezone.utc) - timedelta(days=364)
        defn = {
            "id": 1, "name": "borderline-ci", "path": "\\",
            "queueStatus": "enabled",
            "modifiedDate": "2024-01-01T00:00:00Z",
            "latestCompletedBuild": {"finishTime": dt.strftime("%Y-%m-%dT%H:%M:%SZ")},
            "url": "https://dev.azure.com/org/proj/_apis/build/definitions/1",
        }
        row = build_ci_row(defn, inactive_days=365, tz_name="UTC")
        assert row["deprecado"] == DEPRECADO_NO

    @pytest.mark.unit
    def test_pipeline_at_366_days_is_deprecated(self):
        """Pipeline con 366 días inactivo SÍ debe ser deprecado (> 365)."""
        dt = datetime.now(timezone.utc) - timedelta(days=366)
        defn = {
            "id": 2, "name": "old-ci", "path": "\\",
            "queueStatus": "enabled",
            "modifiedDate": "2024-01-01T00:00:00Z",
            "latestCompletedBuild": {"finishTime": dt.strftime("%Y-%m-%dT%H:%M:%SZ")},
            "url": "https://dev.azure.com/org/proj/_apis/build/definitions/2",
        }
        row = build_ci_row(defn, inactive_days=365, tz_name="UTC")
        assert row["deprecado"] == DEPRECADO_SI


class TestApiGet:
    """Tests para api_get() con requests mockeado."""

    @pytest.mark.unit
    def test_returns_json_on_success(self):
        from scm.azdo.cicd_pipeline_status import api_get
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"value": ["item1"]}
        mock_resp.raise_for_status = MagicMock()
        with patch("scm.azdo.cicd_pipeline_status.requests.get", return_value=mock_resp):
            result = api_get("http://test.url", {}, {})
        assert result == {"value": ["item1"]}

    @pytest.mark.unit
    def test_returns_none_on_exception(self):
        from scm.azdo.cicd_pipeline_status import api_get
        with patch("scm.azdo.cicd_pipeline_status.requests.get", side_effect=Exception("timeout")):
            result = api_get("http://test.url", {})
        assert result is None

    @pytest.mark.unit
    def test_returns_none_on_http_error(self):
        from scm.azdo.cicd_pipeline_status import api_get
        import requests as req_module
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.raise_for_status.side_effect = req_module.HTTPError("401")
        mock_resp.text = "Unauthorized"
        with patch("scm.azdo.cicd_pipeline_status.requests.get", return_value=mock_resp):
            result = api_get("http://test.url", {}, debug=False)
        assert result is None


class TestGetDefinitions:
    """Tests para get_ci_definitions y get_cd_definitions (usan api_get_paginated)."""

    @pytest.mark.unit
    def test_get_ci_definitions_returns_list(self):
        """Paso 1 devuelve IDs, paso 2 enriquece con includeLatestBuilds."""
        from scm.azdo.cicd_pipeline_status import get_ci_definitions
        raw_ids = [{"id": 1, "name": "ci-pipeline"}]
        enriched = {"value": [{"id": 1, "name": "ci-pipeline", "latestCompletedBuild": {}}]}
        with patch("scm.azdo.cicd_pipeline_status.api_get_paginated", return_value=raw_ids):
            with patch("scm.azdo.cicd_pipeline_status.api_get", return_value=enriched):
                result = get_ci_definitions("https://dev.azure.com/org", "Project", {})
        assert len(result) == 1
        assert result[0]["name"] == "ci-pipeline"

    @pytest.mark.unit
    def test_get_ci_definitions_empty_on_api_error(self):
        """Si paso 1 no devuelve nada, retorna lista vacía."""
        from scm.azdo.cicd_pipeline_status import get_ci_definitions
        with patch("scm.azdo.cicd_pipeline_status.api_get_paginated", return_value=[]):
            result = get_ci_definitions("https://dev.azure.com/org", "Project", {})
        assert result == []

    @pytest.mark.unit
    def test_get_cd_definitions_returns_list(self):
        from scm.azdo.cicd_pipeline_status import get_cd_definitions
        mock_page = [{"id": 10, "name": "cd-release"}]
        with patch("scm.azdo.cicd_pipeline_status.api_get_paginated", return_value=mock_page):
            result = get_cd_definitions("https://dev.azure.com/org", "Project", {})
        assert len(result) == 1
        assert result[0]["name"] == "cd-release"

    @pytest.mark.unit
    def test_get_cd_definitions_empty_on_api_error(self):
        from scm.azdo.cicd_pipeline_status import get_cd_definitions
        with patch("scm.azdo.cicd_pipeline_status.api_get_paginated", return_value=[]):
            result = get_cd_definitions("https://dev.azure.com/org", "Project", {})
        assert result == []

    @pytest.mark.unit
    def test_get_ci_definitions_multi_page_1692(self):
        """Con 1692 defs se hacen ceil(1692/200)=9 llamadas de enriquecimiento."""
        import math
        from scm.azdo.cicd_pipeline_status import get_ci_definitions
        raw_ids = [{"id": i, "name": f"ci-{i}"} for i in range(1, 1693)]
        enriched_batch = {"value": [{"id": d["id"]} for d in raw_ids[:200]]}
        with patch("scm.azdo.cicd_pipeline_status.api_get_paginated", return_value=raw_ids):
            with patch("scm.azdo.cicd_pipeline_status.api_get",
                       return_value={"value": []}) as mock_api:
                get_ci_definitions("https://dev.azure.com/org", "Project", {})
        expected_batches = math.ceil(1692 / 200)
        assert mock_api.call_count == expected_batches

    @pytest.mark.unit
    def test_get_ci_definitions_uses_top_5000_step1(self):
        """Paso 1 usa $top=5000 (sin includeLatestBuilds) para obtener todos los IDs."""
        from scm.azdo.cicd_pipeline_status import get_ci_definitions
        with patch("scm.azdo.cicd_pipeline_status.api_get_paginated", return_value=[]) as mock_pag:
            get_ci_definitions("https://dev.azure.com/org", "Project", {})
        call_params = mock_pag.call_args[0][2]
        assert call_params["$top"] == 5000
        assert "includeLatestBuilds" not in call_params

    @pytest.mark.unit
    def test_get_ci_definitions_step2_uses_include_latest_builds(self):
        """Paso 2 pasa includeLatestBuilds=true y definitionIds al API."""
        from scm.azdo.cicd_pipeline_status import get_ci_definitions
        raw_ids = [{"id": 1}, {"id": 2}]
        with patch("scm.azdo.cicd_pipeline_status.api_get_paginated", return_value=raw_ids):
            with patch("scm.azdo.cicd_pipeline_status.api_get",
                       return_value={"value": []}) as mock_api:
                get_ci_definitions("https://dev.azure.com/org", "Project", {})
        batch_params = mock_api.call_args[0][2]
        assert batch_params["includeLatestBuilds"] == "true"
        assert "1" in batch_params["definitionIds"]
        assert "2" in batch_params["definitionIds"]

    @pytest.mark.unit
    def test_get_latest_release_returns_first(self):
        from scm.azdo.cicd_pipeline_status import get_latest_release
        mock_data = {"value": [{"id": 99, "createdOn": "2024-05-01T10:00:00Z"}]}
        with patch("scm.azdo.cicd_pipeline_status.api_get", return_value=mock_data):
            result = get_latest_release(1, "https://dev.azure.com/org", "Project", {}, False)
        assert result["id"] == 99

    @pytest.mark.unit
    def test_get_latest_release_none_when_empty(self):
        from scm.azdo.cicd_pipeline_status import get_latest_release
        with patch("scm.azdo.cicd_pipeline_status.api_get", return_value={"value": []}):
            result = get_latest_release(1, "https://dev.azure.com/org", "Project", {}, False)
        assert result is None


class TestCdWorker:
    """Tests para _cd_worker()."""

    @pytest.mark.unit
    def _make_defn(self, defn_id=10, name="release-prod"):
        return {
            "id": defn_id,
            "name": name,
            "path": "\\",
            "modifiedOn": "2024-04-01T08:00:00Z",
            "url": f"https://vsrm.dev.azure.com/org/proj/_apis/release/definitions/{defn_id}",
        }

    @pytest.mark.unit
    def test_never_released_is_deprecated(self):
        from scm.azdo.cicd_pipeline_status import _cd_worker
        defn = self._make_defn()
        with patch("scm.azdo.cicd_pipeline_status.get_latest_release", return_value=None):
            row = _cd_worker(defn, "https://dev.azure.com/org", "Project", {}, 90, "UTC", False)
        assert row["deprecado"] == DEPRECADO_SI
        assert row["dias_inactivo"] == "Nunca"
        assert row["tipo"] == "CD"

    @pytest.mark.unit
    def test_recent_release_is_active(self):
        from scm.azdo.cicd_pipeline_status import _cd_worker
        recent = (datetime.now(timezone.utc) - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
        defn = self._make_defn()
        with patch("scm.azdo.cicd_pipeline_status.get_latest_release",
                   return_value={"createdOn": recent}):
            row = _cd_worker(defn, "https://dev.azure.com/org", "Project", {}, 90, "UTC", False)
        assert row["deprecado"] == DEPRECADO_NO
        assert "✅" in row["estado"]

    @pytest.mark.unit
    def test_inactive_release_is_deprecated(self):
        from scm.azdo.cicd_pipeline_status import _cd_worker
        old = (datetime.now(timezone.utc) - timedelta(days=120)).strftime("%Y-%m-%dT%H:%M:%SZ")
        defn = self._make_defn()
        with patch("scm.azdo.cicd_pipeline_status.get_latest_release",
                   return_value={"createdOn": old}):
            row = _cd_worker(defn, "https://dev.azure.com/org", "Project", {}, 90, "UTC", False)
        assert row["deprecado"] == DEPRECADO_SI
        assert "🔴" in row["estado"]

    @pytest.mark.unit
    def test_inactivo_state_between_30_and_90_days(self):
        from scm.azdo.cicd_pipeline_status import _cd_worker
        mid = (datetime.now(timezone.utc) - timedelta(days=60)).strftime("%Y-%m-%dT%H:%M:%SZ")
        defn = self._make_defn()
        with patch("scm.azdo.cicd_pipeline_status.get_latest_release",
                   return_value={"createdOn": mid}):
            row = _cd_worker(defn, "https://dev.azure.com/org", "Project", {}, 90, "UTC", False)
        assert "⚠" in row["estado"]

    @pytest.mark.unit
    def test_row_has_required_cd_keys(self):
        from scm.azdo.cicd_pipeline_status import _cd_worker
        defn = self._make_defn()
        with patch("scm.azdo.cicd_pipeline_status.get_latest_release", return_value=None):
            row = _cd_worker(defn, "https://dev.azure.com/org", "Project", {}, 90, "UTC", False)
        for key in ["tipo", "id", "nombre", "estado", "deprecado", "dias_inactivo", "url"]:
            assert key in row


class TestPrintPlainTable:
    """Tests para print_plain_table()."""

    @pytest.mark.unit
    def _sample_rows(self):
        return [
            {
                "tipo": "CI", "nombre": "pipeline-a", "estado": "✅ Activo",
                "deprecado": DEPRECADO_NO, "ultima_act": "2024-05-01 10:00",
                "ultimo_run": "2024-05-01 10:00", "dias_inactivo": "5",
            },
        ]

    @pytest.mark.unit
    def test_print_plain_table_runs(self, capsys):
        from scm.azdo.cicd_pipeline_status import print_plain_table
        print_plain_table(self._sample_rows(), elapsed=1.5, inactive_days=90)
        captured = capsys.readouterr()
        assert "CI" in captured.out
        assert "pipeline-a" in captured.out

    @pytest.mark.unit
    def test_print_plain_table_shows_totals(self, capsys):
        from scm.azdo.cicd_pipeline_status import print_plain_table
        print_plain_table(self._sample_rows(), elapsed=2.0, inactive_days=90)
        captured = capsys.readouterr()
        assert "Total" in captured.out


# ═══════════════════════════════════════════════════════════════════════════════
# Export results
# ═══════════════════════════════════════════════════════════════════════════════
class TestExportResults:
    """Tests para la función export_results()."""

    @pytest.mark.unit
    def _sample_rows(self):
        return [
            {
                "tipo": "CI", "id": 1, "nombre": "pipeline-ci",
                "path": "\\", "estado": "✅ Activo", "deprecado": DEPRECADO_NO,
                "ultima_act": "2024-05-01 10:00", "ultimo_run": "2024-05-01 10:00",
                "dias_inactivo": "5", "url": "https://dev.azure.com/test",
                "queue_status": "enabled", "ultima_act_raw": "", "ultimo_run_raw": "",
            },
            {
                "tipo": "CD", "id": 2, "nombre": "release-cd",
                "path": "\\", "estado": "🔴 Sin uso", "deprecado": DEPRECADO_SI,
                "ultima_act": "2023-01-01 08:00", "ultimo_run": "Nunca",
                "dias_inactivo": "Nunca", "url": "https://vsrm.dev.azure.com/test",
                "queue_status": "", "ultima_act_raw": "", "ultimo_run_raw": "",
            },
        ]

    @pytest.mark.unit
    def test_export_json_creates_file(self, tmp_path):
        """export_results JSON crea un archivo con estructura válida."""
        from scm.azdo.cicd_pipeline_status import export_results
        rows = self._sample_rows()
        with patch("scm.azdo.cicd_pipeline_status.get_output_dir", return_value=tmp_path):
            filepath = export_results(rows, "json", "UTC")
        assert filepath is not None
        assert Path(filepath).exists()
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
        assert "summary" in data
        assert data["summary"]["total"] == 2
        assert data["summary"]["ci"] == 1
        assert data["summary"]["cd"] == 1

    @pytest.mark.unit
    def test_export_csv_creates_file(self, tmp_path):
        """export_results CSV crea un archivo con cabeceras."""
        import csv
        from scm.azdo.cicd_pipeline_status import export_results
        rows = self._sample_rows()
        with patch("scm.azdo.cicd_pipeline_status.get_output_dir", return_value=tmp_path):
            filepath = export_results(rows, "csv", "UTC")
        assert filepath is not None
        assert Path(filepath).exists()
        with open(filepath, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            csv_rows = list(reader)
        assert len(csv_rows) == 2
        assert "tipo" in csv_rows[0]
        assert "nombre" in csv_rows[0]

    @pytest.mark.unit
    def test_export_unknown_format_returns_none(self, tmp_path):
        """export_results retorna None para formato desconocido."""
        from scm.azdo.cicd_pipeline_status import export_results
        rows = self._sample_rows()
        with patch("scm.azdo.cicd_pipeline_status.get_output_dir", return_value=tmp_path):
            result = export_results(rows, "xml", "UTC")
        assert result is None

    @pytest.mark.unit
    def test_export_json_deprecated_count(self, tmp_path):
        """export_results JSON incluye conteo correcto de deprecados."""
        from scm.azdo.cicd_pipeline_status import export_results
        rows = self._sample_rows()
        with patch("scm.azdo.cicd_pipeline_status.get_output_dir", return_value=tmp_path):
            filepath = export_results(rows, "json", "UTC")
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
        assert data["summary"]["deprecated"] == 1


# ═══════════════════════════════════════════════════════════════════════════════
# Constants and defaults
# ═══════════════════════════════════════════════════════════════════════════════
class TestConstants:
    """Verifica los valores de las constantes del módulo."""

    @pytest.mark.unit
    def test_script_name(self):
        assert SCRIPT_NAME == "cicd_pipeline_status"

    @pytest.mark.unit
    def test_cache_ttl_positive(self):
        assert CACHE_TTL_HOURS > 0

    @pytest.mark.unit
    def test_deprecado_si_not_empty(self):
        assert DEPRECADO_SI != ""
        assert DEPRECADO_NO != ""

    @pytest.mark.unit
    def test_buckets_has_six_values(self):
        assert len(BUCKETS) == 6

    @pytest.mark.unit
    def test_buckets_includes_nunca(self):
        assert "Nunca" in BUCKETS

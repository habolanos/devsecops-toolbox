#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit Tests — Utils Module
Tests para validar funcionalidad de utilidades compartidas

Version: 1.0.0
Author: Harold Adrian
"""

import pytest
import os
from pathlib import Path
from datetime import datetime
import sys

# Add scm to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scm.utils import get_output_dir, resolve_output_path, FORMAT_EXTENSIONS


class TestGetOutputDir:
    """Tests para la función get_output_dir."""
    
    @pytest.mark.unit
    def test_get_output_dir_default(self, tmp_path):
        """Test: Obtener directorio de salida con default."""
        # Limpiar variable de entorno
        old_env = os.getenv("DEVSECOPS_OUTPUT_DIR")
        if "DEVSECOPS_OUTPUT_DIR" in os.environ:
            del os.environ["DEVSECOPS_OUTPUT_DIR"]
        
        try:
            result = get_output_dir(str(tmp_path))
            assert result.exists()
            assert result.is_dir()
        finally:
            if old_env:
                os.environ["DEVSECOPS_OUTPUT_DIR"] = old_env
    
    @pytest.mark.unit
    def test_get_output_dir_from_env(self, tmp_path):
        """Test: Obtener directorio de salida desde variable de entorno."""
        old_env = os.getenv("DEVSECOPS_OUTPUT_DIR")
        
        try:
            os.environ["DEVSECOPS_OUTPUT_DIR"] = str(tmp_path / "custom_output")
            result = get_output_dir()
            
            assert result.exists()
            assert "custom_output" in str(result)
        finally:
            if old_env:
                os.environ["DEVSECOPS_OUTPUT_DIR"] = old_env
            elif "DEVSECOPS_OUTPUT_DIR" in os.environ:
                del os.environ["DEVSECOPS_OUTPUT_DIR"]
    
    @pytest.mark.unit
    def test_get_output_dir_creates_directory(self, tmp_path):
        """Test: Crear directorio si no existe."""
        new_dir = tmp_path / "new_output" / "nested" / "path"
        
        result = get_output_dir(str(new_dir))
        
        assert result.exists()
        assert result.is_dir()
    
    @pytest.mark.unit
    def test_get_output_dir_returns_absolute_path(self, tmp_path):
        """Test: Retorna ruta absoluta."""
        result = get_output_dir(str(tmp_path))
        
        assert result.is_absolute()
    
    @pytest.mark.unit
    def test_get_output_dir_idempotent(self, tmp_path):
        """Test: Llamadas múltiples retornan el mismo resultado."""
        result1 = get_output_dir(str(tmp_path))
        result2 = get_output_dir(str(tmp_path))
        
        assert result1 == result2


class TestFormatExtensions:
    """Tests para la constante FORMAT_EXTENSIONS."""
    
    @pytest.mark.unit
    def test_format_extensions_has_excel(self):
        """Test: FORMAT_EXTENSIONS contiene excel."""
        assert "excel" in FORMAT_EXTENSIONS
        assert FORMAT_EXTENSIONS["excel"] == ".xlsx"
    
    @pytest.mark.unit
    def test_format_extensions_has_csv(self):
        """Test: FORMAT_EXTENSIONS contiene csv."""
        assert "csv" in FORMAT_EXTENSIONS
        assert FORMAT_EXTENSIONS["csv"] == ".csv"
    
    @pytest.mark.unit
    def test_format_extensions_has_json(self):
        """Test: FORMAT_EXTENSIONS contiene json."""
        assert "json" in FORMAT_EXTENSIONS
        assert FORMAT_EXTENSIONS["json"] == ".json"
    
    @pytest.mark.unit
    def test_format_extensions_values_are_extensions(self):
        """Test: Todos los valores son extensiones válidas."""
        for key, value in FORMAT_EXTENSIONS.items():
            assert value.startswith(".")
            assert len(value) > 1


class TestResolveOutputPath:
    """Tests para la función resolve_output_path."""
    
    @pytest.mark.unit
    def test_resolve_output_path_none_default_format(self, tmp_path):
        """Test: Resolver path con None y formato default."""
        old_env = os.getenv("DEVSECOPS_OUTPUT_DIR")
        
        try:
            os.environ["DEVSECOPS_OUTPUT_DIR"] = str(tmp_path)
            result = resolve_output_path(None, "test_report")
            
            assert "test_report" in result
            assert result.endswith(".xlsx")
            assert "outcome" in result or str(tmp_path) in result
        finally:
            if old_env:
                os.environ["DEVSECOPS_OUTPUT_DIR"] = old_env
            elif "DEVSECOPS_OUTPUT_DIR" in os.environ:
                del os.environ["DEVSECOPS_OUTPUT_DIR"]
    
    @pytest.mark.unit
    def test_resolve_output_path_excel_format(self, tmp_path):
        """Test: Resolver path con formato excel."""
        old_env = os.getenv("DEVSECOPS_OUTPUT_DIR")
        
        try:
            os.environ["DEVSECOPS_OUTPUT_DIR"] = str(tmp_path)
            result = resolve_output_path("excel", "test_report")
            
            assert result.endswith(".xlsx")
            assert "test_report" in result
        finally:
            if old_env:
                os.environ["DEVSECOPS_OUTPUT_DIR"] = old_env
            elif "DEVSECOPS_OUTPUT_DIR" in os.environ:
                del os.environ["DEVSECOPS_OUTPUT_DIR"]
    
    @pytest.mark.unit
    def test_resolve_output_path_csv_format(self, tmp_path):
        """Test: Resolver path con formato csv."""
        old_env = os.getenv("DEVSECOPS_OUTPUT_DIR")
        
        try:
            os.environ["DEVSECOPS_OUTPUT_DIR"] = str(tmp_path)
            result = resolve_output_path("csv", "test_report")
            
            assert result.endswith(".csv")
            assert "test_report" in result
        finally:
            if old_env:
                os.environ["DEVSECOPS_OUTPUT_DIR"] = old_env
            elif "DEVSECOPS_OUTPUT_DIR" in os.environ:
                del os.environ["DEVSECOPS_OUTPUT_DIR"]
    
    @pytest.mark.unit
    def test_resolve_output_path_json_format(self, tmp_path):
        """Test: Resolver path con formato json."""
        old_env = os.getenv("DEVSECOPS_OUTPUT_DIR")
        
        try:
            os.environ["DEVSECOPS_OUTPUT_DIR"] = str(tmp_path)
            result = resolve_output_path("json", "test_report")
            
            assert result.endswith(".json")
            assert "test_report" in result
        finally:
            if old_env:
                os.environ["DEVSECOPS_OUTPUT_DIR"] = old_env
            elif "DEVSECOPS_OUTPUT_DIR" in os.environ:
                del os.environ["DEVSECOPS_OUTPUT_DIR"]
    
    @pytest.mark.unit
    def test_resolve_output_path_custom_path_no_extension(self, tmp_path):
        """Test: Resolver path personalizado sin extensión."""
        custom_path = str(tmp_path / "custom_report")
        result = resolve_output_path(custom_path, "ignored")
        
        assert result.endswith(".xlsx")
        assert "custom_report" in result
    
    @pytest.mark.unit
    def test_resolve_output_path_custom_path_with_extension(self, tmp_path):
        """Test: Resolver path personalizado con extensión."""
        custom_path = str(tmp_path / "custom_report.csv")
        result = resolve_output_path(custom_path, "ignored")
        
        assert result.endswith(".csv")
        assert "custom_report" in result
    
    @pytest.mark.unit
    def test_resolve_output_path_case_insensitive_format(self, tmp_path):
        """Test: Formato case-insensitive."""
        old_env = os.getenv("DEVSECOPS_OUTPUT_DIR")
        
        try:
            os.environ["DEVSECOPS_OUTPUT_DIR"] = str(tmp_path)
            result = resolve_output_path("EXCEL", "test_report")
            
            assert result.endswith(".xlsx")
        finally:
            if old_env:
                os.environ["DEVSECOPS_OUTPUT_DIR"] = old_env
            elif "DEVSECOPS_OUTPUT_DIR" in os.environ:
                del os.environ["DEVSECOPS_OUTPUT_DIR"]
    
    @pytest.mark.unit
    def test_resolve_output_path_returns_absolute_path(self, tmp_path):
        """Test: Retorna ruta absoluta."""
        old_env = os.getenv("DEVSECOPS_OUTPUT_DIR")
        
        try:
            os.environ["DEVSECOPS_OUTPUT_DIR"] = str(tmp_path)
            result = resolve_output_path(None, "test_report")
            
            assert Path(result).is_absolute()
        finally:
            if old_env:
                os.environ["DEVSECOPS_OUTPUT_DIR"] = old_env
            elif "DEVSECOPS_OUTPUT_DIR" in os.environ:
                del os.environ["DEVSECOPS_OUTPUT_DIR"]
    
    @pytest.mark.unit
    def test_resolve_output_path_custom_default_format(self, tmp_path):
        """Test: Usar formato default personalizado."""
        old_env = os.getenv("DEVSECOPS_OUTPUT_DIR")
        
        try:
            os.environ["DEVSECOPS_OUTPUT_DIR"] = str(tmp_path)
            result = resolve_output_path(None, "test_report", default_format="json")
            
            assert result.endswith(".json")
        finally:
            if old_env:
                os.environ["DEVSECOPS_OUTPUT_DIR"] = old_env
            elif "DEVSECOPS_OUTPUT_DIR" in os.environ:
                del os.environ["DEVSECOPS_OUTPUT_DIR"]
    
    @pytest.mark.unit
    def test_resolve_output_path_timestamp_in_filename(self, tmp_path):
        """Test: Timestamp incluido en nombre de archivo."""
        old_env = os.getenv("DEVSECOPS_OUTPUT_DIR")
        
        try:
            os.environ["DEVSECOPS_OUTPUT_DIR"] = str(tmp_path)
            result = resolve_output_path(None, "test_report")
            
            # Verificar que contiene timestamp (YYYYMMDD_HHMMSS)
            assert any(c.isdigit() for c in result)
            assert "_" in result
        finally:
            if old_env:
                os.environ["DEVSECOPS_OUTPUT_DIR"] = old_env
            elif "DEVSECOPS_OUTPUT_DIR" in os.environ:
                del os.environ["DEVSECOPS_OUTPUT_DIR"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

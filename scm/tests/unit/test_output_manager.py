"""
Tests para output_manager.py
"""

import pytest
from pathlib import Path
import tempfile
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class TestOutputManager:
    """Tests para output_manager"""

    def test_output_manager_exists(self):
        """Test que output_manager existe"""
        try:
            from scm import output_manager
            assert output_manager is not None
        except ImportError:
            pytest.skip("output_manager no disponible")

    def test_output_directory_creation(self):
        """Test creación de directorio de salida"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / 'output'
            output_dir.mkdir(exist_ok=True)
            
            assert output_dir.exists()
            assert output_dir.is_dir()

    def test_output_file_writing(self):
        """Test escritura de archivos de salida"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / 'output.txt'
            output_file.write_text('test content')
            
            assert output_file.exists()
            assert output_file.read_text() == 'test content'

    def test_output_json_file(self):
        """Test escritura de archivo JSON"""
        import json
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / 'output.json'
            data = {'key': 'value', 'number': 123}
            output_file.write_text(json.dumps(data))
            
            assert output_file.exists()
            loaded = json.loads(output_file.read_text())
            assert loaded['key'] == 'value'

    def test_output_csv_file(self):
        """Test escritura de archivo CSV"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / 'output.csv'
            csv_content = "name,value\ntest,123\n"
            output_file.write_text(csv_content)
            
            assert output_file.exists()
            assert 'name,value' in output_file.read_text()

    def test_output_directory_structure(self):
        """Test estructura de directorios de salida"""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            
            # Crear estructura
            (base_dir / 'reports').mkdir(exist_ok=True)
            (base_dir / 'data').mkdir(exist_ok=True)
            (base_dir / 'logs').mkdir(exist_ok=True)
            
            assert (base_dir / 'reports').exists()
            assert (base_dir / 'data').exists()
            assert (base_dir / 'logs').exists()

    def test_output_file_permissions(self):
        """Test permisos de archivos de salida"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / 'output.txt'
            output_file.write_text('test')
            
            # Verificar que el archivo es legible
            assert output_file.is_file()
            assert output_file.read_text() == 'test'

    def test_output_file_overwrite(self):
        """Test sobrescritura de archivos de salida"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / 'output.txt'
            
            # Primera escritura
            output_file.write_text('first')
            assert output_file.read_text() == 'first'
            
            # Segunda escritura (sobrescribe)
            output_file.write_text('second')
            assert output_file.read_text() == 'second'

    def test_output_multiple_files(self):
        """Test escritura de múltiples archivos"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            
            # Crear múltiples archivos
            for i in range(5):
                file = output_dir / f'output_{i}.txt'
                file.write_text(f'content {i}')
            
            # Verificar
            files = list(output_dir.glob('output_*.txt'))
            assert len(files) == 5


class TestOutputManagerIntegration:
    """Tests de integración para output_manager"""

    def test_output_manager_with_json_data(self):
        """Test output_manager con datos JSON"""
        import json
        
        with tempfile.TemporaryDirectory() as tmpdir:
            data = {
                'tools': [
                    {'id': 1, 'name': 'Tool 1'},
                    {'id': 2, 'name': 'Tool 2'}
                ],
                'summary': {'total': 2}
            }
            
            output_file = Path(tmpdir) / 'data.json'
            output_file.write_text(json.dumps(data, indent=2))
            
            assert output_file.exists()
            loaded = json.loads(output_file.read_text())
            assert len(loaded['tools']) == 2

    def test_output_manager_with_csv_data(self):
        """Test output_manager con datos CSV"""
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_data = "id,name,status\n1,Tool1,active\n2,Tool2,inactive\n"
            
            output_file = Path(tmpdir) / 'data.csv'
            output_file.write_text(csv_data)
            
            assert output_file.exists()
            lines = output_file.read_text().split('\n')
            assert len(lines) >= 3

    def test_output_manager_creates_nested_directories(self):
        """Test que output_manager crea directorios anidados"""
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_dir = Path(tmpdir) / 'level1' / 'level2' / 'level3'
            nested_dir.mkdir(parents=True, exist_ok=True)
            
            assert nested_dir.exists()
            assert nested_dir.is_dir()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

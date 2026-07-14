"""
Generador de reportes para Pipeline Updater
"""

import json
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, List
from .config import REPORT_DIR
from .models import UpdateResult


class Reporter:
    """Generador de reportes de actualización"""
    
    def __init__(self, results: List[UpdateResult], errors: List[Dict]):
        """
        Inicializar reporter
        
        Args:
            results: Lista de resultados
            errors: Lista de errores
        """
        self.results = results
        self.errors = errors
        self.output_dir = Path(REPORT_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def generate_all(self):
        """Generar todos los reportes"""
        self.generate_json()
        self.generate_csv()
        self.generate_html()
    
    def generate_json(self) -> str:
        """
        Generar reporte JSON
        
        Returns:
            Ruta del archivo generado
        """
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total': len(self.results) + len(self.errors),
                'success': len(self.results),
                'failed': len(self.errors),
                'total_matches': sum(r.matches_found for r in self.results),
                'total_changes': sum(r.changes_applied for r in self.results),
            },
            'details': [
                {
                    'definition_id': r.definition_id,
                    'success': r.success,
                    'snapshot_id': r.snapshot_id,
                    'matches_found': r.matches_found,
                    'changes_applied': r.changes_applied,
                    'changes': r.changes,
                    'duration': r.duration,
                    'error': r.error
                }
                for r in self.results
            ],
            'errors': self.errors
        }
        
        output_file = self.output_dir / f"report_{self.timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        return str(output_file)
    
    def generate_csv(self) -> str:
        """
        Generar reporte CSV
        
        Returns:
            Ruta del archivo generado
        """
        output_file = self.output_dir / f"report_{self.timestamp}.csv"
        
        rows = []
        for result in self.results:
            rows.append({
                'definition_id': result.definition_id,
                'success': 'Yes' if result.success else 'No',
                'snapshot_id': result.snapshot_id,
                'matches_found': result.matches_found,
                'changes_applied': result.changes_applied,
                'duration': f"{result.duration:.2f}s",
                'error': result.error or ''
            })
        
        if rows:
            fieldnames = ['definition_id', 'success', 'snapshot_id', 'matches_found', 'changes_applied', 'duration', 'error']
            
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
        
        return str(output_file)
    
    def generate_html(self) -> str:
        """
        Generar reporte HTML
        
        Returns:
            Ruta del archivo generado
        """
        output_file = self.output_dir / f"report_{self.timestamp}.html"
        
        total = len(self.results) + len(self.errors)
        success_rate = (len(self.results) / total * 100) if total > 0 else 0
        
        rows_html = ''
        for result in self.results:
            status = '✓' if result.success else '✗'
            status_color = 'green' if result.success else 'red'
            rows_html += f"""
            <tr>
                <td>{result.definition_id}</td>
                <td style="color: {status_color};">{status}</td>
                <td>{result.matches_found}</td>
                <td>{result.changes_applied}</td>
                <td>{result.duration:.2f}s</td>
                <td>{result.error or '-'}</td>
            </tr>
            """
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Pipeline Updates Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #333; }}
                .summary {{ background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                .success {{ color: green; font-weight: bold; }}
                .failed {{ color: red; font-weight: bold; }}
                table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
                th {{ background-color: #4CAF50; color: white; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
            </style>
        </head>
        <body>
            <h1>Pipeline Updates Report</h1>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            <div class="summary">
                <h2>Summary</h2>
                <p>Total Pipelines: <strong>{total}</strong></p>
                <p class="success">Successful: {len(self.results)}</p>
                <p class="failed">Failed: {len(self.errors)}</p>
                <p>Success Rate: <strong>{success_rate:.1f}%</strong></p>
                <p>Total Matches: <strong>{sum(r.matches_found for r in self.results)}</strong></p>
                <p>Total Changes: <strong>{sum(r.changes_applied for r in self.results)}</strong></p>
            </div>
            
            <h2>Details</h2>
            <table>
                <tr>
                    <th>Definition ID</th>
                    <th>Status</th>
                    <th>Matches</th>
                    <th>Changes</th>
                    <th>Duration</th>
                    <th>Error</th>
                </tr>
                {rows_html}
            </table>
        </body>
        </html>
        """
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return str(output_file)

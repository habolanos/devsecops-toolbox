"""
Analizadores para Service Accounts
Análisis de seguridad, cumplimiento y riesgos
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional


class RolesAndPermissionsAnalyzer:
    """Analiza roles, permisos temporales y días restantes."""
    
    ROLE_TITLES = {
        'roles/editor': 'Editor',
        'roles/owner': 'Owner',
        'roles/viewer': 'Viewer',
        'roles/compute.admin': 'Compute Admin',
        'roles/storage.admin': 'Storage Admin',
        'roles/iam.securityAdmin': 'Security Admin',
        'roles/resourcemanager.organizationAdmin': 'Organization Admin'
    }
    
    ROLE_DESCRIPTIONS = {
        'roles/editor': 'Acceso completo de lectura y escritura',
        'roles/owner': 'Acceso completo incluyendo gestión de permisos',
        'roles/viewer': 'Acceso de lectura a todos los recursos',
        'roles/compute.admin': 'Acceso completo a Compute Engine'
    }
    
    PERMISSION_COUNTS = {
        'roles/editor': 5000,
        'roles/owner': 5000,
        'roles/viewer': 5000,
        'roles/compute.admin': 127,
        'roles/storage.admin': 50
    }
    
    def __init__(self, debug: bool = False):
        self.debug = debug
    
    def analyze_roles(self, sa_email: str, iam_bindings: List[Dict]) -> Dict:
        """Analiza roles de un service account."""
        analyzed_bindings = []
        
        for binding in iam_bindings:
            if self._is_sa_in_binding(sa_email, binding):
                analyzed_binding = self._analyze_single_binding(binding)
                analyzed_bindings.append(analyzed_binding)
        
        return {
            'iam_bindings': analyzed_bindings,
            'role_summary': self._generate_role_summary(analyzed_bindings)
        }
    
    def _analyze_single_binding(self, binding: Dict) -> Dict:
        """Analiza un binding individual."""
        role = binding.get('role', '')
        condition = binding.get('condition', {})
        
        # Extraer información de la condición
        granted_at = self._extract_grant_date(condition)
        requested_duration = self._extract_duration(condition)
        expiration_date = self._calculate_expiration(granted_at, requested_duration)
        days_remaining = self._calculate_days_remaining(expiration_date)
        
        return {
            'role': role,
            'role_title': self._get_role_title(role),
            'role_description': self._get_role_description(role),
            'permission_count': self._get_permission_count(role),
            'granted_at': granted_at,
            'requested_duration_days': requested_duration,
            'expiration_date': expiration_date,
            'days_remaining': days_remaining,
            'is_temporary': requested_duration is not None,
            'is_expired': days_remaining is not None and days_remaining < 0,
            'condition': condition if condition else None,
            'risk_level': self._calculate_role_risk(role, days_remaining),
            'risk_factors': self._identify_role_risks(role, days_remaining)
        }
    
    def _is_sa_in_binding(self, sa_email: str, binding: Dict) -> bool:
        """Verifica si el service account está en el binding."""
        members = binding.get('members', [])
        return any(sa_email in member for member in members)
    
    def _extract_grant_date(self, condition: Dict) -> Optional[str]:
        """Extrae fecha de otorgamiento de la condición."""
        if not condition:
            return None
        # En implementación real, parsear desde condition.expression
        return None
    
    def _extract_duration(self, condition: Dict) -> Optional[int]:
        """Extrae duración solicitada de la condición."""
        if not condition:
            return None
        # En implementación real, parsear desde condition.expression
        return None
    
    def _calculate_expiration(self, granted_at: str, duration_days: int) -> Optional[str]:
        """Calcula fecha de expiración."""
        if not granted_at or not duration_days:
            return None
        
        try:
            grant_date = datetime.fromisoformat(granted_at.replace('Z', '+00:00'))
            expiration = grant_date + timedelta(days=duration_days)
            return expiration.isoformat()
        except:
            return None
    
    def _calculate_days_remaining(self, expiration_date: str) -> Optional[int]:
        """Calcula días restantes hasta expiración."""
        if not expiration_date:
            return None
        
        try:
            exp_date = datetime.fromisoformat(expiration_date.replace('Z', '+00:00'))
            today = datetime.now(exp_date.tzinfo)
            delta = (exp_date - today).days
            return delta
        except:
            return None
    
    def _calculate_role_risk(self, role: str, days_remaining: Optional[int]) -> str:
        """Calcula nivel de riesgo del rol."""
        risk_score = 0
        
        # Riesgo por tipo de rol
        dangerous_roles = {
            'roles/editor': 50,
            'roles/owner': 60,
            'roles/compute.admin': 40,
            'roles/iam.securityAdmin': 50,
            'roles/resourcemanager.organizationAdmin': 60
        }
        
        risk_score += dangerous_roles.get(role, 0)
        
        # Riesgo por expiración
        if days_remaining is not None:
            if days_remaining < 0:
                risk_score += 30  # Expirado
            elif days_remaining < 7:
                risk_score += 20  # Expira pronto
            elif days_remaining < 30:
                risk_score += 10  # Expira en menos de 30 días
        else:
            risk_score += 15  # Permanente sin expiración
        
        if risk_score >= 70:
            return 'CRITICAL'
        elif risk_score >= 50:
            return 'HIGH'
        elif risk_score >= 30:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def _identify_role_risks(self, role: str, days_remaining: Optional[int]) -> List[str]:
        """Identifica factores de riesgo."""
        risks = []
        
        dangerous_roles = [
            'roles/editor', 'roles/owner', 'roles/compute.admin',
            'roles/iam.securityAdmin', 'roles/resourcemanager.organizationAdmin'
        ]
        
        if role in dangerous_roles:
            risks.append(f"Rol administrativo: {role}")
        
        if days_remaining is None:
            risks.append("Permiso permanente sin fecha de expiración")
        elif days_remaining < 0:
            risks.append(f"Permiso expirado hace {abs(days_remaining)} días")
        elif days_remaining < 7:
            risks.append(f"Permiso expira en {days_remaining} días")
        elif days_remaining < 30:
            risks.append(f"Permiso expira en {days_remaining} días (menos de 30)")
        
        return risks
    
    def _generate_role_summary(self, bindings: List[Dict]) -> Dict:
        """Genera resumen de roles."""
        temporary = [b for b in bindings if b['is_temporary']]
        expired = [b for b in bindings if b['is_expired']]
        expiring_soon = [b for b in bindings 
                        if b['days_remaining'] and 0 <= b['days_remaining'] < 30]
        
        return {
            'total_roles': len(bindings),
            'temporary_roles': len(temporary),
            'permanent_roles': len(bindings) - len(temporary),
            'expired_roles': len(expired),
            'expiring_soon': [
                {
                    'role': b['role'],
                    'days_remaining': b['days_remaining'],
                    'expiration_date': b['expiration_date']
                }
                for b in expiring_soon
            ],
            'total_permissions': sum(b['permission_count'] for b in bindings),
            'average_days_remaining': self._calculate_average_days_remaining(bindings)
        }
    
    def _calculate_average_days_remaining(self, bindings: List[Dict]) -> Optional[int]:
        """Calcula promedio de días restantes."""
        days_list = [b['days_remaining'] for b in bindings if b['days_remaining'] is not None]
        return int(sum(days_list) / len(days_list)) if days_list else None
    
    def _get_role_title(self, role: str) -> str:
        """Obtiene título del rol."""
        return self.ROLE_TITLES.get(role, role.replace('roles/', ''))
    
    def _get_role_description(self, role: str) -> str:
        """Obtiene descripción del rol."""
        return self.ROLE_DESCRIPTIONS.get(role, 'Descripción no disponible')
    
    def _get_permission_count(self, role: str) -> int:
        """Obtiene cantidad de permisos del rol."""
        return self.PERMISSION_COUNTS.get(role, 0)


class SecurityAnalyzer:
    """Analiza riesgos de seguridad de service accounts."""
    
    DANGEROUS_ROLES = [
        'roles/editor',
        'roles/owner',
        'roles/compute.admin',
        'roles/iam.securityAdmin',
        'roles/resourcemanager.organizationAdmin'
    ]
    
    def __init__(self, debug: bool = False):
        self.debug = debug
    
    def analyze(self, sa: Dict) -> Dict:
        """Analiza seguridad de un service account."""
        return {
            'has_user_managed_keys': self._check_user_managed_keys(sa),
            'key_rotation_compliant': self._check_key_rotation(sa),
            'excessive_permissions': self._check_excessive_permissions(sa),
            'risk_level': self._calculate_risk_level(sa),
            'risk_factors': self._identify_risk_factors(sa)
        }
    
    def _check_user_managed_keys(self, sa: Dict) -> bool:
        """Verifica si tiene claves user-managed."""
        keys = sa.get('keys', [])
        return any(key.get('key_type') == 'USER_MANAGED' for key in keys)
    
    def _check_key_rotation(self, sa: Dict) -> bool:
        """Verifica cumplimiento de rotación de claves."""
        keys = sa.get('keys', [])
        for key in keys:
            if key.get('key_type') == 'USER_MANAGED':
                age_days = key.get('age_days', 0)
                if age_days > 90:  # Política estándar
                    return False
        return True
    
    def _check_excessive_permissions(self, sa: Dict) -> bool:
        """Verifica si tiene permisos excesivos."""
        roles_analysis = sa.get('roles_analysis', {})
        bindings = roles_analysis.get('iam_bindings', [])
        
        for binding in bindings:
            if binding.get('role') in self.DANGEROUS_ROLES:
                return True
        return False
    
    def _calculate_risk_level(self, sa: Dict) -> str:
        """Calcula nivel de riesgo (LOW, MEDIUM, HIGH, CRITICAL)."""
        risk_score = 0
        
        if self._check_excessive_permissions(sa):
            risk_score += 40
        if not self._check_key_rotation(sa):
            risk_score += 30
        if self._check_user_managed_keys(sa):
            risk_score += 20
        
        if risk_score >= 70:
            return 'CRITICAL'
        elif risk_score >= 50:
            return 'HIGH'
        elif risk_score >= 30:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def _identify_risk_factors(self, sa: Dict) -> List[str]:
        """Identifica factores de riesgo."""
        factors = []
        
        if self._check_excessive_permissions(sa):
            factors.append("Permisos excesivos (roles administrativos)")
        
        if not self._check_key_rotation(sa):
            factors.append("Claves no rotadas (> 90 días)")
        
        if self._check_user_managed_keys(sa):
            factors.append("Claves user-managed detectadas")
        
        return factors

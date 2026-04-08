"""SemVer Version Manager for devsecops-toolbox

Usage:
    python scripts/bump_version.py [major|minor|patch|prerelease|finalize]
    python scripts/bump_version.py 2.0.0

Examples:
    python scripts/bump_version.py patch      # 1.5.0 -> 1.5.1
    python scripts/bump_version.py minor      # 1.5.1 -> 1.6.0
    python scripts/bump_version.py major      # 1.6.0 -> 2.0.0
    python scripts/bump_version.py prerelease # 2.0.0 -> 2.0.0-alpha.1
    python scripts/bump_version.py finalize   # 2.0.0-alpha.1 -> 2.0.0
    python scripts/bump_version.py 2.1.0      # Set explicit version
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Tuple, Optional


class SemVer:
    """Semantic Versioning parser and validator."""
    
    # SemVer 2.0.0 regex pattern
    PATTERN = re.compile(
        r'^(?P<major>0|[1-9]\d*)\.'
        r'(?P<minor>0|[1-9]\d*)\.'
        r'(?P<patch>0|[1-9]\d*)'
        r'(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?'
        r'(?:\+(?P<buildmetadata>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$'
    )
    
    def __init__(self, version: str):
        match = self.PATTERN.match(version)
        if not match:
            raise ValueError(f"Invalid SemVer version: {version}")
        
        self.major = int(match.group('major'))
        self.minor = int(match.group('minor'))
        self.patch = int(match.group('patch'))
        self.prerelease = match.group('prerelease')
        self.buildmetadata = match.group('buildmetadata')
    
    def __str__(self) -> str:
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            version += f"-{self.prerelease}"
        if self.buildmetadata:
            version += f"+{self.buildmetadata}"
        return version
    
    def bump_major(self) -> 'SemVer':
        return SemVer(f"{self.major + 1}.0.0")
    
    def bump_minor(self) -> 'SemVer':
        return SemVer(f"{self.major}.{self.minor + 1}.0")
    
    def bump_patch(self) -> 'SemVer':
        return SemVer(f"{self.major}.{self.minor}.{self.patch + 1}")
    
    def bump_prerelease(self, identifier: str = "alpha") -> 'SemVer':
        if self.prerelease:
            # Increment existing prerelease
            parts = self.prerelease.split('.')
            if len(parts) >= 2 and parts[-1].isdigit():
                parts[-1] = str(int(parts[-1]) + 1)
                new_prerelease = '.'.join(parts)
            else:
                new_prerelease = f"{self.prerelease}.1"
            return SemVer(f"{self.major}.{self.minor}.{self.patch}-{new_prerelease}")
        else:
            return SemVer(f"{self.major}.{self.minor}.{self.patch}-{identifier}.1")
    
    def finalize(self) -> 'SemVer':
        """Remove prerelease identifier."""
        return SemVer(f"{self.major}.{self.minor}.{self.patch}")


class VersionManager:
    """Manages version across all project files."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.version_file = project_root / "VERSION"
        self.init_file = project_root / "scm" / "__init__.py"
        self.pyproject_file = project_root / "pyproject.toml"
    
    def get_current_version(self) -> str:
        """Read version from VERSION file."""
        if self.version_file.exists():
            return self.version_file.read_text().strip()
        # Fallback to __init__.py
        if self.init_file.exists():
            content = self.init_file.read_text()
            match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
            if match:
                return match.group(1)
        return "0.0.0"
    
    def update_version(self, new_version: str) -> None:
        """Update version in all relevant files."""
        semver = SemVer(new_version)
        version_str = str(semver)
        
        # Update VERSION file
        self.version_file.write_text(version_str + "\n")
        print(f"✓ Updated {self.version_file}")
        
        # Update scm/__init__.py
        if self.init_file.exists():
            content = self.init_file.read_text()
            content = re.sub(
                r'__version__\s*=\s*["\'][^"\']+["\']',
                f'__version__ = "{version_str}"',
                content
            )
            self.init_file.write_text(content)
            print(f"✓ Updated {self.init_file}")
        
        # Update pyproject.toml
        if self.pyproject_file.exists():
            content = self.pyproject_file.read_text()
            content = re.sub(
                r'^version\s*=\s*["\'][^"\']+["\']',
                f'version = "{version_str}"',
                content,
                flags=re.MULTILINE
            )
            self.pyproject_file.write_text(content)
            print(f"✓ Updated {self.pyproject_file}")
    
    def validate_versions(self) -> bool:
        """Check that all files have consistent versions."""
        versions = {}
        
        # Check VERSION file
        if self.version_file.exists():
            versions['VERSION'] = self.version_file.read_text().strip()
        
        # Check scm/__init__.py
        if self.init_file.exists():
            content = self.init_file.read_text()
            match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
            if match:
                versions['scm/__init__.py'] = match.group(1)
        
        # Check pyproject.toml
        if self.pyproject_file.exists():
            content = self.pyproject_file.read_text()
            match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
            if match:
                versions['pyproject.toml'] = match.group(1)
        
        if len(set(versions.values())) > 1:
            print("❌ Version mismatch detected:")
            for file, version in versions.items():
                print(f"  {file}: {version}")
            return False
        
        print(f"✓ All files consistent at version: {list(versions.values())[0]}")
        return True


def main():
    parser = argparse.ArgumentParser(
        description="SemVer Version Manager for devsecops-toolbox",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/bump_version.py patch        # 1.5.0 -> 1.5.1
  python scripts/bump_version.py minor        # 1.5.1 -> 1.6.0  
  python scripts/bump_version.py major        # 1.6.0 -> 2.0.0
  python scripts/bump_version.py prerelease   # 2.0.0 -> 2.0.0-alpha.1
  python scripts/bump_version.py finalize     # 2.0.0-alpha.1 -> 2.0.0
  python scripts/bump_version.py 2.1.0        # Set explicit version
  python scripts/bump_version.py --validate   # Check version consistency
        """
    )
    parser.add_argument(
        'action',
        nargs='?',
        choices=['major', 'minor', 'patch', 'prerelease', 'finalize'],
        help='Version bump type'
    )
    parser.add_argument(
        'version',
        nargs='?',
        help='Explicit version (e.g., 2.0.0)'
    )
    parser.add_argument(
        '--validate', '-v',
        action='store_true',
        help='Validate version consistency across files'
    )
    parser.add_argument(
        '--show',
        action='store_true',
        help='Show current version'
    )
    
    args = parser.parse_args()
    
    project_root = Path(__file__).parent.parent
    manager = VersionManager(project_root)
    
    # Show current version
    if args.show or (not args.action and not args.version and not args.validate):
        current = manager.get_current_version()
        print(f"Current version: {current}")
        return 0
    
    # Validate versions
    if args.validate:
        success = manager.validate_versions()
        return 0 if success else 1
    
    # Set explicit version
    if args.version and not args.action:
        try:
            semver = SemVer(args.version)
            manager.update_version(str(semver))
            print(f"\n✅ Version updated to: {semver}")
            return 0
        except ValueError as e:
            print(f"❌ Error: {e}")
            return 1
    
    # Bump version
    if args.action:
        current = manager.get_current_version()
        try:
            semver = SemVer(current)
            
            if args.action == 'major':
                new_version = semver.bump_major()
            elif args.action == 'minor':
                new_version = semver.bump_minor()
            elif args.action == 'patch':
                new_version = semver.bump_patch()
            elif args.action == 'prerelease':
                new_version = semver.bump_prerelease()
            elif args.action == 'finalize':
                new_version = semver.finalize()
            
            manager.update_version(str(new_version))
            print(f"\n✅ Version bumped: {current} -> {new_version}")
            return 0
            
        except ValueError as e:
            print(f"❌ Error: {e}")
            return 1
    
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())

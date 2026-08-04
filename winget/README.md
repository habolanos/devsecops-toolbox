# Winget Distribution - DevSecOps Toolbox

This directory contains the winget manifests for distributing DevSecOps Toolbox via Windows Package Manager (winget).

## Installation (for end users)

### From winget-pkgs (once merged)

```powershell
winget install habolanos.devsecops-toolbox
```

### From local manifest (for testing)

```powershell
# Validate the manifest
winget validate .\winget\manifests\h\habolanos\devsecops-toolbox\1.7.20\

# Install from local manifest
winget install --manifest .\winget\manifests\h\habolanos\devsecops-toolbox\1.7.20\
```

## Manifest Structure

```
winget/
└── manifests/
    └── h/
        └── habolanos/
            └── devsecops-toolbox/
                └── 1.7.20/
                    ├── habolanos.devsecops-toolbox.yaml              (version manifest)
                    ├── habolanos.devsecops-toolbox.installer.yaml    (installer manifest)
                    └── habolanos.devsecops-toolbox.locale.en-US.yaml (default locale manifest)
```

## How to Update for a New Release

1. Build the executable: `python build_executables.py`
2. Calculate SHA256: `Get-FileHash -Algorithm SHA256 dist/devsecops-toolbox.exe`
3. Upload to GitHub release: `gh release upload <version> dist/devsecops-toolbox.exe --clobber`
4. Create a new version folder under `winget/manifests/h/habolanos/devsecops-toolbox/<version>/`
5. Copy the 3 YAML files and update:
   - `PackageVersion` in all 3 files
   - `InstallerUrl` (change version in URL) in installer manifest
   - `InstallerSha256` with the new hash in installer manifest
   - `ReleaseNotes` and `ReleaseNotesUrl` in locale manifest
6. Validate: `winget validate .\winget\manifests\h\habolanos\devsecops-toolbox\<version>\`
7. Test: `winget install --manifest .\winget\manifests\h\habolanos\devsecops-toolbox\<version>\`

## Publishing to winget-pkgs

To make the package available to all winget users:

```powershell
# Fork microsoft/winget-pkgs, then create a PR with the manifest
# Or use wingetcreate to automate the process:
wingetcreate update habolanos.devsecops-toolbox --version <new-version> --urls <url1> --submit
```

## Package Identifier

`habolanos.devsecops-toolbox`

## Installer Type

`portable` - The executable is a standalone PyInstaller binary that requires no installation.

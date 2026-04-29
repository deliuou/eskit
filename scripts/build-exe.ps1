# Build a standalone Windows executable with PyInstaller.
# Run from the repository root:
#   powershell -ExecutionPolicy Bypass -File scripts/build-exe.ps1

$venvPython = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    python -m venv .venv
}

& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install pyinstaller .
& .\.venv\Scripts\pyinstaller.exe --onefile --name eskit .\eskit\cli.py
Write-Host "Built: dist\eskit.exe"

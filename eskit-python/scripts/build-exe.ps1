# Build a standalone Windows executable with PyInstaller.
# Run from the repository root:
#   powershell -ExecutionPolicy Bypass -File scripts/build-exe.ps1

python -m pip install --upgrade pip
python -m pip install pyinstaller .
pyinstaller --onefile --name eskit .\eskit\cli.py
Write-Host "Built: dist\eskit.exe"

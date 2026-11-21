param([string]$Environment = (Join-Path $PSScriptRoot '.venv'))
$ErrorActionPreference = 'Stop'
if (!(Test-Path -LiteralPath (Join-Path $Environment 'Scripts/python.exe'))) {
    uv venv --python 3.12.14 $Environment
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
$interpreter = Join-Path $Environment 'Scripts/python.exe'
& $interpreter -c "import sys; assert sys.version_info[:3] == (3, 12, 14), 'Expected Python 3.12.14'"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
uv pip install --python $interpreter --extra-index-url https://download.pytorch.org/whl/cu130 --index-strategy unsafe-best-match -r (Join-Path $PSScriptRoot 'requirements-windows.txt')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $interpreter -B (Join-Path $PSScriptRoot 'check_startup.py')
exit $LASTEXITCODE

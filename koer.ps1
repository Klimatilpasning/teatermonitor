# Kører teatermonitoren og logger resultatet.
# Kaldes af den planlagte opgave "Teatermonitor" hver mandag.
$ErrorActionPreference = "Stop"
$rod = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $rod

$python = Join-Path $env:LOCALAPPDATA "Programs\Python\Python311\python.exe"
if (-not (Test-Path $python)) { $python = "python" }

& $python "$rod\monitor.py" *>> "$rod\state\koersler.log"
$resultat = $LASTEXITCODE

# Genopbyg den offentlige side, også selvom afsendelsen fejlede —
# data.json er skrevet inden afsendelsen forsøges.
& $python "$rod\byg_side.py" *>> "$rod\state\koersler.log"

exit $resultat

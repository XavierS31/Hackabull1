$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$venv = Join-Path $root ".venv"

Write-Host "==> Backend env file"
$envExample = Join-Path $backend ".env.example"
$envFile = Join-Path $backend ".env"
if (-not (Test-Path $envFile) -and (Test-Path $envExample)) {
  Copy-Item -Path $envExample -Destination $envFile
}

Write-Host "==> Python virtual environment"
if (-not (Test-Path $venv)) {
  python -m venv $venv
}

$pythonExe = Join-Path $venv "Scripts\\python.exe"

Write-Host "==> Installing backend dependencies"
& $pythonExe -m pip install --upgrade pip
& $pythonExe -m pip install -r (Join-Path $backend "requirements.txt")

Write-Host "==> Installing frontend dependencies"
Push-Location $frontend
npm install
Pop-Location

Write-Host ""
Write-Host "Setup complete."
Write-Host "Run backend:  `"$pythonExe`" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload (from backend/)"
Write-Host "Run frontend: npm run dev (from frontend/)"

# Idempotent setup for the full stack. Safe to re-run.
# Builds firmware, creates Python venv + installs deps, runs npm install -- only if missing.
# Exits non-zero on any failure so the calling pipeline can stop.

$ErrorActionPreference = "Stop"

$root     = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$backend  = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$firmware = Join-Path $root "firmware"
$venv     = Join-Path $root ".venv"
$pythonExe = Join-Path $venv "Scripts\python.exe"

function Section($msg) { Write-Host ""; Write-Host "==> $msg" -ForegroundColor Cyan }
function Ok($msg)      { Write-Host "  [ok] $msg" -ForegroundColor Green }
function Skip($msg)    { Write-Host "  [skip] $msg" -ForegroundColor DarkGray }

# --- 1. backend/.env ---
Section "Backend .env"
$envExample = Join-Path $backend ".env.example"
$envFile    = Join-Path $backend ".env"
if (-not (Test-Path $envFile)) {
    if (Test-Path $envExample) {
        Copy-Item $envExample $envFile
        Ok "Created backend/.env from .env.example -- edit it before flashing."
    } else {
        New-Item -ItemType File -Path $envFile | Out-Null
        Ok "Created empty backend/.env."
    }
} else { Skip "backend/.env exists." }

# --- 2. Python venv ---
Section "Python venv"
if (-not (Test-Path $pythonExe)) {
    python -m venv $venv
    if (-not (Test-Path $pythonExe)) { throw "venv creation failed" }
    Ok "Created venv at .venv/"
} else { Skip ".venv already exists." }

# --- 3. Backend deps ---
Section "Backend dependencies"
$marker = Join-Path $venv ".deps_installed"
$reqs   = Join-Path $backend "requirements.txt"
$reqsHash = (Get-FileHash $reqs).Hash
if ((-not (Test-Path $marker)) -or ((Get-Content $marker -Raw -ErrorAction SilentlyContinue).Trim() -ne $reqsHash)) {
    & $pythonExe -m pip install --upgrade pip | Out-Null
    & $pythonExe -m pip install -r $reqs
    if ($LASTEXITCODE -ne 0) { throw "pip install failed" }
    Set-Content -Path $marker -Value $reqsHash -Encoding utf8
    Ok "Installed/updated backend deps."
} else { Skip "Backend deps already match requirements.txt." }

# --- 4. Frontend deps ---
Section "Frontend dependencies"
$nodeMod = Join-Path $frontend "node_modules"
if (-not (Test-Path $nodeMod)) {
    Push-Location $frontend
    try {
        npm install
        if ($LASTEXITCODE -ne 0) { throw "npm install failed" }
    } finally { Pop-Location }
    Ok "Ran npm install."
} else { Skip "node_modules exists." }

# --- 5. Firmware builds (PlatformIO) ---
Section "Firmware builds"
$pio = Get-Command pio -ErrorAction SilentlyContinue
if (-not $pio) {
    Write-Host "  [warn] PlatformIO Core (pio) not on PATH. Skipping firmware build." -ForegroundColor Yellow
    Write-Host "         Install with: pip install platformio   (or use the VS Code extension)" -ForegroundColor Yellow
} else {
    foreach ($proj in @("glasses", "node_b_glove")) {
        $projDir = Join-Path $firmware $proj
        $bin     = Join-Path $projDir ".pio\build\$proj\firmware.bin"
        if (Test-Path $bin) {
            Skip "$proj firmware.bin already built."
        } else {
            Push-Location $projDir
            try {
                & pio run
                if ($LASTEXITCODE -ne 0) { throw "pio run failed for $proj" }
            } finally { Pop-Location }
            Ok "Built $proj firmware."
        }
    }
}

Write-Host ""
Write-Host "Setup OK." -ForegroundColor Green

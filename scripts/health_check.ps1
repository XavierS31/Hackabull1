# Poll the backend /healthz endpoint until it answers OK or we time out.
# Exit 0 on success, 1 on timeout. Used by the run-stack pipeline.

param(
    [string]$Url = "http://127.0.0.1:8000/healthz",
    [int]$TimeoutSeconds = 30
)

$ErrorActionPreference = "SilentlyContinue"
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)

Write-Host "Waiting for backend at $Url (timeout ${TimeoutSeconds}s)..."

while ((Get-Date) -lt $deadline) {
    try {
        $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
        if ($resp.StatusCode -eq 200 -and $resp.Content -match '"ok"') {
            Write-Host "Backend healthy: $($resp.Content)" -ForegroundColor Green
            exit 0
        }
    } catch {
        # connection refused -- backend not up yet, keep polling
    }
    Start-Sleep -Milliseconds 500
}

Write-Host "Backend did not become healthy within ${TimeoutSeconds}s." -ForegroundColor Red
exit 1

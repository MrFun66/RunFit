# GRF Coach one-click start: backend + public tunnel
# Run: right-click "Run with PowerShell", or double-click start.bat
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$PORT = 7788
$URLFILE = Join-Path $PSScriptRoot "current_url.txt"
$LOG = Join-Path $PSScriptRoot "cloudflared.log"

# ---------- 0. cleanup ----------
Write-Host "[0/3] Cleaning old processes ..." -ForegroundColor Cyan
$old = Get-NetTCPConnection -LocalPort $PORT -State Listen -ErrorAction SilentlyContinue
if ($old) {
    try { Stop-Process -Id $old.OwningProcess -Force -ErrorAction SilentlyContinue } catch {}
    Start-Sleep -Seconds 2
}
Get-Process cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

# ---------- 1. backend ----------
Write-Host "[1/3] Starting backend on http://127.0.0.1:$PORT ..." -ForegroundColor Cyan
$py = (Get-Command python).Source
Start-Process -FilePath $py `
    -ArgumentList "-m","uvicorn","app.main:app","--host","0.0.0.0","--port","$PORT" `
    -WorkingDirectory $PSScriptRoot -WindowStyle Hidden

$health = $null
for ($i = 0; $i -lt 40; $i++) {
    Start-Sleep -Milliseconds 500
    try {
        $health = Invoke-RestMethod "http://127.0.0.1:$PORT/api/health" -TimeoutSec 3
        if ($health.ok) { break }
    } catch {}
}
if (-not $health -or -not $health.ok) {
    Write-Host "  Backend failed to start. Run manually: python -m uvicorn app.main:app --port $PORT" -ForegroundColor Red
    exit 1
}
$llmStatus = if ($health.llm_configured) { "configured" } else { "NOT configured (set GRF_LLM_API_KEY in .env for AI coach)" }
Write-Host "  Backend ready | LLM: $llmStatus" -ForegroundColor Green

# ---------- 2. tunnel ----------
Write-Host "[2/3] Starting public tunnel (cloudflared) ..." -ForegroundColor Cyan
if (Test-Path $LOG) { Remove-Item $LOG -Force }
Start-Process -FilePath "cloudflared" `
    -ArgumentList "tunnel","--url","http://127.0.0.1:$PORT","--logfile",$LOG `
    -WindowStyle Hidden

$url = $null
for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep -Seconds 1
    if (Test-Path $LOG) {
        $m = Select-String -Path $LOG -Pattern "https://[a-z0-9-]+\.trycloudflare\.com" -AllMatches |
             Select-Object -First 1
        if ($m) { $url = $m.Matches[0].Value; break }
    }
}

# ---------- 3. result ----------
Write-Host ""
if ($url) {
    $url | Set-Content -Path $URLFILE -Encoding utf8
    Write-Host "[3/3] Public URL: $url" -ForegroundColor Green
    Write-Host "      (saved to current_url.txt; valid for this run)" -ForegroundColor DarkGray

    try {
        $pub = Invoke-RestMethod "$url/api/health" -TimeoutSec 20
        Write-Host "      Public self-check: OK  $($pub | ConvertTo-Json -Compress)" -ForegroundColor Green
    } catch {
        Write-Host "      Public self-check failed (may need 10s, just refresh): $($_.Exception.Message)" -ForegroundColor Yellow
    }
} else {
    Write-Host "[3/3] No public URL found. Check $LOG" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Done. Open the URL above on your phone and 'Add to Home Screen'." -ForegroundColor Cyan
# 域名生效后一键修复：重建 DNS 记录 + 重启隧道
$ErrorActionPreference = "Continue"
Write-Host "=== 1. 检查 wenhh.top 的 NS 是否已指向 Cloudflare ===" -ForegroundColor Cyan
$ns = $null
try { $ns = (Resolve-DnsName wenhh.top -Type NS -Server 8.8.8.8 -ErrorAction Stop | Where-Object {$_.NameHost} | Select-Object -Expand NameHost) } catch {}
if (-not $ns) { Write-Host "NS 查询失败" -ForegroundColor Red; exit 1 }
Write-Host ("当前 NS: " + ($ns -join ", "))
$cf = $ns | Where-Object { $_ -like "*ns.cloudflare.com" }
if (-not $cf) {
    Write-Host "❌ NS 还没切到 Cloudflare，请先去西部数码改 NS，然后重新运行本脚本。" -ForegroundColor Yellow
    exit 1
}
Write-Host "✅ NS 已指向 Cloudflare" -ForegroundColor Green

Write-Host "`n=== 2. 重新绑定隧道 DNS 记录 ===" -ForegroundColor Cyan
& cloudflared tunnel route dns runfit runfit.wenhh.top 2>&1 | Out-String

Write-Host "`n=== 3. 确认 config.yml ===" -ForegroundColor Cyan
$cfg = "$env:USERPROFILE\.cloudflared\config.yml"
if (Test-Path $cfg) { Get-Content $cfg -Raw } else { Write-Host "config.yml 缺失，正在重建" }

Write-Host "`n=== 4. 停止旧的 cloudflared 隧道进程 ===" -ForegroundColor Cyan
Get-Process cloudflared -ErrorAction SilentlyContinue | Where-Object { $_.Id -ne $PID } | ForEach-Object {
    Write-Host "停止 PID $($_.Id)"; Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 2

Write-Host "`n=== 5. 启动命名隧道 ===" -ForegroundColor Cyan
$out = "D:\GRF\logs\named_tunnel.out"; $err = "D:\GRF\logs\named_tunnel.err"
Remove-Item $out,$err -ErrorAction SilentlyContinue
$p = Start-Process -FilePath "cloudflared" -ArgumentList "tunnel","run","runfit" -RedirectStandardOutput $out -RedirectStandardError $err -PassThru -WindowStyle Hidden
Write-Host "隧道进程 PID = $($p.Id)"
Start-Sleep -Seconds 10

Write-Host "`n=== 6. 验证 ===" -ForegroundColor Cyan
Start-Sleep -Seconds 5
foreach ($i in 1..6) {
    try {
        $r = Invoke-WebRequest -Uri "https://runfit.wenhh.top/api/health" -UseBasicParsing -TimeoutSec 15
        Write-Host "✅ https://runfit.wenhh.top/api/health -> $($r.StatusCode) $($r.Content)" -ForegroundColor Green
        break
    } catch {
        Write-Host "第 $i 次尝试失败（DNS 可能还在传播）: $($_.Exception.Message)" -ForegroundColor Yellow
        Start-Sleep -Seconds 10
    }
}
Write-Host "`n完成。若仍失败，请检查 Cloudflare 后台该 zone 是否为 Active。" -ForegroundColor Cyan
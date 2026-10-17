# 等待并验证 NS 切换 + 域名可用
$want = @("anita.ns.cloudflare.com","jobs.ns.cloudflare.com")
$ok = $false
for ($i=1; $i -le 120; $i++) {
    $ns = @()
    try { $ns = (Resolve-DnsName wenhh.top -Type NS -Server 8.8.8.8 -ErrorAction Stop | Where-Object {$_.NameHost} | Select-Object -Expand NameHost) } catch {}
    $now = ($ns -join ", ")
    $hit = ($ns | Where-Object { $_ -like "*ns.cloudflare.com*" }).Count
    $ts = Get-Date -Format "HH:mm:ss"
    if ($hit -ge 2) {
        Write-Host "[$ts] ✅ NS 已切换到 Cloudflare: $now" -ForegroundColor Green
        $ok = $true; break
    } else {
        Write-Host "[$ts] 第 $i 次: 仍为 [$now]（等待中，约每 15 秒查一次）" -ForegroundColor Yellow
        Start-Sleep -Seconds 15
    }
}
if (-not $ok) { Write-Host "超时：NS 仍未切换，请检查西部数码是否保存成功。" -ForegroundColor Red; exit 1 }

Write-Host "`n等待解析生效（最多 10 分钟）..." -ForegroundColor Cyan
for ($j=1; $j -le 40; $j++) {
    try {
        $r = Invoke-WebRequest "https://runfit.wenhh.top/api/health" -UseBasicParsing -TimeoutSec 15
        Write-Host "`n✅✅✅ 成功！https://runfit.wenhh.top/api/health -> $($r.StatusCode) $($r.Content)" -ForegroundColor Green
        Write-Host "`n固定域名已可用：https://runfit.wenhh.top" -ForegroundColor Green
        exit 0
    } catch {
        Write-Host "[$(Get-Date -Format HH:mm:ss)] 第 $j 次: $($_.Exception.Message)" -ForegroundColor Yellow
        Start-Sleep -Seconds 15
    }
}
Write-Host "解析超时，但 NS 已正确。请稍后手动访问 https://runfit.wenhh.top" -ForegroundColor Yellow
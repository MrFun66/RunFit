# RunFit 固定域名一键配置（cloudflared 命名隧道）
# 前置条件：
#   1. 已购买域名，且 NS 已托管到 Cloudflare（免费套餐即可）
#   2. 已安装 cloudflared（本机已装）
# 用法：右键「使用 PowerShell 运行」，按提示操作

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$PORT = 7788
$TUNNEL = "runfit"

Write-Host "=== RunFit 固定域名配置 ===" -ForegroundColor Cyan

# 0. 检查 cloudflared
$cf = (Get-Command cloudflared -ErrorAction SilentlyContinue).Source
if (-not $cf) {
    Write-Host "未找到 cloudflared，请先安装：" -ForegroundColor Red
    Write-Host "  winget install --id Cloudflare.cloudflared" -ForegroundColor Yellow
    exit 1
}
Write-Host "cloudflared: $cf"

# 1. 登录（会打开浏览器，选择你要绑定的域名所属的 Cloudflare 账号）
$cert = "$env:USERPROFILE\.cloudflared\cert.pem"
if (Test-Path $cert) {
    Write-Host "`n[1/5] 已登录（cert.pem 存在），跳过" -ForegroundColor Green
} else {
    Write-Host "`n[1/5] 即将打开浏览器进行 Cloudflare 授权..." -ForegroundColor Yellow
    Write-Host "      请在浏览器里选中你要使用的域名（如 runfit.xxx.com 的根域 xxx.com）" -ForegroundColor Yellow
    cloudflared tunnel login
    if (-not (Test-Path $cert)) {
        Write-Host "登录未完成，退出。" -ForegroundColor Red
        exit 1
    }
}

# 2. 创建隧道（已存在则跳过）
Write-Host "`n[2/5] 创建隧道 '$TUNNEL' ..." -ForegroundColor Yellow
$list = cloudflared tunnel list 2>&1 | Out-String
if ($list -match "\b$TUNNEL\b") {
    Write-Host "  隧道已存在，跳过创建" -ForegroundColor Green
} else {
    cloudflared tunnel create $TUNNEL
}

# 3. 读取隧道 ID 与凭据路径
$json = Get-ChildItem "$env:USERPROFILE\.cloudflared" -Filter "*.json" |
        Where-Object { $_.Name -notlike "cert*" } | Select-Object -First 1
if (-not $json) { Write-Host "找不到隧道凭据 json" -ForegroundColor Red; exit 1 }
$tunnelId = $json.BaseName
Write-Host "  隧道 ID: $tunnelId" -ForegroundColor Green

# 4. 询问绑定的域名
Write-Host "`n[3/5] 请输入要绑定的完整域名" -ForegroundColor Yellow
Write-Host "      例如：runfit.example.com  （example.com 必须已在 Cloudflare 托管）" -ForegroundColor DarkGray
$domain = Read-Host "域名"
if (-not $domain) { Write-Host "未输入，退出。" -ForegroundColor Red; exit 1 }

Write-Host "`n[4/5] 添加 DNS 路由 $domain -> $TUNNEL ..." -ForegroundColor Yellow
cloudflared tunnel route dns $TUNNEL $domain

# 5. 写配置文件
$cfgPath = "$env:USERPROFILE\.cloudflared\config.yml"
$cfg = @"
tunnel: $tunnelId
credentials-file: $($json.FullName)

ingress:
  - hostname: $domain
    service: http://127.0.0.1:$PORT
  - service: http_status:404
"@
[System.IO.File]::WriteAllText($cfgPath, $cfg, [System.Text.UTF8Encoding]::new($false))
Write-Host "  配置写入: $cfgPath" -ForegroundColor Green

# 6. 确保后端在跑
Write-Host "`n[5/5] 检查后端 ..." -ForegroundColor Yellow
$h = $null
try { $h = Invoke-RestMethod "http://127.0.0.1:$PORT/api/health" -TimeoutSec 3 } catch {}
if (-not $h -or -not $h.ok) {
    Write-Host "  后端未运行，先启动 ..." -ForegroundColor Yellow
    Start-Process -FilePath "python" -ArgumentList "-m","uvicorn","app.main:app","--host","0.0.0.0","--port","$PORT" -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
    Start-Sleep -Seconds 6
}
try {
    $h = Invoke-RestMethod "http://127.0.0.1:$PORT/api/health" -TimeoutSec 5
    Write-Host "  后端 OK: $($h | ConvertTo-Json -Compress)" -ForegroundColor Green
} catch {
    Write-Host "  后端启动失败，请手动启动" -ForegroundColor Red
}

# 7. 启动隧道
Write-Host "`n=== 启动隧道（保持此窗口开着）===" -ForegroundColor Cyan
Write-Host "访问地址：https://$domain" -ForegroundColor Green
Write-Host ""
cloudflared tunnel run $TUNNEL
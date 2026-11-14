# Expose this laptop's Ollama (qwen3:8b) to the deployed app through a Cloudflare quick tunnel (https).
#
#   powershell -ExecutionPolicy Bypass -File server\start-llm-tunnel.ps1
#
# The script lets the app's origins call Ollama (OLLAMA_ORIGINS), restarts Ollama, warms the model, opens the tunnel,
# and prints the app link with ?ollama=<tunnel>. Open that link once in each browser: the address is remembered there.
# Ctrl+C closes the tunnel. The tunnel has no password: anyone with the address can use the model, so run it only
# while you need it. Needs cloudflared (winget install Cloudflare.cloudflared) and Ollama with the model pulled.

param(
  [string]$AppUrl = 'https://interplanetary-survival-guide-marti-red.vercel.app',
  [string]$Model = 'qwen3:8b'
)

$ErrorActionPreference = 'Stop'
$origins = "$AppUrl,https://*.vercel.app,http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173"

# 1. Allow the app's origins (kept for later Ollama starts too).
[Environment]::SetEnvironmentVariable('OLLAMA_ORIGINS', $origins, 'User')
$env:OLLAMA_ORIGINS = $origins

# 2. Restart Ollama so it reads OLLAMA_ORIGINS.
$ollamaApp = Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama app.exe'
Get-Process -Name 'ollama app', 'ollama' -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2
Start-Process -FilePath $ollamaApp
for ($i = 0; $i -lt 60; $i++) {
  try { Invoke-RestMethod http://127.0.0.1:11434/api/tags -TimeoutSec 2 | Out-Null; break } catch { Start-Sleep -Seconds 1 }
}

# 3. Warm the model so the first question is not slow.
Write-Host "Loading $Model..."
$body = @{ model = $Model; messages = @(@{ role = 'user'; content = 'OK?' }); stream = $false; think = $false; keep_alive = '2h'; options = @{ num_predict = 2 } } | ConvertTo-Json -Depth 4
Invoke-RestMethod http://127.0.0.1:11434/api/chat -Method Post -Body $body -ContentType 'application/json' -TimeoutSec 180 | Out-Null

# 4. Open the tunnel. Ollama only accepts its own host name, so the tunnel rewrites the Host header to localhost.
$cloudflared = (Get-Command cloudflared -ErrorAction SilentlyContinue).Source
if (-not $cloudflared) { $cloudflared = "${env:ProgramFiles(x86)}\cloudflared\cloudflared.exe" }
Write-Host 'Opening the tunnel (Ctrl+C to close)...'
# cloudflared logs to stderr; Windows PowerShell would treat each line as an error, so do not stop on them.
$ErrorActionPreference = 'Continue'
& $cloudflared tunnel --no-autoupdate --url http://127.0.0.1:11434 --http-host-header localhost:11434 2>&1 | ForEach-Object {
  $line = "$_"
  if ($line -match '(https://[a-z0-9-]+\.trycloudflare\.com)') {
    $tunnel = $Matches[1]
    Write-Host ''
    Write-Host "Ollama tunnel:  $tunnel"
    Write-Host "Open the app:   $AppUrl/?ollama=$tunnel"
    Write-Host '(the copilot says it uses the remote model; Ctrl+C closes the tunnel)'
    Write-Host ''
  }
}

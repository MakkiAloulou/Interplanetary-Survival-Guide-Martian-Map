# Put this laptop's copilot (speech-to-text + qwen3:8b) behind the deployed app, through a Cloudflare quick tunnel.
#
#   powershell -ExecutionPolicy Bypass -File server\start-llm-tunnel.ps1
#
# 1. Starts Ollama and the copilot server (python -m server) if they are not running.
# 2. Opens an https tunnel to the copilot server.
# 3. Writes the tunnel's address to the team's GitHub gist, where the deployed app looks it up, so any browser that
#    opens the plain site link uses this laptop: voice and typed questions, as on the laptop.
# Ctrl+C closes the tunnel; the app then falls back to rules mode. The tunnel has no password: anyone with the
# address can use the copilot, so run it only while you need it.
# Needs cloudflared (winget install Cloudflare.cloudflared), Ollama with the model pulled, the marswalk conda env, and
# the GitHub CLI logged in (gh auth login) for the gist.

param(
  [string]$AppUrl = 'https://interplanetary-survival-guide-marti-red.vercel.app',
  [string]$Python = "$env:USERPROFILE\miniconda3\envs\marswalk\python.exe",
  # The gist the app reads (app/src/copilot/remote.ts, LAPTOP_GIST). Empty: find or create it in your gists.
  [string]$Gist = ''
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$gistFile = 'martian-map-laptop.json'
$server = 'http://127.0.0.1:8787'

function Test-Url($url) {
  try { Invoke-RestMethod $url -TimeoutSec 2 | Out-Null; return $true } catch { return $false }
}

# 1. Ollama, then the copilot server (it loads the model and whisper at start-up).
if (-not (Test-Url 'http://127.0.0.1:11434/api/tags')) {
  Write-Host 'Starting Ollama...'
  Start-Process -FilePath (Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama app.exe')
  for ($i = 0; $i -lt 60 -and -not (Test-Url 'http://127.0.0.1:11434/api/tags'); $i++) { Start-Sleep -Seconds 1 }
}
if (-not (Test-Url "$server/api/copilot/health")) {
  Write-Host 'Starting the copilot server (its own window; keep it open)...'
  Start-Process -FilePath $Python -ArgumentList '-m', 'server' -WorkingDirectory $repo
  for ($i = 0; $i -lt 180 -and -not (Test-Url "$server/api/copilot/health"); $i++) { Start-Sleep -Seconds 1 }
  if (-not (Test-Url "$server/api/copilot/health")) { throw "The copilot server did not start: run 'python -m server' from $repo to see why." }
}
Write-Host 'Copilot server is up (the model and whisper finish loading in the background).'

# The gist the app reads: given, else the one in your gists with our file, else a new secret gist.
$gh = (Get-Command gh -ErrorAction SilentlyContinue).Source
$tmp = Join-Path $env:TEMP $gistFile
function Publish-Address($tunnel) {
  if (-not $gh) { Write-Host 'GitHub CLI not found: the gist was not updated. Use the ?copilot= link below.'; return }
  @{ copilot = $tunnel; updated = (Get-Date).ToUniversalTime().ToString('o') } | ConvertTo-Json | Set-Content -Path $tmp -Encoding ascii
  if (-not $script:Gist) {
    $mine = (& $gh api gists) | ConvertFrom-Json
    $hit = $mine | Where-Object { $_.files.PSObject.Properties.Name -contains $gistFile } | Select-Object -First 1
    if ($hit) {
      $script:Gist = $hit.id
    } else {
      $created = & $gh gist create $tmp -d 'Martian Map: current address of the crew laptop copilot tunnel (server/start-llm-tunnel.ps1)'
      $script:Gist = ($created | Select-Object -Last 1).Split('/')[-1]
      Write-Host "Created gist $script:Gist. The app must know it: LAPTOP_GIST in app/src/copilot/remote.ts (or VITE_LAPTOP_GIST)."
    }
  }
  & $gh api -X PATCH "gists/$script:Gist" -F "files[$gistFile][content]=@$tmp" | Out-Null
  if ($LASTEXITCODE -eq 0) { Write-Host "Published to gist $script:Gist." } else { Write-Host 'Could not update the gist. Use the ?copilot= link below.' }
}

# 2. The tunnel to the copilot server.
$cloudflared = (Get-Command cloudflared -ErrorAction SilentlyContinue).Source
if (-not $cloudflared) { $cloudflared = "${env:ProgramFiles(x86)}\cloudflared\cloudflared.exe" }
Write-Host 'Opening the tunnel (Ctrl+C to close)...'
# cloudflared logs to stderr; Windows PowerShell would treat each line as an error, so do not stop on them.
$ErrorActionPreference = 'Continue'
& $cloudflared tunnel --no-autoupdate --url $server 2>&1 | ForEach-Object {
  $line = "$_"
  if ($line -match '(https://[a-z0-9-]+\.trycloudflare\.com)') {
    $tunnel = $Matches[1]
    Publish-Address $tunnel
    Write-Host ''
    Write-Host "Copilot tunnel: $tunnel"
    Write-Host "Open the app:   $AppUrl   (any browser; it finds this laptop within a minute)"
    Write-Host "Or directly:    $AppUrl/?copilot=$tunnel"
    Write-Host '(Ctrl+C closes the tunnel)'
    Write-Host ''
  }
}

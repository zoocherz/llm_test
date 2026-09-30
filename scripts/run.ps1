[CmdletBinding()]
param(
    [ValidateSet("Start", "Restart", "Stop", "Status")]
    [string]$Action = "Start",
    [switch]$OpenBrowser
)

$ErrorActionPreference = "Stop"
$workspace = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $workspace "llm-tester\backend"
$frontend = Join-Path $workspace "llm-tester\frontend"
$runtime = Join-Path $env:LOCALAPPDATA "LLMTester\runtime"
$statePath = Join-Path $runtime "services.json"
$backendLog = Join-Path $runtime "backend.log"
$backendErrorLog = Join-Path $runtime "backend-error.log"
$frontendLog = Join-Path $runtime "frontend.log"
$frontendErrorLog = Join-Path $runtime "frontend-error.log"
New-Item -ItemType Directory -Force -Path $runtime | Out-Null

function Get-State {
    if (-not (Test-Path $statePath)) { return $null }
    try { return Get-Content -Raw $statePath | ConvertFrom-Json } catch { return $null }
}
function Save-State($backendProcess, $frontendProcess, $activeLogs) {
    [pscustomobject]@{
        backendPid = if ($backendProcess) { $backendProcess.Id } else { $null }
        backendStartTicks = if ($backendProcess) { $backendProcess.StartTime.ToUniversalTime().Ticks } else { $null }
        frontendPid = if ($frontendProcess) { $frontendProcess.Id } else { $null }
        frontendStartTicks = if ($frontendProcess) { $frontendProcess.StartTime.ToUniversalTime().Ticks } else { $null }
        backendLog = $activeLogs.backendLog
        backendErrorLog = $activeLogs.backendErrorLog
        frontendLog = $activeLogs.frontendLog
        frontendErrorLog = $activeLogs.frontendErrorLog
        startedAt = (Get-Date).ToString("o")
    } | ConvertTo-Json | Set-Content -Encoding utf8 $statePath
}
function Stop-OwnedProcess([int]$processId, [string]$label, $expectedStartTicks) {
    $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
    if ($null -eq $process) { return }
    if ($null -eq $expectedStartTicks) {
        Write-Warning "$label PID $processId has no start-time ownership token; it was not stopped."
        return
    }
    $actualStartTicks = $process.StartTime.ToUniversalTime().Ticks
    if ($actualStartTicks -ne [long]$expectedStartTicks) {
        Write-Warning "$label PID $processId was reused by another process; it was not stopped."
        return
    }
    $previousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        & taskkill.exe /PID $processId /T /F 2>$null | Out-Null
    } finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
    for ($attempt = 0; $attempt -lt 10; $attempt++) {
        if (-not (Get-Process -Id $processId -ErrorAction SilentlyContinue)) { break }
        Start-Sleep -Milliseconds 100
    }
    $remainingProcess = Get-Process -Id $processId -ErrorAction SilentlyContinue
    if ($remainingProcess) {
        if ($remainingProcess.StartTime.ToUniversalTime().Ticks -ne [long]$expectedStartTicks) {
            throw "$label PID $processId changed during shutdown; it was not stopped."
        }
        Stop-Process -Id $processId -Force
        for ($attempt = 0; $attempt -lt 40; $attempt++) {
            if (-not (Get-Process -Id $processId -ErrorAction SilentlyContinue)) { break }
            Start-Sleep -Milliseconds 100
        }
    }
    if (Get-Process -Id $processId -ErrorAction SilentlyContinue) { throw "Failed to stop verified $label process tree PID $processId." }
    Write-Host "Stopped $label (PID $processId)."
}
function Test-Url([string]$url) {
    try { $response = Invoke-WebRequest -Uri $url -TimeoutSec 2 -UseBasicParsing; return $response.StatusCode -ge 200 -and $response.StatusCode -lt 500 } catch { return $false }
}
function Get-ListenerProcess([int]$port) {
    $connection = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $connection) { return $null }
    return Get-Process -Id $connection.OwningProcess -ErrorAction SilentlyContinue
}
function Get-Python {
    $candidates = @()
    if ($env:LLM_TESTER_PYTHON) { $candidates += $env:LLM_TESTER_PYTHON }
    $candidates += "C:\Users\zoode\AppData\Local\Programs\Python\Python311\python.exe"
    foreach ($candidate in $candidates | Select-Object -Unique) {
        if (-not (Test-Path $candidate)) { continue }
        & $candidate -c "import fastapi, uvicorn" 2>$null
        if ($LASTEXITCODE -eq 0) { return $candidate }
    }
    throw "Python with FastAPI was not found. Set LLM_TESTER_PYTHON to the full path to python.exe."
}
function Show-Status {
    $state = Get-State
    $backendUp = Test-Url "http://127.0.0.1:8010/health"
    $frontendUp = Test-Url "http://127.0.0.1:3000/"
    Write-Host "Backend  : $(if ($backendUp) { 'running at http://localhost:8010' } else { 'not responding' })"
    Write-Host "Frontend : $(if ($frontendUp) { 'running at http://localhost:3000' } else { 'not responding' })"
    if ($state) { Write-Host "Started  : $($state.startedAt)" }
    Write-Host "Logs     : $runtime"
    return ($backendUp -and $frontendUp)
}
function Start-System {
    $backendAlready = Test-Url "http://127.0.0.1:8010/health"
    $frontendAlready = Test-Url "http://127.0.0.1:3000/"
    if ($backendAlready -and $frontendAlready) { Show-Status; return }
    if ($frontendAlready) { throw "Frontend port 3000 is already in use by another process." }
    $launchId = (Get-Date).ToString("yyyyMMdd-HHmmss-fff") + "-" + $PID
    $backendLog = Join-Path $runtime "backend-$launchId.log"
    $backendErrorLog = Join-Path $runtime "backend-error-$launchId.log"
    $frontendLog = Join-Path $runtime "frontend-$launchId.log"
    $frontendErrorLog = Join-Path $runtime "frontend-error-$launchId.log"
    $effectivePath = $env:Path
    if (-not $effectivePath) { throw "Process Path is empty; services cannot be started." }
    [Environment]::SetEnvironmentVariable("PATH", $null, "Process")
    [Environment]::SetEnvironmentVariable("Path", $effectivePath, "Process")
    $python = Get-Python
    if ($backendAlready) { Write-Host "Reusing backend already listening on port 8010."; $backendProcess = $null } else {
    $backendProcess = Start-Process -FilePath $python -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8010") -WorkingDirectory $backend -WindowStyle Hidden -RedirectStandardOutput $backendLog -RedirectStandardError $backendErrorLog -PassThru
    }
    $node = (Get-Command "node.exe" -ErrorAction Stop).Source
    $vite = Join-Path $frontend "node_modules\vite\bin\vite.js"
    if (-not (Test-Path -LiteralPath $vite)) { throw "Vite is not installed. Run npm.cmd install in $frontend." }
    $frontendProcess = Start-Process -FilePath $node -ArgumentList @($vite, "--host", "127.0.0.1", "--port", "3000") -WorkingDirectory $frontend -WindowStyle Hidden -RedirectStandardOutput $frontendLog -RedirectStandardError $frontendErrorLog -PassThru
    if ($backendProcess) { Write-Host "Started backend process PID $($backendProcess.Id)." }
    Write-Host "Started frontend process PID $($frontendProcess.Id)."
    for ($attempt = 0; $attempt -lt 20; $attempt++) {
        if ($backendProcess -and $backendProcess.HasExited) { throw "Backend process exited early with code $($backendProcess.ExitCode). Check $backendErrorLog." }
        if ($frontendProcess.HasExited) { throw "Frontend process exited early with code $($frontendProcess.ExitCode). Check $frontendErrorLog." }
        if ((Test-Url "http://127.0.0.1:8010/health") -and (Test-Url "http://127.0.0.1:3000/")) {
            $ownedBackendProcess = if ($backendProcess) { Get-ListenerProcess 8010 } else { $null }
            $ownedFrontendProcess = if ($frontendProcess) { Get-ListenerProcess 3000 } else { $null }
            if ($backendProcess -and -not $ownedBackendProcess) { throw "Backend is ready but its listener PID could not be resolved." }
            if ($frontendProcess -and -not $ownedFrontendProcess) { throw "Frontend is ready but its listener PID could not be resolved." }
            $activeLogs = [pscustomobject]@{ backendLog = $backendLog; backendErrorLog = $backendErrorLog; frontendLog = $frontendLog; frontendErrorLog = $frontendErrorLog }
            Save-State $ownedBackendProcess $ownedFrontendProcess $activeLogs
            Write-Host "System is ready: http://localhost:3000"
            Write-Host "API docs:        http://localhost:8010/docs"
            if ($OpenBrowser) { Start-Process "http://localhost:3000" }
            return
        }
        Start-Sleep -Milliseconds 500
    }
    Write-Host "Services were started but did not become ready. Check logs: $runtime" -ForegroundColor Yellow
    exit 1
}
$state = Get-State
switch ($Action) {
    "Status" { if (-not (Show-Status)) { exit 1 } }
    "Stop" {
        if ($state) {
            if ($null -ne $state.backendPid) { Stop-OwnedProcess ([int]$state.backendPid) "backend" $state.backendStartTicks }
            if ($null -ne $state.frontendPid) { Stop-OwnedProcess ([int]$state.frontendPid) "frontend" $state.frontendStartTicks }
            Remove-Item $statePath -Force -ErrorAction SilentlyContinue
        } else { Write-Host "No services were recorded by this script." }
    }
    "Restart" {
        if ($state) {
            if ($null -ne $state.backendPid) { Stop-OwnedProcess ([int]$state.backendPid) "backend" $state.backendStartTicks }
            if ($null -ne $state.frontendPid) { Stop-OwnedProcess ([int]$state.frontendPid) "frontend" $state.frontendStartTicks }
            Remove-Item $statePath -Force -ErrorAction SilentlyContinue
        }
        Start-System
    }
    "Start" { Start-System }
}

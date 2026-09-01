# ==============================================================================
# AutoTask - Windows Service Installer (NSSM)
# Runs backend (FastAPI/uvicorn) and frontend (Vite preview) as Windows Services
# that start on boot and auto-restart on crash.
#
# Run this script once as Administrator:
#   Right-click PowerShell -> "Run as Administrator"
#   .\install_services.ps1
# ==============================================================================

$ProjectRoot  = "C:\Autotask\Autotask"
$BackendDir   = "$ProjectRoot\backend"
$FrontendDir  = "$ProjectRoot\frontend"
$VenvPython   = "$ProjectRoot\.venv\Scripts\python.exe"
$VenvUvicorn  = "$ProjectRoot\.venv\Scripts\uvicorn.exe"
$NssmDir      = "C:\nssm"
$NssmPath     = "$NssmDir\nssm.exe"

# ── Colour helpers ─────────────────────────────────────────────────────────────
function Info  { param($m) Write-Host "[INFO]  $m" -ForegroundColor Cyan }
function Ok    { param($m) Write-Host "[OK]    $m" -ForegroundColor Green }
function Warn  { param($m) Write-Host "[WARN]  $m" -ForegroundColor Yellow }
function Fail  { param($m) Write-Host "[ERROR] $m" -ForegroundColor Red; exit 1 }

# ── Auto-download NSSM if missing ─────────────────────────────────────────────
if (-not (Test-Path $NssmPath)) {
    Info "NSSM not found. Downloading automatically..."
    $ZipUrl  = "https://nssm.cc/ci/nssm-2.24-101-g897c7ad.zip"
    $ZipFile = "$env:TEMP\nssm.zip"
    $ExtractTo = "$env:TEMP\nssm_extract"

    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri $ZipUrl -OutFile $ZipFile -UseBasicParsing
        Expand-Archive -Path $ZipFile -DestinationPath $ExtractTo -Force

        # Find nssm.exe (win64 preferred)
        $NssmBin = Get-ChildItem -Path $ExtractTo -Recurse -Filter "nssm.exe" |
                   Where-Object { $_.FullName -like "*win64*" } |
                   Select-Object -First 1

        if (-not $NssmBin) {
            $NssmBin = Get-ChildItem -Path $ExtractTo -Recurse -Filter "nssm.exe" |
                       Select-Object -First 1
        }

        if (-not $NssmBin) { Fail "Could not find nssm.exe in downloaded archive." }

        New-Item -ItemType Directory -Force -Path $NssmDir | Out-Null
        Copy-Item -Path $NssmBin.FullName -Destination $NssmPath -Force
        Ok "NSSM downloaded and saved to $NssmPath"
    } catch {
        Fail "Failed to download NSSM: $_`nPlease manually download from https://nssm.cc/download and place nssm.exe at $NssmPath"
    }
} else {
    Ok "NSSM found at $NssmPath"
}

# ── Pre-flight checks ──────────────────────────────────────────────────────────
Info "Checking prerequisites..."

if (-not (Test-Path $VenvPython)) {
    Fail "Python venv not found at $VenvPython`nRun:  python -m venv .venv  then  .venv\Scripts\pip install -r requirements.txt"
}

if (-not (Test-Path $VenvUvicorn)) {
    Fail "uvicorn not found in venv.`nRun:  .venv\Scripts\pip install uvicorn[standard]"
}

$NodeCmd = Get-Command node -ErrorAction SilentlyContinue
if (-not $NodeCmd) {
    Fail "Node.js not found in PATH. Install Node.js from https://nodejs.org"
}

$NpmCmd = Get-Command npm -ErrorAction SilentlyContinue
if (-not $NpmCmd) {
    Fail "npm not found in PATH."
}

Ok "All prerequisites found."

# ── Build frontend (production) ────────────────────────────────────────────────
Info "Installing frontend dependencies..."
Push-Location $FrontendDir
& npm install
if ($LASTEXITCODE -ne 0) { Fail "npm install failed." }

Info "Building React frontend..."
& npm run build
if ($LASTEXITCODE -ne 0) { Fail "Frontend build failed." }
Pop-Location
Ok "Frontend built to $FrontendDir\dist"

# ── Create logs directory ──────────────────────────────────────────────────────
New-Item -ItemType Directory -Force -Path "$ProjectRoot\logs" | Out-Null

# ── Helper: install or re-configure a service ─────────────────────────────────
function Install-NssmService {
    param(
        [string]$Name,
        [string]$Exe,
        [string]$Args,
        [string]$WorkDir,
        [string]$LogFile
    )

    # Remove existing service if present
    $existing = Get-Service -Name $Name -ErrorAction SilentlyContinue
    if ($existing) {
        Info "Removing existing service: $Name"
        & $NssmPath stop   $Name confirm 2>$null
        Start-Sleep -Seconds 2
        & $NssmPath remove $Name confirm
        Start-Sleep -Seconds 2
    }

    Info "Installing service: $Name"
    # Install with just the executable — set arguments separately so NSSM
    # doesn't treat the whole "exe args" string as the application path.
    & $NssmPath install $Name $Exe
    & $NssmPath set $Name AppParameters  $Args
    & $NssmPath set $Name AppDirectory   $WorkDir
    & $NssmPath set $Name AppStdout      $LogFile
    & $NssmPath set $Name AppStderr      $LogFile
    & $NssmPath set $Name AppRotateFiles 1
    & $NssmPath set $Name AppRotateBytes 10485760
    & $NssmPath set $Name Start          SERVICE_AUTO_START
    & $NssmPath set $Name ObjectName     LocalSystem ""

    Ok "Service installed: $Name"
}

# ── 1. Backend service ─────────────────────────────────────────────────────────
Install-NssmService `
    -Name    "AutoTaskBackend" `
    -Exe     $VenvUvicorn `
    -Args    "main:app --host 0.0.0.0 --port 8001" `
    -WorkDir $BackendDir `
    -LogFile "$ProjectRoot\logs\backend.log"

# ── 2. Frontend service (vite preview of built dist) ──────────────────────────
$ViteCmd = "$FrontendDir\node_modules\.bin\vite.cmd"
if (-not (Test-Path $ViteCmd)) {
    $ViteObj = Get-Command vite -ErrorAction SilentlyContinue
    if ($ViteObj) {
        $ViteCmd = $ViteObj.Source
    } else {
        Fail "vite not found. Make sure npm install succeeded."
    }
}

Install-NssmService `
    -Name    "AutoTaskFrontend" `
    -Exe     $ViteCmd `
    -Args    "preview --host 0.0.0.0 --port 5173" `
    -WorkDir $FrontendDir `
    -LogFile "$ProjectRoot\logs\frontend.log"

# ── Start both services ────────────────────────────────────────────────────────
Info "Starting services..."
Start-Service -Name "AutoTaskBackend"  -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3
Start-Service -Name "AutoTaskFrontend" -ErrorAction SilentlyContinue
Start-Sleep -Seconds 5

$be = Get-Service -Name "AutoTaskBackend"  -ErrorAction SilentlyContinue
$fe = Get-Service -Name "AutoTaskFrontend" -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "=============================================" -ForegroundColor White
Write-Host "  AutoTask Services Status" -ForegroundColor White
Write-Host "=============================================" -ForegroundColor White

$beStatus = if ($be) { $be.Status } else { "NotFound" }
$feStatus = if ($fe) { $fe.Status } else { "NotFound" }

Write-Host ("  Backend  ({0,-10}) -> http://13.202.236.112:8001" -f $beStatus) `
    -ForegroundColor $(if ($beStatus -eq 'Running') { 'Green' } else { 'Red' })
Write-Host ("  Frontend ({0,-10}) -> http://13.202.236.112:5173" -f $feStatus) `
    -ForegroundColor $(if ($feStatus -eq 'Running') { 'Green' } else { 'Red' })

Write-Host "=============================================" -ForegroundColor White
Write-Host ""
Write-Host "  Logs:     $ProjectRoot\logs\" -ForegroundColor Gray
Write-Host "  Stop:     Stop-Service AutoTaskBackend; Stop-Service AutoTaskFrontend" -ForegroundColor Gray
Write-Host "  Remove:   .\uninstall_services.ps1" -ForegroundColor Gray
Write-Host ""

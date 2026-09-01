# ==============================================================================
# AutoTask - Remove Windows Services
# Run as Administrator
# ==============================================================================

$NssmPath = "C:\nssm\nssm.exe"

foreach ($svc in @("AutoTaskBackend", "AutoTaskFrontend")) {
    $existing = Get-Service -Name $svc -ErrorAction SilentlyContinue
    if ($existing) {
        Write-Host "Stopping and removing: $svc" -ForegroundColor Yellow
        & $NssmPath stop   $svc confirm 2>$null
        & $NssmPath remove $svc confirm
        Write-Host "Removed: $svc" -ForegroundColor Green
    } else {
        Write-Host "Not found: $svc" -ForegroundColor Gray
    }
}

Write-Host "Done." -ForegroundColor Green

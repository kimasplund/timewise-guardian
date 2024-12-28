# TimeWise Guardian Uninstallation Script
param(
    [switch]$KeepLogs = $false,
    [switch]$KeepConfig = $false,
    [switch]$Force = $false
)

# Ensure running as administrator
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error "Please run this script as Administrator"
    exit 1
}

# Set error action preference
$ErrorActionPreference = "Stop"

# Create log function
function Write-Log {
    param($Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] $Message"
    Add-Content -Path "$env:ProgramData\TimeWiseGuardian\uninstall.log" -Value "[$timestamp] $Message"
}

try {
    Write-Log "Starting TimeWise Guardian uninstallation..."

    # Stop and remove service
    Write-Log "Stopping and removing service..."
    if (Get-Service TimeWiseGuardian -ErrorAction SilentlyContinue) {
        Stop-Service TimeWiseGuardian -Force
        python -m twg.service remove
    }

    # Uninstall package
    Write-Log "Uninstalling TimeWise Guardian package..."
    python -m pip uninstall -y timewise-guardian-client

    # Clean up program files
    $programDir = "$env:ProgramData\TimeWiseGuardian"
    if (Test-Path $programDir) {
        Write-Log "Cleaning up program files..."
        
        # Backup config if requested
        if ($KeepConfig -and (Test-Path "$programDir\config.yaml")) {
            $backupDir = "$env:USERPROFILE\TimeWiseGuardian_Backup"
            New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
            Copy-Item "$programDir\config.yaml" "$backupDir\config.yaml"
            Write-Log "Configuration backed up to $backupDir\config.yaml"
        }

        # Backup logs if requested
        if ($KeepLogs -and (Test-Path "$programDir\logs")) {
            $backupDir = "$env:USERPROFILE\TimeWiseGuardian_Backup\logs"
            New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
            Copy-Item "$programDir\logs\*" $backupDir -Recurse
            Write-Log "Logs backed up to $backupDir"
        }

        # Remove program directory
        Remove-Item -Path $programDir -Recurse -Force
    }

    # Clean up registry
    Write-Log "Cleaning up registry..."
    $regKeys = @(
        "HKLM:\SOFTWARE\TimeWiseGuardian",
        "HKLM:\SYSTEM\CurrentControlSet\Services\TimeWiseGuardian"
    )
    foreach ($key in $regKeys) {
        if (Test-Path $key) {
            Remove-Item -Path $key -Recurse -Force
        }
    }

    # Clean up scheduled tasks
    Write-Log "Cleaning up scheduled tasks..."
    Get-ScheduledTask | Where-Object {$_.TaskName -like "TimeWiseGuardian*"} | Unregister-ScheduledTask -Confirm:$false

    Write-Log "Uninstallation completed successfully!"
    Write-Host "`nTimeWise Guardian has been uninstalled."
    if ($KeepConfig -or $KeepLogs) {
        Write-Host "Backups can be found in $env:USERPROFILE\TimeWiseGuardian_Backup"
    }

} catch {
    Write-Log "Uninstallation failed: $_"
    Write-Error $_
    exit 1
} 
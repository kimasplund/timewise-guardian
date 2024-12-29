# TimeWise Guardian Update Script
param(
    [int]$MaxMemoryMB = 100,
    [int]$CleanupIntervalMinutes = 5,
    [switch]$Debug = $false
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
    Add-Content -Path "$env:ProgramData\TimeWiseGuardian\update.log" -Value "[$timestamp] $Message"
}

try {
    Write-Log "Starting TimeWise Guardian update..."

    # Verify existing installation
    $programDir = "$env:ProgramData\TimeWiseGuardian"
    $configPath = "$programDir\config.yaml"
    if (-not (Test-Path $configPath)) {
        throw "TimeWise Guardian is not installed. Please run install.ps1 first."
    }

    # Stop the service
    Write-Log "Stopping TimeWise Guardian service..."
    if (Get-Service TimeWiseGuardian -ErrorAction SilentlyContinue) {
        Stop-Service TimeWiseGuardian
    }

    # Update pip and package
    Write-Log "Updating TimeWise Guardian..."
    python -m pip install --upgrade pip
    python -m pip install --upgrade timewise-guardian-client

    # Update memory management settings in config
    Write-Log "Updating configuration..."
    $config = Get-Content $configPath -Raw
    $yamlObject = ConvertFrom-Yaml $config

    # Add or update memory management section
    if (-not $yamlObject.ContainsKey("memory_management")) {
        $yamlObject["memory_management"] = @{}
    }
    $yamlObject["memory_management"]["max_client_memory_mb"] = $MaxMemoryMB
    $yamlObject["memory_management"]["cleanup_interval_minutes"] = $CleanupIntervalMinutes
    $yamlObject["memory_management"]["memory_threshold"] = 90
    $yamlObject["memory_management"]["debug_memory"] = $Debug.ToString().ToLower()

    # Update logging if debug is enabled
    if ($Debug -and -not $yamlObject.ContainsKey("logging")) {
        $yamlObject["logging"] = @{
            "level" = "DEBUG"
        }
    }

    # Save updated config
    $yamlObject | ConvertTo-Yaml | Set-Content $configPath

    # Start the service
    Write-Log "Starting TimeWise Guardian service..."
    Start-Service TimeWiseGuardian

    Write-Log "Update completed successfully!"
    Write-Host "`nTimeWise Guardian has been updated."
    Write-Host "Memory limit: $MaxMemoryMB MB"
    Write-Host "Cleanup interval: $CleanupIntervalMinutes minutes"
    Write-Host "Service status: $((Get-Service TimeWiseGuardian).Status)"

} catch {
    Write-Log "Update failed: $_"
    Write-Error $_
    exit 1
} 
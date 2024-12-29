# TimeWise Guardian Installation Script
param(
    [string]$HAUrl = "http://homeassistant.local:8123",
    [string]$HAToken = "",
    [int]$MaxMemoryMB = 100,
    [int]$CleanupIntervalMinutes = 5,
    [switch]$Force = $false,
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
    Add-Content -Path "$env:ProgramData\TimeWiseGuardian\install.log" -Value "[$timestamp] $Message"
}

try {
    Write-Log "Starting TimeWise Guardian installation..."

    # Create program directory
    $programDir = "$env:ProgramData\TimeWiseGuardian"
    if (-not (Test-Path $programDir)) {
        New-Item -ItemType Directory -Path $programDir | Out-Null
    }

    # Create logs directory
    $logDir = "$programDir\logs"
    if (-not (Test-Path $logDir)) {
        New-Item -ItemType Directory -Path $logDir | Out-Null
    }

    # Install Python if not present
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        Write-Log "Python not found. Installing Python..."
        $pythonUrl = "https://www.python.org/ftp/python/3.11.0/python-3.11.0-amd64.exe"
        $pythonInstaller = "$env:TEMP\python-installer.exe"
        Invoke-WebRequest -Uri $pythonUrl -OutFile $pythonInstaller
        Start-Process -FilePath $pythonInstaller -ArgumentList "/quiet", "InstallAllUsers=1", "PrependPath=1" -Wait
        Remove-Item $pythonInstaller
    }

    # Refresh environment variables
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

    # Install/Upgrade pip
    Write-Log "Upgrading pip..."
    python -m pip install --upgrade pip

    # Install TimeWise Guardian
    Write-Log "Installing TimeWise Guardian..."
    python -m pip install --upgrade timewise-guardian-client

    # Create configuration
    $configPath = "$programDir\config.yaml"
    if (-not (Test-Path $configPath) -or $Force) {
        Write-Log "Creating configuration file..."
        $computerName = $env:COMPUTERNAME
        $config = @"
ha_url: "$HAUrl"
ha_token: "$HAToken"

user_mapping:
  "$computerName\\$env:USERNAME": "$env:USERNAME"

categories:
  games:
    processes:
      - minecraft.exe
      - steam.exe
    browser_patterns:
      urls:
        - "*minecraft.net*"
        - "*steampowered.com*"

time_limits:
  games: 120  # 2 hours per day

notifications:
  warning_threshold: 10
  warning_intervals: [30, 15, 10, 5, 1]
  popup_duration: 10
  sound_enabled: true

memory_management:
  max_client_memory_mb: $MaxMemoryMB
  cleanup_interval_minutes: $CleanupIntervalMinutes
  memory_threshold: 90
  debug_memory: $($Debug.ToString().ToLower())
"@
        Set-Content -Path $configPath -Value $config
    }

    # Create service configuration
    $serviceConfig = @{
        Name = "TimeWiseGuardian"
        DisplayName = "TimeWise Guardian"
        Description = "Monitors computer usage and enforces time limits"
        BinaryPathName = "$(Get-Command python).Path -m twg.service"
        StartupType = "Automatic"
        DependsOn = @("LanmanServer")
    }

    # Install and start the service
    Write-Log "Installing Windows service..."
    if (Get-Service TimeWiseGuardian -ErrorAction SilentlyContinue) {
        Write-Log "Stopping existing service..."
        Stop-Service TimeWiseGuardian
        Write-Log "Removing existing service..."
        sc.exe delete TimeWiseGuardian
        Start-Sleep -Seconds 2
    }

    Write-Log "Creating new service..."
    New-Service @serviceConfig

    # Set recovery options
    Write-Log "Configuring service recovery options..."
    sc.exe failure TimeWiseGuardian reset= 86400 actions= restart/60000/restart/60000/restart/60000

    # Start service
    Write-Log "Starting service..."
    Start-Service TimeWiseGuardian

    # Enable debug logging if requested
    if ($Debug) {
        Write-Log "Enabling debug logging..."
        $logConfig = Get-Content $configPath
        $logConfig += "`nlogging:`n  level: DEBUG"
        Set-Content -Path $configPath -Value $logConfig
    }

    Write-Log "Installation completed successfully!"
    Write-Host "`nTimeWise Guardian has been installed and started."
    Write-Host "Configuration file: $configPath"
    Write-Host "Logs directory: $logDir"
    Write-Host "Service status: $((Get-Service TimeWiseGuardian).Status)"
    Write-Host "Memory limit: $MaxMemoryMB MB"
    Write-Host "Cleanup interval: $CleanupIntervalMinutes minutes"

} catch {
    Write-Log "Installation failed: $_"
    Write-Error $_
    exit 1
} 
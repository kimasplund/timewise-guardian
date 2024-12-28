# TimeWise Guardian Installation Script
param(
    [string]$HAUrl = "http://homeassistant.local:8123",
    [string]$HAToken = "",
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
"@
        Set-Content -Path $configPath -Value $config
    }

    # Install and start the service
    Write-Log "Installing Windows service..."
    python -m twg.service install
    Start-Service TimeWiseGuardian

    # Enable debug logging if requested
    if ($Debug) {
        Write-Log "Enabling debug logging..."
        $logConfig = Get-Content $configPath
        $logConfig += "`nlogging:`n  level: DEBUG"
        Set-Content -Path $configPath -Value $logConfig
    }

    Write-Log "Installation completed successfully!"
    Write-Host "`nTimeWise Guardian has been installed and started.`nConfiguration file: $configPath`nLogs directory: $programDir\logs"

} catch {
    Write-Log "Installation failed: $_"
    Write-Error $_
    exit 1
} 
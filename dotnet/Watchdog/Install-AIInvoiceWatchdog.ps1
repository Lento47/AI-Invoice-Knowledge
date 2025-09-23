[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$ExecutablePath,

    [Parameter(Mandatory = $false)]
    [string]$TaskName = "AIInvoiceFastAPIWatchdog",

    [Parameter(Mandatory = $false)]
    [int]$CheckIntervalSeconds = 30,

    [Parameter(Mandatory = $false)]
    [string]$LogDirectory = "$env:ProgramData\AIInvoice\Logs",

    [Parameter(Mandatory = $false)]
    [string]$FirewallRuleName = "AIInvoice FastAPI",

    [switch]$RunWatchdog,
    [switch]$Force
)

function Test-IsAdministrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Ensure-Directory {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

function Ensure-FirewallRule {
    param(
        [Parameter(Mandatory)]
        [string]$DisplayName,
        [Parameter(Mandatory)]
        [ValidateSet("Inbound", "Outbound")]
        [string]$Direction,
        [Parameter(Mandatory)]
        [string]$ProgramPath,
        [switch]$Force
    )

    $existing = Get-NetFirewallRule -DisplayName $DisplayName -ErrorAction SilentlyContinue
    if ($existing -and $Force.IsPresent) {
        $existing | Remove-NetFirewallRule -Confirm:$false
        $existing = $null
    }

    if (-not $existing) {
        New-NetFirewallRule -DisplayName $DisplayName -Direction $Direction -Program $ProgramPath -Action Allow -Profile Any | Out-Null
    }
}

function Install-Watchdog {
    param(
        [Parameter(Mandatory)]
        [string]$ExecutablePath,
        [Parameter(Mandatory)]
        [string]$TaskName,
        [Parameter(Mandatory)]
        [int]$CheckIntervalSeconds,
        [Parameter(Mandatory)]
        [string]$LogDirectory,
        [Parameter(Mandatory)]
        [string]$FirewallRuleName,
        [switch]$Force
    )

    if (-not (Test-IsAdministrator)) {
        throw "Installation requires administrative privileges. Restart PowerShell as Administrator."
    }

    if (-not (Test-Path -LiteralPath $ExecutablePath)) {
        throw "ExecutablePath '$ExecutablePath' was not found."
    }

    $resolvedExecutable = (Resolve-Path -LiteralPath $ExecutablePath).ProviderPath
    $interval = [Math]::Max($CheckIntervalSeconds, 5)

    $installRoot = Join-Path $env:ProgramData 'AIInvoice'
    Ensure-Directory -Path $installRoot
    Ensure-Directory -Path $LogDirectory

    $watchdogScriptPath = Join-Path $installRoot 'AIInvoiceWatchdog.ps1'
    Copy-Item -Path $PSCommandPath -Destination $watchdogScriptPath -Force
    Unblock-File -Path $watchdogScriptPath

    $arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$watchdogScriptPath`" -RunWatchdog -ExecutablePath `"$resolvedExecutable`" -CheckIntervalSeconds $interval -LogDirectory `"$LogDirectory`""

    $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arguments -WorkingDirectory (Split-Path $watchdogScriptPath)
    $triggers = @(
        New-ScheduledTaskTrigger -AtStartup
    )
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero)
    $principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -RunLevel Highest

    if ($Force.IsPresent -and (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue)) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    }

    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $triggers -Settings $settings -Principal $principal -Force | Out-Null
    Start-ScheduledTask -TaskName $TaskName

    Ensure-FirewallRule -DisplayName $FirewallRuleName -Direction Inbound -ProgramPath $resolvedExecutable -Force:$Force
    Ensure-FirewallRule -DisplayName "$FirewallRuleName (Outbound)" -Direction Outbound -ProgramPath $resolvedExecutable -Force:$Force

    Write-Host "Watchdog installed. Scheduled task '$TaskName' will monitor '$resolvedExecutable'."
    Write-Host "Log files are written to '$LogDirectory'."
}

function Start-WatchdogLoop {
    param(
        [Parameter(Mandatory)]
        [string]$ExecutablePath,
        [Parameter(Mandatory)]
        [int]$CheckIntervalSeconds,
        [Parameter(Mandatory)]
        [string]$LogDirectory
    )

    $resolvedExecutable = (Resolve-Path -LiteralPath $ExecutablePath).ProviderPath
    $interval = [Math]::Max($CheckIntervalSeconds, 5)
    Ensure-Directory -Path $LogDirectory
    $script:WatchdogLogFile = Join-Path $LogDirectory 'watchdog.log'

    Write-WatchdogLog -Level 'Info' -Message "Starting watchdog loop for '$resolvedExecutable' with $interval second interval."

    $processName = [System.IO.Path]::GetFileNameWithoutExtension($resolvedExecutable)

    while ($true) {
        try {
            if (-not (Test-Path -LiteralPath $resolvedExecutable)) {
                Write-WatchdogLog -Level 'Error' -Message "Executable missing at '$resolvedExecutable'."
            } else {
                $running = Get-Process -Name $processName -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $resolvedExecutable }
                if (-not $running) {
                    Write-WatchdogLog -Level 'Warning' -Message "Process not detected. Launching '$resolvedExecutable'."
                    Start-Process -FilePath $resolvedExecutable -WindowStyle Hidden | Out-Null
                }
            }
        }
        catch {
            Write-WatchdogLog -Level 'Error' -Message $_.Exception.Message
        }

        Start-Sleep -Seconds $interval
    }
}

function Write-WatchdogLog {
    param(
        [Parameter(Mandatory)]
        [ValidateSet('Info', 'Warning', 'Error')]
        [string]$Level,
        [Parameter(Mandatory)]
        [string]$Message
    )

    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $entry = "$timestamp [$Level] $Message"
    Add-Content -Path $script:WatchdogLogFile -Value $entry
}

if ($RunWatchdog.IsPresent) {
    if (-not $ExecutablePath) {
        throw "ExecutablePath is required when -RunWatchdog is specified."
    }

    if (-not (Test-Path -LiteralPath $ExecutablePath)) {
        throw "ExecutablePath '$ExecutablePath' was not found."
    }

    Start-WatchdogLoop -ExecutablePath $ExecutablePath -CheckIntervalSeconds $CheckIntervalSeconds -LogDirectory $LogDirectory
} else {
    if (-not $ExecutablePath) {
        throw "ExecutablePath is required to install the watchdog."
    }

    Install-Watchdog -ExecutablePath $ExecutablePath -TaskName $TaskName -CheckIntervalSeconds $CheckIntervalSeconds -LogDirectory $LogDirectory -FirewallRuleName $FirewallRuleName -Force:$Force
}

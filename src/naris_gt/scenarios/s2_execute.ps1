
param(
    [string]$LabRoot = "C:\NARIS-Lab\S2",
    [Parameter(Mandatory = $true)]
    [string]$TransferToken,
    [Parameter(Mandatory = $true)]
    [string]$TrialId,
    [string]$TransferUrl = "http://192.168.57.1:8766/s2-upload"
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($TransferToken) -or $TransferToken.Length -lt 24) {
    throw "A transfer token of at least 24 characters is required."
}

if ($TrialId -notmatch '^[0-9a-fA-F-]{36}$') {
    throw "Invalid trial ID format."
}

$ScenarioId = "S2"
$DegradationLevel = "L0"
$RunId = [guid]::NewGuid().ToString()
$ComputerName = $env:COMPUTERNAME

if ($ComputerName -ne "NARIS-WIN") {
    throw "Unexpected execution host: $ComputerName. Expected NARIS-WIN."
}

$RunDirectory = Join-Path $LabRoot $RunId
$EvidenceDirectory = Join-Path $RunDirectory "execution_log"
$ScriptDirectory = Join-Path $RunDirectory "scripts"

$TestScript = Join-Path $ScriptDirectory "naris_s2_marker.ps1"
$MarkerFile = Join-Path $RunDirectory "execution_marker.txt"
$EventLog = Join-Path $EvidenceDirectory "s2_raw_events.json"

$RunKeyPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
$RunValueName = "NARIS_S2_$($TrialId.Replace('-', '').Substring(0,12))"
$PersistenceCommand = "powershell.exe -NoProfile -File `"$TestScript`""

$Events = [System.Collections.Generic.List[object]]::new()
$PersistenceCreated = $false

function Add-S2Event {
    param(
        [string]$Action,
        [string]$ResourceType,
        [string]$ResourcePath,
        [hashtable]$Details
    )

    $Process = Get-Process -Id $PID

    $Event = [ordered]@{
        event_id = [guid]::NewGuid().ToString()
        experiment_id = $TrialId
        scenario_id = $ScenarioId
        degradation_level_id = $DegradationLevel
        run_id = $RunId
        sequence = $Events.Count + 1
        timestamp = [DateTime]::UtcNow.ToString("o")
        action = $Action
        host = $ComputerName
        process = @{
            name = $Process.ProcessName
            pid = $PID
        }
        resource = @{
            type = $ResourceType
            path = $ResourcePath
        }
        outcome = "success"
        details = $Details
    }

    $Events.Add($Event)
}

function Save-S2EventLog {
    $Events |
        ConvertTo-Json -Depth 10 |
        Set-Content -LiteralPath $EventLog -Encoding UTF8
}

try {
    New-Item -ItemType Directory -Path $RunDirectory -Force | Out-Null
    New-Item -ItemType Directory -Path $EvidenceDirectory -Force | Out-Null
    New-Item -ItemType Directory -Path $ScriptDirectory -Force | Out-Null

    # 1. Create a harmless marker script.
    $ScriptContent = @'
$MarkerPath = Join-Path $PSScriptRoot "..\execution_marker.txt"
" NARIS S2 BENIGN EXECUTION MARKER $(Get-Date -Format o)" |
    Set-Content -LiteralPath $MarkerPath -Encoding UTF8
'@

    Set-Content -LiteralPath $TestScript -Value $ScriptContent -Encoding UTF8

    $ScriptHash = (Get-FileHash -LiteralPath $TestScript -Algorithm SHA256).Hash

    Add-S2Event `
        -Action "create_test_script" `
        -ResourceType "file" `
        -ResourcePath $TestScript `
        -Details @{
            sha256 = $ScriptHash
            size_bytes = (Get-Item -LiteralPath $TestScript).Length
            script_type = "benign_powershell_marker"
        }

    # 2. Execute the benign script and verify its marker.
    $ChildProcess = Start-Process `
        -FilePath "powershell.exe" `
        -ArgumentList @(
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-File", "`"$TestScript`""
        ) `
        -Wait `
        -PassThru `
        -NoNewWindow

    if ($ChildProcess.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $MarkerFile)) {
        throw "Benign test process failed to create its execution marker."
    }

    $MarkerContent = Get-Content -LiteralPath $MarkerFile -Raw

    if ([string]::IsNullOrWhiteSpace($MarkerContent)) {
        throw "Execution marker is empty."
    }

    Add-S2Event `
        -Action "execute_test_process" `
        -ResourceType "process" `
        -ResourcePath $TestScript `
        -Details @{
            process_name = "powershell.exe"
            process_id = $ChildProcess.Id
            exit_code = $ChildProcess.ExitCode
            marker_path = $MarkerFile
            marker_sha256 = (Get-FileHash -LiteralPath $MarkerFile -Algorithm SHA256).Hash
        }

    # 3. Create a uniquely named, harmless HKCU Run-key artifact.
    if (-not (Test-Path -LiteralPath $RunKeyPath)) {
        New-Item -Path $RunKeyPath -Force | Out-Null
    }

    if ((Get-ItemProperty -Path $RunKeyPath -Name $RunValueName -ErrorAction SilentlyContinue)) {
        throw "The unique persistence value already exists. Refusing to overwrite it."
    }

    New-ItemProperty `
        -Path $RunKeyPath `
        -Name $RunValueName `
        -Value $PersistenceCommand `
        -PropertyType String `
        -Force:$false | Out-Null

    $PersistenceCreated = $true

    Add-S2Event `
        -Action "create_persistence_artifact" `
        -ResourceType "registry" `
        -ResourcePath "HKCU\Software\Microsoft\Windows\CurrentVersion\Run\$RunValueName" `
        -Details @{
            registry_hive = "HKEY_CURRENT_USER"
            registry_key = "Software\Microsoft\Windows\CurrentVersion\Run"
            value_name = $RunValueName
            value_type = "REG_SZ"
            configured_command = $PersistenceCommand
            execution_triggered = $false
        }

    # 4. Verify the exact registry value without executing it.
    $RegistryValue = Get-ItemPropertyValue `
        -Path $RunKeyPath `
        -Name $RunValueName

    if ($RegistryValue -ne $PersistenceCommand) {
        throw "Persistence registry value verification failed."
    }

    Add-S2Event `
        -Action "verify_persistence_artifact" `
        -ResourceType "registry" `
        -ResourcePath "HKCU\Software\Microsoft\Windows\CurrentVersion\Run\$RunValueName" `
        -Details @{
            value_name = $RunValueName
            configured_command = $RegistryValue
            verification = "exact_match"
            execution_triggered = $false
        }

    Save-S2EventLog

    # Upload only a complete, successful four-event run.
    $Headers = @{
        "X-NARIS-Token" = $TransferToken
    }

    $TransferResult = Invoke-RestMethod `
        -Uri $TransferUrl `
        -Method Post `
        -Headers $Headers `
        -ContentType "application/json" `
        -InFile $EventLog `
        -TimeoutSec 20

    if (
        $TransferResult.status -ne "received" -or
        $TransferResult.trial_id -ne $TrialId -or
        $TransferResult.scenario_id -ne "S2" -or
        $TransferResult.event_count -ne 4
    ) {
        throw "Host receiver did not confirm the expected S2 upload."
    }

    Write-Host ""
    Write-Host "NARIS S2 EXECUTION"
    Write-Host "----------------------------------------"
    Write-Host "Trial ID: $TrialId"
    Write-Host "Run ID: $RunId"
    Write-Host "Host: $ComputerName"
    Write-Host "Events: $($Events.Count)"
    Write-Host "Registry value: $RunValueName"
    Write-Host "Persistence execution triggered: No"
    Write-Host "Transfer file: $($TransferResult.filename)"
    Write-Host "Status: SUCCESS"
}
catch {
    $ErrorMessage = $_.Exception.Message

    if (Test-Path -LiteralPath $EvidenceDirectory) {
        try {
            $FailureEvent = [ordered]@{
                event_id = [guid]::NewGuid().ToString()
                experiment_id = $TrialId
                scenario_id = $ScenarioId
                degradation_level_id = $DegradationLevel
                run_id = $RunId
                sequence = $Events.Count + 1
                timestamp = [DateTime]::UtcNow.ToString("o")
                action = "scenario_execution_error"
                host = $ComputerName
                process = @{
                    name = "powershell"
                    pid = $PID
                }
                resource = @{
                    type = "experiment"
                    path = $RunDirectory
                }
                outcome = "failure"
                details = @{
                    error = $ErrorMessage
                    persistence_value_created = $PersistenceCreated
                }
            }

            $Events.Add($FailureEvent)
            Save-S2EventLog
        }
        catch {
            Write-Host "Could not save the partial execution log."
        }
    }

    Write-Host "S2 EXECUTION FAILED: $ErrorMessage"
    Write-Host "Local log: $EventLog"
    Write-Host "No failed or partial run was uploaded as a successful trial."
    exit 1
}

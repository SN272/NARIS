
param(
    [string]$LabRoot = "C:\NARIS-Lab\S1",
    [Parameter(Mandatory = $true)]
    [string]$TransferToken,
    [Parameter(Mandatory = $true)]
    [string]$TrialId,
    [string]$TransferUrl = "http://192.168.57.1:8766/s1-upload"
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($TransferToken)) {
    throw "Transfer token is required."
}

$DegradationLevel = "L0"
$ScenarioId = "S1"
$RunId = [guid]::NewGuid().ToString()

$RunDirectory = Join-Path $LabRoot $RunId
$StagingDirectory = Join-Path $RunDirectory "transfer_staging"
$EvidenceDirectory = Join-Path $RunDirectory "execution_log"

$TestFile = Join-Path $RunDirectory "synthetic_sensitive_data.txt"
$StagedFile = Join-Path $StagingDirectory "synthetic_sensitive_data.txt"
$EventLog = Join-Path $EvidenceDirectory "s1_raw_events.json"

$Events = [System.Collections.Generic.List[object]]::new()

function Add-GroundTruthEvent {
    param(
        [string]$Action,
        [string]$Outcome,
        [string]$ResourcePath,
        [hashtable]$Details = @{}
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
        host = $env:COMPUTERNAME
        process = @{
            name = $Process.ProcessName
            pid = $PID
        }
        resource = @{
            type = "file"
            path = $ResourcePath
        }
        outcome = $Outcome
        details = $Details
    }

    $Events.Add($Event)
}

function Save-EventLog {
    $Events |
        ConvertTo-Json -Depth 8 |
        Set-Content -Path $EventLog -Encoding UTF8
}

try {
    New-Item -ItemType Directory -Path $RunDirectory -Force | Out-Null
    New-Item -ItemType Directory -Path $StagingDirectory -Force | Out-Null
    New-Item -ItemType Directory -Path $EvidenceDirectory -Force | Out-Null

    # 1. Create synthetic test file.
    $SyntheticContent = @"
NARIS CONTROLLED TEST DATA
Scenario: S1
Trial ID: $TrialId
Run ID: $RunId
Degradation: L0
Classification: Synthetic
"@

    Set-Content -Path $TestFile -Value $SyntheticContent -Encoding UTF8

    $InitialHash = (Get-FileHash -Path $TestFile -Algorithm SHA256).Hash

    Add-GroundTruthEvent `
        -Action "create_test_file" `
        -Outcome "success" `
        -ResourcePath $TestFile `
        -Details @{
            sha256 = $InitialHash
            size_bytes = (Get-Item $TestFile).Length
        }

    # 2. Access file.
    $FileMetadata = Get-Item -LiteralPath $TestFile

    Add-GroundTruthEvent `
        -Action "access_file" `
        -Outcome "success" `
        -ResourcePath $TestFile `
        -Details @{
            sha256 = $InitialHash
            size_bytes = $FileMetadata.Length
        }

    # 3. Read file.
    $ReadContent = Get-Content -LiteralPath $TestFile -Raw

    if ([string]::IsNullOrWhiteSpace($ReadContent)) {
        throw "Synthetic file was unexpectedly empty."
    }

    Add-GroundTruthEvent `
        -Action "read_file" `
        -Outcome "success" `
        -ResourcePath $TestFile `
        -Details @{
            bytes_read = [System.Text.Encoding]::UTF8.GetByteCount($ReadContent)
            sha256 = $InitialHash
        }

    # 4. Stage local copy.
    Copy-Item -LiteralPath $TestFile -Destination $StagedFile

    $StagedHash = (Get-FileHash -Path $StagedFile -Algorithm SHA256).Hash

    if ($InitialHash -ne $StagedHash) {
        throw "Staged file hash mismatch."
    }

    Add-GroundTruthEvent `
        -Action "stage_file_transfer" `
        -Outcome "success" `
        -ResourcePath $StagedFile `
        -Details @{
            source_path = $TestFile
            source_sha256 = $InitialHash
            staged_sha256 = $StagedHash
            transfer_type = "local_copy"
        }

    Save-EventLog

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
        $TransferResult.event_count -ne 4
    ) {
        throw "Host receiver did not confirm the expected trial-bound upload."
    }

    Write-Host ""
    Write-Host "NARIS TRIAL-AWARE S1 EXECUTION"
    Write-Host "----------------------------------------"
    Write-Host "Trial ID: $TrialId"
    Write-Host "Scenario: S1"
    Write-Host "Degradation: L0"
    Write-Host "Run ID: $RunId"
    Write-Host "Events: $($Events.Count)"
    Write-Host "Original SHA256: $InitialHash"
    Write-Host "Staged SHA256: $StagedHash"
    Write-Host "Transfer file: $($TransferResult.filename)"
    Write-Host "Status: SUCCESS"
}
catch {
    $ErrorMessage = $_.Exception.Message

    if (Test-Path $EvidenceDirectory) {
        try {
            Add-GroundTruthEvent `
                -Action "scenario_execution_error" `
                -Outcome "failure" `
                -ResourcePath $RunDirectory `
                -Details @{ error = $ErrorMessage }

            Save-EventLog
        }
        catch {
            Write-Host "Could not save failure log."
        }
    }

    Write-Host "S1 EXECUTION FAILED: $ErrorMessage"
    Write-Host "Local log: $EventLog"
    exit 1
}

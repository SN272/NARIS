
param(
    [Parameter(Mandatory = $true)]
    [string]$ExperimentId,

    [Parameter(Mandatory = $true)]
    [string]$Token,

    [string]$ServerUrl = "http://192.168.57.1:8765/collect"
)

$ErrorActionPreference = "Stop"

Write-Host "NARIS Windows Collector"
Write-Host "======================="

$os = Get-CimInstance Win32_OperatingSystem
$computer = Get-CimInstance Win32_ComputerSystem
$processor = Get-CimInstance Win32_Processor |
    Select-Object -First 1

$network = Get-NetIPConfiguration |
    ForEach-Object {
        [PSCustomObject]@{
            Interface = $_.InterfaceAlias
            IPv4 = @(
                $_.IPv4Address |
                ForEach-Object { $_.IPAddress }
            )
            Gateway = @(
                $_.IPv4DefaultGateway |
                ForEach-Object { $_.NextHop }
            )
        }
    }

$record = @{
    schema_version = "1.0"
    source = "windows"
    hostname = $env:COMPUTERNAME
    collected_at = (Get-Date).ToUniversalTime().ToString("o")

    operating_system = @{
        caption = $os.Caption
        version = $os.Version
        build = $os.BuildNumber
        architecture = $os.OSArchitecture
        last_boot_time = $os.LastBootUpTime.ToUniversalTime().ToString("o")
    }

    hardware = @{
        manufacturer = $computer.Manufacturer
        model = $computer.Model
        total_memory_bytes = $computer.TotalPhysicalMemory
        processor = $processor.Name
        logical_processors = $computer.NumberOfLogicalProcessors
    }

    network_interfaces = @($network)
}

$payload = @{
    experiment_id = $ExperimentId
    token = $Token
    source = "windows"
    record = $record
}

$json = $payload | ConvertTo-Json -Depth 10

Write-Host "`nCollected Windows system information."
Write-Host "Sending collection to NARIS host..."

$response = Invoke-RestMethod `
    -Uri $ServerUrl `
    -Method Post `
    -ContentType "application/json" `
    -Body $json `
    -TimeoutSec 30

Write-Host "`nServer response:"
$response | Format-List

Write-Host "Windows collection submitted successfully."

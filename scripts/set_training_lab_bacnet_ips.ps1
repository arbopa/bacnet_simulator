param(
    [string]$ProjectPath = "sample_projects\\training_lab.yaml",
    [string]$PrimaryIp = "192.168.1.114",
    [string]$Prefix = "192.168.1",
    [int]$StartHost = 211,
    [int]$Port = 47808
)

$project = Get-Content $ProjectPath -Raw | ConvertFrom-Json

for ($i = 0; $i -lt $project.devices.Count; $i++) {
    if ($i -eq 0) {
        $project.devices[$i].bacnet_ip = $PrimaryIp
    } else {
        $project.devices[$i].bacnet_ip = "$Prefix.$($StartHost + $i - 1)"
    }
    $project.devices[$i].bacnet_port = $Port
}

$project | ConvertTo-Json -Depth 100 | Set-Content $ProjectPath
Write-Host "Updated $($project.devices.Count) devices in $ProjectPath"

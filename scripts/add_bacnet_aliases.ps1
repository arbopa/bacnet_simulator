param(
    [string]$InterfaceAlias = "Ethernet",
    [string]$Prefix = "192.168.1",
    [int]$StartHost = 211,
    [int]$Count = 21,
    [int]$PrefixLength = 24
)

$existing = Get-NetIPAddress -InterfaceAlias $InterfaceAlias -AddressFamily IPv4 -ErrorAction Stop |
    Select-Object -ExpandProperty IPAddress

for ($i = 0; $i -lt $Count; $i++) {
    $ip = "$Prefix.$($StartHost + $i)"
    if ($existing -contains $ip) {
        Write-Host "Skipping existing alias $ip"
        continue
    }

    Write-Host "Adding alias $ip/$PrefixLength on $InterfaceAlias"
    New-NetIPAddress -InterfaceAlias $InterfaceAlias -IPAddress $ip -PrefixLength $PrefixLength -AddressFamily IPv4 | Out-Null
}

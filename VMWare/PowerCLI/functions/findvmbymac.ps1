
function FindVMbyMac {
    $vCenter = $args[0]
    $match_mac = $args[1]

    Connect-VCenter $vCenter

    get-vm | Get-NetworkAdapter | where {$_.macaddress -eq $match_mac} | select parent, macaddress
}

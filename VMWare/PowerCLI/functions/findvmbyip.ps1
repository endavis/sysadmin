

function FindVMbyIP {
    $vCenter = $args[0]
    $match_ip = $args[1]

    Connect-VCenter $vCenter

    get-vm | where {$_.Guest.IPAddress -contains $match_ip} | select name, @{N="IP Address";E={@($_.guest.IPAddress)}}
}

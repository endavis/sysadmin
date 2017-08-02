

function Connect-Vcenter
{
 $vCenter = $args[0]
 $Credential = $args[1]

 $SessionID = ($global:DefaultVIServers | Where-Object -FilterScript {$_.name -eq $vCenter}).sessionId
 if ($SessionID) {Connect-VIServer -Server $vCenter -Session $SessionID}
 elseif ($Credential) {Connect-VIServer -Server $vCenter -Credential $Credential}
 else {Connect-VIServer -Server $vCenter}
}
#Connect-Viserver #vcenterserver                                                                
                                                               
 function _GetEventsHelper {
    $hosts = Get-VMHost
    $match = $args[0]
                                                            
    foreach ($thost in $hosts) {                                                                
        $events = Get-VIEvent -Entity $thost
        $hostname = $thost.Name
        foreach ($event in $events) {
           if ($event.FullFormattedMessage.StartsWith($match)) {
                $Obj = New-Object PSObject                                                               
                $Obj | Add-Member -Name VMhost -MemberType NoteProperty -Value $hostname
                $Obj | Add-Member -Name Time -MemberType NoteProperty -Value $event.CreatedTime
                $Obj | Add-Member -Name Event -MemberType NoteProperty -Value $event.FullFormattedMessage  
                $Obj      
            }
        }

    }
}

function GetVServerEvents {
    $match = $args[0]

    _GetEventsHelper($match) | Export-Csv -NoTypeInformation .\Hostevents.csv 
}
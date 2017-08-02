
function FindVMbyNet {
    $vCenter = $args[0]
    $matchnet = $args[1] # 10.183.137*

    Connect-VCenter $vCenter

    foreach($vm in (Get-VM)){
  
      $vmIP = $vm.Guest.IPAddress
      foreach($ip in $vmIP){
        if($ip -like $matchnet) {
          ($vm.Name + ',' + $ip)
        }
      }
    }
}

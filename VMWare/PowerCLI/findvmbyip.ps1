
#requires -Modules VMware.VimAutomation.Core

param( $server, $match_ip)

Connect-VIServer -Server $server

Get-VM | %{
      $vmIPs = $_.Guest.IPAddress
      foreach($ip in $vmIPs) {
          if ($ip -eq $match_ip) {
              "Found VM with matching address: {0}" -f $_.Name
          }
      }
  }



function adddisk {

    $vmn = $args[0]
    $datastoren = $args[1]

    $vm = Get-VM $vmn

    $ds = Get-Datastore $datastoren

    $dsava = $ds.CapacityGB - 1

    New-HardDisk -VM $vm -Datastore $ds -CapacityGB $dsava
}

function mountcluster {
    $vcenter = $args[0]
    $cluster = $args[1]
    $dsname = $args[2]
    $nfshost = $args[3]
    $path = $args[4]


    $srv = Connect-viserver $vcenter

    $hosts = Get-VMHost -location $cluster

    Foreach ($hst in $hosts) {
        ("Adding datastore to " + $hst.Name)
        New-Datastore -Name $dsname -Nfs -NfsHost $nfshost -Path $path -VMHost $hst
    }
    Disconnect-VIServer -Server $srv -Confirm:$false -Force
}

function checkforslvolume {
   $vcenter = $args[0]
   $path = $args[1]

   $srv = Connect-viserver $vcenter

   $datastores = Get-Datastore

   Foreach ($ds in $datastores) {
        if ($ds.RemotePath -match $path) {
            ("Datastore " +  $ds.Name + " with Remote Path: " + $ds.RemotePath + " is ID: " + $path)
        }
   }
   Disconnect-VIServer -Server $srv -Confirm:$false -Force
}
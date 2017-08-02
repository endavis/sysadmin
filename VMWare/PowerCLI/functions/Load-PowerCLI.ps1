function Load-PowerCLI
{
 Get-Module -Name VMware* -ListAvailable | Import-Module -Scope Global
}


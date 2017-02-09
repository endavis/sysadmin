# Load own custom functions at startup
$OwnFunctionsDir = "$env:USERPROFILE\Documents\WindowsPowerShell\functions"
Write-Host "Loading own PowerShell functions from:" -ForegroundColor Green
Write-Host "$OwnFunctionsDir" -ForegroundColor Yellow
Get-ChildItem "$OwnFunctionsDir\*.ps1" | %{.$_}
Write-Host ''
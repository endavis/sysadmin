# Load own custom functions at startup
$OwnFunctionsDir = "$env:USERPROFILE\Documents\WindowsPowerShell\functions"
Write-Host "Loading own PowerShell functions from:" -ForegroundColor Green
Write-Host "$OwnFunctionsDir" -ForegroundColor Yellow
Foreach ($file in (Get-ChildItem -recurse "$OwnFunctionsDir\*.ps1")) {
  "loading " + $file
  %{.$file} 
}
Write-Host 'Done'

# Lets the browser open Optilens at http://optilens:8002/ by mapping the name "optilens" to this PC.
# Needs administrator rights (Windows hosts file).
$hosts = "$env:SystemRoot\System32\drivers\etc\hosts"
if (Select-String -Path $hosts -Pattern '^\s*127\.0\.0\.1\s+optilens\s*$' -Quiet) {
    Write-Host "The 'optilens' address is already set up."
    exit 0
}
Add-Content -Path $hosts -Value "`r`n127.0.0.1 optilens" -Encoding ASCII
ipconfig /flushdns | Out-Null
Write-Host "Added: 127.0.0.1 optilens"

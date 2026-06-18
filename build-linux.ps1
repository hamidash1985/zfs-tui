param()

$ErrorActionPreference = "Stop"
$Image = "zfs-tui-builder"
$ScriptDir = Split-Path -Parent $PSScriptRoot

Write-Host "==> Building Docker image: $Image"
docker build -t $Image -f "$ScriptDir/Dockerfile.build" $ScriptDir

Write-Host "`n==> Building zfs-tui Linux executable..."
New-Item -ItemType Directory -Force -Path "$ScriptDir/dist" | Out-Null

docker run --rm `
    -v "${ScriptDir}:/project" `
    -v "${ScriptDir}/dist:/output" `
    $Image

Write-Host "`n==> Done! Executable at: $ScriptDir/dist/zfs-tui"
Get-ChildItem "$ScriptDir/dist/zfs-tui" | Select-Object Name, Length

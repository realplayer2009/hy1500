# Install and start the standalone Qt Android app.
# Usage: powershell -File android/provision_apk.ps1 -DeviceAddr <IP>:<PORT>
param(
    [Parameter(Mandatory=$true)]
    [string]$DeviceAddr,
    [string]$ApkPath = (Join-Path $PSScriptRoot 'dist/RS485Control-arm64-v8a-debug.apk')
)

$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $ApkPath -PathType Leaf)) {
    throw "Native APK missing: $ApkPath. Run android/build_apk.sh first."
}

Write-Host "Connecting to $DeviceAddr ..."
adb connect $DeviceAddr
if ($LASTEXITCODE -ne 0) { throw 'ADB connection failed.' }

Write-Host 'Installing native RS485Control APK ...'
adb -s $DeviceAddr install -r $ApkPath
if ($LASTEXITCODE -ne 0) { throw 'Native APK installation failed.' }

Write-Host 'Starting native RS485Control ...'
adb -s $DeviceAddr shell am start -W -n com.rs485.control/.MainActivity
if ($LASTEXITCODE -ne 0) { throw 'Native app start failed.' }

Write-Host 'Native app started. Verify serial port access on the device separately.'

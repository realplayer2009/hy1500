# Provisioning script for new devices
# Usage: powershell -File android/provision.ps1 -DeviceAddr <设备IP>:<端口>

param(
    [Parameter(Mandatory=$true)]
    [string]$DeviceAddr
)

$ErrorActionPreference='SilentlyContinue'

Write-Host "Connecting to $DeviceAddr ..."
adb connect $DeviceAddr | Out-Null

Write-Host "Installing RS485Launcher APK ..."
adb -s $DeviceAddr install -r android/dist/RS485Control-arm64-v8a-debug.apk

Write-Host "Configuring Termux environment ..."
adb -s $DeviceAddr shell 'export PREFIX=/data/data/com.termux/files/usr; export PATH=$PREFIX/bin:$PATH; termux-wake-lock'

Write-Host "Starting launcher ..."
adb -s $DeviceAddr shell am start -n com.rs485.launcher/.MainActivity

Write-Host "Provisioning complete."

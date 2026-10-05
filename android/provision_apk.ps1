# Install and start the standalone Qt Android app.
# Usage: powershell -File android/provision_apk.ps1 -DeviceAddr <IP>:<PORT> [-Kiosk]
param(
    [Parameter(Mandatory=$true)]
    [string]$DeviceAddr,
    [string]$ApkPath = (Join-Path $PSScriptRoot 'dist/RS485Control-arm64-v8a-debug.apk'),
    [switch]$Kiosk
)

$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $ApkPath -PathType Leaf)) {
    throw "Native APK missing: $ApkPath. Run android/build_apk.sh first."
}

Write-Host "Connecting to $DeviceAddr ..."
adb connect $DeviceAddr
if ($LASTEXITCODE -ne 0) { throw 'ADB connection failed.' }

Write-Host 'Installing native RS485Control APK ...'
adb -s $DeviceAddr install --no-streaming -r $ApkPath
if ($LASTEXITCODE -ne 0) { throw 'Native APK installation failed.' }

if ($Kiosk) {
    Write-Host 'Configuring the device owner for system navigation lock ...'
    $owners = adb -s $DeviceAddr shell dpm list-owners
    if ($LASTEXITCODE -ne 0) { throw 'Failed to read device owners.' }
    if (($owners -join "`n") -notmatch 'com\.rs485\.control/\.?(?:com\.rs485\.control\.)?KioskAdminReceiver') {
        adb -s $DeviceAddr shell dpm set-device-owner --user 0 com.rs485.control/.KioskAdminReceiver
        if ($LASTEXITCODE -ne 0) { throw 'Failed to configure the device owner. Resolve the reported account/owner conflict without clearing device data.' }
    }
    adb -s $DeviceAddr shell dpm set-active-admin --user 0 com.rs485.control/.KioskAdminReceiver
    if ($LASTEXITCODE -ne 0) { throw 'Failed to activate the kiosk device admin.' }
    Write-Host 'Setting RS485Control as the default Home ...'
    adb -s $DeviceAddr shell cmd package set-home-activity --user 0 com.rs485.control/.MainActivity
    if ($LASTEXITCODE -ne 0) { throw 'Failed to set the default Home.' }
    Write-Host 'Configuring the panel engineering auto-start and watchdog ...'
    adb -s $DeviceAddr shell settings put system xzjh_auto_boot_package_name com.rs485.control
    if ($LASTEXITCODE -ne 0) { throw 'Failed to configure panel auto-start.' }
    adb -s $DeviceAddr shell settings put system xzjh_daemon_package_name com.rs485.control
    if ($LASTEXITCODE -ne 0) { throw 'Failed to configure panel watchdog.' }
}

adb -s $DeviceAddr shell am force-stop com.rs485.control
if ($LASTEXITCODE -ne 0) { throw 'Failed to stop the previous app instance.' }

Write-Host 'Starting native RS485Control ...'
adb -s $DeviceAddr shell am start -W -n com.rs485.control/.MainActivity
if ($LASTEXITCODE -ne 0) { throw 'Native app start failed.' }

Write-Host 'Native app started.'

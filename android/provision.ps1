# Install the existing Termux launcher on a device with Termux/X11 configured.
# Usage: powershell -File android/provision.ps1 -DeviceAddr <IP>:<PORT> -LauncherApk <launcher.apk>

param(
    [Parameter(Mandatory=$true)]
    [string]$DeviceAddr,
    [string]$LauncherApk = (Join-Path $PSScriptRoot 'dist/RS485Launcher-debug.apk')
)

$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $LauncherApk -PathType Leaf)) {
    throw "Termux launcher APK missing: $LauncherApk. Supply the existing com.rs485.launcher APK; build_apk.sh builds the separate native app."
}

Write-Host "Connecting to $DeviceAddr ..."
adb connect $DeviceAddr
if ($LASTEXITCODE -ne 0) { throw 'ADB connection failed.' }

foreach ($package in @('com.termux', 'com.termux.x11')) {
    $packagePath = adb -s $DeviceAddr shell pm path $package
    if ($LASTEXITCODE -ne 0 -or -not ($packagePath -match '^package:')) {
        throw "Required app missing: $package. Configure Termux/X11 before installing the launcher."
    }
}

Write-Host 'Installing Termux launcher ...'
adb -s $DeviceAddr install -r $LauncherApk
if ($LASTEXITCODE -ne 0) { throw 'Termux launcher installation failed.' }

# Let the launcher use its RUN_COMMAND chain so the Termux wake lock can work.
Write-Host 'Starting Termux launcher ...'
adb -s $DeviceAddr shell am start -W -n com.rs485.launcher/.MainActivity
if ($LASTEXITCODE -ne 0) { throw 'Termux launcher start failed.' }

Write-Host 'Launcher started. Verify RS485Control, X11 and the Termux wake lock as described in docs/DEBUGGING_GUIDE.md.'

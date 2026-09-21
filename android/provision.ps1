# Provisioning script for new devices
# Usage: powershell -File android/provision.ps1 -DeviceAddr <设备IP>:<端口>

param(
    [Parameter(Mandatory=$true)]
    [string]$DeviceAddr
)

# TODO: 实现设备预装流程
# 1. adb connect $DeviceAddr
# 2. 安装 RS485Launcher.apk
# 3. 注册为 HOME/桌面
# 4. 设置屏幕常亮
# 5. 配置 Termux 环境

Write-Host "Provisioning script placeholder. Implement device setup here."

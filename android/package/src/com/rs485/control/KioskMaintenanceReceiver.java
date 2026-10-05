package com.rs485.control;

import android.app.admin.DevicePolicyManager;
import android.content.BroadcastReceiver;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;

public class KioskMaintenanceReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context context, Intent intent) {
        if (!"com.rs485.control.MAINTENANCE".equals(intent.getAction())) {
            return;
        }
        DevicePolicyManager policy = (DevicePolicyManager) context.getSystemService(Context.DEVICE_POLICY_SERVICE);
        if (!policy.isDeviceOwnerApp(context.getPackageName())) {
            return;
        }
        boolean maintenance = intent.getBooleanExtra("enabled", false);
        context.getSharedPreferences("kiosk", Context.MODE_PRIVATE).edit()
            .putBoolean("maintenance", maintenance).commit();
        policy.setLockTaskPackages(new ComponentName(context, KioskAdminReceiver.class),
            maintenance ? new String[] {} : new String[] {context.getPackageName()});
    }
}

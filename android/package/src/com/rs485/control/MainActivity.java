package com.rs485.control;

import android.os.Bundle;
import android.app.ActivityManager;
import android.app.admin.DevicePolicyManager;
import android.content.ComponentName;
import android.util.Log;
import android.view.KeyEvent;
import android.view.View;
import android.view.WindowManager;
import org.qtproject.qt5.android.bindings.QtActivity;

public class MainActivity extends QtActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        setFullscreen(true);
    }

    @Override
    public boolean dispatchKeyEvent(KeyEvent event) {
        // Qt handles Back before onBackPressed, so consume both edges here.
        if (event.getKeyCode() == KeyEvent.KEYCODE_BACK) {
            return true;
        }
        return super.dispatchKeyEvent(event);
    }

    @Override
    public void onResume() {
        super.onResume();
        DevicePolicyManager policy = (DevicePolicyManager) getSystemService(DEVICE_POLICY_SERVICE);
        if (getSharedPreferences("kiosk", MODE_PRIVATE).getBoolean("maintenance", false)) {
            return;
        }
        if (policy.isDeviceOwnerApp(getPackageName())) {
            ComponentName admin = new ComponentName(this, KioskAdminReceiver.class);
            policy.setLockTaskPackages(admin, new String[] {getPackageName()});
            policy.setLockTaskFeatures(admin, DevicePolicyManager.LOCK_TASK_FEATURE_NONE);
            ActivityManager activities = (ActivityManager) getSystemService(ACTIVITY_SERVICE);
            if (activities.getLockTaskModeState() == ActivityManager.LOCK_TASK_MODE_NONE) {
                startLockTask();
            }
        } else {
            Log.w("RS485Control", "System navigation lock requires provisioning the device owner.");
        }
    }

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus) {
            setFullscreen(true);
        }
    }

    private void setFullscreen(boolean enable) {
        if (enable) {
            getWindow().getDecorView().setSystemUiVisibility(
                View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                    | View.SYSTEM_UI_FLAG_FULLSCREEN
                    | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                    | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                    | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                    | View.SYSTEM_UI_FLAG_LAYOUT_STABLE
            );
        } else {
            getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_VISIBLE);
        }
    }
}

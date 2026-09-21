package com.rs485.launcher;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.util.Log;

public class MainActivity extends Activity {
    private static final String TAG = "RS485Launcher";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        Log.i(TAG, "Launcher started");
        // TODO: 启动链路实现
        // 1. 通过 RUN_COMMAND 拉起 Termux 服务
        // 2. 执行 start_rs485.sh
        // 3. 打开 Termux:X11 Activity
    }
}

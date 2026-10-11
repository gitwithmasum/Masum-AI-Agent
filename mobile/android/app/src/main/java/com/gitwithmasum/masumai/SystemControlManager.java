package com.gitwithmasum.masumai;

import android.accessibilityservice.AccessibilityService;
import android.app.NotificationManager;
import android.content.ContentResolver;
import android.content.Context;
import android.content.Intent;
import android.hardware.camera2.CameraAccessException;
import android.hardware.camera2.CameraCharacteristics;
import android.hardware.camera2.CameraManager;
import android.media.AudioManager;
import android.net.Uri;
import android.os.BatteryManager;
import android.os.Build;
import android.provider.Settings;
import android.view.KeyEvent;

public final class SystemControlManager {
    public static final class Result {
        public final boolean ok;
        public final String message;

        Result(boolean ok, String message) {
            this.ok = ok;
            this.message = message;
        }
    }

    private SystemControlManager() {}

    public static Result setFlashlight(
        Context context,
        boolean enabled
    ) {
        CameraManager manager =
            (CameraManager) context.getSystemService(
                Context.CAMERA_SERVICE
            );

        if (manager == null) {
            return new Result(false, "Flashlight is unavailable.");
        }

        try {
            for (String id : manager.getCameraIdList()) {
                CameraCharacteristics chars =
                    manager.getCameraCharacteristics(id);

                Boolean flash = chars.get(
                    CameraCharacteristics.FLASH_INFO_AVAILABLE
                );

                Integer facing = chars.get(
                    CameraCharacteristics.LENS_FACING
                );

                if (
                    Boolean.TRUE.equals(flash) &&
                    (
                        facing == null ||
                        facing == CameraCharacteristics.LENS_FACING_BACK
                    )
                ) {
                    manager.setTorchMode(id, enabled);
                    return new Result(
                        true,
                        enabled
                            ? "Flashlight on."
                            : "Flashlight off."
                    );
                }
            }
        } catch (
            CameraAccessException |
            SecurityException error
        ) {
            return new Result(
                false,
                "Android could not control the flashlight."
            );
        }

        return new Result(
            false,
            "No usable flashlight was found."
        );
    }

    public static Result batteryStatus(
        Context context
    ) {
        BatteryManager battery =
            (BatteryManager) context.getSystemService(
                Context.BATTERY_SERVICE
            );

        if (battery == null) {
            return new Result(
                false,
                "Battery information is unavailable."
            );
        }

        int level = battery.getIntProperty(
            BatteryManager.BATTERY_PROPERTY_CAPACITY
        );

        boolean charging = battery.isCharging();

        return new Result(
            true,
            "Battery is " +
                level +
                " percent" +
                (charging ? " and charging." : ".")
        );
    }

    public static Result setBrightness(
        Context context,
        int percent
    ) {
        int clamped = Math.max(
            1,
            Math.min(100, percent)
        );

        if (!Settings.System.canWrite(context)) {
            Intent intent = new Intent(
                Settings.ACTION_MANAGE_WRITE_SETTINGS,
                Uri.parse(
                    "package:" +
                    context.getPackageName()
                )
            );
            intent.addFlags(
                Intent.FLAG_ACTIVITY_NEW_TASK
            );

            try {
                context.startActivity(intent);
            } catch (Exception ignored) {}

            return new Result(
                false,
                "Allow Modify system settings once, then repeat the brightness command."
            );
        }

        int value = Math.round(
            clamped * 255f / 100f
        );

        try {
            ContentResolver resolver =
                context.getContentResolver();

            Settings.System.putInt(
                resolver,
                Settings.System.SCREEN_BRIGHTNESS_MODE,
                Settings.System.SCREEN_BRIGHTNESS_MODE_MANUAL
            );

            Settings.System.putInt(
                resolver,
                Settings.System.SCREEN_BRIGHTNESS,
                value
            );

            return new Result(
                true,
                "Brightness set to " +
                    clamped +
                    " percent."
            );
        } catch (Exception error) {
            return new Result(
                false,
                "Android blocked brightness control."
            );
        }
    }

    public static Result adjustBrightness(
        Context context,
        int delta
    ) {
        int current = 128;

        try {
            current = Settings.System.getInt(
                context.getContentResolver(),
                Settings.System.SCREEN_BRIGHTNESS
            );
        } catch (Exception ignored) {}

        int percent = Math.round(
            current * 100f / 255f
        );

        return setBrightness(
            context,
            percent + delta
        );
    }

    public static Result setAutoRotate(
        Context context,
        boolean enabled
    ) {
        if (!Settings.System.canWrite(context)) {
            Intent intent = new Intent(
                Settings.ACTION_MANAGE_WRITE_SETTINGS,
                Uri.parse(
                    "package:" +
                    context.getPackageName()
                )
            );
            intent.addFlags(
                Intent.FLAG_ACTIVITY_NEW_TASK
            );

            try {
                context.startActivity(intent);
            } catch (Exception ignored) {}

            return new Result(
                false,
                "Allow Modify system settings once, then repeat the rotation command."
            );
        }

        try {
            Settings.System.putInt(
                context.getContentResolver(),
                Settings.System.ACCELEROMETER_ROTATION,
                enabled ? 1 : 0
            );

            return new Result(
                true,
                enabled
                    ? "Auto rotate on."
                    : "Auto rotate off."
            );
        } catch (Exception error) {
            return new Result(
                false,
                "Android blocked screen rotation control."
            );
        }
    }

    public static Result media(
        Context context,
        String action
    ) {
        AudioManager audio =
            (AudioManager) context.getSystemService(
                Context.AUDIO_SERVICE
            );

        if (audio == null) {
            return new Result(
                false,
                "Media controls are unavailable."
            );
        }

        int keyCode;

        switch (action) {
            case "play":
                keyCode =
                    KeyEvent.KEYCODE_MEDIA_PLAY;
                break;
            case "pause":
                keyCode =
                    KeyEvent.KEYCODE_MEDIA_PAUSE;
                break;
            case "next":
                keyCode =
                    KeyEvent.KEYCODE_MEDIA_NEXT;
                break;
            case "previous":
                keyCode =
                    KeyEvent.KEYCODE_MEDIA_PREVIOUS;
                break;
            default:
                keyCode =
                    KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE;
                break;
        }

        try {
            audio.dispatchMediaKeyEvent(
                new KeyEvent(
                    KeyEvent.ACTION_DOWN,
                    keyCode
                )
            );
            audio.dispatchMediaKeyEvent(
                new KeyEvent(
                    KeyEvent.ACTION_UP,
                    keyCode
                )
            );

            return new Result(
                true,
                "Media " + action + "."
            );
        } catch (Exception error) {
            return new Result(
                false,
                "Android blocked that media action."
            );
        }
    }

    public static Result doNotDisturb(
        Context context,
        boolean enabled
    ) {
        NotificationManager manager =
            (NotificationManager) context.getSystemService(
                Context.NOTIFICATION_SERVICE
            );

        if (manager == null) {
            return new Result(
                false,
                "Do Not Disturb is unavailable."
            );
        }

        if (
            !manager.isNotificationPolicyAccessGranted()
        ) {
            Intent intent = new Intent(
                Settings.ACTION_NOTIFICATION_POLICY_ACCESS_SETTINGS
            );
            intent.addFlags(
                Intent.FLAG_ACTIVITY_NEW_TASK
            );

            try {
                context.startActivity(intent);
            } catch (Exception ignored) {}

            return new Result(
                false,
                "Allow Do Not Disturb access once, then repeat the command."
            );
        }

        try {
            manager.setInterruptionFilter(
                enabled
                    ? NotificationManager.INTERRUPTION_FILTER_PRIORITY
                    : NotificationManager.INTERRUPTION_FILTER_ALL
            );

            return new Result(
                true,
                enabled
                    ? "Do Not Disturb on."
                    : "Do Not Disturb off."
            );
        } catch (Exception error) {
            return new Result(
                false,
                "Android blocked Do Not Disturb control."
            );
        }
    }

    public static Result screenshot(
        Context context
    ) {
        CirillaAccessibilityService service =
            CirillaAccessibilityService.getInstance();

        if (service == null) {
            return new Result(
                false,
                "Enable Accessibility Voice Control first."
            );
        }

        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.P) {
            return new Result(
                false,
                "Voice screenshot needs Android 9 or newer."
            );
        }

        boolean ok = service.performGlobalAction(
            AccessibilityService.GLOBAL_ACTION_TAKE_SCREENSHOT
        );

        return new Result(
            ok,
            ok
                ? "Taking screenshot."
                : "Android blocked the screenshot action."
        );
    }

    public static Result openHotspotSettings(
        Context context
    ) {
        Intent intent = new Intent(
            Settings.ACTION_WIRELESS_SETTINGS
        );
        intent.addFlags(
            Intent.FLAG_ACTIVITY_NEW_TASK
        );

        try {
            context.startActivity(intent);
            return new Result(
                true,
                "Opening hotspot and wireless settings."
            );
        } catch (Exception error) {
            return new Result(
                false,
                "I could not open hotspot settings."
            );
        }
    }
}

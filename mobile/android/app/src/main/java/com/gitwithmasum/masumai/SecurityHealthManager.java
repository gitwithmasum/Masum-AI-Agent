package com.gitwithmasum.masumai;

import android.Manifest;
import android.app.NotificationManager;
import android.content.ComponentName;
import android.content.Context;
import android.content.pm.PackageManager;
import android.os.Build;
import android.provider.Settings;
import android.service.voice.VoiceInteractionService;

import java.util.ArrayList;
import java.util.List;

public final class SecurityHealthManager {
    private SecurityHealthManager() {}

    public static boolean hasNotificationAccess(
        Context context
    ) {
        String enabled = Settings.Secure.getString(
            context.getContentResolver(),
            "enabled_notification_listeners"
        );

        if (enabled == null) return false;

        String component = new ComponentName(
            context,
            CallNotificationService.class
        ).flattenToString();

        return enabled.contains(component);
    }

    public static boolean assistantActive(
        Context context
    ) {
        return VoiceInteractionService.isActiveService(
            context,
            new ComponentName(
                context,
                CirillaVoiceInteractionService.class
            )
        );
    }

    public static boolean phoneControlReady(
        Context context
    ) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) {
            return true;
        }

        return context.checkSelfPermission(
            Manifest.permission.ANSWER_PHONE_CALLS
        ) == PackageManager.PERMISSION_GRANTED &&
        context.checkSelfPermission(
            Manifest.permission.READ_PHONE_STATE
        ) == PackageManager.PERMISSION_GRANTED;
    }

    public static boolean reminderNotificationsReady(
        Context context
    ) {
        return Build.VERSION.SDK_INT < 33 ||
            context.checkSelfPermission(
                Manifest.permission.POST_NOTIFICATIONS
            ) == PackageManager.PERMISSION_GRANTED;
    }

    public static boolean dndReady(
        Context context
    ) {
        NotificationManager manager =
            (NotificationManager) context.getSystemService(
                Context.NOTIFICATION_SERVICE
            );

        return manager != null &&
            manager.isNotificationPolicyAccessGranted();
    }

    public static int readyCount(
        Context context
    ) {
        int ready = 0;

        if (granted(context, Manifest.permission.RECORD_AUDIO)) ready++;
        if (assistantActive(context)) ready++;
        if (phoneControlReady(context)) ready++;
        if (hasNotificationAccess(context)) ready++;
        if (CirillaAccessibilityService.isRunning()) ready++;
        if (granted(context, Manifest.permission.READ_CONTACTS)) ready++;
        if (granted(context, Manifest.permission.CALL_PHONE)) ready++;
        if (reminderNotificationsReady(context)) ready++;
        if (granted(context, Manifest.permission.CAMERA)) ready++;
        if (Settings.System.canWrite(context)) ready++;
        if (dndReady(context)) ready++;
        if (BridgeClient.isConfigured(context)) ready++;

        return ready;
    }

    public static int totalChecks() {
        return 12;
    }

    public static String fullReport(
        Context context
    ) {
        StringBuilder report = new StringBuilder();

        report.append("SECURITY + PERMISSION HEALTH\n\n");
        report.append(line(
            "Microphone",
            granted(context, Manifest.permission.RECORD_AUDIO),
            "required for voice"
        ));
        report.append(line(
            "Default Assistant",
            assistantActive(context),
            "required for assistant role"
        ));
        report.append(line(
            "SIM Call Control",
            phoneControlReady(context),
            "optional unless controlling SIM calls"
        ));
        report.append(line(
            "Notification Access",
            hasNotificationAccess(context),
            "needed for call/message notifications"
        ));
        report.append(line(
            "Accessibility",
            CirillaAccessibilityService.isRunning(),
            "optional powerful UI control"
        ));
        report.append(line(
            "Contacts",
            granted(context, Manifest.permission.READ_CONTACTS),
            "needed for contact-name actions"
        ));
        report.append(line(
            "Outgoing Calls",
            granted(context, Manifest.permission.CALL_PHONE),
            "otherwise dialer fallback"
        ));
        report.append(line(
            "Reminder Notifications",
            reminderNotificationsReady(context),
            "needed for reminders on Android 13+"
        ));
        report.append(line(
            "Camera / Flashlight",
            granted(context, Manifest.permission.CAMERA),
            "needed for camera vision and torch"
        ));
        report.append(line(
            "Modify System Settings",
            Settings.System.canWrite(context),
            "needed for brightness/rotation"
        ));
        report.append(line(
            "Do Not Disturb Access",
            dndReady(context),
            "needed only for DND voice control"
        ));
        report.append(line(
            "Unified Laptop Bridge",
            BridgeClient.isConfigured(context),
            "pairing required for shared AI brain"
        ));

        int ready = readyCount(context);
        report.append("\nReadiness: ")
            .append(ready)
            .append("/")
            .append(totalChecks())
            .append(" checks ready.\n");

        report.append(
            "\nPolicy: passwords, PINs, OTPs, CVV/security codes are protected. " +
            "Outgoing calls/messages and direct replies require confirmation. " +
            "Pending confirmations expire automatically."
        );

        return report.toString();
    }

    public static String spokenSummary(
        Context context
    ) {
        int ready = readyCount(context);
        List<String> missing = new ArrayList<>();

        if (!granted(context, Manifest.permission.RECORD_AUDIO)) {
            missing.add("microphone");
        }
        if (!assistantActive(context)) {
            missing.add("default assistant");
        }
        if (!hasNotificationAccess(context)) {
            missing.add("notification access");
        }
        if (!BridgeClient.isConfigured(context)) {
            missing.add("laptop bridge");
        }

        String summary =
            "Security health is " +
            ready +
            " of " +
            totalChecks() +
            " checks ready.";

        if (!missing.isEmpty()) {
            summary += " Main items still needed: " +
                String.join(", ", missing) +
                ".";
        }

        summary +=
            " Sensitive codes remain protected, and risky outgoing actions use confirmation.";

        return summary;
    }

    private static boolean granted(
        Context context,
        String permission
    ) {
        return context.checkSelfPermission(permission)
            == PackageManager.PERMISSION_GRANTED;
    }

    private static String line(
        String label,
        boolean ready,
        String note
    ) {
        return (ready ? "✓ " : "• ") +
            label +
            ": " +
            (ready ? "READY" : "NEEDS SETUP") +
            " — " +
            note +
            "\n";
    }
}

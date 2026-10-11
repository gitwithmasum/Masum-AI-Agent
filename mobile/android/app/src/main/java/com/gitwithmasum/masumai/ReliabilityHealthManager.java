package com.gitwithmasum.masumai;

import android.app.ActivityManager;
import android.content.Context;
import android.net.ConnectivityManager;
import android.net.Network;
import android.net.NetworkCapabilities;
import android.os.Build;
import android.os.PowerManager;

public final class ReliabilityHealthManager {
    private ReliabilityHealthManager() {}

    public static boolean batteryOptimizationExempt(
        Context context
    ) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.M) {
            return true;
        }

        PowerManager power =
            (PowerManager) context.getSystemService(
                Context.POWER_SERVICE
            );

        return power != null &&
            power.isIgnoringBatteryOptimizations(
                context.getPackageName()
            );
    }

    public static boolean backgroundRestricted(
        Context context
    ) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.P) {
            return false;
        }

        ActivityManager manager =
            (ActivityManager) context.getSystemService(
                Context.ACTIVITY_SERVICE
            );

        return manager != null &&
            manager.isBackgroundRestricted();
    }

    public static String networkStatus(
        Context context
    ) {
        ConnectivityManager manager =
            (ConnectivityManager) context.getSystemService(
                Context.CONNECTIVITY_SERVICE
            );

        if (manager == null) return "UNKNOWN";

        Network network = manager.getActiveNetwork();
        if (network == null) return "OFFLINE";

        NetworkCapabilities capabilities =
            manager.getNetworkCapabilities(network);

        if (capabilities == null) return "CONNECTED";

        if (
            capabilities.hasTransport(
                NetworkCapabilities.TRANSPORT_WIFI
            )
        ) {
            return "WI-FI";
        }

        if (
            capabilities.hasTransport(
                NetworkCapabilities.TRANSPORT_CELLULAR
            )
        ) {
            return "CELLULAR";
        }

        if (
            capabilities.hasTransport(
                NetworkCapabilities.TRANSPORT_ETHERNET
            )
        ) {
            return "ETHERNET";
        }

        return "CONNECTED";
    }

    public static String fullReport(
        Context context
    ) {
        String battery =
            batteryOptimizationExempt(context)
                ? "EXEMPT / UNRESTRICTED BY DOZE"
                : "STANDARD ANDROID OPTIMIZATION";

        String background =
            backgroundRestricted(context)
                ? "RESTRICTED"
                : "NOT RESTRICTED";

        String bridge =
            BridgeClient.isConfigured(context)
                ? "PAIRED"
                : "NOT PAIRED";

        String lastBridge =
            BridgeClient.lastHealthText(context);

        return "STABILITY + BACKGROUND HEALTH\n\n" +
            "Default Assistant: " +
            (SecurityHealthManager.assistantActive(context)
                ? "ACTIVE"
                : "NOT ACTIVE") +
            "\nBattery optimization: " + battery +
            "\nBackground restriction: " + background +
            "\nActive network: " + networkStatus(context) +
            "\nUnified bridge: " + bridge +
            "\nBridge history: " + lastBridge +
            "\n\nAndroid controls background execution. " +
            "This app does not bypass battery or background restrictions. " +
            "For best wake/bridge reliability, keep Masum AI Agent as the selected assistant and review the device battery settings if the OEM is aggressively restricting it.";
    }

    public static String spokenSummary(
        Context context
    ) {
        StringBuilder summary = new StringBuilder(
            "Reliability status. "
        );

        summary.append(
            SecurityHealthManager.assistantActive(context)
                ? "Default assistant is active. "
                : "Default assistant is not active. "
        );

        if (backgroundRestricted(context)) {
            summary.append(
                "Android reports background restriction. "
            );
        } else {
            summary.append(
                "No Android background restriction is reported. "
            );
        }

        summary.append(
            "Network is " +
            networkStatus(context).toLowerCase() +
            ". "
        );

        summary.append(
            BridgeClient.lastHealthText(context)
        );

        return summary.toString();
    }
}

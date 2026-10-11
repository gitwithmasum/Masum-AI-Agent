package com.gitwithmasum.masumai;

import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.os.Build;

public class ReminderReceiver extends BroadcastReceiver {
    private static final String CHANNEL_ID =
        "masum_ai_reminders";

    @Override
    public void onReceive(
        Context context,
        Intent intent
    ) {
        String id = intent.getStringExtra(
            "reminder_id"
        );
        String text = intent.getStringExtra(
            "reminder_text"
        );

        if (text == null || text.isBlank()) {
            text = "Masum AI Agent reminder";
        }

        NotificationManager manager =
            (NotificationManager)
                context.getSystemService(
                    Context.NOTIFICATION_SERVICE
                );

        if (manager == null) return;

        if (Build.VERSION.SDK_INT >= 26) {
            NotificationChannel channel =
                new NotificationChannel(
                    CHANNEL_ID,
                    "Masum AI Reminders",
                    NotificationManager.IMPORTANCE_HIGH
                );
            channel.setDescription(
                "Voice-created reminders from Masum AI Agent"
            );
            manager.createNotificationChannel(
                channel
            );
        }

        Intent open = new Intent(
            context,
            MainActivity.class
        );
        open.addFlags(
            Intent.FLAG_ACTIVITY_NEW_TASK |
                Intent.FLAG_ACTIVITY_CLEAR_TOP
        );

        PendingIntent content = PendingIntent.getActivity(
            context,
            0,
            open,
            PendingIntent.FLAG_UPDATE_CURRENT |
                PendingIntent.FLAG_IMMUTABLE
        );

        android.app.Notification.Builder builder =
            Build.VERSION.SDK_INT >= 26
                ? new android.app.Notification.Builder(
                    context,
                    CHANNEL_ID
                )
                : new android.app.Notification.Builder(
                    context
                );

        builder
            .setSmallIcon(
                com.gitwithmasum.masumai.R.drawable.ic_launcher
            )
            .setContentTitle("Cirilla Reminder")
            .setContentText(text)
            .setStyle(
                new android.app.Notification.BigTextStyle()
                    .bigText(text)
            )
            .setAutoCancel(true)
            .setContentIntent(content)
            .setPriority(
                android.app.Notification.PRIORITY_HIGH
            );

        manager.notify(
            id == null ? 5300 : id.hashCode(),
            builder.build()
        );

        if (id != null) {
            ProductivityActionManager.removeReminder(
                context,
                id
            );
        }
    }
}

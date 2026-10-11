package com.gitwithmasum.masumai;

import android.Manifest;
import android.app.AlarmManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.provider.AlarmClock;
import android.provider.CalendarContract;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

public final class ProductivityActionManager {
    public static final class Result {
        public final boolean ok;
        public final String message;

        Result(boolean ok, String message) {
            this.ok = ok;
            this.message = message;
        }
    }

    private static final String PREFS = "masum_productivity";
    private static final String NOTES_KEY = "notes";
    private static final String REMINDERS_KEY = "reminders";

    private ProductivityActionManager() {}

    public static Result setAlarm(
        Context context,
        int hour,
        int minute,
        String label
    ) {
        Intent intent = new Intent(AlarmClock.ACTION_SET_ALARM);
        intent.putExtra(AlarmClock.EXTRA_HOUR, hour);
        intent.putExtra(AlarmClock.EXTRA_MINUTES, minute);
        intent.putExtra(
            AlarmClock.EXTRA_MESSAGE,
            label == null || label.isBlank()
                ? "Masum AI Agent alarm"
                : label
        );
        intent.putExtra(AlarmClock.EXTRA_SKIP_UI, true);
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);

        try {
            context.startActivity(intent);
            return new Result(
                true,
                String.format(
                    "Alarm set for %02d:%02d.",
                    hour,
                    minute
                )
            );
        } catch (Exception error) {
            return new Result(
                false,
                "I could not set an alarm on this device."
            );
        }
    }

    public static Result setTimer(
        Context context,
        int seconds,
        String label
    ) {
        if (seconds <= 0 || seconds > 86400) {
            return new Result(
                false,
                "Timer length must be between one second and 24 hours."
            );
        }

        Intent intent = new Intent(AlarmClock.ACTION_SET_TIMER);
        intent.putExtra(AlarmClock.EXTRA_LENGTH, seconds);
        intent.putExtra(
            AlarmClock.EXTRA_MESSAGE,
            label == null || label.isBlank()
                ? "Masum AI Agent timer"
                : label
        );
        intent.putExtra(AlarmClock.EXTRA_SKIP_UI, true);
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);

        try {
            context.startActivity(intent);
            return new Result(true, "Timer started.");
        } catch (Exception error) {
            return new Result(
                false,
                "I could not start a timer on this device."
            );
        }
    }

    public static Result addNote(
        Context context,
        String note
    ) {
        String value = note == null ? "" : note.trim();

        if (value.isBlank()) {
            return new Result(false, "The note is empty.");
        }

        SharedPreferences prefs = prefs(context);
        JSONArray notes = loadArray(
            prefs.getString(NOTES_KEY, "[]")
        );

        JSONObject item = new JSONObject();
        try {
            item.put("id", UUID.randomUUID().toString());
            item.put("text", value);
            item.put(
                "created_at",
                System.currentTimeMillis()
            );
            notes.put(item);
        } catch (Exception error) {
            return new Result(false, "I could not save that note.");
        }

        prefs.edit()
            .putString(NOTES_KEY, notes.toString())
            .apply();

        return new Result(true, "Note saved.");
    }

    public static Result readNotes(
        Context context,
        int limit
    ) {
        JSONArray notes = loadArray(
            prefs(context).getString(NOTES_KEY, "[]")
        );

        if (notes.length() == 0) {
            return new Result(true, "You have no saved notes.");
        }

        int count = Math.min(
            Math.max(limit, 1),
            notes.length()
        );

        StringBuilder message = new StringBuilder(
            "Your latest notes are: "
        );

        int start = notes.length() - count;

        for (int i = start; i < notes.length(); i++) {
            JSONObject item = notes.optJSONObject(i);
            if (item == null) continue;

            String text = item.optString("text", "").trim();
            if (text.isBlank()) continue;

            if (message.length() > 23) {
                message.append(" ");
            }

            message.append(i - start + 1)
                .append(". ")
                .append(shortText(text, 180));
        }

        return new Result(true, message.toString());
    }

    public static Result createReminder(
        Context context,
        long triggerAtMillis,
        String text
    ) {
        if (triggerAtMillis <= System.currentTimeMillis()) {
            return new Result(
                false,
                "Reminder time must be in the future."
            );
        }

        if (
            Build.VERSION.SDK_INT >= 33 &&
            context.checkSelfPermission(
                Manifest.permission.POST_NOTIFICATIONS
            ) != PackageManager.PERMISSION_GRANTED
        ) {
            return new Result(
                false,
                "Allow Reminder Notifications in the Masum AI Agent app first."
            );
        }

        String reminderText =
            text == null || text.isBlank()
                ? "Masum AI Agent reminder"
                : text.trim();

        String id = UUID.randomUUID().toString();

        JSONObject reminder = new JSONObject();
        try {
            reminder.put("id", id);
            reminder.put("text", reminderText);
            reminder.put("trigger_at", triggerAtMillis);
        } catch (Exception error) {
            return new Result(
                false,
                "I could not create that reminder."
            );
        }

        SharedPreferences prefs = prefs(context);
        JSONArray reminders = loadArray(
            prefs.getString(REMINDERS_KEY, "[]")
        );
        reminders.put(reminder);

        prefs.edit()
            .putString(
                REMINDERS_KEY,
                reminders.toString()
            )
            .apply();

        if (!scheduleReminder(
            context,
            id,
            reminderText,
            triggerAtMillis
        )) {
            removeReminder(context, id);
            return new Result(
                false,
                "Android could not schedule that reminder."
            );
        }

        return new Result(true, "Reminder scheduled.");
    }

    public static Result listReminders(
        Context context,
        int limit
    ) {
        JSONArray reminders = loadArray(
            prefs(context).getString(
                REMINDERS_KEY,
                "[]"
            )
        );

        long now = System.currentTimeMillis();
        List<JSONObject> future =
            new ArrayList<>();

        for (int i = 0; i < reminders.length(); i++) {
            JSONObject item = reminders.optJSONObject(i);
            if (item == null) continue;

            if (item.optLong("trigger_at", 0) > now) {
                future.add(item);
            }
        }

        future.sort(
            (a, b) -> Long.compare(
                a.optLong("trigger_at", 0),
                b.optLong("trigger_at", 0)
            )
        );

        if (future.isEmpty()) {
            return new Result(
                true,
                "You have no upcoming reminders."
            );
        }

        int count = Math.min(
            Math.max(limit, 1),
            future.size()
        );

        StringBuilder message = new StringBuilder(
            "Your upcoming reminders are: "
        );

        for (int i = 0; i < count; i++) {
            JSONObject item = future.get(i);
            if (i > 0) message.append(" ");

            message.append(i + 1)
                .append(". ")
                .append(
                    shortText(
                        item.optString("text", ""),
                        150
                    )
                );
        }

        return new Result(true, message.toString());
    }

    public static Result openCalendarEvent(
        Context context,
        String title,
        long beginMillis
    ) {
        long start = Math.max(
            beginMillis,
            System.currentTimeMillis()
        );
        long end = start + 60L * 60L * 1000L;

        Intent intent = new Intent(
            Intent.ACTION_INSERT
        );
        intent.setData(
            CalendarContract.Events.CONTENT_URI
        );
        intent.putExtra(
            CalendarContract.Events.TITLE,
            title == null || title.isBlank()
                ? "Masum AI Agent event"
                : title.trim()
        );
        intent.putExtra(
            CalendarContract.EXTRA_EVENT_BEGIN_TIME,
            start
        );
        intent.putExtra(
            CalendarContract.EXTRA_EVENT_END_TIME,
            end
        );
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);

        try {
            context.startActivity(intent);
            return new Result(
                true,
                "Calendar event is ready. Review and save it."
            );
        } catch (Exception error) {
            return new Result(
                false,
                "I could not open a calendar app."
            );
        }
    }

    public static void rescheduleAll(
        Context context
    ) {
        JSONArray reminders = loadArray(
            prefs(context).getString(
                REMINDERS_KEY,
                "[]"
            )
        );

        long now = System.currentTimeMillis();

        for (int i = 0; i < reminders.length(); i++) {
            JSONObject item = reminders.optJSONObject(i);
            if (item == null) continue;

            String id = item.optString("id", "");
            String text = item.optString("text", "");
            long trigger = item.optLong(
                "trigger_at",
                0
            );

            if (
                !id.isBlank() &&
                trigger > now
            ) {
                scheduleReminder(
                    context,
                    id,
                    text,
                    trigger
                );
            }
        }
    }

    public static void removeReminder(
        Context context,
        String id
    ) {
        JSONArray reminders = loadArray(
            prefs(context).getString(
                REMINDERS_KEY,
                "[]"
            )
        );

        JSONArray remaining = new JSONArray();

        for (int i = 0; i < reminders.length(); i++) {
            JSONObject item = reminders.optJSONObject(i);
            if (item == null) continue;

            if (!id.equals(item.optString("id", ""))) {
                remaining.put(item);
            }
        }

        prefs(context)
            .edit()
            .putString(
                REMINDERS_KEY,
                remaining.toString()
            )
            .apply();
    }

    private static boolean scheduleReminder(
        Context context,
        String id,
        String text,
        long triggerAtMillis
    ) {
        AlarmManager alarm =
            (AlarmManager) context.getSystemService(
                Context.ALARM_SERVICE
            );

        if (alarm == null) return false;

        Intent intent = new Intent(
            context,
            ReminderReceiver.class
        );
        intent.putExtra("reminder_id", id);
        intent.putExtra("reminder_text", text);

        PendingIntent pending = PendingIntent.getBroadcast(
            context,
            stableRequestCode(id),
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT |
                PendingIntent.FLAG_IMMUTABLE
        );

        try {
            alarm.setAndAllowWhileIdle(
                AlarmManager.RTC_WAKEUP,
                triggerAtMillis,
                pending
            );
            return true;
        } catch (Exception error) {
            return false;
        }
    }

    private static int stableRequestCode(
        String id
    ) {
        return id.hashCode() & 0x7fffffff;
    }

    private static SharedPreferences prefs(
        Context context
    ) {
        return context.getSharedPreferences(
            PREFS,
            Context.MODE_PRIVATE
        );
    }

    private static JSONArray loadArray(
        String value
    ) {
        try {
            return new JSONArray(
                value == null ? "[]" : value
            );
        } catch (Exception error) {
            return new JSONArray();
        }
    }

    private static String shortText(
        String text,
        int max
    ) {
        String value =
            text == null ? "" : text.trim();

        if (value.length() <= max) {
            return value;
        }

        return value.substring(
            0,
            Math.max(1, max - 3)
        ) + "...";
    }
}

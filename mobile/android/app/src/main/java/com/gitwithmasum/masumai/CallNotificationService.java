package com.gitwithmasum.masumai;

import android.app.Notification;
import android.app.PendingIntent;
import android.app.RemoteInput;
import android.content.Intent;
import android.os.Bundle;
import android.service.notification.NotificationListenerService;
import android.service.notification.StatusBarNotification;

import java.util.Arrays;
import java.util.Comparator;
import java.util.Locale;

public class CallNotificationService extends NotificationListenerService {
    private static volatile CallNotificationService instance;

    public static final class Result {
        public final boolean handled;
        public final String message;

        Result(boolean handled, String message) {
            this.handled = handled;
            this.message = message;
        }
    }

    private static final class MessageSnapshot {
        final String packageName;
        final String source;
        final String title;
        final String text;
        final Notification notification;
        final long postTime;

        MessageSnapshot(
            String packageName,
            String source,
            String title,
            String text,
            Notification notification,
            long postTime
        ) {
            this.packageName = packageName;
            this.source = source;
            this.title = title;
            this.text = text;
            this.notification = notification;
            this.postTime = postTime;
        }
    }

    private static final class CallSnapshot {
        final String packageName;
        final String source;
        final String caller;
        final Notification notification;
        final long postTime;

        CallSnapshot(
            String packageName,
            String source,
            String caller,
            Notification notification,
            long postTime
        ) {
            this.packageName = packageName;
            this.source = source;
            this.caller = caller;
            this.notification = notification;
            this.postTime = postTime;
        }
    }

    @Override
    public void onListenerConnected() {
        super.onListenerConnected();
        instance = this;
    }

    @Override
    public void onListenerDisconnected() {
        if (instance == this) instance = null;
        super.onListenerDisconnected();
    }

    @Override
    public void onDestroy() {
        if (instance == this) instance = null;
        super.onDestroy();
    }

    public static boolean isRunning() {
        return instance != null;
    }

    public static Result answer(String source) {
        CallNotificationService service = instance;
        if (service == null) {
            return new Result(
                false,
                "Enable WhatsApp and Messenger call access in Notification Access first."
            );
        }
        return service.perform(source, true);
    }

    public static Result reject(String source) {
        CallNotificationService service = instance;
        if (service == null) {
            return new Result(
                false,
                "Enable WhatsApp and Messenger call access in Notification Access first."
            );
        }
        return service.perform(source, false);
    }

    public static Result describe(String source) {
        CallNotificationService service = instance;
        if (service == null) {
            return new Result(
                false,
                "Notification call access is not enabled."
            );
        }

        CallSnapshot snapshot = service.findBest(source);
        if (snapshot == null) {
            return new Result(false, "I cannot see an incoming call right now.");
        }

        String caller = snapshot.caller;
        if (caller == null || caller.isBlank()) {
            caller = "an unknown caller";
        }

        return new Result(
            true,
            snapshot.source + " call from " + caller + "."
        );
    }


    public static Result latestNotification(String source) {
        CallNotificationService service = instance;
        if (service == null) {
            return new Result(
                false,
                "Enable Masum AI Call and Message Access in Notification Access first."
            );
        }

        MessageSnapshot snapshot = service.findLatestMessage(source, false);
        if (snapshot == null) {
            return new Result(
                false,
                "I cannot find a matching message notification right now."
            );
        }

        String title = snapshot.title.isBlank() ? "unknown sender" : snapshot.title;
        String body = snapshot.text.isBlank() ? "No message preview is available." : snapshot.text;

        if (service.looksSensitive(body)) {
            body = "This notification contains a security or verification code, so I will not read the code aloud.";
        }

        return new Result(
            true,
            snapshot.source + " from " + title + ". " + body
        );
    }

    public static Result listNotifications(int limit) {
        CallNotificationService service = instance;
        if (service == null) {
            return new Result(
                false,
                "Enable Masum AI Call and Message Access in Notification Access first."
            );
        }

        StatusBarNotification[] active;
        try {
            active = service.getActiveNotifications();
        } catch (Exception error) {
            return new Result(false, "I could not read active notifications.");
        }

        if (active == null || active.length == 0) {
            return new Result(true, "You have no active notifications.");
        }

        Arrays.sort(
            active,
            Comparator.comparingLong(StatusBarNotification::getPostTime).reversed()
        );

        StringBuilder summary = new StringBuilder();
        int count = 0;

        for (StatusBarNotification item : active) {
            if (count >= Math.max(1, Math.min(limit, 5))) break;
            if (service.isCallLike(item)) continue;

            MessageSnapshot snapshot = service.messageSnapshot(item);
            if (snapshot.title.isBlank() && snapshot.text.isBlank()) continue;

            if (count > 0) summary.append(" ");
            summary.append(count + 1)
                .append(". ")
                .append(snapshot.source)
                .append(" from ")
                .append(snapshot.title.isBlank() ? "unknown sender" : snapshot.title)
                .append(". ");

            if (service.looksSensitive(snapshot.text)) {
                summary.append("Sensitive notification hidden.");
            } else if (!snapshot.text.isBlank()) {
                summary.append(service.shortText(snapshot.text, 120));
            }

            count++;
        }

        if (count == 0) {
            return new Result(true, "I found no readable message notifications.");
        }

        return new Result(
            true,
            "Your latest " + count + " notifications are: " + summary
        );
    }

    public static Result reply(String source, String message) {
        CallNotificationService service = instance;
        if (service == null) {
            return new Result(
                false,
                "Enable Masum AI Call and Message Access in Notification Access first."
            );
        }

        String replyText = message == null ? "" : message.trim();
        if (replyText.isBlank()) {
            return new Result(false, "The reply message is empty.");
        }

        MessageSnapshot snapshot = service.findLatestMessage(source, true);
        if (snapshot == null) {
            return new Result(
                false,
                "I cannot find a matching notification with a direct Reply action."
            );
        }

        Notification.Action replyAction =
            service.findReplyAction(snapshot.notification);

        if (replyAction == null ||
            replyAction.actionIntent == null ||
            replyAction.getRemoteInputs() == null ||
            replyAction.getRemoteInputs().length == 0) {
            return new Result(
                false,
                "That notification does not expose Android direct reply."
            );
        }

        try {
            RemoteInput[] inputs = replyAction.getRemoteInputs();
            Bundle results = new Bundle();
            for (RemoteInput input : inputs) {
                results.putCharSequence(input.getResultKey(), replyText);
            }

            Intent fillIn = new Intent();
            RemoteInput.addResultsToIntent(inputs, fillIn, results);
            replyAction.actionIntent.send(service, 0, fillIn);

            String target = snapshot.title.isBlank()
                ? snapshot.source
                : snapshot.title + " on " + snapshot.source;

            return new Result(true, "Reply sent to " + target + ".");
        } catch (PendingIntent.CanceledException error) {
            return new Result(
                false,
                "The notification reply action expired before I could use it."
            );
        } catch (Exception error) {
            return new Result(false, "Android blocked that notification reply.");
        }
    }

    private MessageSnapshot findLatestMessage(
        String requestedSource,
        boolean requireReply
    ) {
        StatusBarNotification[] active;
        try {
            active = getActiveNotifications();
        } catch (Exception error) {
            return null;
        }

        if (active == null || active.length == 0) return null;

        Arrays.sort(
            active,
            Comparator.comparingLong(StatusBarNotification::getPostTime).reversed()
        );

        for (StatusBarNotification item : active) {
            if (isCallLike(item)) continue;
            if (!messageSourceMatches(item.getPackageName(), requestedSource)) continue;

            MessageSnapshot snapshot = messageSnapshot(item);
            if (snapshot.title.isBlank() && snapshot.text.isBlank()) continue;

            if (requireReply && findReplyAction(snapshot.notification) == null) {
                continue;
            }

            return snapshot;
        }

        return null;
    }

    private MessageSnapshot messageSnapshot(StatusBarNotification sbn) {
        Notification notification = sbn.getNotification();

        String title = readExtra(notification, Notification.EXTRA_TITLE);
        String text = readExtra(notification, Notification.EXTRA_TEXT);

        if (text.isBlank()) {
            text = readExtra(notification, Notification.EXTRA_BIG_TEXT);
        }
        if (text.isBlank()) {
            text = readExtra(notification, Notification.EXTRA_SUB_TEXT);
        }

        return new MessageSnapshot(
            sbn.getPackageName(),
            messageSourceName(sbn.getPackageName()),
            title,
            text,
            notification,
            sbn.getPostTime()
        );
    }

    private Notification.Action findReplyAction(Notification notification) {
        if (notification == null || notification.actions == null) return null;

        Notification.Action fallback = null;

        for (Notification.Action action : notification.actions) {
            if (action == null || action.actionIntent == null) continue;

            RemoteInput[] inputs = action.getRemoteInputs();
            if (inputs == null || inputs.length == 0) continue;

            String title = action.title == null
                ? ""
                : action.title.toString().toLowerCase(Locale.ROOT).trim();

            if (title.contains("reply") ||
                title.contains("respond") ||
                title.contains("message") ||
                title.contains("উত্তর") ||
                title.contains("রিপ্লাই")) {
                return action;
            }

            if (fallback == null) fallback = action;
        }

        return fallback;
    }

    private boolean messageSourceMatches(
        String pkg,
        String requestedSource
    ) {
        String source = requestedSource == null
            ? "any"
            : requestedSource.toLowerCase(Locale.ROOT).trim();

        if (source.equals("any") || source.equals("notification")) return true;
        if (source.equals("whatsapp")) return isWhatsApp(pkg);
        if (source.equals("messenger")) return isMessenger(pkg);
        if (source.equals("gmail")) return "com.google.android.gm".equals(pkg);
        if (source.equals("sms")) {
            return pkg.contains("messaging") ||
                pkg.contains("messages") ||
                pkg.contains("mms");
        }

        return messageSourceName(pkg).toLowerCase(Locale.ROOT).contains(source);
    }

    private String messageSourceName(String pkg) {
        if (isWhatsApp(pkg)) return "WhatsApp";
        if (isMessenger(pkg)) return "Messenger";
        if ("com.google.android.gm".equals(pkg)) return "Gmail";
        if (pkg.contains("messaging") ||
            pkg.contains("messages") ||
            pkg.contains("mms")) {
            return "Messages";
        }

        try {
            return getPackageManager()
                .getApplicationLabel(
                    getPackageManager().getApplicationInfo(pkg, 0)
                )
                .toString();
        } catch (Exception error) {
            return pkg;
        }
    }

    private boolean looksSensitive(String text) {
        String value = text == null
            ? ""
            : text.toLowerCase(Locale.ROOT);

        boolean keyword =
            value.contains("otp") ||
            value.contains("verification code") ||
            value.contains("security code") ||
            value.contains("one-time password") ||
            value.contains("one time password");

        return keyword && value.matches(".*\\b\\d{4,8}\\b.*");
    }

    private String shortText(String text, int max) {
        String value = text == null ? "" : text.trim();
        if (value.length() <= max) return value;
        return value.substring(0, Math.max(1, max - 3)) + "...";
    }

    private Result perform(String source, boolean answer) {
        CallSnapshot snapshot = findBest(source);
        if (snapshot == null) {
            return new Result(
                false,
                "I cannot see a matching incoming " + sourceLabel(source) + " call."
            );
        }

        Notification.Action action = findAction(snapshot.notification, answer);
        if (action == null || action.actionIntent == null) {
            return new Result(
                false,
                "I found the " + snapshot.source +
                " call, but its notification did not expose a safe " +
                (answer ? "Answer" : "Decline") + " action."
            );
        }

        try {
            action.actionIntent.send();
            return new Result(
                true,
                (answer ? "Answering " : "Rejecting ") +
                snapshot.source + " call" +
                (
                    snapshot.caller == null || snapshot.caller.isBlank()
                        ? "."
                        : " from " + snapshot.caller + "."
                )
            );
        } catch (PendingIntent.CanceledException error) {
            return new Result(
                false,
                "That call action expired before I could use it."
            );
        }
    }

    private CallSnapshot findBest(String requestedSource) {
        StatusBarNotification[] active;
        try {
            active = getActiveNotifications();
        } catch (Exception error) {
            return null;
        }

        if (active == null || active.length == 0) return null;

        Arrays.sort(
            active,
            Comparator.comparingLong(StatusBarNotification::getPostTime).reversed()
        );

        for (StatusBarNotification item : active) {
            if (!isCallLike(item)) continue;

            CallSnapshot snapshot = snapshot(item);
            if (sourceMatches(snapshot.packageName, requestedSource)) {
                return snapshot;
            }
        }

        return null;
    }

    private boolean isCallLike(StatusBarNotification sbn) {
        Notification notification = sbn.getNotification();
        if (notification == null) return false;

        if (Notification.CATEGORY_CALL.equals(notification.category)) {
            return true;
        }

        String pkg = sbn.getPackageName();
        boolean callApp = isWhatsApp(pkg) || isMessenger(pkg);
        if (!callApp) return false;

        String text = (
            readExtra(notification, Notification.EXTRA_TITLE) + " " +
            readExtra(notification, Notification.EXTRA_TEXT) + " " +
            readExtra(notification, Notification.EXTRA_SUB_TEXT)
        ).toLowerCase(Locale.ROOT);

        return text.contains("incoming call") ||
            text.contains("voice call") ||
            text.contains("video call") ||
            text.contains("calling") ||
            hasRecognizedAction(notification);
    }

    private boolean hasRecognizedAction(Notification notification) {
        if (notification.actions == null) return false;
        for (Notification.Action action : notification.actions) {
            String title = action.title == null
                ? ""
                : action.title.toString().toLowerCase(Locale.ROOT);
            if (isAnswerTitle(title) || isRejectTitle(title)) return true;
        }
        return false;
    }

    private Notification.Action findAction(
        Notification notification,
        boolean answer
    ) {
        if (notification.actions == null) return null;

        for (Notification.Action action : notification.actions) {
            String title = action.title == null
                ? ""
                : action.title.toString().toLowerCase(Locale.ROOT).trim();

            if (answer ? isAnswerTitle(title) : isRejectTitle(title)) {
                return action;
            }
        }

        return null;
    }

    private boolean isAnswerTitle(String title) {
        return title.contains("answer") ||
            title.contains("accept") ||
            title.contains("receive") ||
            title.contains("pick up") ||
            title.equals("join") ||
            title.contains("রিসিভ") ||
            title.contains("গ্রহণ") ||
            title.contains("উত্তর") ||
            title.contains("ধরুন");
    }

    private boolean isRejectTitle(String title) {
        return title.contains("decline") ||
            title.contains("reject") ||
            title.contains("dismiss") ||
            title.contains("hang up") ||
            title.contains("end call") ||
            title.contains("প্রত্যাখ্যান") ||
            title.contains("রিজেক্ট") ||
            title.contains("কেটে");
    }

    private CallSnapshot snapshot(StatusBarNotification sbn) {
        Notification notification = sbn.getNotification();
        String caller = readExtra(notification, Notification.EXTRA_TITLE);
        String source = sourceName(sbn.getPackageName());

        if (caller.equalsIgnoreCase(source) || caller.equalsIgnoreCase("incoming call")) {
            String alternative = readExtra(notification, Notification.EXTRA_TEXT);
            if (!alternative.isBlank()) caller = alternative;
        }

        return new CallSnapshot(
            sbn.getPackageName(),
            source,
            caller,
            notification,
            sbn.getPostTime()
        );
    }

    private String readExtra(Notification notification, String key) {
        Bundle extras = notification.extras;
        if (extras == null) return "";
        CharSequence value = extras.getCharSequence(key);
        return value == null ? "" : value.toString().trim();
    }

    private boolean sourceMatches(String pkg, String requestedSource) {
        String source = requestedSource == null
            ? "any"
            : requestedSource.toLowerCase(Locale.ROOT);

        if (source.equals("any")) return true;
        if (source.equals("whatsapp")) return isWhatsApp(pkg);
        if (source.equals("messenger")) return isMessenger(pkg);

        if (source.equals("phone")) {
            return !isWhatsApp(pkg) && !isMessenger(pkg);
        }

        return true;
    }

    private String sourceName(String pkg) {
        if (isWhatsApp(pkg)) return "WhatsApp";
        if (isMessenger(pkg)) return "Messenger";
        return "phone";
    }

    private String sourceLabel(String source) {
        if ("whatsapp".equals(source)) return "WhatsApp";
        if ("messenger".equals(source)) return "Messenger";
        if ("phone".equals(source)) return "phone";
        return "";
    }

    private boolean isWhatsApp(String pkg) {
        return "com.whatsapp".equals(pkg) || "com.whatsapp.w4b".equals(pkg);
    }

    private boolean isMessenger(String pkg) {
        return "com.facebook.orca".equals(pkg);
    }
}

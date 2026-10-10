package com.gitwithmasum.masumai;

import android.Manifest;
import android.accessibilityservice.AccessibilityService;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.media.AudioManager;
import android.net.Uri;
import android.os.Build;
import android.provider.Settings;
import android.speech.tts.TextToSpeech;
import android.telecom.TelecomManager;
import android.telephony.TelephonyManager;

import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class VoiceCommandRouter {
    private final Context context;
    private final AudioManager audio;
    private TextToSpeech tts;
    private String pendingReplySource;
    private String pendingReplyText;

    public VoiceCommandRouter(Context context) {
        this.context = context;
        this.audio = (AudioManager) context.getSystemService(Context.AUDIO_SERVICE);
        this.tts = new TextToSpeech(context, status -> {
            if (status == TextToSpeech.SUCCESS) {
                tts.setLanguage(Locale.US);
                tts.setSpeechRate(0.96f);
            }
        });
    }

    public void shutdown() {
        if (tts != null) {
            tts.stop();
            tts.shutdown();
        }
    }

    public void speak(String text) {
        if (tts != null && text != null) {
            tts.speak(text, TextToSpeech.QUEUE_FLUSH, null, "masum-ai");
        }
    }

    public boolean hasPendingConfirmation() {
        return pendingReplySource != null && pendingReplyText != null;
    }

    private void clearPendingReply() {
        pendingReplySource = null;
        pendingReplyText = null;
    }

    public void execute(String raw, String persona) {
        String cmd = raw.toLowerCase(Locale.ROOT).trim();

        if (hasPendingConfirmation()) {
            if (matches(
                cmd,
                "yes",
                "yeah",
                "yep",
                "confirm",
                "send it",
                "do it",
                "হ্যাঁ",
                "জি",
                "পাঠাও"
            )) {
                String source = pendingReplySource;
                String message = pendingReplyText;
                clearPendingReply();

                CallNotificationService.Result result =
                    CallNotificationService.reply(source, message);
                speak(result.message);
                return;
            }

            if (matches(
                cmd,
                "no",
                "cancel",
                "do not send",
                "don't send",
                "না",
                "ক্যানসেল",
                "বাদ দাও"
            )) {
                clearPendingReply();
                speak("Reply cancelled.");
                return;
            }

            speak("Please say yes to send the reply, or no to cancel.");
            return;
        }

        if (cmd.contains("switch to geralt") ||
            cmd.equals("geralt mode") ||
            cmd.equals("গেরাল্ট মোড") ||
            cmd.equals("গেরাল্ট চালু করো")) {
            speak("Geralt mode active.");
            return;
        }
        if (cmd.contains("switch to cirilla") ||
            cmd.equals("cirilla mode") ||
            cmd.equals("সিরিলা মোড") ||
            cmd.equals("সিরিলা চালু করো")) {
            speak("Cirilla mode active.");
            return;
        }

        String callSource = callSource(cmd);

        if (isWhoIsCalling(cmd)) {
            CallNotificationService.Result result =
                CallNotificationService.describe(callSource);
            speak(result.message);
            return;
        }

        if (isAnswerCall(cmd)) {
            CallNotificationService.Result notificationResult =
                CallNotificationService.answer(callSource);

            if (notificationResult.handled) {
                speak(notificationResult.message);
                return;
            }

            if (callSource.equals("whatsapp") || callSource.equals("messenger")) {
                speak(notificationResult.message);
                return;
            }

            if (answerPhoneCall()) {
                speak("Answering the phone call.");
            } else {
                speak(
                    notificationResult.message +
                    " For a SIM call, allow SIM Call Control in the Masum AI Agent app."
                );
            }
            return;
        }

        if (isRejectCall(cmd)) {
            CallNotificationService.Result notificationResult =
                CallNotificationService.reject(callSource);

            if (notificationResult.handled) {
                speak(notificationResult.message);
                return;
            }

            if (callSource.equals("whatsapp") || callSource.equals("messenger")) {
                speak(notificationResult.message);
                return;
            }

            if (rejectRingingPhoneCall()) {
                speak("Rejecting the phone call.");
            } else {
                speak(
                    notificationResult.message +
                    " I did not end any active call."
                );
            }
            return;
        }

        if (matches(
            cmd,
            "read latest notification",
            "read my latest notification",
            "latest notification",
            "সর্বশেষ নোটিফিকেশন পড়ো",
            "শেষ নোটিফিকেশন পড়ো",
            "আমার শেষ নোটিফিকেশন পড়ো"
        )) {
            CallNotificationService.Result result =
                CallNotificationService.latestNotification("any");
            speak(result.message);
            return;
        }

        if (matches(
            cmd,
            "list notifications",
            "read my notifications",
            "what notifications do i have",
            "নোটিফিকেশনগুলো পড়ো",
            "আমার নোটিফিকেশন পড়ো"
        )) {
            CallNotificationService.Result result =
                CallNotificationService.listNotifications(3);
            speak(result.message);
            return;
        }

        if (matches(
            cmd,
            "read latest whatsapp message",
            "read whatsapp message",
            "latest whatsapp message",
            "সর্বশেষ হোয়াটসঅ্যাপ মেসেজ পড়ো",
            "হোয়াটসঅ্যাপ মেসেজ পড়ো"
        )) {
            CallNotificationService.Result result =
                CallNotificationService.latestNotification("whatsapp");
            speak(result.message);
            return;
        }

        if (matches(
            cmd,
            "read latest messenger message",
            "read messenger message",
            "latest messenger message",
            "সর্বশেষ মেসেঞ্জার মেসেজ পড়ো",
            "মেসেঞ্জার মেসেজ পড়ো"
        )) {
            CallNotificationService.Result result =
                CallNotificationService.latestNotification("messenger");
            speak(result.message);
            return;
        }

        Matcher banglaReply = Pattern
            .compile(
                "^(?:হোয়াটসঅ্যাপে|হোয়াটসঅ্যাপ|মেসেঞ্জারে|মেসেঞ্জার)\\s+" +
                "(?:রিপ্লাই|উত্তর)\\s+(?:দাও\\s+)?(.+)$"
            )
            .matcher(raw.trim());

        if (banglaReply.find()) {
            String lower = raw.toLowerCase(Locale.ROOT);
            pendingReplySource =
                lower.contains("মেসেঞ্জার")
                    ? "messenger"
                    : "whatsapp";
            pendingReplyText = banglaReply.group(1).trim();

            speak(
                "এই রিপ্লাই পাঠাবো: " + pendingReplyText +
                "? হ্যাঁ অথবা না বলো।"
            );
            return;
        }

        Matcher replyMessage = Pattern
            .compile(
                "^(?:reply(?: to)?|respond(?: to)?)\\s+" +
                "(whatsapp|messenger|notification)\\s+(.+)$",
                Pattern.CASE_INSENSITIVE
            )
            .matcher(raw.trim());

        if (replyMessage.find()) {
            pendingReplySource =
                replyMessage.group(1).toLowerCase(Locale.ROOT);
            pendingReplyText = replyMessage.group(2).trim();

            String target =
                pendingReplySource.equals("notification")
                    ? "the latest replyable notification"
                    : "the latest " + pendingReplySource + " chat";

            speak(
                "Send reply, " + pendingReplyText +
                ", to " + target + "? Say yes or no."
            );
            return;
        }

        if (matches(
            cmd,
            "laptop status",
            "check laptop",
            "is my laptop online",
            "ল্যাপটপ স্ট্যাটাস",
            "ল্যাপটপ অনলাইন আছে"
        )) {
            sendLaptopAction("status");
            return;
        }

        if (matches(
            cmd,
            "open vs code on laptop",
            "open vscode on laptop",
            "ল্যাপটপে ভিএস কোড খোলো",
            "ল্যাপটপে ভিজুয়াল স্টুডিও কোড খোলো"
        )) {
            sendLaptopAction("open_vscode");
            return;
        }

        if (matches(
            cmd,
            "open masum ai agent on laptop",
            "open my ai project on laptop",
            "ল্যাপটপে মাসুম এআই এজেন্ট প্রজেক্ট খোলো",
            "ল্যাপটপে আমার এআই প্রজেক্ট খোলো"
        )) {
            sendLaptopAction("open_project");
            return;
        }

        if (matches(
            cmd,
            "open chrome on laptop",
            "ল্যাপটপে ক্রোম খোলো"
        )) {
            sendLaptopAction("open_chrome");
            return;
        }

        if (matches(
            cmd,
            "open github on laptop",
            "ল্যাপটপে গিটহাব খোলো"
        )) {
            sendLaptopAction("open_github");
            return;
        }

        if (matches(
            cmd,
            "open gmail on laptop",
            "ল্যাপটপে জিমেইল খোলো"
        )) {
            sendLaptopAction("open_gmail");
            return;
        }

        if (matches(
            cmd,
            "open chatgpt on laptop",
            "ল্যাপটপে চ্যাটজিপিটি খোলো"
        )) {
            sendLaptopAction("open_chatgpt");
            return;
        }

        if (matches(
            cmd,
            "open downloads on laptop",
            "ল্যাপটপে ডাউনলোডস খোলো"
        )) {
            sendLaptopAction("open_downloads");
            return;
        }

        if (matches(cmd, "open chrome", "chrome open", "ক্রোম খোলো")) {
            openPackageOrUrl("com.android.chrome", "https://www.google.com/");
            speak("Opening Chrome.");
            return;
        }
        if (matches(cmd, "open youtube", "youtube open", "ইউটিউব খোলো")) {
            openPackageOrUrl("com.google.android.youtube", "https://www.youtube.com/");
            speak("Opening YouTube.");
            return;
        }
        if (matches(cmd, "open gmail", "gmail open", "জিমেইল খোলো")) {
            openPackageOrUrl("com.google.android.gm", "https://mail.google.com/");
            speak("Opening Gmail.");
            return;
        }
        if (matches(cmd, "open whatsapp", "whatsapp open", "হোয়াটসঅ্যাপ খোলো")) {
            openPackageOrUrl("com.whatsapp", "https://wa.me/");
            speak("Opening WhatsApp.");
            return;
        }
        if (matches(cmd, "open maps", "open google maps", "maps open", "ম্যাপস খোলো", "গুগল ম্যাপস খোলো")) {
            openPackageOrUrl("com.google.android.apps.maps", "https://maps.google.com/");
            speak("Opening Maps.");
            return;
        }
        if (matches(cmd, "open github", "github open", "গিটহাব খোলো")) {
            openUrl("https://github.com/");
            speak("Opening GitHub.");
            return;
        }
        if (matches(cmd, "open chatgpt", "chatgpt open", "open chat gpt", "চ্যাটজিপিটি খোলো")) {
            openUrl("https://chatgpt.com/");
            speak("Opening ChatGPT.");
            return;
        }
        if (matches(cmd, "open camera", "camera open", "ক্যামেরা খোলো")) {
            Intent intent = new Intent("android.media.action.IMAGE_CAPTURE");
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            safeStart(intent);
            speak("Opening camera.");
            return;
        }

        if (matches(cmd, "open settings", "settings open", "সেটিংস খোলো")) {
            openSettings(Settings.ACTION_SETTINGS);
            speak("Opening settings.");
            return;
        }
        if (matches(cmd, "wifi settings", "open wifi settings", "wi fi settings", "ওয়াইফাই সেটিংস খোলো", "ওয়াই ফাই সেটিংস খোলো")) {
            openSettings(Settings.ACTION_WIFI_SETTINGS);
            speak("Opening Wi-Fi settings.");
            return;
        }
        if (matches(cmd, "bluetooth settings", "open bluetooth settings", "ব্লুটুথ সেটিংস খোলো")) {
            openSettings(Settings.ACTION_BLUETOOTH_SETTINGS);
            speak("Opening Bluetooth settings.");
            return;
        }

        if (matches(cmd, "volume up", "increase volume", "ভলিউম বাড়াও", "সাউন্ড বাড়াও")) {
            audio.adjustStreamVolume(
                AudioManager.STREAM_MUSIC,
                AudioManager.ADJUST_RAISE,
                AudioManager.FLAG_SHOW_UI
            );
            speak("Volume up.");
            return;
        }
        if (matches(cmd, "volume down", "decrease volume", "ভলিউম কমাও", "সাউন্ড কমাও")) {
            audio.adjustStreamVolume(
                AudioManager.STREAM_MUSIC,
                AudioManager.ADJUST_LOWER,
                AudioManager.FLAG_SHOW_UI
            );
            speak("Volume down.");
            return;
        }
        if (matches(cmd, "mute", "mute volume", "volume mute", "মিউট করো", "সাউন্ড বন্ধ করো")) {
            audio.adjustStreamVolume(
                AudioManager.STREAM_MUSIC,
                AudioManager.ADJUST_MUTE,
                AudioManager.FLAG_SHOW_UI
            );
            speak("Muted.");
            return;
        }
        if (matches(cmd, "unmute", "unmute volume", "আনমিউট করো", "সাউন্ড চালু করো")) {
            audio.adjustStreamVolume(
                AudioManager.STREAM_MUSIC,
                AudioManager.ADJUST_UNMUTE,
                AudioManager.FLAG_SHOW_UI
            );
            speak("Unmuted.");
            return;
        }

        CirillaAccessibilityService accessibility =
            CirillaAccessibilityService.getInstance();

        if (matches(cmd, "go home", "home", "হোম")) {
            if (accessibility != null) {
                accessibility.performGlobalAction(
                    AccessibilityService.GLOBAL_ACTION_HOME
                );
                speak("Home.");
            } else {
                speak("Enable Accessibility Voice Control first.");
            }
            return;
        }

        if (matches(cmd, "go back", "back", "পিছনে যাও")) {
            if (accessibility != null) {
                accessibility.performGlobalAction(
                    AccessibilityService.GLOBAL_ACTION_BACK
                );
                speak("Back.");
            } else {
                speak("Enable Accessibility Voice Control first.");
            }
            return;
        }

        if (matches(cmd, "recent apps", "open recent apps", "রিসেন্ট অ্যাপস খোলো")) {
            if (accessibility != null) {
                accessibility.performGlobalAction(
                    AccessibilityService.GLOBAL_ACTION_RECENTS
                );
            } else {
                speak("Enable Accessibility Voice Control first.");
            }
            return;
        }

        if (matches(cmd, "scroll down", "স্ক্রল ডাউন")) {
            if (accessibility != null && accessibility.scroll(false)) {
                speak("Scrolling down.");
            } else {
                speak("I could not scroll this screen.");
            }
            return;
        }

        if (matches(cmd, "scroll up", "স্ক্রল আপ")) {
            if (accessibility != null && accessibility.scroll(true)) {
                speak("Scrolling up.");
            } else {
                speak("I could not scroll this screen.");
            }
            return;
        }

        Matcher click = Pattern
            .compile("^(?:click|tap|press)\\s+(.+)$")
            .matcher(cmd);

        Matcher banglaClick = Pattern
            .compile("^(.+?)\\s+(?:ক্লিক|ট্যাপ)\\s+করো$")
            .matcher(cmd);

        if (click.find() || banglaClick.find()) {
            String clickText = click.matches()
                ? click.group(1)
                : banglaClick.group(1);

            if (accessibility != null &&
                accessibility.clickText(clickText)) {
                speak("Done.");
            } else {
                speak("I could not find that control.");
            }
            return;
        }

        Matcher banglaType = Pattern
            .compile("^(?:টাইপ|লিখে দাও|লিখো)\\s+(.+)$")
            .matcher(raw.trim());

        if (banglaType.find()) {
            if (accessibility != null &&
                accessibility.typeText(banglaType.group(1))) {
                speak("Typed.");
            } else {
                speak(
                    "Focus a text field and enable Accessibility Voice Control first."
                );
            }
            return;
        }

        Matcher type = Pattern
            .compile(
                "^(?:type|write)\\s+(.+)$",
                Pattern.CASE_INSENSITIVE
            )
            .matcher(raw.trim());

        if (type.find()) {
            if (accessibility != null &&
                accessibility.typeText(type.group(1))) {
                speak("Typed.");
            } else {
                speak(
                    "Focus a text field and enable Accessibility Voice Control first."
                );
            }
            return;
        }

        Matcher dial = Pattern
            .compile("^(?:dial|call)\\s+([+0-9][0-9 -]{4,})$")
            .matcher(cmd);

        if (dial.find()) {
            String number = dial.group(1)
                .replace(" ", "")
                .replace("-", "");
            Intent intent = new Intent(
                Intent.ACTION_DIAL,
                Uri.parse("tel:" + number)
            );
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            safeStart(intent);
            speak("Opening the dialer. You can confirm the call.");
            return;
        }

        speak(
            ("geralt".equals(persona) ? "Geralt here. " : "Cirilla here. ") +
            "That mobile action is not on my safe voice list yet."
        );
    }

    private boolean isAnswerCall(String cmd) {
        return cmd.matches(
            ".*\\b(answer|accept|receive|pick up)\\b.*\\bcall\\b.*"
        ) || cmd.equals("answer") ||
           cmd.equals("receive the call") ||
           cmd.equals("কল রিসিভ করো") ||
           cmd.equals("কল ধরো") ||
           cmd.equals("কল রিসিভ কর") ||
           cmd.equals("কলটি ধরো");
    }

    private boolean isRejectCall(String cmd) {
        return cmd.matches(
            ".*\\b(reject|decline|dismiss)\\b.*\\bcall\\b.*"
        ) || cmd.equals("reject") ||
           cmd.equals("decline") ||
           cmd.equals("কল কেটে দাও") ||
           cmd.equals("কল রিজেক্ট করো") ||
           cmd.equals("কল কেটে দাও") ||
           cmd.equals("কলটি কেটে দাও");
    }

    private boolean isWhoIsCalling(String cmd) {
        return cmd.equals("who is calling") ||
            cmd.equals("who's calling") ||
            cmd.equals("who is calling me") ||
            cmd.equals("caller name") ||
            cmd.equals("কে কল করছে") ||
            cmd.equals("কে ফোন করেছে") ||
            cmd.equals("কলটি কার");
    }

    private String callSource(String cmd) {
        if (cmd.contains("whatsapp") || cmd.contains("হোয়াটসঅ্যাপ")) return "whatsapp";
        if (cmd.contains("messenger") || cmd.contains("মেসেঞ্জার")) return "messenger";
        if (cmd.contains("phone call") || cmd.contains("sim call")) {
            return "phone";
        }
        return "any";
    }

    @SuppressWarnings("deprecation")
    private boolean answerPhoneCall() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return false;
        if (!hasPhoneControlPermissions()) return false;
        if (!isPhoneRinging()) return false;

        try {
            TelecomManager telecom =
                (TelecomManager) context.getSystemService(
                    Context.TELECOM_SERVICE
                );
            if (telecom == null) return false;
            telecom.acceptRingingCall();
            return true;
        } catch (SecurityException error) {
            return false;
        }
    }

    @SuppressWarnings("deprecation")
    private boolean rejectRingingPhoneCall() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.P) return false;
        if (!hasPhoneControlPermissions()) return false;
        if (!isPhoneRinging()) return false;

        try {
            TelecomManager telecom =
                (TelecomManager) context.getSystemService(
                    Context.TELECOM_SERVICE
                );
            return telecom != null && telecom.endCall();
        } catch (SecurityException error) {
            return false;
        }
    }

    private boolean isPhoneRinging() {
        if (context.checkSelfPermission(
            Manifest.permission.READ_PHONE_STATE
        ) != PackageManager.PERMISSION_GRANTED) {
            return false;
        }

        try {
            TelephonyManager telephony =
                (TelephonyManager) context.getSystemService(
                    Context.TELEPHONY_SERVICE
                );
            return telephony != null &&
                telephony.getCallState()
                    == TelephonyManager.CALL_STATE_RINGING;
        } catch (SecurityException error) {
            return false;
        }
    }

    private boolean hasPhoneControlPermissions() {
        return context.checkSelfPermission(
            Manifest.permission.ANSWER_PHONE_CALLS
        ) == PackageManager.PERMISSION_GRANTED &&
        context.checkSelfPermission(
            Manifest.permission.READ_PHONE_STATE
        ) == PackageManager.PERMISSION_GRANTED;
    }

    private void sendLaptopAction(String action) {
        BridgeClient.send(
            context,
            action,
            (ok, message) -> speak(message)
        );
    }

    private boolean matches(String value, String... options) {
        for (String option : options) {
            if (value.equals(option)) return true;
        }
        return false;
    }

    private void openPackageOrUrl(
        String packageName,
        String fallbackUrl
    ) {
        Intent launch =
            context.getPackageManager()
                .getLaunchIntentForPackage(packageName);

        if (launch != null) {
            launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            safeStart(launch);
        } else {
            openUrl(fallbackUrl);
        }
    }

    private void openUrl(String url) {
        Intent intent = new Intent(
            Intent.ACTION_VIEW,
            Uri.parse(url)
        );
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        safeStart(intent);
    }

    private void openSettings(String action) {
        Intent intent = new Intent(action);
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        safeStart(intent);
    }

    private void safeStart(Intent intent) {
        try {
            context.startActivity(intent);
        } catch (Exception ignored) {
            speak("Android blocked that action.");
        }
    }
}

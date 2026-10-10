package com.gitwithmasum.masumai;

import android.accessibilityservice.AccessibilityService;
import android.content.Context;
import android.content.Intent;
import android.media.AudioManager;
import android.net.Uri;
import android.provider.Settings;
import android.speech.tts.TextToSpeech;

import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class VoiceCommandRouter {
    private final Context context;
    private final AudioManager audio;
    private TextToSpeech tts;

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

    public void execute(String raw, String persona) {
        String cmd = raw.toLowerCase(Locale.ROOT).trim();

        if (cmd.contains("switch to geralt") || cmd.equals("geralt mode")) {
            speak("Geralt mode active.");
            return;
        }
        if (cmd.contains("switch to cirilla") || cmd.equals("cirilla mode")) {
            speak("Cirilla mode active.");
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
        if (matches(cmd, "open maps", "open google maps", "maps open")) {
            openPackageOrUrl("com.google.android.apps.maps", "https://maps.google.com/");
            speak("Opening Maps.");
            return;
        }
        if (matches(cmd, "open github", "github open")) {
            openUrl("https://github.com/");
            speak("Opening GitHub.");
            return;
        }
        if (matches(cmd, "open chatgpt", "chatgpt open", "open chat gpt")) {
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

        if (matches(cmd, "open settings", "settings open")) {
            openSettings(Settings.ACTION_SETTINGS);
            speak("Opening settings.");
            return;
        }
        if (matches(cmd, "wifi settings", "open wifi settings", "wi fi settings")) {
            openSettings(Settings.ACTION_WIFI_SETTINGS);
            speak("Opening Wi-Fi settings.");
            return;
        }
        if (matches(cmd, "bluetooth settings", "open bluetooth settings")) {
            openSettings(Settings.ACTION_BLUETOOTH_SETTINGS);
            speak("Opening Bluetooth settings.");
            return;
        }

        if (matches(cmd, "volume up", "increase volume")) {
            audio.adjustStreamVolume(AudioManager.STREAM_MUSIC, AudioManager.ADJUST_RAISE, AudioManager.FLAG_SHOW_UI);
            speak("Volume up.");
            return;
        }
        if (matches(cmd, "volume down", "decrease volume")) {
            audio.adjustStreamVolume(AudioManager.STREAM_MUSIC, AudioManager.ADJUST_LOWER, AudioManager.FLAG_SHOW_UI);
            speak("Volume down.");
            return;
        }
        if (matches(cmd, "mute", "mute volume", "volume mute")) {
            audio.adjustStreamVolume(AudioManager.STREAM_MUSIC, AudioManager.ADJUST_MUTE, AudioManager.FLAG_SHOW_UI);
            speak("Muted.");
            return;
        }
        if (matches(cmd, "unmute", "unmute volume")) {
            audio.adjustStreamVolume(AudioManager.STREAM_MUSIC, AudioManager.ADJUST_UNMUTE, AudioManager.FLAG_SHOW_UI);
            speak("Unmuted.");
            return;
        }

        CirillaAccessibilityService accessibility = CirillaAccessibilityService.getInstance();

        if (matches(cmd, "go home", "home", "হোম")) {
            if (accessibility != null) {
                accessibility.performGlobalAction(AccessibilityService.GLOBAL_ACTION_HOME);
                speak("Home.");
            } else {
                speak("Enable Accessibility Voice Control first.");
            }
            return;
        }

        if (matches(cmd, "go back", "back", "পিছনে যাও")) {
            if (accessibility != null) {
                accessibility.performGlobalAction(AccessibilityService.GLOBAL_ACTION_BACK);
                speak("Back.");
            } else {
                speak("Enable Accessibility Voice Control first.");
            }
            return;
        }

        if (matches(cmd, "recent apps", "open recent apps")) {
            if (accessibility != null) {
                accessibility.performGlobalAction(AccessibilityService.GLOBAL_ACTION_RECENTS);
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

        Matcher click = Pattern.compile("^(?:click|tap|press)\\s+(.+)$").matcher(cmd);
        if (click.find()) {
            if (accessibility != null && accessibility.clickText(click.group(1))) {
                speak("Done.");
            } else {
                speak("I could not find that control.");
            }
            return;
        }

        Matcher type = Pattern.compile("^(?:type|write)\\s+(.+)$", Pattern.CASE_INSENSITIVE).matcher(raw.trim());
        if (type.find()) {
            if (accessibility != null && accessibility.typeText(type.group(1))) {
                speak("Typed.");
            } else {
                speak("Focus a text field and enable Accessibility Voice Control first.");
            }
            return;
        }

        Matcher dial = Pattern.compile("^(?:dial|call)\\s+([+0-9][0-9 -]{4,})$").matcher(cmd);
        if (dial.find()) {
            String number = dial.group(1).replace(" ", "").replace("-", "");
            Intent intent = new Intent(Intent.ACTION_DIAL, Uri.parse("tel:" + number));
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

    private boolean matches(String value, String... options) {
        for (String option : options) {
            if (value.equals(option)) return true;
        }
        return false;
    }

    private void openPackageOrUrl(String packageName, String fallbackUrl) {
        Intent launch = context.getPackageManager().getLaunchIntentForPackage(packageName);
        if (launch != null) {
            launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            safeStart(launch);
        } else {
            openUrl(fallbackUrl);
        }
    }

    private void openUrl(String url) {
        Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
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

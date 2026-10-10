package com.gitwithmasum.masumai;

import android.Manifest;
import android.app.Activity;
import android.app.role.RoleManager;
import android.content.ComponentName;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.os.Build;
import android.os.Bundle;
import android.provider.Settings;
import android.service.voice.VoiceInteractionService;
import android.view.Gravity;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import java.util.Locale;

public class MainActivity extends Activity {
    private static final int MIC_REQUEST = 41;
    private static final int PHONE_REQUEST = 43;
    private TextView status;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        ScrollView scroll = new ScrollView(this);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(40, 48, 40, 48);
        root.setBackgroundColor(Color.rgb(5, 11, 21));
        scroll.addView(root);

        TextView title = new TextView(this);
        title.setText("MASUM AI AGENT\nMobile Companion v5.3");
        title.setTextColor(Color.rgb(103, 232, 255));
        title.setTextSize(26);
        title.setGravity(Gravity.CENTER_HORIZONTAL);
        root.addView(title, matchWrap());

        TextView intro = new TextView(this);
        intro.setText(
            "\nOne-time Android setup:\n" +
            "1. Allow microphone\n" +
            "2. Set Masum AI Agent as Default Assistant\n" +
            "3. Allow phone call control for SIM calls\n" +
            "4. Enable Notification Access for calls, notifications and direct replies\n" +
            "5. Optional: enable Accessibility Voice Control\n" +
            "6. Pair with the Windows companion for laptop voice control\n\n" +
            "Cirilla/Geralt never auto-answer calls. A call action only runs after your explicit voice command."
        );
        intro.setTextColor(Color.WHITE);
        intro.setTextSize(16);
        root.addView(intro, matchWrap());

        status = new TextView(this);
        status.setTextColor(Color.rgb(121, 242, 178));
        status.setTextSize(15);
        status.setPadding(0, 24, 0, 24);
        root.addView(status, matchWrap());

        Button mic = button("1 — ALLOW MICROPHONE");
        mic.setOnClickListener(v -> requestMic());
        root.addView(mic, matchWrap());

        Button assistant = button("2 — SET AS DEFAULT ASSISTANT");
        assistant.setOnClickListener(v -> requestAssistantRole());
        root.addView(assistant, matchWrap());

        Button phone = button("3 — ALLOW SIM CALL CONTROL");
        phone.setOnClickListener(v -> requestPhoneControl());
        root.addView(phone, matchWrap());

        Button notifications = button("4 — ENABLE CALL + MESSAGE NOTIFICATION ACCESS");
        notifications.setOnClickListener(v -> {
            try {
                startActivity(new Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS));
            } catch (Exception error) {
                startActivity(new Intent(Settings.ACTION_SETTINGS));
            }
        });
        root.addView(notifications, matchWrap());

        Button accessibility = button("5 — ENABLE ACCESSIBILITY VOICE CONTROL");
        accessibility.setOnClickListener(v -> startActivity(
            new Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)
        ));
        root.addView(accessibility, matchWrap());

        TextView languageTitle = new TextView(this);
        languageTitle.setText("\nVOICE LANGUAGE");
        languageTitle.setTextColor(Color.rgb(103, 232, 255));
        languageTitle.setTextSize(17);
        root.addView(languageTitle, matchWrap());

        Button language = button(languageButtonText());
        language.setOnClickListener(v -> {
            cycleVoiceLanguage();
            language.setText(languageButtonText());
            updateStatus();
        });
        root.addView(language, matchWrap());

        TextView bridgeTitle = new TextView(this);
        bridgeTitle.setText("\nMOBILE ↔ LAPTOP BRIDGE");
        bridgeTitle.setTextColor(Color.rgb(103, 232, 255));
        bridgeTitle.setTextSize(17);
        root.addView(bridgeTitle, matchWrap());

        EditText bridgeUrl = new EditText(this);
        bridgeUrl.setHint("Bridge URL e.g. http://192.168.0.5:8767");
        bridgeUrl.setSingleLine(true);
        bridgeUrl.setText(BridgeClient.getUrl(this));
        root.addView(bridgeUrl, matchWrap());

        EditText bridgeKey = new EditText(this);
        bridgeKey.setHint("Pairing key from laptop");
        bridgeKey.setSingleLine(true);
        bridgeKey.setInputType(
            android.text.InputType.TYPE_CLASS_TEXT |
            android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD
        );
        bridgeKey.setText(BridgeClient.getSecret(this));
        root.addView(bridgeKey, matchWrap());

        Button saveBridge = button("SAVE + TEST LAPTOP PAIRING");
        saveBridge.setOnClickListener(v -> {
            BridgeClient.savePairing(
                this,
                bridgeUrl.getText().toString(),
                bridgeKey.getText().toString()
            );

            BridgeClient.send(
                this,
                "status",
                (ok, message) -> runOnUiThread(() -> {
                    updateStatus();
                    status.append(
                        "\nBridge test: " +
                        (ok ? "CONNECTED — " : "FAILED — ") +
                        message
                    );
                })
            );
        });
        root.addView(saveBridge, matchWrap());

        Button settings = button("OPEN VOICE / ASSISTANT SETTINGS");
        settings.setOnClickListener(v -> {
            try {
                startActivity(new Intent(Settings.ACTION_VOICE_INPUT_SETTINGS));
            } catch (Exception error) {
                startActivity(new Intent(Settings.ACTION_SETTINGS));
            }
        });
        root.addView(settings, matchWrap());

        TextView commands = new TextView(this);
        commands.setText(
            "\nCALL VOICE EXAMPLES\n\n" +
            "Hey Cirilla, answer the call\n" +
            "Hey Cirilla, receive the call\n" +
            "Hey Cirilla, reject the call\n" +
            "Hey Cirilla, who is calling?\n" +
            "Hey Cirilla, answer WhatsApp call\n" +
            "Hey Cirilla, reject WhatsApp call\n" +
            "Hey Cirilla, answer Messenger call\n" +
            "Hey Cirilla, reject Messenger call\n\n" +
            "MESSAGE VOICE EXAMPLES\n\n" +
            "Hey Cirilla, read latest notification\n" +
            "Hey Cirilla, list notifications\n" +
            "Hey Cirilla, read latest WhatsApp message\n" +
            "Hey Cirilla, read latest Messenger message\n" +
            "Hey Cirilla, reply WhatsApp I will call you later\n" +
            "Hey Cirilla, reply Messenger Okay I am coming\n" +
            "হেই সিরিলা, সর্বশেষ নোটিফিকেশন পড়ো\n" +
            "হেই সিরিলা, হোয়াটসঅ্যাপে রিপ্লাই দাও আমি পরে কল করব\n\n" +
            "LAPTOP BRIDGE EXAMPLES\n\n" +
            "Hey Cirilla, open VS Code on laptop\n" +
            "Hey Cirilla, open Chrome on laptop\n" +
            "হেই সিরিলা, ল্যাপটপে ভিএস কোড খোলো\n" +
            "হেই সিরিলা, ল্যাপটপে ক্রোম খোলো\n" +
            "হেই সিরিলা, ল্যাপটপ স্ট্যাটাস\n\n" +
            "OTHER EXAMPLES\n\n" +
            "Hey Cirilla, open Chrome\n" +
            "Hey Cirilla, open YouTube\n" +
            "Hey Cirilla, open Gmail\n" +
            "Hey Cirilla, open WhatsApp\n" +
            "Hey Cirilla, volume up\n" +
            "Hey Cirilla, go home\n" +
            "Hey Cirilla, scroll down\n" +
            "Hey Cirilla, click Send\n" +
            "Hey Cirilla, switch to Geralt"
        );
        commands.setTextColor(Color.LTGRAY);
        commands.setTextSize(15);
        root.addView(commands, matchWrap());

        setContentView(scroll);
    }

    @Override
    protected void onResume() {
        super.onResume();
        updateStatus();
    }

    private LinearLayout.LayoutParams matchWrap() {
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.WRAP_CONTENT
        );
        params.setMargins(0, 10, 0, 10);
        return params;
    }

    private Button button(String label) {
        Button button = new Button(this);
        button.setText(label);
        button.setAllCaps(false);
        return button;
    }

    private void requestMic() {
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, MIC_REQUEST);
        } else {
            updateStatus();
        }
    }

    private void requestPhoneControl() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) {
            updateStatus();
            return;
        }

        boolean answer = checkSelfPermission(Manifest.permission.ANSWER_PHONE_CALLS)
            == PackageManager.PERMISSION_GRANTED;
        boolean state = checkSelfPermission(Manifest.permission.READ_PHONE_STATE)
            == PackageManager.PERMISSION_GRANTED;

        if (!answer || !state) {
            requestPermissions(
                new String[]{
                    Manifest.permission.ANSWER_PHONE_CALLS,
                    Manifest.permission.READ_PHONE_STATE
                },
                PHONE_REQUEST
            );
        } else {
            updateStatus();
        }
    }

    private void requestAssistantRole() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            RoleManager roleManager = getSystemService(RoleManager.class);
            if (roleManager != null && roleManager.isRoleAvailable(RoleManager.ROLE_ASSISTANT)) {
                startActivityForResult(
                    roleManager.createRequestRoleIntent(RoleManager.ROLE_ASSISTANT),
                    42
                );
                return;
            }
        }

        try {
            startActivity(new Intent(Settings.ACTION_VOICE_INPUT_SETTINGS));
        } catch (Exception error) {
            startActivity(new Intent(Settings.ACTION_SETTINGS));
        }
    }

    private boolean hasNotificationAccess() {
        String enabled = Settings.Secure.getString(
            getContentResolver(),
            "enabled_notification_listeners"
        );
        if (enabled == null) return false;

        String component = new ComponentName(
            this,
            CallNotificationService.class
        ).flattenToString();

        return enabled.contains(component);
    }

    private SharedPreferences mobilePrefs() {
        return getSharedPreferences(
            "masum_mobile",
            MODE_PRIVATE
        );
    }

    private String voiceLanguageMode() {
        return mobilePrefs().getString(
            "voice_language",
            "auto"
        );
    }

    private String languageButtonText() {
        String mode = voiceLanguageMode();
        if ("bn".equals(mode)) {
            return "VOICE LANGUAGE: বাংলা";
        }
        if ("en".equals(mode)) {
            return "VOICE LANGUAGE: ENGLISH";
        }
        return "VOICE LANGUAGE: AUTO";
    }

    private void cycleVoiceLanguage() {
        String mode = voiceLanguageMode();
        String next = "auto";

        if ("auto".equals(mode)) {
            next = "bn";
        } else if ("bn".equals(mode)) {
            next = "en";
        }

        mobilePrefs()
            .edit()
            .putString("voice_language", next)
            .apply();
    }

    private void updateStatus() {
        boolean mic = checkSelfPermission(Manifest.permission.RECORD_AUDIO)
            == PackageManager.PERMISSION_GRANTED;

        boolean activeAssistant = VoiceInteractionService.isActiveService(
            this,
            new ComponentName(this, CirillaVoiceInteractionService.class)
        );

        boolean phoneControl = Build.VERSION.SDK_INT < Build.VERSION_CODES.O ||
            (
                checkSelfPermission(Manifest.permission.ANSWER_PHONE_CALLS)
                    == PackageManager.PERMISSION_GRANTED &&
                checkSelfPermission(Manifest.permission.READ_PHONE_STATE)
                    == PackageManager.PERMISSION_GRANTED
            );

        status.setText(
            "Microphone: " + (mic ? "READY" : "PERMISSION NEEDED") +
            "\nDefault Assistant: " + (activeAssistant ? "MASUM AI ACTIVE" : "NOT SELECTED") +
            "\nSIM Call Control: " + (phoneControl ? "READY" : "PERMISSION NEEDED") +
            "\nCall + Message Notification Access: " + (hasNotificationAccess() ? "READY" : "NOTIFICATION ACCESS NEEDED") +
            "\nAccessibility: " + (CirillaAccessibilityService.isRunning() ? "ENABLED" : "OPTIONAL / OFF") +
            "\nVoice Language: " + voiceLanguageMode().toUpperCase(Locale.ROOT) +
            "\nLaptop Bridge: " + (BridgeClient.isConfigured(this) ? "PAIRED" : "NOT PAIRED")
        );
    }
}

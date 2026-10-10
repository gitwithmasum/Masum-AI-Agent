package com.gitwithmasum.masumai;

import android.Manifest;
import android.app.Activity;
import android.app.role.RoleManager;
import android.content.ComponentName;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.os.Build;
import android.os.Bundle;
import android.provider.Settings;
import android.service.voice.VoiceInteractionService;
import android.view.Gravity;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

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
        title.setText("MASUM AI AGENT\nMobile Companion v5.1");
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
            "4. Enable Notification Access for WhatsApp/Messenger calls\n" +
            "5. Optional: enable Accessibility Voice Control\n\n" +
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

        Button notifications = button("4 — ENABLE WHATSAPP / MESSENGER CALL ACCESS");
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
            "\nWhatsApp/Messenger Call Access: " + (hasNotificationAccess() ? "READY" : "NOTIFICATION ACCESS NEEDED") +
            "\nAccessibility: " + (CirillaAccessibilityService.isRunning() ? "ENABLED" : "OPTIONAL / OFF")
        );
    }
}

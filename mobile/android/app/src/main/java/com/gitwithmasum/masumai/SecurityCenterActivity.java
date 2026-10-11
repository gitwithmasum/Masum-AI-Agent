package com.gitwithmasum.masumai;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.provider.Settings;
import android.view.Gravity;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

public class SecurityCenterActivity extends Activity {
    private TextView report;
    private TextView remoteHealth;

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
        title.setText(
            "MASUM AI AGENT\nSecurity + Permission Center"
        );
        title.setTextColor(Color.rgb(103, 232, 255));
        title.setTextSize(24);
        title.setGravity(Gravity.CENTER_HORIZONTAL);
        root.addView(title, matchWrap());

        TextView note = new TextView(this);
        note.setText(
            "\nThis screen does not auto-grant permissions. " +
            "Android keeps every special permission under your control.\n"
        );
        note.setTextColor(Color.LTGRAY);
        note.setTextSize(15);
        root.addView(note, matchWrap());

        report = new TextView(this);
        report.setTextColor(Color.WHITE);
        report.setTextSize(15);
        root.addView(report, matchWrap());

        Button refresh = button("REFRESH LOCAL HEALTH");
        refresh.setOnClickListener(v -> refresh());
        root.addView(refresh, matchWrap());

        Button fullCheck = button(
            "TEST BRIDGE + UNIFIED AI BRAIN"
        );
        fullCheck.setOnClickListener(v -> runRemoteHealthCheck());
        root.addView(fullCheck, matchWrap());

        remoteHealth = new TextView(this);
        remoteHealth.setTextColor(Color.rgb(121, 242, 178));
        remoteHealth.setTextSize(15);
        root.addView(remoteHealth, matchWrap());

        addSettingsButton(
            root,
            "OPEN APP PERMISSIONS",
            new Intent(
                Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                Uri.parse("package:" + getPackageName())
            )
        );

        addSettingsButton(
            root,
            "OPEN DEFAULT ASSISTANT SETTINGS",
            new Intent(Settings.ACTION_VOICE_INPUT_SETTINGS)
        );

        addSettingsButton(
            root,
            "OPEN NOTIFICATION ACCESS",
            new Intent(
                Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS
            )
        );

        addSettingsButton(
            root,
            "OPEN ACCESSIBILITY SETTINGS",
            new Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)
        );

        addSettingsButton(
            root,
            "OPEN MODIFY SYSTEM SETTINGS",
            new Intent(
                Settings.ACTION_MANAGE_WRITE_SETTINGS,
                Uri.parse("package:" + getPackageName())
            )
        );

        addSettingsButton(
            root,
            "OPEN DO NOT DISTURB ACCESS",
            new Intent(
                Settings.ACTION_NOTIFICATION_POLICY_ACCESS_SETTINGS
            )
        );

        Button pairing = button(
            "RETURN TO PAIRING + SETUP"
        );
        pairing.setOnClickListener(v -> finish());
        root.addView(pairing, matchWrap());

        TextView policy = new TextView(this);
        policy.setText(
            "\nSECURITY POLICY\n\n" +
            "• Password/PIN/OTP/CVV/security-code fields are protected.\n" +
            "• No arbitrary voice-to-shell execution.\n" +
            "• Outgoing calls/messages and notification replies require confirmation.\n" +
            "• Pending confirmations expire after 20 seconds.\n" +
            "• Incoming call answer/reject requires an explicit live voice command.\n" +
            "• Payment/security confirmation screens are not auto-clicked.\n" +
            "• Unified brain traffic uses the authenticated local bridge; dashboard stays localhost-only."
        );
        policy.setTextColor(Color.LTGRAY);
        policy.setTextSize(14);
        root.addView(policy, matchWrap());

        setContentView(scroll);
        refresh();
    }

    @Override
    protected void onResume() {
        super.onResume();
        refresh();
    }

    private void refresh() {
        report.setText(
            SecurityHealthManager.fullReport(this)
        );
    }

    private void runRemoteHealthCheck() {
        if (!BridgeClient.isConfigured(this)) {
            remoteHealth.setText(
                "Bridge: NOT PAIRED\nBrain: cannot test until pairing is configured."
            );
            return;
        }

        remoteHealth.setText("Testing bridge...");

        BridgeClient.send(
            this,
            "security_status",
            (bridgeOk, bridgeMessage) -> {
                runOnUiThread(() ->
                    remoteHealth.setText(
                        "Windows security: " +
                        (bridgeOk ? "READY" : "CHECK NEEDED") +
                        "\n" +
                        bridgeMessage +
                        "\n\nTesting unified brain..."
                    )
                );

                BridgeClient.send(
                    this,
                    "brain_status",
                    (brainOk, brainMessage) ->
                        runOnUiThread(() ->
                            remoteHealth.append(
                                "\nBrain: " +
                                (brainOk ? "READY" : "CHECK NEEDED") +
                                "\n" +
                                brainMessage
                            )
                        )
                );
            }
        );
    }

    private void addSettingsButton(
        LinearLayout root,
        String label,
        Intent intent
    ) {
        Button button = button(label);
        button.setOnClickListener(v -> {
            try {
                startActivity(intent);
            } catch (Exception error) {
                startActivity(
                    new Intent(Settings.ACTION_SETTINGS)
                );
            }
        });
        root.addView(button, matchWrap());
    }

    private Button button(String label) {
        Button button = new Button(this);
        button.setText(label);
        button.setAllCaps(false);
        return button;
    }

    private LinearLayout.LayoutParams matchWrap() {
        LinearLayout.LayoutParams params =
            new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            );
        params.setMargins(0, 10, 0, 10);
        return params;
    }
}

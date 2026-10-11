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

public class ReliabilityCenterActivity extends Activity {
    private TextView report;
    private TextView remote;

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
            "MASUM AI AGENT\nReliability Center"
        );
        title.setTextColor(Color.rgb(103, 232, 255));
        title.setTextSize(24);
        title.setGravity(Gravity.CENTER_HORIZONTAL);
        root.addView(title, matchWrap());

        TextView note = new TextView(this);
        note.setText(
            "\nReliability controls respect Android battery/background policy. " +
            "Nothing here silently grants an exemption or bypasses OEM restrictions.\n"
        );
        note.setTextColor(Color.LTGRAY);
        note.setTextSize(15);
        root.addView(note, matchWrap());

        report = new TextView(this);
        report.setTextColor(Color.WHITE);
        report.setTextSize(15);
        root.addView(report, matchWrap());

        Button refresh = button("REFRESH RELIABILITY HEALTH");
        refresh.setOnClickListener(v -> refresh());
        root.addView(refresh, matchWrap());

        Button reconnect = button("RETRY LAPTOP BRIDGE");
        reconnect.setOnClickListener(v -> testBridge());
        root.addView(reconnect, matchWrap());

        Button brain = button("TEST UNIFIED AI BRAIN");
        brain.setOnClickListener(v ->
            BridgeClient.send(
                this,
                "brain_status",
                (ok, message) ->
                    runOnUiThread(() ->
                        remote.setText(
                            "Brain: " +
                            (ok ? "READY" : "CHECK NEEDED") +
                            "\n" +
                            message
                        )
                    )
            )
        );
        root.addView(brain, matchWrap());

        remote = new TextView(this);
        remote.setTextColor(Color.rgb(121, 242, 178));
        remote.setTextSize(15);
        root.addView(remote, matchWrap());

        addSettingsButton(
            root,
            "OPEN BATTERY OPTIMIZATION SETTINGS",
            new Intent(
                Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS
            )
        );

        addSettingsButton(
            root,
            "OPEN APP BATTERY / BACKGROUND SETTINGS",
            new Intent(
                Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                Uri.parse("package:" + getPackageName())
            )
        );

        addSettingsButton(
            root,
            "OPEN WI-FI SETTINGS",
            new Intent(Settings.ACTION_WIFI_SETTINGS)
        );

        Button security = button(
            "OPEN SECURITY + PERMISSION CENTER"
        );
        security.setOnClickListener(v ->
            startActivity(
                new Intent(
                    this,
                    SecurityCenterActivity.class
                )
            )
        );
        root.addView(security, matchWrap());

        TextView guidance = new TextView(this);
        guidance.setText(
            "\nRELIABILITY NOTES\n\n" +
            "• Voice recognition now uses bounded restart backoff instead of a tight retry loop.\n" +
            "• Bridge requests retry transient connection failures with fresh HMAC nonces.\n" +
            "• Windows bridge server re-binds after recoverable failures.\n" +
            "• Android reboot still re-schedules future reminders.\n" +
            "• A changed laptop LAN IP can still require updating the saved Bridge URL.\n" +
            "• Lock-screen and OEM-specific assistant behavior must be verified on the real phone."
        );
        guidance.setTextColor(Color.LTGRAY);
        guidance.setTextSize(14);
        root.addView(guidance, matchWrap());

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
            ReliabilityHealthManager.fullReport(this)
        );
    }

    private void testBridge() {
        remote.setText("Retrying bridge...");

        BridgeClient.send(
            this,
            "reliability_status",
            (ok, message) ->
                runOnUiThread(() -> {
                    remote.setText(
                        "Windows reliability: " +
                        (ok ? "READY" : "CHECK NEEDED") +
                        "\n" +
                        message
                    );
                    refresh();
                })
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

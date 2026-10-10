package com.gitwithmasum.masumai;

import android.content.Context;
import android.content.SharedPreferences;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.UUID;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

public final class BridgeClient {
    public interface Callback {
        void onResult(boolean ok, String message);
    }

    private static final String PREFS = "masum_mobile";
    private static final String KEY_URL = "bridge_url";
    private static final String KEY_SECRET = "bridge_secret";

    private BridgeClient() {}

    public static void savePairing(
        Context context,
        String url,
        String secret
    ) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putString(KEY_URL, normalizeUrl(url))
            .putString(KEY_SECRET, secret == null ? "" : secret.trim())
            .apply();
    }

    public static String getUrl(Context context) {
        return context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getString(KEY_URL, "");
    }

    public static String getSecret(Context context) {
        return context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getString(KEY_SECRET, "");
    }

    public static boolean isConfigured(Context context) {
        return !getUrl(context).isBlank() && !getSecret(context).isBlank();
    }

    public static void send(
        Context context,
        String action,
        Callback callback
    ) {
        new Thread(() -> {
            if (!isConfigured(context)) {
                callback.onResult(
                    false,
                    "Pair your phone with the laptop bridge first."
                );
                return;
            }

            HttpURLConnection connection = null;

            try {
                String url = getUrl(context);
                String secret = getSecret(context);
                String timestamp =
                    String.valueOf(System.currentTimeMillis() / 1000L);
                String nonce = UUID.randomUUID().toString();

                JSONObject payload = new JSONObject();
                payload.put("action", action);
                String body = payload.toString();

                String signature = sign(
                    secret,
                    timestamp + "\n" + nonce + "\n" + body
                );

                connection = (HttpURLConnection)
                    new URL(url + "/action").openConnection();

                connection.setRequestMethod("POST");
                connection.setConnectTimeout(4000);
                connection.setReadTimeout(6000);
                connection.setDoOutput(true);
                connection.setRequestProperty(
                    "Content-Type",
                    "application/json; charset=utf-8"
                );
                connection.setRequestProperty(
                    "X-Masum-Timestamp",
                    timestamp
                );
                connection.setRequestProperty(
                    "X-Masum-Nonce",
                    nonce
                );
                connection.setRequestProperty(
                    "X-Masum-Signature",
                    signature
                );

                byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
                connection.setFixedLengthStreamingMode(bytes.length);
                connection.getOutputStream().write(bytes);

                int status = connection.getResponseCode();
                InputStream stream = status >= 200 && status < 300
                    ? connection.getInputStream()
                    : connection.getErrorStream();

                String response = readAll(stream);
                JSONObject result = new JSONObject(response);
                callback.onResult(
                    result.optBoolean("ok", false),
                    result.optString(
                        "message",
                        "Laptop bridge returned no message."
                    )
                );
            } catch (Exception error) {
                callback.onResult(
                    false,
                    "Laptop bridge is unreachable. Check Wi-Fi, pairing and Windows Firewall."
                );
            } finally {
                if (connection != null) connection.disconnect();
            }
        }, "MasumBridgeClient").start();
    }

    private static String normalizeUrl(String value) {
        String url = value == null ? "" : value.trim();
        while (url.endsWith("/")) {
            url = url.substring(0, url.length() - 1);
        }
        if (!url.isBlank() &&
            !url.startsWith("http://") &&
            !url.startsWith("https://")) {
            url = "http://" + url;
        }
        return url;
    }

    private static String sign(
        String secret,
        String canonical
    ) throws Exception {
        Mac mac = Mac.getInstance("HmacSHA256");
        mac.init(
            new SecretKeySpec(
                secret.getBytes(StandardCharsets.UTF_8),
                "HmacSHA256"
            )
        );
        byte[] digest = mac.doFinal(
            canonical.getBytes(StandardCharsets.UTF_8)
        );

        StringBuilder hex = new StringBuilder();
        for (byte value : digest) {
            hex.append(String.format("%02x", value & 0xff));
        }
        return hex.toString();
    }

    private static String readAll(InputStream stream)
        throws Exception {
        if (stream == null) return "{}";

        BufferedReader reader = new BufferedReader(
            new InputStreamReader(stream, StandardCharsets.UTF_8)
        );
        StringBuilder result = new StringBuilder();
        String line;

        while ((line = reader.readLine()) != null) {
            result.append(line);
        }

        return result.toString();
    }
}

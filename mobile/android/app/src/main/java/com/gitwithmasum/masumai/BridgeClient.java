package com.gitwithmasum.masumai;

import android.content.Context;
import android.content.SharedPreferences;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.ConnectException;
import java.net.SocketTimeoutException;
import java.net.UnknownHostException;
import java.net.NoRouteToHostException;
import java.net.MalformedURLException;
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
    private static final String KEY_LAST_OK = "bridge_last_ok";
    private static final String KEY_LAST_ERROR = "bridge_last_error";
    private static final String KEY_LAST_ATTEMPT = "bridge_last_attempt";

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

    public static String lastHealthText(
        Context context
    ) {
        SharedPreferences prefs =
            context.getSharedPreferences(
                PREFS,
                Context.MODE_PRIVATE
            );

        long okAt = prefs.getLong(KEY_LAST_OK, 0L);
        long attemptAt =
            prefs.getLong(KEY_LAST_ATTEMPT, 0L);
        String error =
            prefs.getString(KEY_LAST_ERROR, "");

        if (okAt > 0L && okAt >= attemptAt) {
            return "Last bridge request succeeded.";
        }

        if (attemptAt > 0L) {
            return error == null || error.isBlank()
                ? "Last bridge request failed."
                : "Last bridge request failed: " + error;
        }

        return isConfigured(context)
            ? "Bridge paired but not tested yet."
            : "Bridge not paired.";
    }

    private static void markSuccess(
        Context context
    ) {
        long now = System.currentTimeMillis();
        context.getSharedPreferences(
            PREFS,
            Context.MODE_PRIVATE
        ).edit()
            .putLong(KEY_LAST_ATTEMPT, now)
            .putLong(KEY_LAST_OK, now)
            .putString(KEY_LAST_ERROR, "")
            .apply();
    }

    private static void markFailure(
        Context context,
        String message
    ) {
        context.getSharedPreferences(
            PREFS,
            Context.MODE_PRIVATE
        ).edit()
            .putLong(
                KEY_LAST_ATTEMPT,
                System.currentTimeMillis()
            )
            .putString(
                KEY_LAST_ERROR,
                message == null ? "" : message
            )
            .apply();
    }

    public static void send(
        Context context,
        String action,
        Callback callback
    ) {
        JSONObject payload = new JSONObject();
        try {
            payload.put("action", action);
        } catch (Exception ignored) {}

        sendRequest(
            context,
            "/action",
            payload,
            8000,
            callback
        );
    }

    public static void askBrain(
        Context context,
        String prompt,
        Callback callback
    ) {
        JSONObject payload = new JSONObject();
        try {
            payload.put(
                "prompt",
                prompt == null ? "" : prompt.trim()
            );
        } catch (Exception ignored) {}

        sendRequest(
            context,
            "/brain",
            payload,
            180000,
            callback
        );
    }

    /** Find a paired laptop even if its DHCP address has changed. */
    public static void discover(Context context, Callback callback) {
        new Thread(() -> {
            if (getSecret(context).isBlank()) {
                callback.onResult(false, "Save a pairing key or scan the laptop QR first.");
                return;
            }
            String url = BridgeDiscovery.find(context, getSecret(context));
            if (url == null) {
                callback.onResult(false,
                    "No authenticated laptop found. Connect both devices to the same " +
                    "private Wi-Fi; allow UDP 8768 discovery and TCP 8767 bridge in Windows Firewall.");
                return;
            }
            savePairing(context, url, getSecret(context));
            callback.onResult(true, "Laptop discovered at " + url + ". Tap SAVE + TEST to verify.");
        }, "MasumBridgeDiscovery").start();
    }

    private static void sendRequest(
        Context context,
        String path,
        JSONObject payload,
        int readTimeout,
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

            int maxAttempts =
                path.equals("/brain") ? 2 : 3;

            String lastError =
                "Laptop bridge is unreachable.";

            boolean rediscovered = false;
            for (
                int attempt = 1;
                attempt <= maxAttempts;
                attempt++
            ) {
                HttpURLConnection connection = null;

                try {
                    String url = getUrl(context);
                    String secret = getSecret(context);
                    String timestamp =
                        String.valueOf(
                            System.currentTimeMillis() /
                            1000L
                        );
                    String nonce =
                        UUID.randomUUID().toString();
                    String body = payload.toString();

                    String signature = sign(
                        secret,
                        timestamp +
                            "\n" +
                            nonce +
                            "\n" +
                            body
                    );

                    connection =
                        (HttpURLConnection)
                            new URL(
                                url + path
                            ).openConnection();

                    connection.setRequestMethod("POST");
                    connection.setConnectTimeout(5000);
                    connection.setReadTimeout(readTimeout);
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

                    byte[] bytes =
                        body.getBytes(
                            StandardCharsets.UTF_8
                        );

                    connection
                        .setFixedLengthStreamingMode(
                            bytes.length
                        );

                    connection
                        .getOutputStream()
                        .write(bytes);

                    int status =
                        connection.getResponseCode();

                    InputStream stream =
                        status >= 200 &&
                        status < 300
                            ? connection.getInputStream()
                            : connection.getErrorStream();

                    String response =
                        readAll(stream);

                    JSONObject result =
                        new JSONObject(response);

                    boolean ok =
                        result.optBoolean(
                            "ok",
                            false
                        );

                    String message =
                        result.optString(
                            "message",
                            "Laptop bridge returned no message."
                        );

                    if (ok) {
                        markSuccess(context);
                    } else {
                        markFailure(
                            context,
                            message
                        );
                    }

                    callback.onResult(
                        ok,
                        message
                    );
                    return;
                } catch (Exception error) {
                    // A stale DHCP address is common. Discover an authenticated
                    // laptop once and retry the same signed request on its new URL.
                    if (!rediscovered && attempt < maxAttempts &&
                        (error instanceof ConnectException ||
                         error instanceof NoRouteToHostException ||
                         error instanceof SocketTimeoutException)) {
                        rediscovered = true;
                        String found = BridgeDiscovery.find(context, getSecret(context));
                        if (found != null && !found.equals(getUrl(context))) {
                            savePairing(context, found, getSecret(context));
                        }
                    }
                    // Preserve actionable diagnostics instead of collapsing every
                    // exception into "bridge unreachable". Do not expose the key.
                    if (error instanceof ConnectException ||
                        error instanceof NoRouteToHostException) {
                        lastError = "Connection refused or no route to laptop. " +
                            "Confirm the laptop bridge is running, both devices " +
                            "use the same private Wi-Fi, and Windows Firewall " +
                            "allows TCP 8767.";
                    } else if (error instanceof SocketTimeoutException) {
                        lastError = "Connection timed out. Check the laptop IP " +
                            "address, Wi-Fi client isolation, and Private " +
                            "network firewall access to TCP 8767.";
                    } else if (error instanceof UnknownHostException ||
                               error instanceof MalformedURLException) {
                        lastError = "Invalid or unresolved bridge address. " +
                            "Use the current laptop IPv4 URL, e.g. " +
                            "http://192.168.0.5:8767.";
                    } else if (error instanceof java.net.UnknownServiceException ||
                               error instanceof java.net.ProtocolException) {
                        lastError = "Bridge URL or protocol is incorrect. " +
                            "Use http://<laptop IPv4>:8767 on trusted Wi-Fi.";
                    } else {
                        lastError = "Bridge request failed (" +
                            error.getClass().getSimpleName() +
                            "). Check app network permission and laptop bridge.";
                    }

                    if (attempt < maxAttempts) {
                        try {
                            Thread.sleep(
                                attempt == 1
                                    ? 600L
                                    : 1800L
                            );
                        } catch (
                            InterruptedException ignored
                        ) {
                            Thread.currentThread()
                                .interrupt();
                            break;
                        }
                    }
                } finally {
                    if (connection != null) {
                        connection.disconnect();
                    }
                }
            }

            markFailure(
                context,
                lastError
            );

            callback.onResult(
                false,
                lastError
            );
        }, path.equals("/brain")
            ? "MasumUnifiedBrainClient"
            : "MasumBridgeClient"
        ).start();
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

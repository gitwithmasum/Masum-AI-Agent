package com.gitwithmasum.masumai;

import android.content.Context;
import android.net.wifi.DhcpInfo;
import android.net.wifi.WifiManager;
import org.json.JSONObject;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.util.Arrays;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

/** One-shot, authenticated LAN discovery. Never transmits the pairing key. */
public final class BridgeDiscovery {
    private BridgeDiscovery() {}
    private static final int PORT = 8768;

    public static String find(Context context, String pairingKey) {
        if (pairingKey == null || pairingKey.isBlank()) return null;
        byte[] random = new byte[16];
        new SecureRandom().nextBytes(random);
        StringBuilder hex = new StringBuilder();
        for (byte b : random) hex.append(String.format("%02x", b & 255));
        String nonce = hex.toString();
        DatagramSocket socket = null;
        try {
            socket = new DatagramSocket();
            socket.setBroadcast(true);
            socket.setSoTimeout(2500);
            byte[] query = new JSONObject()
                .put("type", "masum-discover-v1")
                .put("nonce", nonce).toString()
                .getBytes(StandardCharsets.UTF_8);
            send(socket, query, "255.255.255.255");
            try {
                WifiManager manager = (WifiManager) context.getApplicationContext()
                    .getSystemService(Context.WIFI_SERVICE);
                DhcpInfo info = manager == null ? null : manager.getDhcpInfo();
                if (info != null) {
                    int addr = (info.ipAddress & info.netmask) | ~info.netmask;
                    String broadcast = (addr & 255) + "." + ((addr >>> 8) & 255)
                        + "." + ((addr >>> 16) & 255) + "."
                        + ((addr >>> 24) & 255);
                    send(socket, query, broadcast);
                }
            } catch (Exception ignored) {}
            long end = System.currentTimeMillis() + 2500L;
            while (System.currentTimeMillis() < end) {
                try {
                    byte[] buffer = new byte[2048];
                    DatagramPacket packet = new DatagramPacket(buffer, buffer.length);
                    socket.receive(packet);
                    JSONObject response = new JSONObject(new String(
                        packet.getData(), 0, packet.getLength(), StandardCharsets.UTF_8));
                    if (!"masum-discover-reply-v1".equals(response.optString("type"))
                        || !nonce.equals(response.optString("nonce"))) continue;
                    String url = response.optString("url", "");
                    String signature = response.optString("signature", "");
                    if (!url.startsWith("http://") || !url.endsWith(":8767")
                        || !url.substring(7, url.length() - 5).equals(
                            packet.getAddress().getHostAddress())) continue;
                    Mac mac = Mac.getInstance("HmacSHA256");
                    mac.init(new SecretKeySpec(
                        pairingKey.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
                    byte[] digest = mac.doFinal((nonce + "\n" + url)
                        .getBytes(StandardCharsets.UTF_8));
                    StringBuilder proof = new StringBuilder();
                    for (byte b : digest) proof.append(String.format("%02x", b & 255));
                    if (MessageDigest.isEqual(proof.toString().getBytes(StandardCharsets.US_ASCII),
                        signature.getBytes(StandardCharsets.US_ASCII))) return url;
                } catch (java.net.SocketTimeoutException timeout) {
                    break;
                } catch (Exception ignored) {}
            }
        } catch (Exception ignored) {
            // Same Wi-Fi, UDP permissions and firewall are prerequisites.
        } finally {
            if (socket != null) socket.close();
        }
        return null;
    }

    private static void send(DatagramSocket socket, byte[] data, String address)
        throws Exception {
        InetAddress dst = InetAddress.getByName(address);
        socket.send(new DatagramPacket(data, data.length, dst, PORT));
    }
}

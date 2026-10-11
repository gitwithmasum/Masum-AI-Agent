package com.gitwithmasum.masumai;

import android.accessibilityservice.AccessibilityService;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.text.InputType;
import android.view.accessibility.AccessibilityEvent;
import android.view.accessibility.AccessibilityNodeInfo;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;

public class CirillaAccessibilityService extends AccessibilityService {
    public interface ScreenSearchCallback {
        void onResult(boolean found, String message);
    }

    public static final class ScreenResult {
        public final boolean ok;
        public final String message;

        ScreenResult(boolean ok, String message) {
            this.ok = ok;
            this.message = message;
        }
    }

    private static CirillaAccessibilityService instance;
    private final Handler handler = new Handler(Looper.getMainLooper());

    public static CirillaAccessibilityService getInstance() {
        return instance;
    }

    public static boolean isRunning() {
        return instance != null;
    }

    @Override
    protected void onServiceConnected() {
        super.onServiceConnected();
        instance = this;
    }

    @Override
    public void onDestroy() {
        handler.removeCallbacksAndMessages(null);
        if (instance == this) instance = null;
        super.onDestroy();
    }

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {}

    @Override
    public void onInterrupt() {}

    public boolean scroll(boolean up) {
        AccessibilityNodeInfo root = getRootInActiveWindow();
        if (root == null) return false;

        int action = up
            ? AccessibilityNodeInfo.ACTION_SCROLL_BACKWARD
            : AccessibilityNodeInfo.ACTION_SCROLL_FORWARD;

        return performScroll(root, action);
    }

    private boolean performScroll(
        AccessibilityNodeInfo node,
        int action
    ) {
        if (
            node.isScrollable() &&
            node.performAction(action)
        ) {
            return true;
        }

        for (int i = 0; i < node.getChildCount(); i++) {
            AccessibilityNodeInfo child = node.getChild(i);
            if (
                child != null &&
                performScroll(child, action)
            ) {
                return true;
            }
        }

        return false;
    }

    public boolean clickText(String text) {
        AccessibilityNodeInfo root = getRootInActiveWindow();
        if (root == null) return false;

        AccessibilityNodeInfo node =
            findSafeNode(root, text);

        if (node == null) return false;

        AccessibilityNodeInfo target = node;

        while (target != null) {
            if (
                target.isClickable() &&
                target.performAction(
                    AccessibilityNodeInfo.ACTION_CLICK
                )
            ) {
                return true;
            }
            target = target.getParent();
        }

        return false;
    }

    public boolean typeText(String text) {
        AccessibilityNodeInfo root = getRootInActiveWindow();
        if (root == null) return false;

        AccessibilityNodeInfo focused = root.findFocus(
            AccessibilityNodeInfo.FOCUS_INPUT
        );

        if (
            focused == null ||
            !focused.isEditable() ||
            isSensitiveNode(focused)
        ) {
            return false;
        }

        Bundle args = new Bundle();
        args.putCharSequence(
            AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE,
            text
        );

        return focused.performAction(
            AccessibilityNodeInfo.ACTION_SET_TEXT,
            args
        );
    }

    public ScreenResult describeScreen() {
        AccessibilityNodeInfo root = getRootInActiveWindow();

        if (root == null) {
            return new ScreenResult(
                false,
                "I cannot inspect the current screen. Enable Accessibility Voice Control first."
            );
        }

        Set<String> labels = new LinkedHashSet<>();
        collectLabels(root, labels, 14);

        if (labels.isEmpty()) {
            return new ScreenResult(
                true,
                "I can access this screen, but I found no readable visible labels."
            );
        }

        List<String> items = new ArrayList<>(labels);
        StringBuilder message = new StringBuilder(
            "On this screen I can see: "
        );

        for (int i = 0; i < items.size(); i++) {
            if (i > 0) message.append(". ");

            String item = items.get(i);
            if (message.length() + item.length() > 700) {
                message.append("And more.");
                break;
            }

            message.append(item);
        }

        return new ScreenResult(
            true,
            message.toString()
        );
    }

    public ScreenResult findOnScreen(String query) {
        AccessibilityNodeInfo root = getRootInActiveWindow();

        if (root == null) {
            return new ScreenResult(
                false,
                "I cannot inspect the current screen."
            );
        }

        String target = query == null ? "" : query.trim();

        if (target.isBlank()) {
            return new ScreenResult(
                false,
                "Tell me what to find."
            );
        }

        AccessibilityNodeInfo node =
            findSafeNode(root, target);

        if (node == null) {
            return new ScreenResult(
                false,
                "I cannot see " + target + " on the current screen."
            );
        }

        String label = safeLabel(node);

        if (
            label.isBlank() ||
            label.equals("protected field")
        ) {
            label = target;
        }

        String kind = node.isClickable()
            ? "a clickable control"
            : "visible text";

        return new ScreenResult(
            true,
            "I found " + label + ". It is " + kind + "."
        );
    }

    public void scrollUntilFind(
        String query,
        int maxScrolls,
        ScreenSearchCallback callback
    ) {
        String target = query == null ? "" : query.trim();

        if (target.isBlank()) {
            callback.onResult(
                false,
                "Tell me what to find."
            );
            return;
        }

        scrollSearchStep(
            target,
            Math.max(1, Math.min(maxScrolls, 8)),
            0,
            callback
        );
    }

    private void scrollSearchStep(
        String query,
        int maxScrolls,
        int attempt,
        ScreenSearchCallback callback
    ) {
        AccessibilityNodeInfo root =
            getRootInActiveWindow();

        if (root == null) {
            callback.onResult(
                false,
                "I cannot inspect the current screen."
            );
            return;
        }

        AccessibilityNodeInfo found =
            findSafeNode(root, query);

        if (found != null) {
            String label = safeLabel(found);
            callback.onResult(
                true,
                "Found " +
                    (label.isBlank() ? query : label) +
                    "."
            );
            return;
        }

        if (attempt >= maxScrolls) {
            callback.onResult(
                false,
                "I could not find " +
                    query +
                    " after scrolling."
            );
            return;
        }

        boolean scrolled = performScroll(
            root,
            AccessibilityNodeInfo.ACTION_SCROLL_FORWARD
        );

        if (!scrolled) {
            callback.onResult(
                false,
                "I could not find " +
                    query +
                    ", and this screen cannot scroll further."
            );
            return;
        }

        handler.postDelayed(
            () -> scrollSearchStep(
                query,
                maxScrolls,
                attempt + 1,
                callback
            ),
            450
        );
    }

    private AccessibilityNodeInfo findSafeNode(
        AccessibilityNodeInfo root,
        String query
    ) {
        String target = normalize(query);

        if (target.isBlank()) return null;

        if (!isSensitiveNode(root)) {
            String label = normalize(safeLabel(root));

            if (
                !label.isBlank() &&
                (
                    label.equals(target) ||
                    label.contains(target) ||
                    target.contains(label)
                )
            ) {
                return root;
            }
        }

        for (int i = 0; i < root.getChildCount(); i++) {
            AccessibilityNodeInfo child =
                root.getChild(i);

            if (child == null) continue;

            AccessibilityNodeInfo match =
                findSafeNode(child, query);

            if (match != null) return match;
        }

        return null;
    }

    private void collectLabels(
        AccessibilityNodeInfo node,
        Set<String> labels,
        int maxItems
    ) {
        if (
            node == null ||
            labels.size() >= maxItems
        ) {
            return;
        }

        String label = safeLabel(node);

        if (
            !label.isBlank() &&
            !isNoise(label)
        ) {
            labels.add(shortText(label, 100));
        }

        for (
            int i = 0;
            i < node.getChildCount() &&
            labels.size() < maxItems;
            i++
        ) {
            AccessibilityNodeInfo child =
                node.getChild(i);

            if (child != null) {
                collectLabels(
                    child,
                    labels,
                    maxItems
                );
            }
        }
    }

    private String safeLabel(
        AccessibilityNodeInfo node
    ) {
        if (node == null) return "";

        if (isSensitiveNode(node)) {
            if (
                node.isEditable() ||
                node.isPassword()
            ) {
                return "protected field";
            }
            return "";
        }

        CharSequence text = node.getText();

        if (
            text != null &&
            !text.toString().trim().isBlank()
        ) {
            return cleanLabel(
                text.toString()
            );
        }

        CharSequence description =
            node.getContentDescription();

        if (
            description != null &&
            !description.toString().trim().isBlank()
        ) {
            return cleanLabel(
                description.toString()
            );
        }

        CharSequence hint = node.getHintText();

        if (
            hint != null &&
            !hint.toString().trim().isBlank()
        ) {
            return cleanLabel(
                hint.toString()
            );
        }

        return "";
    }

    private boolean isSensitiveNode(
        AccessibilityNodeInfo node
    ) {
        if (node == null) return false;
        if (node.isPassword()) return true;

        int inputType = node.getInputType();

        int variation =
            inputType &
            (
                InputType.TYPE_MASK_CLASS |
                InputType.TYPE_MASK_VARIATION
            );

        if (
            variation ==
                (
                    InputType.TYPE_CLASS_TEXT |
                    InputType.TYPE_TEXT_VARIATION_PASSWORD
                ) ||
            variation ==
                (
                    InputType.TYPE_CLASS_TEXT |
                    InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD
                ) ||
            variation ==
                (
                    InputType.TYPE_CLASS_TEXT |
                    InputType.TYPE_TEXT_VARIATION_WEB_PASSWORD
                ) ||
            variation ==
                (
                    InputType.TYPE_CLASS_NUMBER |
                    InputType.TYPE_NUMBER_VARIATION_PASSWORD
                )
        ) {
            return true;
        }

        String combined =
            (
                node.getText() + " " +
                node.getHintText() + " " +
                node.getContentDescription()
            ).toLowerCase(Locale.ROOT);

        return combined.contains("password") ||
            combined.contains("passcode") ||
            combined.contains("pin") ||
            combined.contains("otp") ||
            combined.contains("one time password") ||
            combined.contains("verification code") ||
            combined.contains("security code") ||
            combined.contains("cvv") ||
            combined.contains("পাসওয়ার্ড") ||
            combined.contains("পিন") ||
            combined.contains("ওটিপি");
    }

    private boolean isNoise(String label) {
        String value = normalize(label);

        return value.isBlank() ||
            value.equals("null") ||
            value.equals("android") ||
            value.length() == 1;
    }

    private String cleanLabel(String value) {
        String cleaned = value
            .replaceAll("\\s+", " ")
            .trim();

        if (looksLikeSensitiveCode(cleaned)) {
            return "protected information";
        }

        return cleaned;
    }

    private boolean looksLikeSensitiveCode(
        String value
    ) {
        String lower =
            value.toLowerCase(Locale.ROOT);

        boolean keyword =
            lower.contains("otp") ||
            lower.contains("verification code") ||
            lower.contains("security code") ||
            lower.contains("one time password");

        return keyword &&
            lower.matches(".*\\b\\d{4,8}\\b.*");
    }

    private String normalize(String value) {
        return value == null
            ? ""
            : value
                .toLowerCase(Locale.ROOT)
                .replaceAll("\\s+", " ")
                .trim();
    }

    private String shortText(
        String value,
        int max
    ) {
        String text = value == null
            ? ""
            : value.trim();

        if (text.length() <= max) {
            return text;
        }

        return text.substring(
            0,
            Math.max(1, max - 3)
        ) + "...";
    }
}

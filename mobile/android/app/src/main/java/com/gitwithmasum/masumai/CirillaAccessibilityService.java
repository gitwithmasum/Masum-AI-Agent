package com.gitwithmasum.masumai;

import android.accessibilityservice.AccessibilityService;
import android.os.Bundle;
import android.view.accessibility.AccessibilityEvent;
import android.view.accessibility.AccessibilityNodeInfo;

import java.util.List;

public class CirillaAccessibilityService extends AccessibilityService {
    private static CirillaAccessibilityService instance;

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

    private boolean performScroll(AccessibilityNodeInfo node, int action) {
        if (node.isScrollable() && node.performAction(action)) return true;
        for (int i = 0; i < node.getChildCount(); i++) {
            AccessibilityNodeInfo child = node.getChild(i);
            if (child != null && performScroll(child, action)) return true;
        }
        return false;
    }

    public boolean clickText(String text) {
        AccessibilityNodeInfo root = getRootInActiveWindow();
        if (root == null) return false;

        List<AccessibilityNodeInfo> nodes = root.findAccessibilityNodeInfosByText(text);
        for (AccessibilityNodeInfo node : nodes) {
            AccessibilityNodeInfo target = node;
            while (target != null) {
                if (target.isClickable() && target.performAction(AccessibilityNodeInfo.ACTION_CLICK)) {
                    return true;
                }
                target = target.getParent();
            }
        }
        return false;
    }

    public boolean typeText(String text) {
        AccessibilityNodeInfo root = getRootInActiveWindow();
        if (root == null) return false;

        AccessibilityNodeInfo focused = root.findFocus(AccessibilityNodeInfo.FOCUS_INPUT);
        if (focused == null || !focused.isEditable()) return false;

        Bundle args = new Bundle();
        args.putCharSequence(
            AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE,
            text
        );
        return focused.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args);
    }
}

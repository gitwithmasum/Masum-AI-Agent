package com.gitwithmasum.masumai;

import android.Manifest;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.service.voice.VoiceInteractionService;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;

import java.util.ArrayList;
import java.util.Locale;

public class CirillaVoiceInteractionService extends VoiceInteractionService {
    private final Handler handler = new Handler(Looper.getMainLooper());
    private SpeechRecognizer recognizer;
    private boolean awake = false;
    private boolean listening = false;
    private String persona = "cirilla";
    private VoiceCommandRouter router;

    @Override
    public void onReady() {
        super.onReady();
        router = new VoiceCommandRouter(this);
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) {
            startRecognizer();
        }
    }

    @Override
    public void onShutdown() {
        stopRecognizer();
        super.onShutdown();
    }

    @Override
    public void onDestroy() {
        stopRecognizer();
        if (router != null) router.shutdown();
        super.onDestroy();
    }

    private void startRecognizer() {
        if (!SpeechRecognizer.isRecognitionAvailable(this)) return;

        handler.post(() -> {
            try {
                if (recognizer == null) {
                    if (Build.VERSION.SDK_INT >= 31 &&
                        SpeechRecognizer.isOnDeviceRecognitionAvailable(this)) {
                        recognizer = SpeechRecognizer.createOnDeviceSpeechRecognizer(this);
                    } else {
                        recognizer = SpeechRecognizer.createSpeechRecognizer(this);
                    }
                    recognizer.setRecognitionListener(new Listener());
                }
                listenAgain(250);
            } catch (Exception ignored) {
                listenAgain(1500);
            }
        });
    }

    private void stopRecognizer() {
        handler.removeCallbacksAndMessages(null);
        listening = false;
        if (recognizer != null) {
            try { recognizer.cancel(); } catch (Exception ignored) {}
            recognizer.destroy();
            recognizer = null;
        }
    }

    private Intent recognitionIntent() {
        Intent intent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
        intent.putExtra(
            RecognizerIntent.EXTRA_LANGUAGE_MODEL,
            RecognizerIntent.LANGUAGE_MODEL_FREE_FORM
        );
        intent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true);
        intent.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 3);

        String languageMode = getSharedPreferences(
            "masum_mobile",
            MODE_PRIVATE
        ).getString("voice_language", "auto");

        if ("bn".equals(languageMode)) {
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, "bn-BD");
        } else if ("en".equals(languageMode)) {
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, "en-US");
        }

        intent.putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE, true);
        return intent;
    }

    private void listenAgain(long delayMs) {
        handler.postDelayed(() -> {
            if (recognizer == null || listening) return;
            try {
                listening = true;
                recognizer.startListening(recognitionIntent());
            } catch (Exception ignored) {
                listening = false;
                listenAgain(1200);
            }
        }, delayMs);
    }

    private boolean hasWake(String text) {
        String value = text.toLowerCase(Locale.ROOT);
        if ("geralt".equals(persona)) {
            return value.contains("hey geralt") ||
                   value.contains("geralt") ||
                   value.contains("gerald") ||
                   value.contains("গেরাল্ট");
        }
        return value.contains("hey cirilla") ||
               value.contains("cirilla") ||
               value.contains("sirilla") ||
               value.contains("cirila") ||
               value.contains("সিরিলা");
    }

    private String stripWake(String text) {
        return text
            .replaceAll("(?i)hey\\s+(cirilla|sirilla|cirila|geralt|gerald)[,.:;!?\\s-]*", "")
            .replaceAll("(?i)\\b(cirilla|sirilla|cirila|geralt|gerald)\\b[,.:;!?\\s-]*", "")
            .replace("হেই সিরিলা", "")
            .replace("সিরিলা", "")
            .replace("হেই গেরাল্ট", "")
            .replace("গেরাল্ট", "")
            .trim();
    }

    private void handleText(String text) {
        if (text == null || text.trim().isEmpty()) return;

        if (!awake) {
            if (!hasWake(text)) return;
            awake = true;
            String inline = stripWake(text);
            if (!inline.isEmpty()) {
                route(inline);
                awake = router != null && router.hasPendingConfirmation();
            } else {
                router.speak("Yes?");
            }
            return;
        }

        route(text);
        awake = router != null && router.hasPendingConfirmation();
    }

    private void route(String command) {
        String normalized = command.trim().toLowerCase(Locale.ROOT);

        if (normalized.matches(".*(switch to|use)\\s+geralt.*") ||
            normalized.contains("গেরাল্ট মোড") ||
            normalized.contains("গেরাল্ট চালু")) {
            persona = "geralt";
        } else if (normalized.matches(".*(switch to|use)\\s+cirilla.*") ||
            normalized.contains("সিরিলা মোড") ||
            normalized.contains("সিরিলা চালু")) {
            persona = "cirilla";
        }

        router.execute(command, persona);
    }

    private class Listener implements RecognitionListener {
        @Override public void onReadyForSpeech(Bundle params) {}
        @Override public void onBeginningOfSpeech() {}
        @Override public void onRmsChanged(float rmsdB) {}
        @Override public void onBufferReceived(byte[] buffer) {}
        @Override public void onEndOfSpeech() {}

        @Override
        public void onError(int error) {
            listening = false;
            listenAgain(error == SpeechRecognizer.ERROR_RECOGNIZER_BUSY ? 1400 : 500);
        }

        @Override
        public void onResults(Bundle results) {
            listening = false;
            ArrayList<String> list = results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
            if (list != null && !list.isEmpty()) {
                handleText(list.get(0));
            }
            listenAgain(250);
        }

        @Override
        public void onPartialResults(Bundle partialResults) {
            ArrayList<String> list = partialResults.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
            if (!awake && list != null && !list.isEmpty() && hasWake(list.get(0))) {
                awake = true;
            }
        }

        @Override public void onEvent(int eventType, Bundle params) {}
    }
}

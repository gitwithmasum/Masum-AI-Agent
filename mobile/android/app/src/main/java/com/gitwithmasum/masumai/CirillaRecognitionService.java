package com.gitwithmasum.masumai;

import android.content.Intent;
import android.speech.RecognitionService;
import android.speech.SpeechRecognizer;

public class CirillaRecognitionService extends RecognitionService {
    @Override
    protected void onStartListening(Intent recognizerIntent, Callback callback) {
        try {
            callback.error(SpeechRecognizer.ERROR_CLIENT);
        } catch (Exception ignored) {}
    }

    @Override
    protected void onCancel(Callback callback) {}

    @Override
    protected void onStopListening(Callback callback) {}
}

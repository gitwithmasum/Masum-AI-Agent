package com.gitwithmasum.masumai;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.speech.tts.TextToSpeech;
import android.provider.MediaStore;
import android.view.Gravity;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import androidx.core.content.FileProvider;

import com.google.mlkit.vision.common.InputImage;
import com.google.mlkit.vision.label.ImageLabel;
import com.google.mlkit.vision.label.ImageLabeler;
import com.google.mlkit.vision.label.ImageLabeling;
import com.google.mlkit.vision.label.defaults.ImageLabelerOptions;
import com.google.mlkit.vision.text.TextRecognition;
import com.google.mlkit.vision.text.TextRecognizer;
import com.google.mlkit.vision.text.latin.TextRecognizerOptions;

import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

public class CameraVisionActivity extends Activity {
    public static final String EXTRA_MODE = "vision_mode";
    public static final String MODE_OCR = "ocr";
    public static final String MODE_DESCRIBE = "describe";

    private static final int CAPTURE_REQUEST = 9001;

    private TextView status;
    private TextView resultView;
    private String mode;
    private Uri photoUri;
    private File photoFile;
    private TextToSpeech tts;
    private boolean ttsReady;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        mode = getIntent().getStringExtra(EXTRA_MODE);
        if (!MODE_DESCRIBE.equals(mode)) {
            mode = MODE_OCR;
        }

        buildUi();

        tts = new TextToSpeech(this, state -> {
            if (state == TextToSpeech.SUCCESS) {
                ttsReady = true;
                tts.setLanguage(Locale.US);
                tts.setSpeechRate(0.96f);
            }
        });

        if (
            checkSelfPermission(Manifest.permission.CAMERA)
                != PackageManager.PERMISSION_GRANTED
        ) {
            status.setText(
                "Camera permission is required. Open Masum AI Agent and allow Flashlight / Camera access first."
            );
            return;
        }

        launchCamera();
    }

    private void buildUi() {
        ScrollView scroll = new ScrollView(this);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(40, 48, 40, 48);
        root.setBackgroundColor(Color.rgb(5, 11, 21));
        scroll.addView(root);

        TextView title = new TextView(this);
        title.setText(
            MODE_DESCRIBE.equals(mode)
                ? "CIRILLA VISION — DESCRIBE"
                : "CIRILLA VISION — READ TEXT"
        );
        title.setTextColor(Color.rgb(103, 232, 255));
        title.setTextSize(24);
        title.setGravity(Gravity.CENTER_HORIZONTAL);
        root.addView(title, matchWrap());

        TextView privacy = new TextView(this);
        privacy.setText(
            "\nPrivacy: the captured image is processed on-device and stored only as a temporary cache file.\n"
        );
        privacy.setTextColor(Color.LTGRAY);
        privacy.setTextSize(15);
        root.addView(privacy, matchWrap());

        status = new TextView(this);
        status.setText("Preparing camera...");
        status.setTextColor(Color.rgb(121, 242, 178));
        status.setTextSize(16);
        root.addView(status, matchWrap());

        resultView = new TextView(this);
        resultView.setTextColor(Color.WHITE);
        resultView.setTextSize(17);
        resultView.setPadding(0, 24, 0, 24);
        root.addView(resultView, matchWrap());

        Button captureAgain = new Button(this);
        captureAgain.setText("CAPTURE ANOTHER PHOTO");
        captureAgain.setAllCaps(false);
        captureAgain.setOnClickListener(v -> launchCamera());
        root.addView(captureAgain, matchWrap());

        Button close = new Button(this);
        close.setText("CLOSE");
        close.setAllCaps(false);
        close.setOnClickListener(v -> finish());
        root.addView(close, matchWrap());

        setContentView(scroll);
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

    private void launchCamera() {
        cleanupPhoto();

        try {
            File dir = new File(
                getCacheDir(),
                "vision"
            );

            if (!dir.exists() && !dir.mkdirs()) {
                status.setText(
                    "Could not create temporary vision storage."
                );
                return;
            }

            photoFile = File.createTempFile(
                "cirilla_vision_",
                ".jpg",
                dir
            );

            photoUri = FileProvider.getUriForFile(
                this,
                getPackageName() + ".fileprovider",
                photoFile
            );

            Intent intent =
                new Intent(MediaStore.ACTION_IMAGE_CAPTURE);

            intent.putExtra(
                MediaStore.EXTRA_OUTPUT,
                photoUri
            );

            intent.addFlags(
                Intent.FLAG_GRANT_READ_URI_PERMISSION |
                Intent.FLAG_GRANT_WRITE_URI_PERMISSION
            );

            if (
                intent.resolveActivity(
                    getPackageManager()
                ) == null
            ) {
                status.setText(
                    "No camera app is available."
                );
                return;
            }

            status.setText(
                MODE_DESCRIBE.equals(mode)
                    ? "Capture a photo for visual labels."
                    : "Capture a clear photo of the text or document."
            );

            startActivityForResult(
                intent,
                CAPTURE_REQUEST
            );
        } catch (IOException error) {
            status.setText(
                "Could not prepare the camera image."
            );
        }
    }

    @Override
    protected void onActivityResult(
        int requestCode,
        int resultCode,
        Intent data
    ) {
        super.onActivityResult(
            requestCode,
            resultCode,
            data
        );

        if (requestCode != CAPTURE_REQUEST) {
            return;
        }

        if (
            resultCode != RESULT_OK ||
            photoUri == null
        ) {
            status.setText("Camera capture cancelled.");
            cleanupPhoto();
            return;
        }

        analyzePhoto();
    }

    private void analyzePhoto() {
        status.setText("Analyzing on-device...");
        resultView.setText("");

        try {
            InputImage image =
                InputImage.fromFilePath(
                    this,
                    photoUri
                );

            if (MODE_DESCRIBE.equals(mode)) {
                runImageLabels(image);
            } else {
                runTextRecognition(image);
            }
        } catch (IOException error) {
            showResult(
                "I could not read the captured image."
            );
        }
    }

    private void runTextRecognition(
        InputImage image
    ) {
        TextRecognizer recognizer =
            TextRecognition.getClient(
                TextRecognizerOptions.DEFAULT_OPTIONS
            );

        recognizer
            .process(image)
            .addOnSuccessListener(result -> {
                String text =
                    sanitizeRecognizedText(
                        result.getText()
                    );

                if (text.isBlank()) {
                    showResult(
                        "I could not find readable Latin-script text. Try a sharper, closer photo."
                    );
                } else {
                    showResult(
                        "I found this text: " +
                        shortText(text, 1200)
                    );
                }

                recognizer.close();
            })
            .addOnFailureListener(error -> {
                showResult(
                    "Text recognition failed on this photo."
                );
                recognizer.close();
            });
    }

    private void runImageLabels(
        InputImage image
    ) {
        ImageLabelerOptions options =
            new ImageLabelerOptions.Builder()
                .setConfidenceThreshold(0.55f)
                .build();

        ImageLabeler labeler =
            ImageLabeling.getClient(options);

        labeler
            .process(image)
            .addOnSuccessListener(labels -> {
                List<String> useful =
                    new ArrayList<>();

                for (ImageLabel label : labels) {
                    String name =
                        label.getText() == null
                            ? ""
                            : label.getText().trim();

                    if (name.isBlank()) continue;

                    useful.add(
                        name +
                        " " +
                        Math.round(
                            label.getConfidence() * 100f
                        ) +
                        " percent"
                    );

                    if (useful.size() >= 5) {
                        break;
                    }
                }

                if (useful.isEmpty()) {
                    showResult(
                        "I could not confidently label this image. Try a clearer photo."
                    );
                } else {
                    showResult(
                        "I can see: " +
                        String.join(", ", useful) +
                        "."
                    );
                }

                labeler.close();
            })
            .addOnFailureListener(error -> {
                showResult(
                    "Image labeling failed on this photo."
                );
                labeler.close();
            });
    }

    private void showResult(String message) {
        status.setText("Analysis complete.");
        resultView.setText(message);

        if (ttsReady && tts != null) {
            tts.speak(
                message,
                TextToSpeech.QUEUE_FLUSH,
                null,
                "cirilla-vision"
            );
        }
    }

    private String sanitizeRecognizedText(
        String value
    ) {
        String text =
            value == null
                ? ""
                : value
                    .replaceAll("\\s+", " ")
                    .trim();

        String lower =
            text.toLowerCase(Locale.ROOT);

        boolean sensitive =
            lower.contains("otp") ||
            lower.contains("one time password") ||
            lower.contains("verification code") ||
            lower.contains("security code") ||
            lower.contains("cvv");

        if (
            sensitive &&
            lower.matches(".*\\b\\d{3,8}\\b.*")
        ) {
            return "Protected security-code information detected. I will not read the code aloud.";
        }

        return text;
    }

    private String shortText(
        String value,
        int max
    ) {
        String text =
            value == null ? "" : value.trim();

        if (text.length() <= max) {
            return text;
        }

        return text.substring(
            0,
            Math.max(1, max - 3)
        ) + "...";
    }

    private void cleanupPhoto() {
        if (
            photoFile != null &&
            photoFile.exists()
        ) {
            // Best-effort privacy cleanup of the previous capture.
            photoFile.delete();
        }

        photoFile = null;
        photoUri = null;
    }

    @Override
    protected void onDestroy() {
        if (tts != null) {
            tts.stop();
            tts.shutdown();
        }

        cleanupPhoto();
        super.onDestroy();
    }
}

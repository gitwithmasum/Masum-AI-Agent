package com.gitwithmasum.masumai;

import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.telephony.PhoneNumberUtils;
import android.telephony.TelephonyManager;

import java.util.Locale;

public final class SmartAppAutomationManager {
    public static final class Result {
        public final boolean ok;
        public final String message;

        Result(boolean ok, String message) {
            this.ok = ok;
            this.message = message;
        }
    }

    private SmartAppAutomationManager() {}

    public static Result searchYouTube(
        Context context,
        String query
    ) {
        String value = cleanQuery(query);
        if (value.isBlank()) {
            return new Result(false, "Tell me what to search on YouTube.");
        }

        Uri uri = Uri.parse(
            "https://www.youtube.com/results?search_query=" +
            Uri.encode(value)
        );

        Intent intent = new Intent(Intent.ACTION_VIEW, uri);
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);

        if (
            context.getPackageManager()
                .getLaunchIntentForPackage(
                    "com.google.android.youtube"
                ) != null
        ) {
            intent.setPackage("com.google.android.youtube");
        }

        return start(
            context,
            intent,
            "Searching YouTube for " + value + "."
        );
    }

    public static Result searchWeb(
        Context context,
        String query
    ) {
        String value = cleanQuery(query);
        if (value.isBlank()) {
            return new Result(false, "Tell me what to search on the web.");
        }

        Uri uri = Uri.parse(
            "https://www.google.com/search?q=" +
            Uri.encode(value)
        );

        Intent intent = new Intent(Intent.ACTION_VIEW, uri);
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);

        if (
            context.getPackageManager()
                .getLaunchIntentForPackage(
                    "com.android.chrome"
                ) != null
        ) {
            intent.setPackage("com.android.chrome");
        }

        return start(
            context,
            intent,
            "Searching the web for " + value + "."
        );
    }

    public static Result searchMaps(
        Context context,
        String query
    ) {
        String value = cleanQuery(query);
        if (value.isBlank()) {
            return new Result(false, "Tell me what place to find.");
        }

        Uri uri = Uri.parse(
            "geo:0,0?q=" + Uri.encode(value)
        );

        Intent intent = new Intent(Intent.ACTION_VIEW, uri);
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);

        if (
            context.getPackageManager()
                .getLaunchIntentForPackage(
                    "com.google.android.apps.maps"
                ) != null
        ) {
            intent.setPackage("com.google.android.apps.maps");
        }

        try {
            context.startActivity(intent);
            return new Result(
                true,
                "Searching Maps for " + value + "."
            );
        } catch (Exception primaryError) {
            Intent fallback = new Intent(
                Intent.ACTION_VIEW,
                Uri.parse(
                    "https://www.google.com/maps/search/?api=1&query=" +
                    Uri.encode(value)
                )
            );
            fallback.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);

            return start(
                context,
                fallback,
                "Searching Maps for " + value + "."
            );
        }
    }

    public static Result navigateTo(
        Context context,
        String destination
    ) {
        String value = cleanQuery(destination);
        if (value.isBlank()) {
            return new Result(false, "Tell me where you want to navigate.");
        }

        Uri uri = Uri.parse(
            "google.navigation:q=" +
            Uri.encode(value) +
            "&mode=d"
        );

        Intent intent = new Intent(Intent.ACTION_VIEW, uri);
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);

        if (
            context.getPackageManager()
                .getLaunchIntentForPackage(
                    "com.google.android.apps.maps"
                ) != null
        ) {
            intent.setPackage("com.google.android.apps.maps");
        }

        try {
            context.startActivity(intent);
            return new Result(
                true,
                "Opening navigation to " + value + "."
            );
        } catch (Exception primaryError) {
            return searchMaps(context, value);
        }
    }

    public static Result searchGitHub(
        Context context,
        String query
    ) {
        String value = cleanQuery(query);
        if (value.isBlank()) {
            return new Result(false, "Tell me what to search on GitHub.");
        }

        Intent intent = new Intent(
            Intent.ACTION_VIEW,
            Uri.parse(
                "https://github.com/search?q=" +
                Uri.encode(value)
            )
        );
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);

        return start(
            context,
            intent,
            "Searching GitHub for " + value + "."
        );
    }

    public static Result searchPlayStore(
        Context context,
        String query
    ) {
        String value = cleanQuery(query);
        if (value.isBlank()) {
            return new Result(false, "Tell me what app to find.");
        }

        Intent intent = new Intent(
            Intent.ACTION_VIEW,
            Uri.parse(
                "market://search?q=" +
                Uri.encode(value)
            )
        );
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        intent.setPackage("com.android.vending");

        try {
            context.startActivity(intent);
            return new Result(
                true,
                "Searching Play Store for " + value + "."
            );
        } catch (Exception primaryError) {
            Intent fallback = new Intent(
                Intent.ACTION_VIEW,
                Uri.parse(
                    "https://play.google.com/store/search?q=" +
                    Uri.encode(value) +
                    "&c=apps"
                )
            );
            fallback.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);

            return start(
                context,
                fallback,
                "Searching Play Store for " + value + "."
            );
        }
    }

    public static Result openWhatsAppChat(
        Context context,
        String number,
        String name
    ) {
        String international = toInternationalNumber(
            context,
            number
        );

        if (
            international == null ||
            international.isBlank()
        ) {
            return new Result(
                false,
                "I could not convert that contact number for WhatsApp."
            );
        }

        String digits = international.replaceAll(
            "[^0-9]",
            ""
        );

        Intent intent = new Intent(
            Intent.ACTION_VIEW,
            Uri.parse("https://wa.me/" + digits)
        );
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);

        if (
            context.getPackageManager()
                .getLaunchIntentForPackage(
                    "com.whatsapp"
                ) != null
        ) {
            intent.setPackage("com.whatsapp");
        }

        return start(
            context,
            intent,
            "Opening WhatsApp chat with " + name + "."
        );
    }

    private static Result start(
        Context context,
        Intent intent,
        String success
    ) {
        try {
            context.startActivity(intent);
            return new Result(true, success);
        } catch (Exception error) {
            return new Result(
                false,
                "Android could not open that app action."
            );
        }
    }

    private static String cleanQuery(String value) {
        return value == null
            ? ""
            : value
                .replaceAll("\\s+", " ")
                .trim();
    }

    private static String toInternationalNumber(
        Context context,
        String number
    ) {
        String region = "";

        try {
            TelephonyManager telephony =
                (TelephonyManager) context.getSystemService(
                    Context.TELEPHONY_SERVICE
                );

            if (telephony != null) {
                region = telephony.getNetworkCountryIso();

                if (
                    region == null ||
                    region.isBlank()
                ) {
                    region = telephony.getSimCountryIso();
                }
            }
        } catch (Exception ignored) {}

        if (
            region == null ||
            region.isBlank()
        ) {
            region = Locale.getDefault().getCountry();
        }

        String e164 =
            PhoneNumberUtils.formatNumberToE164(
                number,
                region == null
                    ? ""
                    : region.toUpperCase(Locale.ROOT)
            );

        if (e164 != null) return e164;

        String fallback =
            number == null
                ? ""
                : number.replaceAll("[^+0-9]", "");

        return fallback.startsWith("+")
            ? fallback
            : null;
    }
}

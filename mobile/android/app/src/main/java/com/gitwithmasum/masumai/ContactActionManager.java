package com.gitwithmasum.masumai;

import android.Manifest;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.database.Cursor;
import android.net.Uri;
import android.provider.ContactsContract;
import android.telephony.PhoneNumberUtils;
import android.telephony.TelephonyManager;

import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;

public final class ContactActionManager {
    public static final class ContactResult {
        public final boolean found;
        public final boolean ambiguous;
        public final String name;
        public final String number;
        public final String message;

        private ContactResult(
            boolean found,
            boolean ambiguous,
            String name,
            String number,
            String message
        ) {
            this.found = found;
            this.ambiguous = ambiguous;
            this.name = name;
            this.number = number;
            this.message = message;
        }

        public static ContactResult success(
            String name,
            String number
        ) {
            return new ContactResult(
                true,
                false,
                name,
                number,
                ""
            );
        }

        public static ContactResult failure(String message) {
            return new ContactResult(
                false,
                false,
                "",
                "",
                message
            );
        }

        public static ContactResult ambiguous(String message) {
            return new ContactResult(
                false,
                true,
                "",
                "",
                message
            );
        }
    }

    public static final class ActionResult {
        public final boolean ok;
        public final String message;

        ActionResult(boolean ok, String message) {
            this.ok = ok;
            this.message = message;
        }
    }

    private static final class Candidate {
        final long contactId;
        final String name;
        String number;
        int type;

        Candidate(
            long contactId,
            String name,
            String number,
            int type
        ) {
            this.contactId = contactId;
            this.name = name;
            this.number = number;
            this.type = type;
        }
    }

    private ContactActionManager() {}

    public static ContactResult resolve(
        Context context,
        String query
    ) {
        if (context.checkSelfPermission(
            Manifest.permission.READ_CONTACTS
        ) != PackageManager.PERMISSION_GRANTED) {
            return ContactResult.failure(
                "Allow Contacts access in the Masum AI Agent app first."
            );
        }

        String target = query == null ? "" : query.trim();
        if (target.isBlank()) {
            return ContactResult.failure(
                "Tell me which contact you want."
            );
        }

        String[] projection = new String[]{
            ContactsContract.CommonDataKinds.Phone.CONTACT_ID,
            ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME_PRIMARY,
            ContactsContract.CommonDataKinds.Phone.NUMBER,
            ContactsContract.CommonDataKinds.Phone.TYPE
        };

        String selection =
            ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME_PRIMARY +
            " LIKE ?";
        String[] args = new String[]{"%" + target + "%"};

        Map<Long, Candidate> contacts = new LinkedHashMap<>();

        try (
            Cursor cursor = context.getContentResolver().query(
                ContactsContract.CommonDataKinds.Phone.CONTENT_URI,
                projection,
                selection,
                args,
                ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME_PRIMARY +
                    " COLLATE NOCASE ASC"
            )
        ) {
            if (cursor == null) {
                return ContactResult.failure(
                    "I could not read contacts."
                );
            }

            int idIndex = cursor.getColumnIndexOrThrow(
                ContactsContract.CommonDataKinds.Phone.CONTACT_ID
            );
            int nameIndex = cursor.getColumnIndexOrThrow(
                ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME_PRIMARY
            );
            int numberIndex = cursor.getColumnIndexOrThrow(
                ContactsContract.CommonDataKinds.Phone.NUMBER
            );
            int typeIndex = cursor.getColumnIndexOrThrow(
                ContactsContract.CommonDataKinds.Phone.TYPE
            );

            while (cursor.moveToNext()) {
                long id = cursor.getLong(idIndex);
                String name = cursor.getString(nameIndex);
                String number = cursor.getString(numberIndex);
                int type = cursor.getInt(typeIndex);

                if (name == null || number == null) continue;

                Candidate existing = contacts.get(id);
                if (existing == null) {
                    contacts.put(
                        id,
                        new Candidate(id, name, number, type)
                    );
                } else if (
                    type ==
                        ContactsContract.CommonDataKinds.Phone.TYPE_MOBILE &&
                    existing.type !=
                        ContactsContract.CommonDataKinds.Phone.TYPE_MOBILE
                ) {
                    existing.number = number;
                    existing.type = type;
                }
            }
        } catch (SecurityException error) {
            return ContactResult.failure(
                "Android blocked Contacts access."
            );
        }

        if (contacts.isEmpty()) {
            return ContactResult.failure(
                "I could not find a contact named " + target + "."
            );
        }

        String normalized = target.toLowerCase(Locale.ROOT);
        Candidate exact = null;
        int exactCount = 0;

        for (Candidate candidate : contacts.values()) {
            if (
                candidate.name
                    .trim()
                    .toLowerCase(Locale.ROOT)
                    .equals(normalized)
            ) {
                exact = candidate;
                exactCount++;
            }
        }

        if (exactCount == 1 && exact != null) {
            return ContactResult.success(
                exact.name,
                exact.number
            );
        }

        if (contacts.size() == 1) {
            Candidate only = contacts.values().iterator().next();
            return ContactResult.success(
                only.name,
                only.number
            );
        }

        return ContactResult.ambiguous(
            "I found multiple contacts matching " +
            target +
            ". Say a more specific contact name."
        );
    }

    public static ActionResult call(
        Context context,
        String number,
        String name
    ) {
        Uri uri = Uri.parse(
            "tel:" + Uri.encode(number)
        );

        Intent intent;
        boolean canCall = context.checkSelfPermission(
            Manifest.permission.CALL_PHONE
        ) == PackageManager.PERMISSION_GRANTED;

        if (canCall) {
            intent = new Intent(Intent.ACTION_CALL, uri);
        } else {
            intent = new Intent(Intent.ACTION_DIAL, uri);
        }

        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);

        try {
            context.startActivity(intent);
            if (canCall) {
                return new ActionResult(
                    true,
                    "Calling " + name + "."
                );
            }
            return new ActionResult(
                true,
                "Opening the dialer for " + name +
                ". Allow Outgoing Call permission for direct calling."
            );
        } catch (Exception error) {
            return new ActionResult(
                false,
                "Android could not open the phone action."
            );
        }
    }

    public static ActionResult composeSms(
        Context context,
        String number,
        String name,
        String message
    ) {
        Intent intent = new Intent(
            Intent.ACTION_SENDTO,
            Uri.parse("smsto:" + Uri.encode(number))
        );
        intent.putExtra("sms_body", message);
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);

        try {
            context.startActivity(intent);
            return new ActionResult(
                true,
                "SMS to " + name +
                " is ready. Say Hey Cirilla, click Send, to send it."
            );
        } catch (Exception error) {
            return new ActionResult(
                false,
                "I could not open an SMS app."
            );
        }
    }

    public static ActionResult composeWhatsApp(
        Context context,
        String number,
        String name,
        String message
    ) {
        String international = toInternationalNumber(
            context,
            number
        );

        if (international == null || international.isBlank()) {
            return new ActionResult(
                false,
                "I could not convert that contact number for WhatsApp."
            );
        }

        String digits = international.replaceAll("[^0-9]", "");
        Uri uri = Uri.parse(
            "https://wa.me/" +
            digits +
            "?text=" +
            Uri.encode(message)
        );

        Intent intent = new Intent(Intent.ACTION_VIEW, uri);
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);

        if (
            context.getPackageManager()
                .getLaunchIntentForPackage("com.whatsapp") != null
        ) {
            intent.setPackage("com.whatsapp");
        }

        try {
            context.startActivity(intent);
            return new ActionResult(
                true,
                "WhatsApp message to " + name +
                " is ready. Say Hey Cirilla, click Send, to send it."
            );
        } catch (Exception error) {
            return new ActionResult(
                false,
                "I could not open WhatsApp for that contact."
            );
        }
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
                if (region == null || region.isBlank()) {
                    region = telephony.getSimCountryIso();
                }
            }
        } catch (Exception ignored) {}

        if (region == null || region.isBlank()) {
            region = Locale.getDefault().getCountry();
        }

        String e164 = PhoneNumberUtils.formatNumberToE164(
            number,
            region == null
                ? ""
                : region.toUpperCase(Locale.ROOT)
        );

        if (e164 != null) return e164;

        String fallback = number.replaceAll("[^+0-9]", "");
        return fallback.startsWith("+") ? fallback : null;
    }
}

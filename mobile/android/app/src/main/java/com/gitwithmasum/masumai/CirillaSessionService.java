package com.gitwithmasum.masumai;

import android.os.Bundle;
import android.service.voice.VoiceInteractionSession;
import android.service.voice.VoiceInteractionSessionService;

public class CirillaSessionService extends VoiceInteractionSessionService {
    @Override
    public VoiceInteractionSession onNewSession(Bundle args) {
        return new CirillaSession(this);
    }
}

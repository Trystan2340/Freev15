"""
voice.py — Moteur vocal unifié de Freev
Fusion de :
  - assistant/voice/text_to_speech.py  (TextToSpeech — Gemini v3)
  - assistant/voice/speech_to_text.py  (SpeechToText — VAD maison + wake word)
Mode texte  : VoiceManager se comporte comme l'ancien VoiceEngine de freev4
Mode vocal  : VoiceManager expose speak/listen/interrupt pour la boucle vocale
"""

import re
import threading
import sys
import unicodedata

# ── Mots de réveil ────────────────────────────────────────────────────────────
WAKE_WORDS = {
    'freev', 'free', 'freeV', 'freeve', 'friv', 'freed',
    'hey freev', 'ok freev', 'salut freev', 'hé freev'
}

# ── Seuil VAD ─────────────────────────────────────────────────────────────────
VAD_THRESHOLD   = 500
VAD_MIN_SILENCE = 0.8


def normalize_spoken_text(text: str) -> str:
    """Nettoie une phrase issue du STT avant de l'envoyer à l'IA."""
    if not text:
        return ""
    text = text.strip().lower()
    text = text.replace("’", "'").replace("`", "'")
    text = re.sub(r"'{2,}", "'", text)
    text = re.sub(r'\s+', ' ', text)

    # Retirer le mot de réveil quand il est prononcé au début.
    wake_variants = (
        'ok freev', 'hey freev', 'hé freev', 'salut freev', 'freev',
        'free v', 'freeve', 'friv', 'freed', 'free'
    )
    for wake in wake_variants:
        if text == wake:
            return ""
        if text.startswith(wake + ' '):
            text = text[len(wake):].strip()
            break

    def strip_accents(value: str) -> str:
        return ''.join(
            ch for ch in unicodedata.normalize('NFD', value)
            if unicodedata.category(ch) != 'Mn'
        )

    compact = strip_accents(text)
    replacements = {
        r'\b(?:voice|voie|vois|la voix|le voie)\s+on\b': 'voix on',
        r'\b(?:voice|voie|vois|la voix|le voie)\s+off\b': 'voix off',
        r'\bactive(?:r)?\s+(?:la\s+)?(?:voice|voie|vois)\b': 'active la voix',
        r'\bdesactive(?:r)?\s+(?:la\s+)?(?:voice|voie|vois)\b': 'voix off',
        r'\becoute\s+moi\b': 'écoute',
        r'\becoute\s+freev\b': 'écoute',
        r'\bstop\s+ecoute\b': 'stop écoute',
        r'\bstatut\s+(?:voice|voie|vois)\b': 'statut voix',
        r'\bstatus\s+(?:voice|voie|vois)\b': 'status voix',
    }
    for pattern, repl in replacements.items():
        if re.search(pattern, compact):
            return repl

    # Corrections fréquentes utiles pour la compréhension.
    text = re.sub(r"\bc est\b", "c'est", text)
    text = re.sub(r"\bqu est ce que\b", "qu'est-ce que", text)
    text = re.sub(r"\bj ai\b", "j'ai", text)
    text = re.sub(r"\bd accord\b", "d'accord", text)
    text = re.sub(r'\s+', ' ', text).strip(" .")
    return text


# ══════════════════════════════════════════════════════════════════════════════
# TextToSpeech — pyttsx3, non-bloquant, barge-in, interruption réelle
# ══════════════════════════════════════════════════════════════════════════════
class TextToSpeech:
    """
    TTS non-bloquant avec flag is_speaking pour le barge-in.
    self._engine partagé permet à interrupt() de couper vraiment la voix.
    """

    def __init__(self):
        self.rate        = 160
        self.volume      = 1.0
        self._voice_id   = None
        self.is_speaking = False
        self._engine     = None
        self._lock       = threading.Lock()
        self._detect_french_voice()

    def _detect_french_voice(self):
        try:
            import pyttsx3
            engine = pyttsx3.init()
            for v in engine.getProperty('voices'):
                name_id = ((v.name or '') + (v.id or '')).lower()
                if any(x in name_id for x in
                       ['french', 'français', 'fr-', 'fr_',
                        'hortense', 'julie', 'paul', 'zira']):
                    self._voice_id = v.id
                    print(f"🔊 Voix détectée : {v.name}")
                    break
            engine.stop()
        except Exception:
            pass

    @staticmethod
    def _clean(text: str) -> str:
        """Nettoie le texte pour la synthèse vocale : supprime ANSI, emojis, Markdown, URLs."""
        # Codes couleur ANSI
        text = re.sub(r'\x1b\[[0-9;]*m', '', text)
        # URLs
        text = re.sub(r'https?://\S+', '', text)
        # Marqueurs Freev
        text = re.sub(r'Mémorisé dans FreevBrain\s*!?', '', text, flags=re.IGNORECASE)
        text = re.sub(r'Wikipedia\s*:\s*[A-ZÀ-Ÿ][^\n]*\n?', '', text)
        text = re.sub(r'\[.*?\]', '', text)
        # Emojis et caractères Unicode hors latin étendu
        text = re.sub(r'[\U00010000-\U0010ffff]', '', text)
        text = re.sub(r'[\u2500-\u259f\u2600-\u26ff\u2700-\u27bf]', '', text)  # box + symboles
        # Caractères Markdown / déco
        text = re.sub(r'[─═╔╗╚╝║╠╣▁▂▃▄▅▆▇█]', '', text)
        text = re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', text)   # **gras** → gras
        text = re.sub(r'#{1,6}\s*', '', text)                    # titres Markdown
        text = re.sub(r'`[^`]*`', '', text)                      # `code`
        # Caractères non-vocaux
        text = re.sub(r'[^\w\s\'\",.\-!?àâäéèêëîïôùûüçœæÀÂÄÉÈÊËÎÏÔÙÛÜÇŒÆ:/()]', ' ', text)
        lines = [l.strip() for l in text.splitlines() if sum(1 for c in l if c.isalpha()) >= 3]
        text = ' '.join(lines)
        text = re.sub(r'\s+', ' ', text).strip()
        # Limiter à 350 caractères — couper à la dernière phrase complète
        if len(text) > 350:
            cut  = text[:400]
            last = max(cut.rfind('.'), cut.rfind('!'), cut.rfind('?'))
            text = cut[:last + 1] if last > 50 else text[:350] + '...'
        return text

    def speak(self, text: str):
        """Non-bloquant — le micro peut écouter pendant la parole (barge-in)."""
        clean = self._clean(text)
        if not clean:
            return
        print(f"🤖 FreeV : {clean}")

        def _say():
            with self._lock:
                try:
                    self.is_speaking = True
                    import pyttsx3
                    self._engine = pyttsx3.init()
                    if self._voice_id:
                        self._engine.setProperty('voice', self._voice_id)
                    self._engine.setProperty('rate',   self.rate)
                    self._engine.setProperty('volume', self.volume)
                    self._engine.say(clean)   # _clean() a déjà tronqué à 350 chars
                    self._engine.runAndWait()
                except Exception as e:
                    print(f"⚠️  TTS erreur : {e}")
                finally:
                    self.is_speaking = False
                    self._engine = None

        threading.Thread(target=_say, daemon=True).start()

    def wait_done(self):
        while self.is_speaking:
            threading.Event().wait(0.1)

    def interrupt(self):
        if self._engine and self.is_speaking:
            try:
                self._engine.stop()
            except Exception:
                pass
        self.is_speaking = False

    def stop(self):
        self.interrupt()


# ══════════════════════════════════════════════════════════════════════════════
# SpeechToText — VAD maison (audioop), wake word, Google STT
# ══════════════════════════════════════════════════════════════════════════════
class SpeechToText:
    """
    STT avec VAD maison (audioop.rms) et détection wake word sans Porcupine.
    wake_word_mode=False → répond à tout
    wake_word_mode=True  → attend "Freev" avant d'écouter
    """

    def __init__(self, wake_word_mode: bool = False):
        try:
            import speech_recognition as sr
            self.recognizer     = sr.Recognizer()
            self.microphone     = sr.Microphone()
            self.wake_word_mode = wake_word_mode
            self._calibrated    = False
            self._closed        = False
            self._calibrate()
        except ImportError:
            self.recognizer  = None
            self.microphone  = None
            self._calibrated = False
            self._closed     = True
            print("⚠️  SpeechRecognition non installé — pip install SpeechRecognition pyaudio")
        except Exception as e:
            self.recognizer  = None
            self.microphone  = None
            self._calibrated = False
            self._closed     = True
            print(f"⚠️  STT init échoué : {e}")

    def _calibrate(self):
        print("🎙️  Calibration micro (silence 2s svp)...")
        try:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
            self._calibrated = True
            print("🎙️  Micro prêt !")
        except Exception as e:
            print(f"⚠️  Calibration échouée : {e}")
            self._calibrated = False

    def _vad_listen(self):
        """VAD maison — audioop.rms() pour détecter début/fin de parole."""
        try:
            try:
                import pyaudiowpatch as pyaudio
            except ImportError:
                import pyaudio
            import audioop
        except ImportError:
            return None

        CHUNK       = 1024
        RATE        = 16000
        SAMPLE_W    = 2
        SILENCE_MAX = int(RATE / CHUNK * VAD_MIN_SILENCE)

        pa     = pyaudio.PyAudio()
        stream = pa.open(format=pyaudio.paInt16, channels=1, rate=RATE,
                         input=True, frames_per_buffer=CHUNK)
        print("🟢 J'écoute...", end='', flush=True)

        frames         = []
        recording      = False
        silence_chunks = 0
        max_chunks     = int(RATE / CHUNK * 10)

        try:
            for _ in range(max_chunks):
                if self._closed:
                    break
                data   = stream.read(CHUNK, exception_on_overflow=False)
                energy = audioop.rms(data, SAMPLE_W)
                if energy > VAD_THRESHOLD:
                    if not recording:
                        print("\r🔴 Enregistrement...", end='', flush=True)
                        recording = True
                    frames.append(data)
                    silence_chunks = 0
                elif recording:
                    frames.append(data)
                    silence_chunks += 1
                    if silence_chunks >= SILENCE_MAX:
                        break
        finally:
            stream.stop_stream()
            stream.close()
            pa.terminate()
            print(f"\r{' '*30}\r", end='', flush=True)

        return b''.join(frames) if frames and recording else None

    def _detect_wake_word(self) -> bool:
        try:
            import speech_recognition as sr
            with self.microphone as source:
                audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=3)
            text = self.recognizer.recognize_google(audio, language='fr-FR').lower()
            for ww in WAKE_WORDS:
                if ww in text:
                    print(f"🎯 Wake word détecté : '{text}'")
                    return True
            return False
        except Exception:
            return False

    def listen(self) -> str:
        if not self._calibrated or self._closed or not self.recognizer:
            return ""

        if self.wake_word_mode:
            print("😴 En veille — dis 'Freev' pour activer...")
            while not self._closed:
                if self._detect_wake_word():
                    break
            if self._closed:
                return ""
            print("⚡ Activé ! Je t'écoute...")

        raw_audio = self._vad_listen()
        if not raw_audio:
            return ""

        try:
            import speech_recognition as sr
            audio_data = sr.AudioData(raw_audio, sample_rate=16000, sample_width=2)
            try:
                text = self.recognizer.recognize_google(audio_data, language='fr-FR')
                normalized = normalize_spoken_text(text)
                print(f"👤 Toi : {text}" + (f" → {normalized}" if normalized and normalized != text.lower() else ""))
                return normalized
            except sr.UnknownValueError:
                return ""   # audio reçu mais rien compris
            except sr.RequestError:
                # Hors-ligne : fallback PocketSphinx
                try:
                    text = self.recognizer.recognize_sphinx(audio_data, language='fr-FR')
                    normalized = normalize_spoken_text(text)
                    print(f"👤 (offline) Toi : {text}" + (f" → {normalized}" if normalized and normalized != text.lower() else ""))
                    return normalized
                except Exception:
                    print("⚠️  STT hors-ligne. Installe PocketSphinx pour fonctionner sans internet :")
                    print("   pip install pocketsphinx")
                    return ""
        except Exception:
            return ""

    def close(self):
        self._closed     = True
        self._calibrated = False


# ══════════════════════════════════════════════════════════════════════════════
# VoiceManager — façade unifiée utilisée par main.py
# ══════════════════════════════════════════════════════════════════════════════
class VoiceManager:
    """
    Façade unique pour la voix.
    En mode texte  : speak() affiche seulement (pas de TTS sauf si activé).
    En mode vocal  : speak() + listen() + interrupt() pour la boucle vocale.

    TTS en lazy-init : le moteur pyttsx3 n'est instancié que si on est en
    mode vocal OU si l'utilisateur tape explicitement 'voix on'.
    Ça évite le ralentissement au démarrage en mode texte pur.
    """

    def __init__(self, vocal_mode: bool = False):
        self.vocal_mode  = vocal_mode
        self.tts_enabled = False
        self.stt_enabled = False
        self.tts = None
        self.stt = None

        # TTS : initialisé immédiatement en mode vocal, lazy en mode texte
        if vocal_mode:
            self._init_tts()

        if vocal_mode:
            try:
                self.stt = SpeechToText()
                self.stt_enabled = self.stt._calibrated
            except Exception as e:
                print(f"⚠️  STT non disponible : {e}")

    def _init_tts(self):
        """Initialise le TTS (appelé au premier besoin si mode texte)."""
        if self.tts is not None:
            return   # déjà initialisé
        try:
            self.tts = TextToSpeech()
            self.tts_enabled = True
        except Exception as e:
            print(f"⚠️  TTS non disponible : {e}")
            self.tts_enabled = False

    def enable_tts(self):
        """Appelé par 'voix on' depuis le mode texte — init lazy du TTS."""
        self._init_tts()
        return self.tts_enabled

    @property
    def is_speaking(self) -> bool:
        return self.tts.is_speaking if self.tts else False

    def speak(self, text: str):
        if self.tts_enabled and self.tts:
            self.tts.speak(text)

    def listen(self) -> str:
        if self.stt_enabled and self.stt:
            return self.stt.listen()
        return ""

    def interrupt(self):
        if self.tts:
            self.tts.interrupt()

    def wait_done(self):
        if self.tts:
            self.tts.wait_done()

    def stop(self):
        if self.tts:
            self.tts.stop()
        if self.stt:
            self.stt.close()

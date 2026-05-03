"""
╔══════════════════════════════════════════════════════════════════╗
║  FREEV — Point d'entrée unique                                   ║
║  python main.py          → mode texte (terminal)                 ║
║  python main.py --vocal  → mode vocal (micro + TTS)              ║
╚══════════════════════════════════════════════════════════════════╝
"""

import sys
import os
import re
import threading
import logging

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(errors='replace')
    except Exception:
        pass

# ── Le dossier de ce fichier EST le dossier du projet ────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from brain    import Freev                  # moteur IA + tous les handlers
from voice    import VoiceManager, normalize_spoken_text  # TTS + STT unifiés
from memory   import ConversationHistory    # historique vocal
from commands import run_command            # commandes système


# ── Logging (mode vocal uniquement) ──────────────────────────────────────────
def _setup_logging():
    logging.basicConfig(
        filename=os.path.join(BASE_DIR, 'freev_vocal.log'),
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        encoding='utf-8'
    )
    return logging.getLogger('freev')


# ── Nettoyage texte pour la parole ───────────────────────────────────────────
def clean_for_speech(text: str) -> str:
    """Supprime sections Wikipedia, crochets, URLs, limite à 350 chars."""
    for marker in ['\nVoir aussi', '\nRéférences', '\nBibliographie',
                   '\nNotes et références', '\nLiens externes']:
        if marker in text:
            text = text.split(marker)[0]
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text) > 350:
        cut      = text[:350]
        last_dot = max(cut.rfind('.'), cut.rfind('!'), cut.rfind('?'))
        text     = cut[:last_dot + 1] if last_dot > 0 else cut + '...'
    return text.strip()


# ── Mots de sortie ───────────────────────────────────────────────────────────
EXIT_WORDS = {"stop", "quitter", "désactiver", "au revoir", "exit", "bye", "arrête"}

def _is_exit(text: str) -> bool:
    tl = text.lower().strip()
    return any(re.search(rf'\b{re.escape(w)}\b', tl) for w in EXIT_WORDS)


# ── Animation "Freev réfléchit" ───────────────────────────────────────────────
def _thinking_animation(stop_event: threading.Event):
    import time
    frames = ['⠋', '⠙', '⠸', '⠴', '⠦', '⠇']
    i = 0
    while not stop_event.is_set():
        print(f"\r  {frames[i % len(frames)]} Freev réfléchit...", end='', flush=True)
        i += 1
        time.sleep(0.12)
    print(f"\r{' ' * 30}\r", end='', flush=True)


# ══════════════════════════════════════════════════════════════════════════════
# MODE TEXTE — boucle terminal classique
# ══════════════════════════════════════════════════════════════════════════════
def run_text_mode():
    """Lance Freev en mode texte interactif."""
    freev = Freev()
    freev.run()


# ══════════════════════════════════════════════════════════════════════════════
# MODE VOCAL — boucle micro + TTS avancée (issue de assistant/main.py)
# ══════════════════════════════════════════════════════════════════════════════
def run_vocal_mode():
    """Lance Freev en mode vocal complet avec barge-in et historique."""
    log = _setup_logging()

    print("╔════════════════════════════════════════╗")
    print("║   🤖 FREEV — Mode Vocal                ║")
    print("╚════════════════════════════════════════╝\n")
    print("⏳ Initialisation...")
    log.info("Démarrage Freev vocal")

    ai      = None
    voice   = None
    history = None

    # ── Init IA ──────────────────────────────────────────────────────────────
    try:
        ai = Freev()
    except Exception as e:
        print(f"❌ IA impossible : {e}")
        log.error(f"AI: {e}")
        sys.exit(1)

    # ── Init voix ─────────────────────────────────────────────────────────────
    try:
        voice = VoiceManager(vocal_mode=True)
    except Exception as e:
        print(f"❌ Voix impossible : {e}")
        log.error(f"Voice: {e}")
        sys.exit(1)

    if not voice.stt_enabled:
        print("❌ Micro non disponible — installe SpeechRecognition + pyaudio")
        sys.exit(1)

    # ── Init historique ───────────────────────────────────────────────────────
    try:
        history = ConversationHistory()
    except Exception as e:
        print(f"⚠️  Historique désactivé : {e}")
        history = None

    voice.speak("Système vocal prêt. Parle, je t'écoute.")
    voice.wait_done()
    print("\n💡 Parle directement — Freev répond à tout.")
    print("   Pour quitter : dis 'stop' ou 'désactiver'")
    print(f"\n{'─'*50}\n")

    CONTEXT_TURNS = 5
    error_count   = 0

    try:
        while True:
            stop_anim = None
            anim_thread = None
            try:
                # ── Barge-in : écoute même pendant la parole ─────────────────
                user_text = voice.listen()

                if not user_text:
                    error_count = 0
                    continue

                tl = normalize_spoken_text(user_text)
                if not tl:
                    continue
                print(f"👤 Tu as dit : '{tl}'")
                log.info(f"STT: '{tl}'")

                # ── Sortie ────────────────────────────────────────────────────
                if _is_exit(tl):
                    voice.speak("Arrêt des systèmes. À bientôt !")
                    voice.wait_done()
                    print("\n👋 Freev vocal désactivé.")
                    log.info("Arrêt normal")
                    break

                # ── Barge-in : couper si Freev parlait ───────────────────────
                if voice.is_speaking:
                    voice.interrupt()

                # ── Animation réflexion ───────────────────────────────────────
                stop_anim = threading.Event()
                anim_thread = threading.Thread(
                    target=_thinking_animation, args=(stop_anim,), daemon=True
                )
                anim_thread.start()

                # ── Commandes système (commands.py) en priorité ───────────────
                response = run_command(tl)

                # ── Toutes les autres commandes passent par Freev (notes, etc.) ─
                if not response:
                    ctx = history.get_last_exchanges(CONTEXT_TURNS) if history else ""
                    if ctx:
                        has_pronoun = any(p in tl.split()
                                          for p in ['il','elle','ils','elles','ça','ce','cela','lui'])
                        if has_pronoun:
                            enriched = f"[Contexte: {ctx[-200:]}] {tl}"
                            response = ai.generate_response(enriched)
                            if not response or 'connais pas' in response.lower():
                                response = ai.generate_response(tl)
                        else:
                            response = ai.generate_response(tl)
                    else:
                        response = ai.generate_response(tl)

                if not response or not response.strip():
                    response = "Je ne suis pas sûr de la réponse. Essaie de reformuler."

                stop_anim.set()
                anim_thread.join(timeout=0.5)

                clean = clean_for_speech(response)

                if history:
                    try:
                        history.save(tl, response)
                    except Exception as he:
                        log.error(f"Historique save: {he}")

                log.info(f"Réponse: '{clean[:80]}'")
                voice.speak(clean)
                print(f"{'─'*50}\n")
                error_count = 0

            except KeyboardInterrupt:
                raise

            except Exception as e:
                if stop_anim:
                    stop_anim.set()
                if anim_thread:
                    anim_thread.join(timeout=0.5)
                error_count += 1
                log.error(f"Erreur ({error_count}): {e}")
                print(f"⚠️  Erreur : {e}")
                if error_count >= 5:
                    voice.speak("Trop d'erreurs. Je m'arrête.")
                    voice.wait_done()
                    log.error("5 erreurs — arrêt forcé")
                    break

    except KeyboardInterrupt:
        print("\n⛔ Arrêt manuel.")
        if voice:
            voice.speak("À bientôt.")
            voice.wait_done()
        log.info("Arrêt Ctrl+C")

    finally:
        print("🔧 Libération des ressources...")
        if voice:
            voice.stop()
        log.info("Fin du programme")
        print("✅ Freev arrêté proprement.")


# ══════════════════════════════════════════════════════════════════════════════
# POINT D'ENTRÉE UNIQUE
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == '__main__':
    if '--vocal' in sys.argv:
        run_vocal_mode()
    else:
        run_text_mode()

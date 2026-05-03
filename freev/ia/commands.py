"""
assistant/system/commands.py
──────────────────────────────
FIX Manus : liste blanche stricte — seules les commandes explicitement
autorisées peuvent exécuter des processus système.
Toute entrée non reconnue est ignorée et renvoyée à l'IA.
"""

import os
import webbrowser
import subprocess
import urllib.parse
from datetime import datetime

# ══ LISTE BLANCHE des exécutables autorisés ═══════════════════════════════
# FIX Manus : run_command ne peut lancer QUE ces exécutables
# Aucune commande shell arbitraire n'est possible
ALLOWED_EXECUTABLES = {
    'notepad.exe',
    'calc.exe',
    'explorer.exe',
    'mspaint.exe',
}

# Sites web autorisés (webbrowser.open est limité à ces domaines)
ALLOWED_DOMAINS = {
    'youtube.com',
    'google.com',
    'github.com',
    'fr.wikipedia.org',
    'stackoverflow.com',
}


def _safe_open_url(url: str) -> bool:
    """
    FIX sécurité : vérifie que le domaine réel de l'URL est dans la liste blanche.
    Utilise urllib.parse pour éviter le contournement via 'google.com.evil.com'.
    """
    try:
        parsed = urllib.parse.urlparse(url)
        netloc = parsed.netloc.lower().lstrip('www.')
        for domain in ALLOWED_DOMAINS:
            # Vérifie domaine exact ou sous-domaine direct (ex: fr.wikipedia.org)
            if netloc == domain or netloc.endswith('.' + domain):
                webbrowser.open(url)
                return True
    except Exception:
        pass
    return False


def _safe_popen(executable: str) -> bool:
    """FIX Manus : vérifie que l'exécutable est dans la liste blanche."""
    if executable in ALLOWED_EXECUTABLES:
        try:
            subprocess.Popen([executable])
            return True
        except FileNotFoundError:
            return False
    return False


def run_command(text: str):
    """
    Intercepte les commandes système dans le texte.
    FIX Manus : toutes les actions système passent par les listes blanches.
    Retourne la réponse vocale (str) ou None si pas de commande reconnue.
    """
    t = text.lower().strip()

    # ── Navigateur ────────────────────────────────────────────────────────
    if 'ouvre youtube' in t or 'lance youtube' in t:
        _safe_open_url('https://youtube.com')
        return "J'ouvre YouTube."

    if 'ouvre google' in t or 'lance google' in t:
        _safe_open_url('https://google.com')
        return "Je lance Google."

    if 'ouvre github' in t:
        _safe_open_url('https://github.com')
        return "J'ouvre GitHub."

    if 'ouvre wikipedia' in t or 'lance wikipedia' in t:
        _safe_open_url('https://fr.wikipedia.org')
        return "J'ouvre Wikipedia."

    if 'ouvre stackoverflow' in t or 'lance stackoverflow' in t:
        _safe_open_url('https://stackoverflow.com')
        return "J'ouvre Stack Overflow."

    # ── Applications (liste blanche) ──────────────────────────────────────
    if 'ouvre le bloc-notes' in t or 'ouvre notepad' in t:
        _safe_popen('notepad.exe')
        return "J'ouvre le Bloc-notes."

    if 'ouvre la calculatrice' in t or 'ouvre calculatrice' in t:
        _safe_popen('calc.exe')
        return "J'ouvre la calculatrice."

    if "ouvre l'explorateur" in t or 'ouvre les fichiers' in t:
        _safe_popen('explorer.exe')
        return "J'ouvre l'explorateur de fichiers."

    if 'ouvre paint' in t or 'ouvre mspaint' in t or 'lance paint' in t:
        _safe_popen('mspaint.exe')
        return "J'ouvre Paint."

    # ── Recherche web ─────────────────────────────────────────────────────
    if t.startswith('recherche ') or t.startswith('cherche sur google '):
        query = t.replace('recherche ', '').replace('cherche sur google ', '').strip()
        if query:
            safe_query = urllib.parse.urlencode({'q': query})
            _safe_open_url(f'https://google.com/search?{safe_query}')
            return f"Je recherche '{query}' sur Google."

    # ── Volume ────────────────────────────────────────────────────────────
    if 'monte le son' in t or 'augmente le volume' in t:
        try:
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            vol = min(volume.GetMasterVolumeLevelScalar() + 0.1, 1.0)
            volume.SetMasterVolumeLevelScalar(vol, None)
            return f"Volume monté à {int(vol*100)}%."
        except Exception:
            return "Je ne peux pas contrôler le volume sur ce système."

    if 'baisse le son' in t or 'diminue le volume' in t or 'volume moins' in t:
        try:
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            vol = max(volume.GetMasterVolumeLevelScalar() - 0.1, 0.0)
            volume.SetMasterVolumeLevelScalar(vol, None)
            return f"Volume baissé à {int(vol*100)}%."
        except Exception:
            return "Je ne peux pas contrôler le volume sur ce système."

    # ── Extinction (désactivée par défaut) ────────────────────────────────
    if 'éteins le pc' in t or "arrête l'ordinateur" in t:
        return "Extinction désactivée en mode sécurisé."

    if 'redémarre le pc' in t or "redémarre l'ordinateur" in t:
        return "Redémarrage désactivé en mode sécurisé."

    return None

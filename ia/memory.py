"""
memory.py — Historique des conversations vocales
Issu de assistant/brain/memory.py (Gemini v3)
Chemin mis à jour : vocal_history.json dans le dossier du script
"""

import json
from pathlib import Path


class ConversationHistory:
    """
    Historique des échanges (texte et vocal) — max 100 tours gardés.
    Cache en mémoire : le fichier n'est relu que si modifié sur le disque.
    """

    MAX_ENTRIES = 100   # was 50

    def __init__(self):
        # Fichier dans le même dossier que ce script
        self.file = Path(__file__).parent / 'vocal_history.json'
        self._cache = None                # cache en mémoire
        self._cache_mtime: float = 0.0    # timestamp du fichier au dernier chargement
        self._ensure_file()

    def _ensure_file(self):
        if not self.file.exists():
            self.file.write_text('[]', encoding='utf-8')

    def save(self, user: str, bot: str):
        data = self.load()
        if len(data) >= self.MAX_ENTRIES:
            data = data[-(self.MAX_ENTRIES - 1):]
        data.append({'user': user, 'bot': bot})
        self.file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
        # Mettre à jour le cache en mémoire directement — évite une relecture disque
        self._cache = data
        self._cache_mtime = self.file.stat().st_mtime

    def load(self) -> list:
        """
        Charge l'historique depuis le disque uniquement si le fichier a changé.
        Sinon retourne le cache en mémoire.
        """
        try:
            mtime = self.file.stat().st_mtime
            if self._cache is not None and mtime == self._cache_mtime:
                return list(self._cache)   # copie légère pour éviter les mutations
            data = json.loads(self.file.read_text(encoding='utf-8'))
            self._cache = data
            self._cache_mtime = mtime
            return list(data)
        except Exception:
            return []

    def recent(self, n: int = 5) -> list:
        return self.load()[-n:]

    def get_last_exchanges(self, n: int = 5) -> str:
        """
        Retourne les n derniers échanges formatés pour injecter dans l'IA.
        Ex : "Utilisateur: qui est Napoléon\nFreev: ..."
        """
        exchanges = self.recent(n)
        if not exchanges:
            return ""
        lines = []
        for e in exchanges:
            lines.append(f"Utilisateur: {e['user']}")
            lines.append(f"Freev: {e['bot'][:100]}")
        return "\n".join(lines)

    def clear(self):
        self.file.write_text('[]', encoding='utf-8')
        self._cache = []
        self._cache_mtime = self.file.stat().st_mtime
        print("🗑️  Historique vocal effacé.")

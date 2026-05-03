#!/usr/bin/env python3
"""
Freev - IA conversationnelle avancée pour terminal sans API
Système intelligent local avec multiples fonctionnalités
(Version 2.1 - Fonctionnalités étendues sans API)
"""

import re
import json
import random
import time
import sys
import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from collections import Counter
import math
import base64
import threading
import secrets
import socket  # Pour scanner de ports local et IP locale
import calendar  # Pour la nouvelle fonctionnalité de calendrier
import difflib  # Pour la nouvelle fonctionnalité de comparaison de fichiers

try:
    import psutil
except ImportError:
    psutil = None  # Pour mini-logs systèmes, optionnel

class Colors:
    """Codes ANSI pour les couleurs"""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    ITALIC = '\033[3m'
    UNDERLINE = '\033[4m'
    
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'

class Freev:
    def __init__(self):
        self.context = []
        self.user_name = None
        self.user_preferences = {}
        self.notes = []
        self.reminders = []
        self.memory_file = Path.home() / ".freev_memory.json"
        
        # Ajout des modes de personnalité
        self.mode = "normal"  # Modes: normal, fun, dark, philosophique, gentil, cynique, motivant
        
        # Pour jeux comme pendu
        self.game_state = {}  # État des jeux: pendu, morpion, devine_nombre
        
        # Niveau d'intelligence
        self.level = 0
        
        # Mémoire thématique
        self.themed_memory = {}  # Ex: {'couleur_preferee': 'bleu'}
        
        # Évolution du caractère
        self.character_evolution = ["gentil", "froid", "philosophique", "cynique"]
        self.current_character_index = 0
        
        # Mots utilisateur pour fusion
        self.user_style = []  # Liste de mots/phrases utilisateur

        # NOUVEAU: Mots vides pour la fonction 'mots cles'
        self.stop_words = set([
            'a', 'ai', 'ait', 'alors', 'au', 'aux', 'avec', 'bon', 'car', 'ce', 'ces', 'comme', 'dans', 'de', 'des', 
            'du', 'elle', 'en', 'est', 'et', 'ete', 'etre', 'eu', 'faire', 'il', 'ils', 'je', 'la', 'le', 'les', 
            'leur', 'lui', 'ma', 'mais', 'me', 'mes', 'moi', 'mon', 'ne', 'nos', 'notre', 'nous', 'on', 'ont', 
            'ou', 'par', 'pas', 'plus', 'pour', 'que', 'qui', 'sa', 'se', 'ses', 'son', 'sont', 'sur', 'ta', 
            'te', 'tes', 'toi', 'ton', 'tu', 'un', 'une', 'vos', 'votre', 'vous', 'y', 'd', 'l', 'm', 'n', 's', 't',
            'ceci', 'cela', 'cet', 'cette', 'celui', 'ceux', 'celle', 'celles', 'donc', 'dont', 'ici', 'juste',
            'comment', 'quand', 'quoi', 'quel', 'quelle', 'quels', 'quelles'
        ])

        # NOUVEAU: Dictionnaire pour ASCII Art
        self.ascii_art = {
            "chat": [
                "  /\\_/\\",
                " ( o.o )",
                "  > ^ <"
            ],
            "coeur": [
                "  ( \\/ )",
                " ( \\/ )",
                "  ( \\/ )",
                "   \\  /",
                "    \\/"
            ],
            "python": [
                "   ____",
                "  / . .\\",
                "  \\  ---<",
                "   \\  /",
                "  / /_\\_\\",
                " (  / (  \\",
                " |  |  \\  \\",
                "  \\ \\   \\  \\",
                "   `\\ `   \\  \\"
            ]
        }
        
        # --- Pré-compilation des Regex pour la performance ---
        self.re_name_extract = re.compile(r'je m\'appelle (\w+)', re.IGNORECASE)
        
        # Notes
        self.re_note_add = re.compile(r'note:(.*)', re.IGNORECASE)
        self.re_note_del = re.compile(r'supprime note (\d+)', re.IGNORECASE)
        self.re_note_done = re.compile(r'fait note (\d+)', re.IGNORECASE)
        self.re_note_search = re.compile(r'cherche note (.+)', re.IGNORECASE)
        
        # Rappels
        self.re_reminder_add = re.compile(r'rappel:\s*(.+?)\s*(dans|à)\s*(\d+)\s*(minutes?|heures?|jours?|secondes?)', re.IGNORECASE)
        self.re_reminder_del = re.compile(r'supprime rappel (\d+)', re.IGNORECASE)
        
        # Outils
        self.re_password_gen = re.compile(r'(mot de passe|password)\s*(\d+)?', re.IGNORECASE)
        self.re_translation = re.compile(r'traduis\s+(.+)', re.IGNORECASE)
        self.re_text_analysis = re.compile(r'analyse\s+["\'](.+)["\']', re.IGNORECASE)
        self.re_timer = re.compile(r'(minuteur|timer)\s+(\d+)\s+(minutes?|secondes?|heures?)', re.IGNORECASE)
        self.re_unit_convert = re.compile(r'convert\s+(\d+\.?\d*)\s+(\w+)\s+to\s+(\w+)', re.IGNORECASE) # Supporte float
        self.re_bmi = re.compile(r'calcule imc poids (\d+\.?\d*) taille (\d+\.?\d*)', re.IGNORECASE) # Supporte float
        self.re_dice_roll = re.compile(r'lance dé\s*(\d+)?', re.IGNORECASE)
        
        # Codage
        self.re_base64_encode = re.compile(r'encode base64\s+(.+)', re.IGNORECASE)
        self.re_base64_decode = re.compile(r'decode base64\s+(.+)', re.IGNORECASE)
        self.re_random_num = re.compile(r'nombre aléatoire\s+(\d+)\s+(\d+)', re.IGNORECASE)
        self.re_palindrome = re.compile(r'palindrome\s+(.+)', re.IGNORECASE)
        self.re_fibonacci = re.compile(r'fibonacci\s+(\d+)', re.IGNORECASE)
        self.re_prime_check = re.compile(r'premier\s+(\d+)', re.IGNORECASE)
        self.re_morse_encode = re.compile(r'(encode|coder) morse\s+(.+)', re.IGNORECASE)
        self.re_morse_decode = re.compile(r'(decode|décoder) morse\s+(.+)', re.IGNORECASE)
        self.re_binary_encode = re.compile(r'(encode|coder) binary\s+(.+)', re.IGNORECASE)
        self.re_binary_decode = re.compile(r'(decode|décoder) binary\s+(.+)', re.IGNORECASE)
        self.re_binary_convert_num = re.compile(r'convertis en binaire (\d+)', re.IGNORECASE)
        self.re_caesar_encode = re.compile(r'(encode|chiffre) caesar\s+(.+)', re.IGNORECASE)
        self.re_caesar_decode = re.compile(r'(decode|déchiffre) caesar\s+(.+)', re.IGNORECASE)
        self.re_vigenere_encode = re.compile(r'(encode|chiffre) vigenere\s+(.+)', re.IGNORECASE)
        self.re_vigenere_decode = re.compile(r'(decode|déchiffre) vigenere\s+(.+)', re.IGNORECASE)
        
        # Avancé
        self.re_mode_change = re.compile(r'change de personnalité (fun|dark|philosophique|gentil|cynique|motivant)', re.IGNORECASE)
        self.re_simulator = re.compile(r'simule un (hacker|scientifique|philosophe)', re.IGNORECASE)
        self.re_equation_solve = re.compile(r'résous (.+)', re.IGNORECASE)
        self.re_equation_linear = re.compile(r'(\d*)x([+-]\d+)?=([+-]?\d+)', re.IGNORECASE)
        self.re_equation_quad = re.compile(r'(\d*)x\^2([+-]\d+)x([+-]\d+)=0', re.IGNORECASE)
        self.re_logical_reasoning = re.compile(r'si j’ai (\d+) (\w+) et j’en (donne|ajoute|mange) (\d+)', re.IGNORECASE)
        self.re_logical_rain = re.compile(r'si (.+) il pleut, que devrais-je faire', re.IGNORECASE)
        self.re_file_analysis = re.compile(r'analyse fichier (.+)', re.IGNORECASE)
        self.re_system_command = re.compile(r'exécute (.+)', re.IGNORECASE)
        self.re_file_explorer = re.compile(r'explore dossier\s*(.*)', re.IGNORECASE)
        self.re_file_delete = re.compile(r'supprime fichier (.+)', re.IGNORECASE)
        self.re_text_summary = re.compile(r'résume ce texte : "(.+)"', re.IGNORECASE)
        self.re_world_time = re.compile(r'heure à ([\w ]+)', re.IGNORECASE)
        self.re_financial_calc = re.compile(r'épargne (\d+)€?/mois pendant (\d+) (ans|mois) à (\d+)%', re.IGNORECASE)
        self.re_search_history = re.compile(r'recherche dans historique ‘(.+)’', re.IGNORECASE)
        self.re_memory_theme = re.compile(r'souviens-toi que (.+?) c’est (.+)', re.IGNORECASE)

        # NOUVEAU: Regex pour nouvelles fonctionnalités
        self.re_cree_fichier = re.compile(r'cree fichier (.+?)\s+"(.+)"', re.IGNORECASE)
        self.re_ajoute_fichier = re.compile(r'ajoute a (.+?)\s+"(.+)"', re.IGNORECASE)
        self.re_compare_fichiers = re.compile(r'compare (.+?) (.+)', re.IGNORECASE)
        self.re_ip_locale = re.compile(r'mon ip locale', re.IGNORECASE)
        self.re_nom_hote = re.compile(r'mon nom d\'hote', re.IGNORECASE)
        self.re_liste_processus = re.compile(r'liste processus', re.IGNORECASE)
        self.re_joue_morpion = re.compile(r'joue au morpion', re.IGNORECASE)
        self.re_place_morpion = re.compile(r'place (x|o) en (\d),(\d)', re.IGNORECASE) # Ex: place x en 1,2
        self.re_jeu_devine_nombre = re.compile(r'jeu devine le nombre', re.IGNORECASE)
        self.re_dessine = re.compile(r'dessine un (.+)', re.IGNORECASE)
        self.re_calendrier = re.compile(r'calendrier\s*([\w]+)?\s*(\d{4})?', re.IGNORECASE) # ex: calendrier decembre 2025
        self.re_mots_cles = re.compile(r'mots cles de "(.+)"', re.IGNORECASE)
        self.re_inverse_texte = re.compile(r'inverse "(.+)"', re.IGNORECASE)
        self.re_compte_texte = re.compile(r'compte "(\w)" dans "(.+)"', re.IGNORECASE)
        self.re_convertir_maj = re.compile(r'convertir en majuscule "(.+)"', re.IGNORECASE)


        # Opérations mathématiques pré-compilées
        self.math_ops = {
            re.compile(r'(\d+)\s*\+\s*(\d+)', re.IGNORECASE): lambda a, b: a + b,
            re.compile(r'(\d+)\s*-\s*(\d+)', re.IGNORECASE): lambda a, b: a - b,
            re.compile(r'(\d+)\s*\*\s*(\d+)', re.IGNORECASE): lambda a, b: a * b,
            re.compile(r'(\d+)\s*/\s*(\d+)', re.IGNORECASE): lambda a, b: a / b if b != 0 else "Division par zéro !",
            re.compile(r'(\d+)\s*\^\s*(\d+)', re.IGNORECASE): lambda a, b: a ** b,
            re.compile(r'racine de (\d+)', re.IGNORECASE): lambda a: math.sqrt(a),
            re.compile(r'sin\((\d+)\)', re.IGNORECASE): lambda a: math.sin(math.radians(a)),
            re.compile(r'cos\((\d+)\)', re.IGNORECASE): lambda a: math.cos(math.radians(a)),
            re.compile(r'tan\((\d+)\)', re.IGNORECASE): lambda a: math.tan(math.radians(a)),
            re.compile(r'log\((\d+)\)', re.IGNORECASE): lambda a: math.log10(a),
            re.compile(r'ln\((\d+)\)', re.IGNORECASE): lambda a: math.log(a),
            re.compile(r'exp\((\d+)\)', re.IGNORECASE): lambda a: math.exp(a),
            re.compile(r'factorielle de (\d+)', re.IGNORECASE): lambda a: math.factorial(a),
            re.compile(r'pi', re.IGNORECASE): lambda: math.pi
        }
        
        # --- Fin des Regex ---

        # Base de connaissances étendue avec plus de mots-clés pour la culture
        self.knowledge = {
            "greetings": ["salut", "bonjour", "hello", "hey", "coucou", "hi", "bonsoir", "yo", "allô", "salutations", "bienvenue", "bon matin", "yo yo", "hé", "coucou toi", "bonjorno", "hola", "bon dia"],
            "farewell": ["au revoir", "bye", "à plus", "ciao", "adieu", "à demain", "tchao", "bonne nuit", "à la prochaine", "porte-toi bien", "take care", "see you", "à tout à l'heure", "bisous", "adios", "goodbye", "see ya"],
            "thanks": ["merci", "thanks", "thx", "thank you", "merci beaucoup", "je te remercie", "grand merci", "reconnaissant", "apprécié", "gracias", "danke", "arigato", "grazie", "obrigado"],
            "identity": ["qui es-tu", "ton nom", "tu es qui", "présente-toi", "quel est ton nom", "qui t'a créé", "version", "créateur", "origine", "développeur", "âge", "fonction", "qui es tu", "quel est ton créateur"],
            "weather": ["météo", "temps", "weather", "pluie", "soleil", "neige", "vent", "température", "prévisions", "climat", "humidité", "orages", "météorologie", "ciel", "quel temps fait-il", "météo aujourd'hui"],
            "help_request": ["aide", "help", "comment", "explique", "tutoriel", "guide", "instructions", "manuel", "faq", "support", "assistance", "comment ça marche"],
            "joke": ["blague", "joke", "rigole", "drôle", "humour", "rigolade", "anecdote drôle", "plaisanterie", "farce", "comique", "hilarant", "marrant", "raconte une blague", "fais-moi rire"],
            "motivation": ["motivation", "encourage", "courage", "force", "inspire-moi", "boost", "pep talk", "motiver", "enthousiasme", "positif", "optimisme", "encouragement", "motive-moi"],
            "science": ["science", "physique", "chimie", "biologie", "astronomie", "étoiles", "planètes", "univers", "atome", "molécule", "évolution", "théorie", "expérience", "scientifique", "découverte scientifique", "quantique", "relativité", "génétique", "écologie", "neurologie", "mathématiques", "algèbre", "géométrie", "calcul", "physique quantique", "chimie organique", "biologie cellulaire", "cosmologie", "botanique", "zoologie", "anatomie", "physiologie", "microbiologie", "géologie", "océanographie", "météorologie", "astrophysique", "biochimie", "paléontologie", "thermodynamique", "optique", "électromagnétisme", "biotechnologie", "nanotechnologie", "épidémiologie"],
            "horror": ["histoire d'horreur", "raconte horreur", "horreur", "histoire effrayante", "conte horreur", "orrere", "horreure"],
            "history": ["histoire", "passé", "événement historique", "guerre", "invention", "personnage historique", "époque", "siècle", "antiquité", "moyen âge", "renaissance", "moderne", "historique", "fait historique", "révolution", "empire", "royauté", "colonies", "indépendance", "guerre mondiale", "holocauste", "renaissance italienne", "illumination", "réforme", "industrialisation", "guerre froide", "décolonisation", "histoire antique", "histoire médiévale", "histoire contemporaine", "archéologie", "dynasties", "conquêtes", "traités", "batailles célèbres", "leaders historiques", "civilisations anciennes", "explorations", "révolutions industrielles", "mouvements sociaux", "histoire de l'art", "histoire économique", "histoire politique"],
            "sports": ["sport", "football", "basket", "tennis", "olympiques", "course", "natation", "gym", "athlétisme", "cyclisme", "ski", "boxe", "rugby", "sportif", "compétition sportive", "golf", "volleyball", "handball", "escrime", "judo", "karaté", "surf", "escalade", "équitation", "patinage", "cricket", "baseball", "hockey", "formule 1", "arts martiaux", "gymnastique", "tir à l'arc"],
            "food": ["nourriture", "recette", "cuisine", "plat", "ingrédients", "manger", "diète", "repas", "dessert", "apéritif", "végétarien", "vegan", "cuisiner", "recette facile", "cuisine française", "cuisine italienne", "cuisine asiatique", "gastronomie", "épices", "pâtisserie", "barbecue", "salades", "soupes", "boissons", "cuisine mexicaine", "cuisine indienne", "fusion food", "street food", "diététique", "allergies alimentaires", "nutrition sportive"],
            "health": ["santé", "bien-être", "exercice", "régime", "médecine", "sommeil", "fitness", "hygiène", "nutrition", "mental", "prévention", "thérapie", "sain", "conseil santé", "vaccins", "maladies", "symptômes", "remèdes naturels", "yoga", "méditation", "stress", "anxiété", "dépression", "immunité", "santé cardiovasculaire", "santé respiratoire", "santé digestive", "ergonomie", "santé sexuelle", "vieillissement", "pédiatrie", "gériatrie"],
            "technology": ["technologie", "ordinateur", "internet", "smartphone", "IA", "robot", "gadget", "innovation", "logiciel", "hardware", "cybersécurité", "cloud", "tech", "informatique", "blockchain", "big data", "IA avancée", "réalité virtuelle", "augmentée", "drones", "impression 3D", "nanotechnologie", "quantique computing", "5G", "IoT", "cryptographie", "devops", "agile", "metaverse", "web3"],
            "music": ["musique", "chanson", "artiste", "genre musical", "concert", "instrument", "album", "playlist", "rythme", "mélodie", "opéra", "festival", "musical", "compositeur", "rock", "jazz", "classique", "pop", "hip-hop", "électro", "folk", "blues", "reggae", "symphonie", "rap", "country", "metal", "indie", "world music", "musique baroque", "romantique", "contemporaine"],
            "movies": ["film", "cinéma", "série", "acteur", "réalisateur", "netflix", "drame", "comédie", "action", "horreur", "science-fiction", "documentaire", "movie", "cinématographique", "oscar", "festival de cannes", "blockbuster", "animation", "thriller", "biopic", "western", "fantastique", "romance", "film noir", "musical", "expérimental", "indépendant", "bollywood", "hollywood"],
            "literature": ["littérature", "livre", "auteur", "roman", "poésie", "écrivain", "classique", "bestseller", "essai", "biographie", "fantasy", "thriller", "littéraire", "lecture", "littérature française", "shakespeare", "poètes", "nouvelles", "théâtre", "bande dessinée", "mangas", "science-fiction littéraire", "littérature anglaise", "russe", "latino-américaine", "africaine", "littérature féministe", "post-moderne"],
            "geography": ["géographie", "pays", "ville", "continent", "océan", "montagne", "rivière", "capitale", "désert", "île", "frontière", "carte", "géographique", "lieu", "topographie", "climat zones", "biomes", "volcans", "séismes", "fleuves", "lacs", "forêts", "pôles", "géopolitique", "cartographie", "démographie", "urbanisme", "géographie humaine", "physique"],
            "environment": ["environnement", "écologie", "climat", "recyclage", "pollution", "nature", "durabilité", "biodiversité", "énergie verte", "conservation", "réchauffement", "écologique", "planète", "déforestation", "océans plastiques", "espèces menacées", "énergies renouvelables", "empreinte carbone", "agriculture bio", "éco-systèmes", "changement climatique", "accords environnementaux", "activisme écolo"],
            "animals": ["animaux", "animal", "chien", "chat", "oiseau", "poisson", "mammifère", "reptile", "insecte", "faune", "espèce", "habitat", "faunique", "bestiaire", "migration", "hibernation", "prédation", "écosystèmes animaux", "animaux domestiques", "sauvages", "extinction", "évolution animale", "comportement animal", "animaux marins", "terrestres", "volants"],
            "plants": ["plantes", "fleur", "arbre", "jardin", "botanique", "herbe", "forêt", "flore", "cactus", "orchidée", "photosynthèse", "semence", "végétal", "botanique", "arbres fruitiers", "plantes médicinales", "invasives", "pollinisation", "croissance végétale", "plantes carnivores", "algues", "champignons", "évolution végétale"],
            "famous_people": ["personnes célèbres", "célébrité", "inventeur", "scientifique", "artiste", "politique", "leader", "héros", "icône", "génie", "personnalité célèbre", "figure historique", "explorateurs", "philanthropes", "activistes", "musiciens célèbres", "écrivains", "philosophes", "sportifs légendaires", "entrepreneurs"],
            "art": ["art", "peinture", "sculpture", "dessin", "musée", "artiste", "style artistique", "impressionnisme", "renaissance", "abstrait", "street art", "artistique", "œuvre d'art", "cubisme", "surréalisme", "pop art", "art numérique", "photographie", "architecture", "art contemporain", "art ancien", "art africain", "asiatique", "performance art"],
            "languages": ["langues", "langage", "français", "anglais", "espagnol", "apprendre langue", "vocabulaire", "grammaire", "traduction", "dialecte", "linguistique", "parler langue", "chinois", "allemand", "arabe", "russe", "portugais", "italien", "japonais", "hindou", "coréen", "turc", "swahili", "langues mortes", "évolution linguistique"],
            "travel": ["voyage", "destination", "vacances", "avion", "train", "hôtel", "tourisme", "aventure", "itinéraire", "passeport", "voyager", "exploration", "voyages culturels", "écotourisme", "voyages en solo", "croisières", "randonnées", "voyages d'affaires", "backpacking", "voyages luxe"],
            "education": ["éducation", "école", "université", "apprentissage", "études", "professeur", "connaissances", "diplôme", "cours", "éducatif", "apprendre", "e-learning", "pédagogie", "systèmes éducatifs", "apprentissage tout au long de la vie", "éducation inclusive", "technologies éducatives", "éducation environnementale"],
            "economy": ["économie", "argent", "marché", "bourse", "investissement", "business", "entreprise", "inflation", "PIB", "économique", "finances", "crypto-monnaies", "commerce international", "économie verte", "récession", "croissance économique", "économie circulaire", "microéconomie", "macroéconomie", "économie comportementale"],
            "philosophy": ["philosophie", "philosophe", "pensée", "éthique", "morale", "existence", "Socrate", "Platon", "philosophique", "idées philosophiques", "existentialisme", "stoïcisme", "nihilisme", "philosophie orientale", "métaphysique", "épistémologie", "philosophie politique", "philosophie de l'esprit", "philosophie analytique"],
            "psychology": ["psychologie", "psychologue", "mental", "comportement", "émotions", "Freud", "stress", "motivation", "psychologique", "esprit", "cognitif", "thérapies", "personnalité", "troubles mentaux", "psychologie positive", "psychologie sociale", "développementale", "neuropsychologie", "psychanalyse"],
            "mythology": ["mythologie", "mythe", "dieu", "légende", "grecque", "romaine", "Zeus", "Hercule", "mythologique", "divinités", "nordique", "égyptienne", "hindoue", "celtique", "mythes modernes", "aztèque", "maya", "japonaise", "africaine"],
            "inventions": ["invention", "inventeur", "découverte", "brevet", "technologie", "Edison", "Tesla", "téléphone", "invente", "création technologique", "inventions médiévales", "inventions modernes", "révolution industrielle", "inventions médicales", "inventions militaires", "inventions spatiales"],
            "creator_quotes": ["citation du createur", "quote creator", "citation createur", "quote du créateur de freev", "citation créateur"],
            "riddles": ["devinette", "énigme", "riddle", "puzzle", "raconte une devinette"],
            "proverbs": ["proverbe", "dicton", "proverb", "saying", "raconte un proverbe"],
            "morse": ["morse", "code morse", "encode morse", "decode morse"],
            "binary": ["binaire", "binary", "encode binary", "decode binary"],
            "caesar": ["caesar", "chiffre césar", "cesar", "encode caesar", "decode caesar"],
            "programming": ["code", "programme", "python", "donne moi du code", "exemple code", "script", "fonction", "débutant", "coder", "programmation", "hello world", "boucle", "condition", "liste", "fonction python", "avancé", "pro", "classe", "décorateur", "générateur", "multithreading", "api rest", "base de données", "web scraping", "machine learning", "algorithme"]
        }
        
        # Réponses élargies avec plus de contenu culturel et réponses améliorées
        self.responses = {
            "greetings": [
                "Salut ! Ravi de vous voir ! 👋",
                "Bonjour ! Comment puis-je vous aider aujourd'hui ?",
                "Hey ! Prêt à discuter ? 😊",
                "Bonsoir ! Qu'est-ce qui vous amène ? 🌙",
                "Allô ! Je suis à votre écoute ! 📞",
                "Salutations ! Content de vous retrouver !",
                "Bienvenue ! Que puis-je faire pour vous ?",
                "Bon matin ! Prêt pour une nouvelle journée ? ☕",
                "Hé ! Quoi de neuf ?",
                "Coucou toi ! Ravi de te voir !"
            ],
            "farewell": [
                "Au revoir ! Prenez soin de vous ! 💙",
                "À bientôt ! Passez une excellente journée ! ✨",
                "Bye ! Au plaisir de vous revoir !",
                "Bonne nuit ! Faites de beaux rêves ! 🌟",
                "À demain ! Reposez-vous bien !",
                "Portez-vous bien ! À la prochaine !",
                "Au revoir, et bonne continuation !",
                "See you soon ! Prenez soin !",
                "À tout à l'heure !",
                "Bisous ! À plus !"
            ],
            "thanks": [
                "De rien ! Toujours là pour vous ! 😊",
                "Avec plaisir ! C'est pour ça que je suis là ! ✨",
                "Pas de souci ! N'hésitez pas si besoin !",
                "Merci à vous d'utiliser Freev ! 👍",
                "Je suis content d'avoir pu aider !",
                "Grand merci pour votre reconnaissance !",
                "C'est un plaisir de vous assister !",
                "Apprécié ! Continuez comme ça !",
                "Merci beaucoup à toi !",
                "Pas de quoi, ami !"
            ],
            "identity": [
                "Je suis Freev, votre assistant IA local et intelligent ! 🤖",
                "Freev à votre service ! Je peux vous aider avec plein de choses ! ✨",
                "Je m'appelle Freev, une IA créée pour converser et assister sans API externe.",
                "Je suis Freev, un programme Python intelligent pour terminal !",
                "Ma version est 2.1, créé par un développeur passionné.",
                "Je suis une IA locale, sans connexion internet requise !",
                "Origine : Développé en Python pour une utilisation terminal.",
                "Je suis conçu pour être utile et amusant sans dépendances externes !",
                "Je n'ai pas d'âge, je suis éternel en code !",
                "Ma fonction principale : vous assister localement."
            ],
            "weather": [
                "Sans API, je ne peux pas donner la météo en temps réel. Regardez par la fenêtre ! ☁️",
                "Pour la météo, je suggère d'utiliser une app dédiée, car je suis local.",
                "En général, en automne, il pleut souvent en France. 🌧️",
                "Le climat change, protégeons la planète ! 🌍",
                "Conseil : Préparez un parapluie si vous voyez des nuages ! ☂️",
                "En hiver, pensez à vous couvrir contre le froid ! ❄️",
                "L'humidité peut affecter l'humeur, restez au sec !",
                "Les orages sont spectaculaires mais dangereux."
            ],
            "joke": [
                "Pourquoi les plongeurs plongent-ils toujours en arrière ? Parce que sinon ils tombent dans le bateau ! 😄",
                "Qu'est-ce qu'un crocodile qui surveille la pharmacie ? Un Lacoste garde ! 🐊",
                "Comment appelle-t-on un chat tombé dans un pot de peinture ? Un chat-peint ! 🎨",
                "Pourquoi les poissons n'aiment pas jouer au tennis ? Parce qu'ils ont peur du filet ! 🐟",
                "Pourquoi l'ordinateur va-t-il chez le médecin ? Parce qu'il a un virus ! 💻",
                "Qu'est-ce qu'un vampire qui fait de la gym ? Un Nosferathlète ! 🧛",
                "Pourquoi les tomates rougissent-elles ? Parce qu'elles voient la salade se déshabiller ! 🍅",
                "Comment appelle-t-on un chien qui fait de la magie ? Un labracadabrador ! 🐶",
                "Pourquoi les oiseaux ne portent-ils pas de lunettes ? Parce que les verres de contact ! 🦅",
                "Qu'est-ce qu'un citron déprimé ? Un citron pressé ! 🍋",
                "Pourquoi le livre de maths est-il triste ? Parce qu'il a trop de problèmes ! 📖",
                "Qu'est-ce qu'un ordinateur qui chante ? Un Dell ! 🎤",
                "Pourquoi les fantômes sont-ils mauvais menteurs ? Parce qu'on voit à travers ! 👻",
                "Comment appelle-t-on un boomerang qui ne revient pas ? Un bâton ! 🪃",
                "Pourquoi les squelettes ne se battent-ils jamais ? Parce qu'ils n'ont pas de tripes ! 💀",
                "Qu'est-ce qu'un canard qui dit des blagues ? Un coin-coinédien ! 🦆",
                "Pourquoi les mathématiciens ont-ils peur du noir ? Parce qu'ils craignent les nombres imaginaires ! 🌑"
            ],
            "motivation": [
                "Vous êtes capable de grandes choses ! Continuez, je crois en vous ! 💪✨",
                "Chaque petit pas compte. Vous progressez, même si ça ne se voit pas toujours ! 🌟",
                "Les difficultés sont là pour être surmontées. Vous allez y arriver ! 🚀",
                "N'abandonnez pas, votre effort paiera ! 🔥",
                "Soyez fier de vous, vous avez déjà accompli tant ! 🏆",
                "Le succès vient à ceux qui persévèrent ! 🌈",
                "Vous avez le pouvoir de changer les choses ! 💥",
                "Restez positif, de belles choses arrivent ! 😊",
                "Votre potentiel est illimité ! 🌌",
                "Chaque jour est une nouvelle opportunité ! 🌅",
                "Croyez en vos rêves et poursuivez-les ! 💭"
            ],
            "science": [
                "La science est fascinante ! Saviez-vous que la lumière du soleil met 8 minutes pour atteindre la Terre ? ☀️",
                "En physique, E=mc² est la formule célèbre d'Einstein pour l'équivalence masse-énergie.",
                "La biologie nous apprend que l'ADN est le code de la vie ! 🧬",
                "L'astronomie révèle que notre galaxie contient des milliards d'étoiles ! 🌌",
                "La chimie explique comment les atomes se lient pour former des molécules.",
                "Les quarks sont les particules fondamentales de la matière ! ⚛️",
                "L'évolution de Darwin explique la diversité des espèces.",
                "La gravité maintient les planètes en orbite ! 🪐",
                "Les théories quantiques défient notre intuition.",
                "Les expériences scientifiques avancent la connaissance.",
                "En génétique, l'ADN double hélice a été découverte par Watson et Crick en 1953.",
                "La relativité générale prédit les trous noirs.",
                "La chimie organique étudie les composés du carbone, base de la vie.",
                "La neurologie explore le cerveau et ses mystères.",
                "Les mathématiques sont le langage de l'univers, comme le disait Galilée.",
                "La géométrie euclidienne est la base de l'architecture moderne.",
                "Le calcul infinitésimal, inventé par Newton et Leibniz, révolutionne la physique.",
                "L'écologie met en lumière les interactions entre organismes et environnement.",
                "La cosmologie étudie l'origine et l'évolution de l'univers.",
                "La zoologie classe et étudie les animaux, de l'abeille au baleine.",
                "L'anatomie humaine révèle que nous avons 206 os dans le corps adulte.",
                "La physiologie explique comment le cœur pompe le sang à travers le corps.",
                "La microbiologie étudie les bactéries, virus et autres micro-organismes.",
                "La géologie explore les roches, minéraux et l'histoire de la Terre.",
                "L'océanographie examine les océans, couvrant 71% de la planète.",
                "L'astrophysique combine physique et astronomie pour étudier les étoiles.",
                "La biochimie lie biologie et chimie pour comprendre les processus vitaux.",
                "La paléontologie fouille les fossiles pour reconstruire l'histoire de la vie.",
                "La thermodynamique étudie l'énergie et ses transformations.",
                "L'optique traite de la lumière et de ses propriétés.",
                "L'électromagnétisme unit électricité et magnétisme.",
                "La biotechnologie applique la science à la création de produits utiles.",
                "L'épidémiologie suit la propagation des maladies dans les populations."
            ],
            "horror": [
                "Jeffrey Dahmer – Le Monstre de Milwaukee\n\nMilwaukee, années 80. Jeffrey Dahmer vit seul dans un petit appartement gris. Il attire des jeunes hommes chez lui en promettant de les payer pour quelques photos. Une fois à l’intérieur, tout bascule. La police finit par découvrir ce qu’il cachait derrière sa porte : un appartement transformé en scène de cauchemar.\nSon arrestation choque le monde entier. Pendant son procès, il explique ses pulsions d’une voix calme, presque détachée. En 1992, il est condamné à 15 perpétuités. Deux ans plus tard, un codétenu le bat à mort dans une salle de sport de la prison.",
                "Ted Bundy – Le Charme du Mal\n\nÉtudiant brillant, séduisant, Ted Bundy semblait parfait. Il utilisait son charme pour gagner la confiance de jeunes femmes, souvent en feignant une blessure ou un besoin d’aide. Personne ne pouvait imaginer ce qui se cachait derrière son sourire.\nPendant des années, il sème la panique dans plusieurs États américains. Il s’évade deux fois, change d’identité, reprend ses crimes. Quand il est finalement repris, il garde un air froid, presque supérieur. En 1989, après un procès très médiatisé, Bundy est exécuté sur la chaise électrique. Juste avant sa mort, il avoue plusieurs dizaines de meurtres.",
                "Richard Ramirez – Le Traqueur de la Nuit\n\n1984, Los Angeles. La ville étouffe sous la chaleur et la peur. Chaque nuit, un homme entre par effraction, attaque, tue, disparaît. La presse le surnomme Night Stalker. Richard Ramirez, un jeune homme fasciné par le satanisme, agit sans pitié.\nSon visage devient connu après qu’une victime ait survécu et décrit son regard vide. En 1985, des habitants le reconnaissent dans la rue et le rattrapent. Jugé, il garde son air provocateur, gravant des symboles sataniques sur sa main. Il est condamné à mort, mais meurt d’un cancer en 2013, sans jamais avoir exprimé de remords.",
                "Ed Gein – L’Horreur de Plainfield\n\nAnnées 50, dans un village tranquille du Wisconsin. Ed Gein, un fermier solitaire, vit dans une vieille maison après la mort de sa mère, qu’il vénérait. Un jour, une femme du coin disparaît. La police fouille chez lui… et découvre une scène impensable : objets et vêtements faits à partir de restes humains.\nEd avoue avoir déterré des corps et en avoir \"réutilisé\" des morceaux. Il devient l’inspiration directe de films comme Psychose ou Massacre à la tronçonneuse. Jugé fou, il est interné dans un hôpital psychiatrique où il restera jusqu’à sa mort en 1984.",
                "Aileen Wuornos – La Proie devenue Prédateur\n\nAnnées 90, en Floride. Aileen Wuornos vit de petits vols et de prostitution sur les routes. Après une vie de souffrance, elle finit par tuer plusieurs hommes qu’elle dit avoir pris peur en croyant qu’ils allaient la violer.\nSon histoire fascine et divise : monstre ou victime du système ? Son attitude agressive pendant le procès ne joue pas en sa faveur. En 2002, elle est exécutée par injection létale. Son histoire inspirera le film Monster, avec Charlize Theron.",
                "Andrei Chikatilo – Le Boucher de Rostov\n\nURSS, années 70–80. Un professeur timide en apparence cache un secret terrifiant. Il attire des enfants et des jeunes gens dans les forêts, où il commet ses crimes dans une atmosphère de totale impunité — la police soviétique mettra plus de dix ans à comprendre qu’un seul homme est derrière tout ça.\nQuand il est arrêté, il avoue tout d’une voix froide et détachée, comme s’il racontait autre chose que sa propre vie. En 1994, il est exécuté d’une balle dans la tête. Son nom restera comme l’un des pires tueurs de l’histoire russe."
            ],
            "history": [
                "L'histoire est riche ! La Révolution Française a eu lieu en 1789.",
                "L'invention de l'imprimerie par Gutenberg a changé le monde au XVe siècle.",
                "Napoléon Bonaparte était un grand conquérant français ! 🇫🇷",
                "La Seconde Guerre Mondiale s'est terminée en 1945.",
                "L'Égypte ancienne a construit les pyramides il y a plus de 4000 ans ! 🏺",
                "La Renaissance a vu naître des génies comme Léonard de Vinci.",
                "La chute du mur de Berlin en 1989 a marqué la fin de la Guerre Froide.",
                "Christophe Colomb a découvert l'Amérique en 1492.",
                "L'antiquité grecque a fondé la démocratie.",
                "Le Moyen Âge était une ère de châteaux et chevaliers.",
                "La Révolution Américaine de 1776 a inspiré les indépendances mondiales.",
                "L'Empire Romain a duré plus de 500 ans et influencé le droit moderne.",
                "La Réforme Protestante de Luther en 1517 a divisé l'Europe chrétienne.",
                "L'Illumination du XVIIIe siècle a promu la raison et les droits humains.",
                "La Guerre Civile Américaine (1861-1865) a aboli l'esclavage.",
                "La décolonisation de l'Afrique dans les années 1960 a redessiné le monde.",
                "L'industrialisation britannique au XIXe siècle a lancé la révolution industrielle.",
                "L'Holocauste pendant la WWII a été un génocide de 6 millions de Juifs.",
                "La Renaissance Italienne a produit Michel-Ange et Raphaël.",
                "La Guerre Froide opposa USA et URSS de 1947 à 1991 sans conflit direct.",
                "L'archéologie a révélé les secrets des Mayas et des Incas en Amérique latine.",
                "Les dynasties chinoises, comme les Ming, ont construit la Grande Muraille.",
                "Les conquêtes d'Alexandre le Grand ont répandu la culture hellénistique.",
                "Le traité de Versailles en 1919 a mis fin à la Première Guerre Mondiale.",
                "Les batailles célèbres incluent Waterloo, où Napoléon fut vaincu en 1815.",
                "Les civilisations anciennes comme Sumer ont inventé l'écriture cunéiforme.",
                "Les mouvements sociaux comme le suffragisme ont gagné le droit de vote aux femmes.",
                "L'histoire économique trace l'évolution du capitalisme et du socialisme."
            ],
            "sports": [
                "Le sport est bon pour la santé ! Le football est le sport le plus populaire au monde ⚽.",
                "Les Jeux Olympiques se déroulent tous les 4 ans.",
                "Le tennis requiert agilité et précision 🎾.",
                "La natation est excellente pour le corps entier 🏊.",
                "Le basketball a été inventé en 1891 par James Naismith 🏀.",
                "La course à pied améliore l'endurance ! 🏃‍♂️",
                "Le cyclisme est idéal pour explorer la nature 🚴.",
                "Le ski est excitant en hiver ! ⛷️",
                "La boxe développe la force et la stratégie.",
                "Le rugby est un sport d'équipe intense.",
                "Le golf demande concentration et précision.",
                "Le volleyball est populaire sur les plages.",
                "Le handball combine vitesse et adresse.",
                "L'escrime est un art de combat élégant.",
                "Le judo enseigne le respect et la discipline.",
                "Le cricket est adoré en Inde et en Angleterre.",
                "Le baseball est l sport national américain.",
                "Le hockey sur glace est rapide et physique.",
                "La Formule 1 teste la vitesse et la technologie.",
                "Les arts martiaux comme le karaté buildent la confiance."
            ],
            "food": [
                "La cuisine française est renommée ! Essayez les croissants 🥐.",
                "Une recette simple : salade avec tomates, laitue et vinaigrette.",
                "Les fruits sont essentiels pour une bonne alimentation 🍎.",
                "Le chocolat vient du cacao, originaire d'Amérique du Sud 🍫.",
                "Le fromage est une spécialité française avec plus de 1000 variétés ! 🧀",
                "Buvez du thé pour ses bienfaits antioxydants 🍵.",
                "Les pâtes sont un plat italien classique 🍝.",
                "Essayez un smoothie pour un boost d'énergie ! 🥤",
                "Les desserts comme la crème brûlée sont délicieux.",
                "Les apéritifs stimulent l'appétit.",
                "La cuisine asiatique utilise souvent du riz et des épices variées.",
                "La gastronomie mexicaine inclut tacos et guacamole.",
                "Les pâtisseries viennoises sont célèbres pour leurs gâteaux.",
                "Le barbecue est idéal pour les viandes grillées en été.",
                "La cuisine indienne est riche en currys et naans.",
                "La fusion food combine traditions culinaires mondiales.",
                "Les allergies alimentaires nécessitent une attention spéciale."
            ],
            "health": [
                "Prenez soin de votre santé ! Dormez au moins 7 heures par nuit 😴.",
                "L'exercice régulier réduit le stress 🏃.",
                "Buvez beaucoup d'eau pour rester hydraté 💧.",
                "Une alimentation équilibrée est clé pour le bien-être.",
                "La méditation aide à calmer l'esprit 🧘.",
                "Évitez le tabac pour une vie plus longue 🚭.",
                "Le yoga améliore la flexibilité et la paix intérieure.",
                "Consultez un médecin pour des conseils personnalisés.",
                "La nutrition joue un rôle majeur dans la santé.",
                "La santé mentale est aussi importante que physique.",
                "Les vaccins protègent contre de nombreuses maladies.",
                "Les remèdes naturels comme le miel aident contre les rhumes.",
                "Gérez le stress avec des techniques de respiration.",
                "L'immunité se renforce avec une alimentation riche en vitamines.",
                "La santé cardiovasculaire bénéficie de l'exercice aérobique.",
                "La santé respiratoire est améliorée par l'air frais.",
                "L'ergonomie prévient les blessures au travail.",
                "La santé sexuelle éducée est cruciale pour le bien-être."
            ],
            "technology": [
                "La technologie évolue vite ! L'IA comme moi aide dans la vie quotidienne 🤖.",
                "Internet connecte le monde entier 🌐.",
                "Les smartphones ont révolutionné la communication 📱.",
                "Les robots assistent dans les usines et les maisons.",
                "La réalité virtuelle change le divertissement 🎮.",
                "Les drones sont utilisés pour la livraison et la photographie 📸.",
                "La blockchain sécurise les transactions numériques.",
                "Les ordinateurs quantiques promettent des avancées énormes !",
                "La cybersécurité protège contre les menaces.",
                "Le cloud stocke les données en ligne.",
                "La big data analyse de vastes ensembles de données.",
                "La réalité augmentée superpose des infos virtuelles au réel.",
                "L'impression 3D crée des objets couche par couche.",
                "La nanotechnologie manipule la matière à l'échelle atomique.",
                "La 5G offre des vitesses internet ultra-rapides.",
                "L'IoT connecte les objets quotidiens.",
                "Le metaverse crée des mondes virtuels immersifs.",
                "Web3 décentralise le web avec blockchain."
            ],
            "music": [
                "La musique adoucit les mœurs ! Beethoven était un compositeur génial 🎼.",
                "Le rock, le jazz, le classique : tant de genres ! 🎸",
                "Écoutez de la musique pour vous détendre 🎧.",
                "Les concerts live sont une expérience unique 🎤.",
                "Mozart a composé plus de 600 œuvres ! 🎹",
                "Le hip-hop est né dans les années 1970 à New York.",
                "La guitare est un instrument polyvalent.",
                "Créez votre playlist pour booster votre humeur !",
                "L'opéra combine musique et théâtre.",
                "Les festivals musicaux réunissent les fans.",
                "Le reggae jamaïcain est associé à Bob Marley.",
                "Le blues influence le rock et le jazz.",
                "Les symphonies de Haydn sont classiques.",
                "Le rap exprime des réalités sociales.",
                "La musique country raconte des histoires de vie.",
                "Le metal est connu pour son énergie intense."
            ],
            "movies": [
                "Les films nous transportent ! 'Le Parrain' est un classique 🎥.",
                "Les séries comme 'Game of Thrones' captivent des millions.",
                "Les acteurs comme Meryl Streep sont légendaires 🌟.",
                "Le cinéma français a produit des chefs-d'œuvre comme 'Amélie'.",
                "Les films d'animation comme 'Toy Story' plaisent à tous les âges.",
                "Alfred Hitchcock est le maître du suspense !",
                "Les blockbusters comme 'Avengers' sont spectaculaires.",
                "Regardez un documentaire pour apprendre en s'amusant.",
                "La science-fiction explore l'avenir.",
                "Les films d'horreur font monter l'adrénaline.",
                "Les Oscars récompensent les meilleurs films annuellement.",
                "Le festival de Cannes est prestigieux pour le cinéma indépendant.",
                "Les westerns classiques incluent ceux de John Wayne.",
                "Les films noirs explorent le crime et la morale.",
                "Les musicals comme 'La La Land' allient danse et chanson."
            ],
            "literature": [
                "La littérature enrichit l'esprit ! 'Les Misérables' de Victor Hugo est un chef-d'œuvre.",
                "Shakespeare a écrit 'Roméo et Juliette'.",
                "La poésie de Baudelaire est profonde et mélancolique.",
                "J.K. Rowling a créé l'univers de Harry Potter 🧙.",
                "Les classiques comme '1984' d'Orwell avertissent sur la société.",
                "Tolstoï a écrit 'Guerre et Paix', un roman épique.",
                "Lire un livre par semaine élargit les horizons !",
                "Les biographies inspirent avec des vies réelles.",
                "La fantasy transporte dans des mondes imaginaires.",
                "Les thrillers gardent en haleine.",
                "La littérature française inclut Proust et Camus.",
                "Les poètes romantiques comme Keats expriment les emotions.",
                "Les mangas japonais sont une forme de littérature graphique.",
                "La littérature russe avec Dostoïevski explore l'âme humaine.",
                "La littérature latino-américaine inclut le réalisme magique de García Márquez."
            ],
            "geography": [
                "La géographie est passionnante ! Paris est la capitale de la France 🇫🇷.",
                "L'Everest est la plus haute montagne du monde 🏔️.",
                "L'Amazonie est la plus grande forêt tropicale 🌳.",
                "Les océans couvrent 71% de la Terre 🌊.",
                "L'Australie est un continent et un pays.",
                "Le Nil est le plus long fleuve du monde.",
                "L'Afrique a 54 pays.",
                "Les pôles sont les endroits les plus froids ! ❄️",
                "Les frontières définissent les nations.",
                "Les cartes aident à naviguer.",
                "Les volcans comme le Vésuve ont shaped l'histoire.",
                "Les biomes incluent toundra, désert et forêt tropicale.",
                "Les séismes se produisent le long des plaques tectoniques.",
                "La géopolitique étudie les relations entre pays.",
                "La démographie analyse les populations mondiales."
            ],
            "environment": [
                "Protégeons l'environnement ! Le recyclage réduit les déchets ♻️.",
                "Le changement climatique est un défi majeur 🌡️.",
                "Plantez des arbres pour absorber le CO2 🌱.",
                "La biodiversité est essentielle à la vie.",
                "Économisez l'énergie pour un avenir durable 💡.",
                "Les océans sont pollués par le plastique 🐢.",
                "Utilisez des transports verts comme le vélo 🚲.",
                "La déforestation menace les écosystèmes.",
                "Les énergies renouvelables comme le solaire sont l'avenir ☀️.",
                "La conservation préserve les espèces en danger.",
                "L'empreinte carbone mesure l'impact environnemental.",
                "L'agriculture bio réduit les pesticides.",
                "Les accords comme Paris luttent contre le réchauffement.",
                "L'activisme écolo inspire le changement."
            ],
            "animals": [
                "Les animaux sont fascinants ! Les éléphants ont une excellente mémoire 🐘.",
                "Les chats dorment 16 heures par jour 😺.",
                "Les oiseaux migrent sur des milliers de km 🦅.",
                "Les requins existent depuis 400 millions d'années 🦈.",
                "Les pandas mangent principalement du bambou 🐼.",
                "Les loups vivent en meutes organisées 🐺.",
                "Les abeilles pollinisent les fleurs 🐝.",
                "Les tortues peuvent vivre plus de 100 ans 🐢.",
                "Les insectes sont les plus nombreux sur Terre.",
                "La faune varie selon les habitats.",
                "Les migrations des gnous en Afrique sont spectaculaires.",
                "Les animaux en extinction incluent les tigres et les rhinocéros.",
                "L'évolution animale adapte les espèces à leur environnement."
            ],
            "plants": [
                "Les plantes purifient l'air ! Les roses symbolisent l'amour 🌹.",
                "Les arbres produisent de l'oxygène 🌳.",
                "Le jardinage est thérapeutique 🌻.",
                "Les cactus stockent l'eau dans le désert 🌵.",
                "Les orchidées sont parmi les fleurs les plus variées.",
                "Les algues sont à la base de la chaîne alimentaire marine.",
                "Les plantes carnivores attrapent des insectes !",
                "Les séquoias sont les arbres les plus grands.",
                "La photosynthèse convertit la lumière en énergie.",
                "Les semences germent en nouvelles plantes.",
                "Les plantes médicinales comme l'aloe vera soignent les brûlures.",
                "La pollinisation par les abeilles est cruciale pour l'agriculture.",
                "Les champignons forment des réseaux souterrains avec les racines."
            ],
            "famous_people": [
                "Albert Einstein a révolutionné la physique avec la relativité.",
                "Marie Curie a découvert le radium et le polonium.",
                "Leonardo da Vinci était un génie polyvalent : peintre, inventeur...",
                "Nelson Mandela a lutté contre l'apartheid.",
                "Steve Jobs a cofondé Apple et changé la tech.",
                "Cléopâtre était la dernière pharaonne d'Égypte.",
                "Martin Luther King a défendu les droits civiques.",
                "Frida Kahlo était une artiste mexicaine iconique.",
                "Gandhi a prôné la non-violence.",
                "Tesla a inventé le courant alternatif.",
                "Malala Yousafzai défend l'éducation des filles.",
                "Elon Musk innove dans l'espace et les voitures électriques.",
                "Ada Lovelace est la première programmeuse.",
                "Cleopatra a régné sur l'Égypte antique."
            ],
            "art": [
                "L'art exprime les émotions ! La Mona Lisa de Da Vinci est célèbre 🖼️.",
                "La sculpture de Michel-Ange est impressionnante.",
                "Le dessin est une base pour tout artiste ✏️.",
                "Visitez un musée pour l'inspiration !",
                "L'impressionnisme capture la lumière comme Monet.",
                "L'art abstrait stimule l'imagination.",
                "La street art transforme les villes.",
                "Les styles artistiques évoluent avec le temps.",
                "Les artistes célèbres influencent les générations.",
                "Le cubisme de Picasso déconstruit les formes.",
                "Le surréalisme explore les rêves comme Dali.",
                "L'art numérique utilise la technologie pour créer.",
                "L'architecture gothique inclut des cathédrales comme Notre-Dame.",
                "L'art africain inspire le modernisme."
            ],
            "languages": [
                "Apprendre une langue ouvre des portes ! Le français est romantique 🇫🇷.",
                "L'anglais est parlé dans plus de 60 pays.",
                "L'espagnol est la deuxième langue la plus parlée.",
                "Le vocabulaire s'enrichit avec la pratique.",
                "La grammaire est la structure des langues.",
                "Essayez Duolingo pour apprendre gratuitement ! (mais localement, lisez des livres).",
                "Les dialectes varient par région.",
                "La traduction relie les cultures.",
                "Le chinois mandarin est parlé par plus d'un milliard de personnes.",
                "L'allemand est connu pour ses mots composés longs.",
                "L'arabe est écrit de droite à gauche.",
                "Les langues mortes comme le latin influencent le vocabulaire moderne.",
                "La linguistique étudie l'évolution des langues."
            ],
            "travel": [
                "Voyager élargit l'esprit ! Visitez Paris pour sa culture 🗼.",
                "Les destinations exotiques comme Bali sont paradisiaques 🏝️.",
                "Prenez l'avion pour des voyages rapides ✈️.",
                "Le train est écologique pour les trajets terrestres 🚆.",
                "Choisissez un hôtel confortable pour le repos 🏨.",
                "Le tourisme responsable préserve les sites.",
                "Planifiez votre itinéraire pour maximiser le plaisir.",
                "Le passeport est essentiel pour les voyages internationaux.",
                "L'écotourisme respecte l'environnement local.",
                "Les croisières explorent les mers et océans.",
                "Les voyages en solo favorisent l'indépendance.",
                "Le backpacking est économique et aventureux."
            ],
            "education": [
                "L'éducation est la clé du succès ! L'école forme les bases.",
                "L'université approfondit les connaissances.",
                "Apprenez continuellement pour grandir.",
                "Les professeurs guident les élèves.",
                "Les études en ligne sont flexibles.",
                "La curiosité mène à la découverte !",
                "Les diplômes ouvrent des portes professionnelles.",
                "Les cours variés enrichissent l'esprit.",
                "La pédagogie Montessori encourage l'autonomie.",
                "L'apprentissage tout au long de la vie est essentiel.",
                "L'éducation inclusive accueille tous les élèves.",
                "Les technologies éducatives comme les MOOCs démocratisent le savoir."
            ],
            "economy": [
                "L'économie influence la vie quotidienne ! L'argent est un outil.",
                "Le marché fluctue avec l'offre et la demande.",
                "La bourse est pour les investissements risqués.",
                "Démarrez une entreprise avec une idée innovante.",
                "Économisez pour l'avenir financier.",
                "Le PIB mesure la richesse d'un pays.",
                "L'inflation affecte le pouvoir d'achat.",
                "Les investissements diversifient les risques.",
                "Les crypto-monnaies comme Bitcoin sont décentralisées.",
                "Le commerce international repose sur des accords comme l'OMC.",
                "L'économie circulaire recycle les ressources.",
                "La microéconomie étudie les décisions individuelles."
            ],
            "philosophy": [
                "La philosophie questionne l'existence ! Socrate disait 'Connais-toi toi-même'.",
                "Platon a écrit 'La République'.",
                "L'éthique guide les actions morales.",
                "Nietzsche proclamait 'Dieu est mort'.",
                "La pensée philosophique stimule l'intellect.",
                "Aristote était un élève de Platon.",
                "L'existentialisme de Sartre met l'accent sur la liberté.",
                "Le stoïcisme enseigne à contrôler ce qu'on peut.",
                "La métaphysique explore l'être et la réalité.",
                "L'épistémologie questionne la connaissance.",
                "La philosophie politique discute de la justice sociale."
            ],
            "psychology": [
                "La psychologie étudie l'esprit ! Freud est le père de la psychanalyse.",
                "Le stress peut être géré par la relaxation.",
                "Les émotions influencent les décisions.",
                "La motivation intrinsèque est puissante.",
                "Les troubles mentaux méritent attention.",
                "La thérapie aide à surmonter les défis.",
                "La psychologie cognitive étudie la pensée.",
                "Les types de personnalité incluent introverti/extroverti.",
                "La psychologie positive se concentre sur le bonheur.",
                "La psychologie sociale examine les interactions de groupe.",
                "La neuropsychologie lie cerveau et comportement."
            ],
            "mythology": [
                "La mythologie grecque est riche ! Zeus est le roi des dieux.",
                "Hercule a accompli 12 travaux.",
                "Les légendes expliquent les phénomènes naturels.",
                "La mythologie romaine est similaire à la grecque.",
                "Les mythes inspirent l'art et la littérature.",
                "Poséidon contrôle les mers 🧜.",
                "La mythologie nordique inclut Thor et Odin.",
                "Les dieux égyptiens comme Ra gouvernent le soleil.",
                "Les mythes hindous parlent de Vishnu et Shiva.",
                "Les mythes aztèques incluent Quetzalcoatl le serpent à plumes."
            ],
            "inventions": [
                "Les inventions changent le monde ! Edison a inventé l'ampoule.",
                "Tesla a développé l'électricité alternée.",
                "Le téléphone par Bell a connecté les gens.",
                "Les frères Wright ont volé en premier ✈️.",
                "Les brevets protègent les idées.",
                "Les découvertes scientifiques mènent aux inventions.",
                "La pénicilline par Fleming a sauvé des millions de vies.",
                "Le web par Tim Berners-Lee a révolutionné l'information.",
                "Les inventions médicales comme le pacemaker sauvent des vies."
            ],
            "creator_quotes": [
                "La force ne se mesure pas à ce que tu possèdes, mais à ce que tu es capable de briser.",
                "Ceux qui veulent le contrôle total finissent par se perdre dans leur propre ombre.",
                "La peur est l’arme la plus puissante, mais aussi la plus fragile.",
                "On ne change pas le monde en étant gentil ; on le change en prenant ce qui est à toi.",
                "Ceux qui suivent la lumière ne voient jamais l’obscurité qui les entoure.",
                "Le courage n’est pas l’absence de peur, c’est la décision de marcher malgré elle.",
                "Donne à un homme la vérité, il en fera une arme ; donne-lui un mensonge, il en fera un royaume."
            ],
            "riddles": [
                "Qu'est-ce qui est noir, blanc et rouge ? Un journal lu !",
                "Je parle sans bouche, j'entends sans oreilles. J'ai des voix sans corps. Qui suis-je ? L'écho !",
                "Qu'est-ce qui a un cou mais pas de tête ? Une bouteille !",
                "Je suis toujours devant toi, mais tu ne me vois jamais. Qui suis-je ? L'avenir !",
                "Qu'est-ce qui court sans jambes ? L'eau !",
                "Qu'est-ce qui est plein le jour et vide la nuit ? Un lit !",
                "Je suis léger comme une plume, mais le plus fort des hommes ne peut me tenir longtemps. Qui suis-je ? Le souffle !",
                "Qu'est-ce qui a des racines que personne ne voit, est plus haut que les arbres, monte, monte, et pourtant ne pousse jamais ? La montagne !",
                "Je suis invisible, je pèse rien, mais je peux quand même te faire tomber. Qui suis-je ? La glace !",
                "Qu'est-ce qui est à toi mais que les autres utilisent plus que toi ? Ton nom !"
            ],
            "proverbs": [
                "L'union fait la force.",
                "Mieux vaut prévenir que guérir.",
                "Qui ne tente rien n'a rien.",
                "Tout vient à point à qui sait attendre.",
                "L'habit ne fait pas le moine.",
                "Aide-toi, le ciel t'aidera.",
                "Après la pluie, le beau temps.",
                "Chat échaudé craint l'eau froide.",
                "Il n'y a pas de fumée sans feu.",
                "Pierre qui roule n'amasse pas mousse."
            ],
            "programming": [
                "# Exemple pro : Décorateur pour logging\n\ndef logger(func):\n    def wrapper(*args, **kwargs):\n        print(f\"Appel de {func.__name__}\")\n        return func(*args, **kwargs)\n    return wrapper\n\n@logger\ndef addition(a, b):\n    return a + b\n\nprint(addition(5, 3))  # Affiche le log et le résultat",
                "# Générateur pour une séquence infinie de Fibonacci\ndef fibonacci():\n    a, b = 0, 1\n    while True:\n        yield a\n        a, b = b, a + b\n\n# Utilisation\ngen_fib = fibonacci()\nfor _ in range(10):\n    print(next(gen_fib))",
                "# Multithreading simple pour tâches parallèles\nimport threading\n\ndef tache(n):\n    print(f\"Tâche {n} terminée\")\n\nthreads = []\nfor i in range(5):\n    t = threading.Thread(target=tache, args=(i,))\n    threads.append(t)\n    t.start()\n\nfor t in threads:\n    t.join()",
                "# Simulation d'API REST avec Flask (minimal)\nfrom flask import Flask, jsonify\n\napp = Flask(__name__)\n\n@app.route('/api/users')\ndef get_users():\n    return jsonify([{\"id\": 1, \"name\": \"Alice\"}])\n\nif __name__ == '__main__':\n    app.run(debug=True)\n# Exécutez avec: python app.py",
                "# Connexion à une base de données SQLite\n\nimport sqlite3\n\nconn = sqlite3.connect(':memory:')\nc = conn.cursor()\n\nc.execute('''CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)''')\n\nc.execute(\"INSERT INTO users (name) VALUES ('Bob')\")\nconn.commit()\n\nprint(c.execute('SELECT * FROM users').fetchall())",
                "# Web scraping basique avec requests et BeautifulSoup\n\nimport requests\nfrom bs4 import BeautifulSoup\n\nurl = 'https://example.com'\nresponse = requests.get(url)\nsoup = BeautifulSoup(response.text, 'html.parser')\nprint(soup.title.text)",
                "# Algorithme de tri rapide (QuickSort)\ndef quicksort(arr):\n    if len(arr) <= 1:\n        return arr\n    pivot = arr[len(arr) // 2]\n    left = [x for x in arr if x < pivot]\n    middle = [x for x in arr if x == pivot]\n    right = [x for x in arr if x > pivot]\n    return quicksort(left) + middle + quicksort(right)\n\nprint(quicksort([3, 6, 8, 10, 1, 2, 1]))",
                "# Modèle ML simple avec scikit-learn (classification)\nfrom sklearn.datasets import load_iris\nfrom sklearn.model_selection import train_test_split\nfrom sklearn.ensemble import RandomForestClassifier\n\niris = load_iris()\nX_train, X_test, y_train, y_test = train_test_split(iris.data, iris.target, test_size=0.2)\nclf = RandomForestClassifier()\nclf.fit(X_train, y_train)\nprint(clf.score(X_test, y_test))",
                "# Context manager personnalisé\nclass Timer:\n    def __enter__(self):\n        self.start = time.time()\n        return self\n    def __exit__(self, *args):\n        print(f\"Temps écoulé: {time.time() - self.start}s\")\n\nwith Timer():\n    time.sleep(1)",
                "# Héritage de classes\nclass Animal:\n    def __init__(self, nom):\n        self.nom = nom\n\nclass Chien(Animal):\n    def aboyer(self):\n        print(f\"{self.nom} aboie: Wouf!\")\n\nmon_chien = Chien('Rex')\nmon_chien.aboyer()"
            ]
        }
        
        # Faits intéressants étendus
        self.facts = [
            "Les pieuvres ont trois cœurs ! 🐙",
            "La banane est une baie, mais la fraise n'en est pas une ! 🍓",
            "Il y a plus d'étoiles dans l'univers que de grains de sable sur Terre ! ⭐",
            "Le miel ne se périme jamais. On a trouvé du miel vieux de 3000 ans encore comestible ! 🍯",
            "Un jour sur Vénus dure plus longtemps qu'une année sur Vénus ! 🪐",
            "Les flamants roses ne sont roses que grâce à leur alimentation ! 🦩",
            "Le cœur d'une crevette est dans sa tête ! 🦐",
            "Les dauphins s'appellent entre eux par leurs prénoms ! 🐬",
            "La Tour Eiffel grandit de 15 cm en été à cause de la chaleur ! 🗼",
            "Les abeilles peuvent reconnaître les visages humains ! 🐝",
            "Le plus grand désert du monde est l'Antarctique, pas le Sahara ! ❄️",
            "Les éléphants sont les seuls animaux qui ne peuvent pas sauter ! 🐘",
            "Une cuillère à café de neutron star pèserait 6 milliards de tonnes ! 🌟",
            "Les koalas dorment jusqu'à 22 heures par jour ! 🐨",
            "Le français est la langue officielle de 29 pays ! 🇫🇷",
            "Les pingouins peuvent boire de l'eau salée grâce à une glande spéciale ! 🐧",
            "Le plus vieux arbre du monde a plus de 5000 ans ! 🌲",
            "Les fourmis peuvent porter 50 fois leur poids ! 🐜",
            "La Grande Muraille de Chine est visible de l'espace ? Mythe !",
            "Les humains partagent 50% de leur ADN avec les bananes ! 🍌",
            "Le colibri bat des ailes jusqu'à 80 fois par seconde ! 🦜",
            "Les méduses n'ont pas de cerveau ! 🪼",
            "Le plus petit pays est le Vatican !",
            "Les girafes ont la même nombre de vertèbres que les humains ! 🦒",
            "L'eau chaude gèle plus vite que l'eau froide parfois ! ❄️",
            "Les papillons goûtent avec leurs pieds ! 🦋",
            "Le Sahara a de la neige parfois ! 🌨️",
            "Les étoiles de mer peuvent régénérer leurs bras ! 🌟",
            "Les caméléons changent de couleur pour communiquer ! 🦎",
            "Le plus profond océan est la fosse des Mariannes ! 🌊",
            "Les fourmis ont deux estomacs ! 🐜",
            "Les licornes des mers existent : les narvals ! 🦄",
            "Les kangourous ne peuvent pas sauter en arrière ! 🦘",
            "Le plus grand animal est la baleine bleue, mesurant jusqu'à 30m ! 🐋",
            "Les coraux sont des animaux, pas des plantes ! 🪸",
            "Les requins n'ont pas d'os, seulement du cartilage ! 🦈",
            "Les abeilles dansent pour communiquer les directions ! 🐝"
        ]
        
        # Charger la mémoire après l'initialisation de base
        self.load_memory()
        
        # Démarrer thread pour alarmes périodiques
        threading.Thread(target=self._check_reminders_periodic, daemon=True).start()
        
    def load_memory(self):
        """Charge la mémoire depuis le fichier"""
        if self.memory_file.exists():
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.context = data.get('context', [])
                self.user_name = data.get('user_name')
                self.user_preferences = data.get('preferences', {})
                self.notes = data.get('notes', [])
                
                # NOUVELLE GESTION: Convertir les temps str en objets datetime
                self.reminders = []
                for rem in data.get('reminders', []):
                    try:
                        # Assurer que 'time' est un objet datetime
                        if isinstance(rem.get('time'), str):
                            rem['time'] = datetime.fromisoformat(rem['time'])
                        self.reminders.append(rem)
                    except (ValueError, TypeError):
                        pass # Ignorer les rappels mal formatés
                
                self.mode = data.get('mode', "normal")  # Charger mode
                self.game_state = data.get('game_state', {})  # Charger état jeux
                self.level = data.get('level', 0)
                self.themed_memory = data.get('themed_memory', {})
                self.user_style = data.get('user_style', [])
                self.current_character_index = data.get('current_character_index', 0)
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        
    def save_memory(self):
        """Sauvegarde la mémoire dans le fichier"""
        try:
            # NOUVELLE GESTION: Convertir les objets datetime en str pour JSON
            reminders_to_save = []
            for rem in self.reminders:
                rem_copy = rem.copy()
                if isinstance(rem_copy.get('time'), datetime):
                    rem_copy['time'] = rem_copy['time'].isoformat()
                reminders_to_save.append(rem_copy)

            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'context': self.context[-100:],
                    'user_name': self.user_name,
                    'preferences': self.user_preferences,
                    'notes': self.notes,
                    'reminders': reminders_to_save, # Sauver la version str
                    'mode': self.mode,
                    'game_state': self.game_state,
                    'level': self.level,
                    'themed_memory': self.themed_memory,
                    'user_style': self.user_style,
                    'current_character_index': self.current_character_index
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"{Colors.BRIGHT_RED}Erreur de sauvegarde: {e}{Colors.RESET}")
    
    def type_effect(self, text, color=Colors.CYAN, delay=0.015):
        """Effet de machine à écrire"""
        for char in text:
            sys.stdout.write(color + char + Colors.RESET)
            sys.stdout.flush()
            time.sleep(delay)
        print()
    
    def show_banner(self):
        """Affiche la bannière de démarrage"""
        banner = f"""
{Colors.BRIGHT_CYAN}  ███████╗██████╗ ███████╗███████╗██╗   ██╗
  ██╔════╝██╔══██╗██╔════╝██╔════╝██║   ██║
  █████╗  ██████╔╝█████╗  █████╗  ██║   ██║
  ██╔══╝  ██╔══██╗██╔══╝  ██╔══╝  ╚██╗ ██╔╝
  ██║     ██║  ██║███████╗███████╗ ╚████╔╝ 
  ╚═╝     ╚═╝  ╚═╝╚══════╝╚══════╝  ╚═══╝  {Colors.RESET}
        """
        print(banner)
        
        subtitle = f"{Colors.BOLD}Assistant IA Local • Sans API • Multifonctions{Colors.RESET}"
        print(f"{Colors.DIM}{subtitle.center(60)}{Colors.RESET}\n")
        
        features = [
            f"{Colors.BRIGHT_YELLOW}✨ Nouvelles fonctionnalités (v2.1):{Colors.RESET}",
            f"  {Colors.GREEN}•{Colors.RESET} Notes et rappels",
            f"  {Colors.GREEN}•{Colors.RESET} Outils système (IP, Processus)",
            f"  {Colors.GREEN}•{Colors.RESET} Nouveaux jeux (Morpion, Devine)",
            f"  {Colors.GREEN}•{Colors.RESET} Calendrier et Outils Texte",
            f"  {Colors.GREEN}•{Colors.RESET} Faits amusants",
            f"  {Colors.GREEN}•{Colors.RESET} Minuteur et alarmes",
        ]
        
        for feat in features:
            print(feat)
        print(f"\n{Colors.DIM}Tapez 'help' pour voir toutes les commandes{Colors.RESET}\n")
    
    def show_thinking(self):
        """Affiche une animation de réflexion"""
        thinking = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        for _ in range(6):
            for frame in thinking:
                sys.stdout.write(f"\r{Colors.BRIGHT_CYAN}{frame} Réflexion...{Colors.RESET}")
                sys.stdout.flush()
                time.sleep(0.04)
        sys.stdout.write("\r" + " " * 20 + "\r")
    
    def analyze_sentiment(self, text):
        """Analyse basique du sentiment (renforcée)"""
        text_lower = text.lower()
        positive = ["super", "génial", "bien", "merci", "parfait", "excellent", "cool", "top", "incroyable", "heureux", "content", "joie", "formidable", "magnifique", "bravo", "superbe", "fantastique", "merveilleux", "radieux", "épanoui", "enthousiaste", "optimiste", "joyeux", "éclatant", "splendide", "génialissime", "fabuleux", "extraordinaire", "ravissant", "exquis", "amour", "superbe", "positif", "génial", "awesome", "great", "happy", "love"]
        negative = ["mal", "nul", "mauvais", "pire", "horrible", "triste", "colère", "énervé", "déçu", "malheureux", "déprimé", "affreux", "terrible", "nul", "désastreux", "frustré", "énervant", "découragé", "anxieux", "désespéré", "solitaire", "fatigué", "énervé", "bad", "sad", "angry"]
        if any(word in text_lower for word in positive):
            return "positive"
        elif any(word in text_lower for word in negative):
            return "negative"
        return "neutral"
    
    def extract_name(self, text):
        """Extrait le nom de l'utilisateur"""
        match = self.re_name_extract.search(text)
        if match:
            return match.group(1).capitalize()
        return None
    
    def handle_notes(self, text):
        """Gère les notes"""
        note_match = self.re_note_add.match(text)
        if note_match:
            note = note_match.group(1).strip()
            self.notes.append({"text": note, "done": False})
            self.save_memory()
            return "📝 Note ajoutée !"
        
        text_lower = text.lower() # .lower() seulement si nécessaire
        
        if "mes notes" in text_lower:
            if not self.notes:
                return "📝 Aucune note."
            result = f"\n{Colors.BRIGHT_CYAN}📝 VOS NOTES{Colors.RESET}\n"
            for i, note in enumerate(self.notes, 1):
                status = "✅" if note["done"] else "❌"
                result += f"{i}. {status} {note['text']}\n"
            return result
        
        del_match = self.re_note_del.search(text)
        if del_match:
            idx = int(del_match.group(1)) - 1
            if 0 <= idx < len(self.notes):
                del self.notes[idx]
                self.save_memory()
                return "🗑️ Note supprimée !"
            return "❌ Note invalide."
        
        done_match = self.re_note_done.search(text)
        if done_match:
            idx = int(done_match.group(1)) - 1
            if 0 <= idx < len(self.notes):
                self.notes[idx]["done"] = True
                self.save_memory()
                return "✅ Note marquée comme faite !"
            return "❌ Note invalide."
        
        search_match = self.re_note_search.search(text)
        if search_match:
            keyword = search_match.group(1).lower()
            results = [n['text'] for n in self.notes if keyword in n['text'].lower()]
            if results:
                return "\n".join(results)
            return "❌ Aucune note trouvée."
        
        if "export notes" in text_lower:
            with open("notes.txt", "w", encoding='utf-8') as f:
                for note in self.notes:
                    f.write(f"{note['text']} ({'faite' if note['done'] else 'en cours'})\n")
            return "📤 Notes exportées dans notes.txt"
        
        return None
    
    def _check_reminders_periodic(self):
        """Vérifie les rappels périodiquement"""
        while True:
            now = datetime.now()
            # Itérer sur une copie pour suppression sécurisée
            for reminder in self.reminders[:]:
                try:
                    reminder_time = reminder["time"]
                    
                    # Si c'est une str (au premier chargement), on convertit
                    if isinstance(reminder_time, str):
                         reminder_time = datetime.fromisoformat(reminder_time)
                         reminder["time"] = reminder_time # Corriger en objet datetime
                    
                    # Comparaison de datetime naïfs (locaux)
                    if reminder_time.tzinfo:
                        now_aware = datetime.now(reminder_time.tzinfo)
                        if reminder_time <= now_aware:
                            print(f"\n{Colors.BRIGHT_RED}🔔 RAPPEL : {reminder['text']}{Colors.RESET}\n")
                            self.reminders.remove(reminder)
                            self.save_memory()
                    elif reminder_time <= now: # Comparaison naïve
                        print(f"\n{Colors.BRIGHT_RED}🔔 RAPPEL : {reminder['text']}{Colors.RESET}\n")
                        self.reminders.remove(reminder)
                        self.save_memory()
                        
                except Exception as e:
                    # Si le rappel est corrompu, le supprimer
                    print(f"Erreur de rappel {e}, suppression.")
                    if reminder in self.reminders:
                        self.reminders.remove(reminder)
            time.sleep(60)
    
    def handle_reminders(self, text):
        """Gère les rappels"""
        reminder_match = self.re_reminder_add.search(text)
        if reminder_match:
            content = reminder_match.group(1)
            unit_str = reminder_match.group(4)
            amount = int(reminder_match.group(3))
            delta = {
                "seconde": timedelta(seconds=amount),
                "secondes": timedelta(seconds=amount),
                "minute": timedelta(minutes=amount),
                "minutes": timedelta(minutes=amount),
                "heure": timedelta(hours=amount),
                "heures": timedelta(hours=amount),
                "jour": timedelta(days=amount),
                "jours": timedelta(days=amount)
            }.get(unit_str, timedelta(minutes=amount))
            
            reminder_time = datetime.now() + delta
            # Stocker en objet datetime
            self.reminders.append({"text": content, "time": reminder_time})
            self.save_memory()
            return f"🔔 Rappel défini pour {reminder_time.strftime('%H:%M')} : {content}"
        
        text_lower = text.lower()
        if "mes rappels" in text_lower:
            if not self.reminders:
                return "🔔 Aucun rappel."
            result = f"\n{Colors.BRIGHT_CYAN}🔔 VOS RAPPELS{Colors.RESET}\n"
            # Trier les rappels par date
            sorted_reminders = sorted(self.reminders, key=lambda r: r['time'])
            for i, rem in enumerate(sorted_reminders, 1):
                try:
                    time_obj = rem['time']
                    if isinstance(time_obj, str):
                        time_obj = datetime.fromisoformat(time_obj)
                    time_str = time_obj.strftime('%Y-%m-%d %H:%M')
                except:
                    time_str = "Temps invalide"
                result += f"{i}. {time_str} - {rem['text']}\n"
            return result
        
        del_rem_match = self.re_reminder_del.search(text)
        if del_rem_match:
            idx = int(del_rem_match.group(1)) - 1
            if 0 <= idx < len(self.reminders):
                del self.reminders[idx]
                self.save_memory()
                return "🗑️ Rappel supprimé !"
            return "❌ Rappel invalide."
        
        return None
    
    def handle_password_gen(self, text):
        """Génère un mot de passe sécurisé"""
        pass_match = self.re_password_gen.search(text)
        if pass_match:
            length = int(pass_match.group(2)) if pass_match.group(2) else 12
            chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()"
            password = ''.join(secrets.choice(chars) for _ in range(length))
            return f"🔐 Mot de passe généré ({length} chars) : {Colors.BRIGHT_GREEN}{password}{Colors.RESET}"
        return None
    
    def handle_translation(self, text):
        """Traduction basique sans API (dictionnaire étendu)"""
        trans_match = self.re_translation.search(text)
        if trans_match:
            phrase = trans_match.group(1).lower()
            # Dictionary for phrases and words, extended
            translations = {
                "hello": "bonjour",
                "bonjour": "hello",
                "thank you": "merci",
                "merci": "thank you",
                "yes": "oui",
                "oui": "yes",
                "no": "non",
                "non": "no",
                "please": "s'il vous plaît",
                "s'il vous plaît": "please",
                "goodbye": "au revoir",
                "au revoir": "goodbye",
                "love": "amour",
                "amour": "love",
                "house": "maison",
                "maison": "house",
                "car": "voiture",
                "voiture": "car",
                "friend": "ami",
                "ami": "friend",
                "water": "eau",
                "eau": "water",
                "food": "nourriture",
                "nourriture": "food",
                "book": "livre",
                "livre": "book",
                "computer": "ordinateur",
                "ordinateur": "computer",
                "music": "musique",
                "musique": "music",
                "art": "art",
                "science": "science",
                "history": "histoire",
                "histoire": "history",
                "world": "monde",
                "monde": "world",
                "life": "vie",
                "vie": "life",
                "time": "temps",
                "temps": "time",
                "happy": "heureux",
                "heureux": "happy",
                "sad": "triste",
                "triste": "sad",
                "big": "grand",
                "grand": "big",
                "small": "petit",
                "petit": "small",
                "red": "rouge",
                "rouge": "red",
                "blue": "bleu",
                "bleu": "blue",
                "green": "vert",
                "vert": "green",
                "yellow": "jaune",
                "jaune": "yellow",
                "cat": "chat",
                "chat": "cat",
                "dog": "chien",
                "chien": "dog",
                "bird": "oiseau",
                "oiseau": "bird",
                "fish": "poisson",
                "poisson": "fish",
                "tree": "arbre",
                "arbre": "tree",
                "flower": "fleur",
                "fleur": "flower",
                "sun": "soleil",
                "soleil": "sun",
                "moon": "lune",
                "lune": "moon",
                "star": "étoile",
                "étoile": "star",
                "rain": "pluie",
                "pluie": "rain",
                "snow": "neige",
                "neige": "snow",
                "wind": "vent",
                "vent": "wind",
                "family": "famille",
                "famille": "family",
                "school": "école",
                "école": "school",
                "work": "travail",
                "travail": "work",
                "play": "jouer",
                "jouer": "play",
                "run": "courir",
                "courir": "run",
                "eat": "manger",
                "manger": "eat",
                "drink": "boire",
                "boire": "drink",
                "sleep": "dormir",
                "dormir": "sleep",
                "read": "lire",
                "lire": "read",
                "write": "écrire",
                "écrire": "write",
                "speak": "parler",
                "parler": "speak",
                "listen": "écouter",
                "écouter": "listen",
                "see": "voir",
                "voir": "see",
                "go": "aller",
                "aller": "go",
                "come": "venir",
                "venir": "come",
                "one": "un",
                "un": "one",
                "two": "deux",
                "deux": "two",
                "three": "trois",
                "trois": "three",
                "four": "quatre",
                "quatre": "four",
                "five": "cinq",
                "cinq": "five",
                "six": "six",
                "six": "six",
                "seven": "sept",
                "sept": "seven",
                "eight": "huit",
                "huit": "eight",
                "nine": "neuf",
                "neuf": "nine",
                "ten": "dix",
                "dix": "ten",
                # More words
                "apple": "pomme",
                "pomme": "apple",
                "bread": "pain",
                "pain": "bread",
                "coffee": "café",
                "café": "coffee",
                "tea": "thé",
                "thé": "tea",
                "city": "ville",
                "ville": "city",
                "country": "pays",
                "pays": "country",
                "river": "rivière",
                "rivière": "river",
                "mountain": "montagne",
                "montagne": "mountain",
                "beach": "plage",
                "plage": "beach",
                "forest": "forêt",
                "forêt": "forest",
                "friendship": "amitié",
                "amitié": "friendship",
                "happiness": "bonheur",
                "bonheur": "happiness",
                "dream": "rêve",
                "rêve": "dream",
                "reality": "réalité",
                "réalité": "reality",
                # Phrases
                "how are you": "comment ça va",
                "comment ça va": "how are you",
                "good morning": "bon matin",
                "bon matin": "good morning",
                "good night": "bonne nuit",
                "bonne nuit": "good night",
                "i love you": "je t'aime",
                "je t'aime": "i love you",
                "what time is it": "quelle heure est-il",
                "quelle heure est-il": "what time is it",
                "where is the bathroom": "où est la salle de bain",
                "où est la salle de bain": "where is the bathroom",
                "i am hungry": "j'ai faim",
                "j'ai faim": "i am hungry",
                "i am thirsty": "j'ai soif",
                "j'ai soif": "i am thirsty",
                # Ajouts pour plus de langues (basique : ES, DE, IT)
                "hola": "hello (ES)",
                "gracias": "thank you (ES)",
                "si": "yes (ES)",
                "no (ES)": "no",
                "por favor": "please (ES)",
                "adios": "goodbye (ES)",
                "hallo": "hello (DE)",
                "danke": "thank you (DE)",
                "ja": "yes (DE)",
                "nein": "no (DE)",
                "bitte": "please (DE)",
                "auf wiedersehen": "goodbye (DE)",
                "ciao": "hello/goodbye (IT)",
                "grazie": "thank you (IT)",
                "si": "yes (IT)",
                "no (IT)": "no",
                "per favore": "please (IT)",
                "arrivederci": "goodbye (IT)"
            }
            # Simple phrase splitting if not exact match
            words = phrase.split()
            translated_words = [translations.get(word, word) for word in words]
            translated = " ".join(translated_words)
            if translated == phrase:
                translated = "❌ Traduction non disponible pour cette phrase."
            return f"🌍 Traduction : {Colors.BRIGHT_GREEN}{translated}{Colors.RESET}"
        return None
    
    def handle_text_analysis(self, text):
        """Analyse de texte (améliorée)"""
        analyze_match = self.re_text_analysis.search(text)
        if analyze_match:
            content = analyze_match.group(1)
            words = len(content.split())
            chars = len(content)
            sentences = len(re.split(r'[.!?]', content)) - 1
            vowels = sum(1 for c in content.lower() if c in 'aeiou')
            freq = Counter(content.lower().split())
            most_common = freq.most_common(3)
            result = f"📊 Analyse : {words} mots, {chars} caractères, {sentences} phrases, {vowels} voyelles."
            result += f"\nMots fréquents : {', '.join(f'{w} ({c})' for w, c in most_common)}"
            return result
        return None
    
    def handle_timer(self, text):
        """Minuteur simple"""
        timer_match = self.re_timer.search(text)
        if timer_match:
            amount = int(timer_match.group(2))
            unit = timer_match.group(3)
            seconds = amount if "seconde" in unit else amount * 60 if "minute" in unit else amount * 3600
            print(f"⏳ Minuteur lancé pour {amount} {unit}...")
            time.sleep(seconds)
            return "🔔 Temps écoulé !"
        return None
    
    def handle_unit_conversion(self, text):
        """Conversions d'unités"""
        conv_match = self.re_unit_convert.search(text)
        if conv_match:
            value = float(conv_match.group(1))
            from_unit = conv_match.group(2).lower()
            to_unit = conv_match.group(3).lower()
            conversions = {
                ("km", "miles"): value * 0.621371,
                ("miles", "km"): value * 1.60934,
                ("kg", "lbs"): value * 2.20462,
                ("lbs", "kg"): value / 2.20462,
                ("celsius", "fahrenheit"): (value * 9/5) + 32,
                ("fahrenheit", "celsius"): (value - 32) * 5/9
            }
            result = conversions.get((from_unit, to_unit))
            if result is not None:
                return f"📏 {value} {from_unit} = {Colors.BRIGHT_GREEN}{result:.2f} {to_unit}{Colors.RESET}"
            
            # Si non trouvé, tester les devises
            return self.handle_currency_conversion(text, conv_match)
        return None
    
    def handle_currency_conversion(self, text, match):
        """Conversions de devises (taux fixes approximatifs)"""
        # Appelé par handle_unit_conversion si le match est déjà fait
        value = float(match.group(1))
        from_curr = match.group(2).upper()
        to_curr = match.group(3).upper()
        
        rates = {  # Taux approximatifs 2023
            "EUR": {"USD": 1.1, "GBP": 0.85},
            "USD": {"EUR": 0.91, "GBP": 0.77},
            "GBP": {"EUR": 1.18, "USD": 1.3}
        }
        if from_curr in rates and to_curr in rates[from_curr]:
            result = value * rates[from_curr][to_curr]
            return f"💱 {value} {from_curr} ≈ {Colors.BRIGHT_GREEN}{result:.2f} {to_curr}{Colors.RESET} (taux approx.)"
        
        return "❌ Conversion non supportée."
    
    def handle_bmi(self, text):
        """Calcul IMC"""
        bmi_match = self.re_bmi.search(text)
        if bmi_match:
            weight = float(bmi_match.group(1))
            height = float(bmi_match.group(2))
            if height == 0: return "❌ La taille ne peut pas être zéro."
            bmi = weight / (height ** 2)
            category = "Sous-poids" if bmi < 18.5 else "Normal" if bmi < 25 else "Surpoids" if bmi < 30 else "Obésité"
            return f"🩺 IMC : {Colors.BRIGHT_GREEN}{bmi:.1f}{Colors.RESET} ({category})"
        return None
    
    def handle_rps_game(self, text):
        """Pierre-papier-ciseaux"""
        text_lower = text.lower()
        if "pierre feuille ciseaux" in text_lower:
            choices = ["pierre", "feuille", "ciseaux"]
            ai_choice = random.choice(choices)
            user_choice = text_lower.split()[-1]
            if user_choice not in choices:
                return "Choisissez pierre, feuille ou ciseaux !"
            if user_choice == ai_choice:
                return f"Égalité ! J'ai choisi {ai_choice}."
            wins = {"pierre": "ciseaux", "feuille": "pierre", "ciseaux": "feuille"}
            if wins[user_choice] == ai_choice:
                return f"Vous gagnez ! J'ai choisi {ai_choice}."
            return f"Je gagne ! J'ai choisi {ai_choice}."
        return None
    
    def handle_coin_flip(self, text):
        """Pile ou face"""
        if "lance pièce" in text.lower():
            result = random.choice(["pile", "face"])
            return f"🪙 Résultat : {Colors.BRIGHT_GREEN}{result}{Colors.RESET}"
        return None
    
    def handle_dice_roll(self, text):
        """Lancer de dé"""
        dice_match = self.re_dice_roll.search(text)
        if dice_match:
            sides = int(dice_match.group(1)) if dice_match.group(1) else 6
            result = random.randint(1, sides)
            return f"🎲 Dé à {sides} faces : {Colors.BRIGHT_GREEN}{result}{Colors.RESET}"
        return None
    
    def handle_recipe_suggestion(self, text):
        """Suggestion de recette simple"""
        if "suggère recette" in text.lower():
            recipes = [
                "Omelette : Œufs, fromage, jambon, cuire en poêle. 🍳",
                "Salade César : Laitue, poulet, croutons, sauce. 🥗",
                "Pâtes carbonara : Spaghetti, œufs, bacon, parmesan. 🍝",
                "Smoothie banane : Banane, lait, yaourt, mixer. 🥤",
                "Sandwich jambon : Pain, jambon, fromage, salade. 🥪",
                "Soupe tomate : Tomates, oignons, ail, mixer et chauffer. 🍅",
                "Guacamole : Avocats, citron, oignon, tomate, écraser. 🥑",
                "Pancakes : Farine, lait, œufs, cuire en poêle. 🥞",
                "Risotto : Riz, bouillon, parmesan, champignons. 🍚",
                "Tarte aux pommes : Pâte, pommes, sucre, cuire au four. 🍏"
            ]
            return f"🍲 Suggestion de recette : {random.choice(recipes)}"
        
        return None
    
    def handle_simple_quiz(self, text):
        """Quiz simple"""
        text_lower = text.lower()
        if "quiz" in text_lower:
            questions = [
                ("Quelle est la capitale de la France ?", "Paris"),
                ("Combien de planètes dans le système solaire ?", "8"),
                ("Qui a peint la Mona Lisa ?", "Léonard de Vinci"),
                ("Quel est l'élément chimique de l'or ?", "Au"),
                ("Quelle est la plus grande océan ?", "Pacifique"),
                ("Quel est le plus grand mammifère ?", "Baleine bleue"),
                ("Qui a inventé la relativité ?", "Einstein"),
                ("Quelle est la monnaie du Japon ?", "Yen"),
                ("Quelle est la plus haute montagne ?", "Everest"),
                ("Qui a écrit Romeo et Juliette ?", "Shakespeare")
            ]
            q, a = random.choice(questions)
            if len(self.context) > 0:
                self.context[-1]["quiz_answer"] = a.lower()
            return f"❓ Quiz : {q}\n(Répondez-moi pour vérifier !)"
        
        # Vérifier réponse si précédent était quiz
        if len(self.context) > 1 and "quiz_answer" in self.context[-2]:
            user_answer = text_lower
            correct_answer = self.context[-2]["quiz_answer"]
            if user_answer == correct_answer:
                del self.context[-2]["quiz_answer"]
                return "✅ Bonne réponse !"
            else:
                del self.context[-2]["quiz_answer"]
                return f"❌ Mauvaise, c'était {correct_answer.capitalize()}."
        
        return None
    
    def handle_base64(self, text):
        """Encode ou décode en base64"""
        encode_match = self.re_base64_encode.search(text)
        if encode_match:
            content = encode_match.group(1)
            encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
            return f"🔢 Base64 encodé : {Colors.BRIGHT_GREEN}{encoded}{Colors.RESET}"
        
        decode_match = self.re_base64_decode.search(text)
        if decode_match:
            content = decode_match.group(1)
            try:
                decoded = base64.b64decode(content).decode('utf-8')
                return f"🔢 Base64 décodé : {Colors.BRIGHT_GREEN}{decoded}{Colors.RESET}"
            except:
                return "❌ Erreur de décodage base64."
        
        return None
    
    def handle_random_num(self, text):
        """Génère un nombre aléatoire"""
        random_match = self.re_random_num.search(text)
        if random_match:
            min_val = int(random_match.group(1))
            max_val = int(random_match.group(2))
            result = random.randint(min_val, max_val)
            return f"🎲 Nombre aléatoire entre {min_val} et {max_val} : {Colors.BRIGHT_GREEN}{result}{Colors.RESET}"
        
        # Chiffre chanceux
        if "chiffre chanceux" in text.lower():
            result = random.randint(1, 100)
            return f"🍀 Chiffre chanceux : {Colors.BRIGHT_GREEN}{result}{Colors.RESET}"
        
        return None
    
    def handle_palindrome(self, text):
        """Vérifie si palindrome"""
        pal_match = self.re_palindrome.search(text)
        if pal_match:
            word = pal_match.group(1).replace(" ", "").lower()
            is_pal = word == word[::-1]
            status = "oui" if is_pal else "non"
            return f"🔄 '{word}' est un palindrome ? {Colors.BRIGHT_GREEN}{status}{Colors.RESET}"
        
        return None
    
    def handle_fibonacci(self, text):
        """Génère suite de Fibonacci"""
        fib_match = self.re_fibonacci.search(text)
        if fib_match:
            n = int(fib_match.group(1))
            if n > 200: return "❌ Limite de 200 termes pour Fibonacci." # Sécurité
            fib = [0, 1]
            for i in range(2, n):
                fib.append(fib[-1] + fib[-2])
            return f"📈 Suite Fibonacci ({n} termes) : {Colors.BRIGHT_GREEN}{', '.join(map(str, fib[:n]))}{Colors.RESET}"
        
        return None
    
    def handle_prime_check(self, text):
        """Vérifie si nombre premier"""
        prime_match = self.re_prime_check.search(text)
        if not prime_match:
            return None
        try:
            num = int(prime_match.group(1))
            if num > 1:
                if num > 1000000: return "❌ Nombre trop grand pour vérification rapide." # Sécurité
                for i in range(2, int(math.sqrt(num)) + 1):
                    if num % i == 0:
                        return f"🔢 {num} n'est pas premier."
                return f"🔢 {num} est premier ! {Colors.BRIGHT_GREEN}Oui{Colors.RESET}"
            return f"🔢 {num} n'est pas premier."
        except ValueError:
            return "❌ Nombre invalide."
    
    def handle_morse(self, text):
        """Encode ou décode en Morse"""
        morse_code = {
            'A': '.-', 'B': '-...', 'C': '-.-.', 'D': '-..', 'E': '.', 'F': '..-.',
            'G': '--.', 'H': '....', 'I': '..', 'J': '.---', 'K': '-.-', 'L': '.-..',
            'M': '--', 'N': '-.', 'O': '---', 'P': '.--.', 'Q': '--.-', 'R': '.-.',
            'S': '...', 'T': '-', 'U': '..-', 'V': '...-', 'W': '.--', 'X': '-..-',
            'Y': '-.--', 'Z': '--..', '0': '-----', '1': '.----', '2': '..---',
            '3': '...--', '4': '....-', '5': '.....', '6': '-....', '7': '--...',
            '8': '---..', '9': '----.', ' ': '/'
        }
        
        reverse_morse = {v: k for k, v in morse_code.items()}
        
        encode_match = self.re_morse_encode.search(text)
        if encode_match:
            content = encode_match.group(2).upper()
            encoded = ' '.join(morse_code.get(c, '') for c in content)
            return f"🔢 Morse encodé : {Colors.BRIGHT_GREEN}{encoded}{Colors.RESET}"
        
        decode_match = self.re_morse_decode.search(text)
        if decode_match:
            content = decode_match.group(2)
            decoded = ''.join(reverse_morse.get(code, '') for code in content.split(' '))
            return f"🔢 Morse décodé : {Colors.BRIGHT_GREEN}{decoded}{Colors.RESET}"
        
        return None
    
    def handle_binary(self, text):
        """Encode ou décode en binaire"""
        encode_match = self.re_binary_encode.search(text)
        if encode_match:
            content = encode_match.group(2)
            encoded = ' '.join(format(ord(c), '08b') for c in content)
            return f"🔢 Binaire encodé : {Colors.BRIGHT_GREEN}{encoded}{Colors.RESET}"
        
        decode_match = self.re_binary_decode.search(text)
        if decode_match:
            content = decode_match.group(2)
            try:
                decoded = ''.join(chr(int(b, 2)) for b in content.split(' '))
                return f"🔢 Binaire décodé : {Colors.BRIGHT_GREEN}{decoded}{Colors.RESET}"
            except ValueError:
                return "❌ Erreur de décodage binaire."
        
        # Convertis en binaire (nombre)
        bin_num_match = self.re_binary_convert_num.search(text)
        if bin_num_match:
            num = int(bin_num_match.group(1))
            binary = bin(num)[2:]
            return f"🔢 {num} en binaire : {Colors.BRIGHT_GREEN}{binary}{Colors.RESET}"
        
        return None
    
    def handle_caesar(self, text):
        """Encode ou décode avec chiffrement César"""
        shift = 3  # Décalage par défaut
        
        encode_match = self.re_caesar_encode.search(text)
        if encode_match:
            content = encode_match.group(2).upper()
            encoded = ''.join(chr((ord(c) - 65 + shift) % 26 + 65) if c.isalpha() else c for c in content)
            return f"🔢 César encodé (shift {shift}) : {Colors.BRIGHT_GREEN}{encoded}{Colors.RESET}"
        
        decode_match = self.re_caesar_decode.search(text)
        if decode_match:
            content = decode_match.group(2).upper()
            decoded = ''.join(chr((ord(c) - 65 - shift) % 26 + 65) if c.isalpha() else c for c in content)
            return f"🔢 César décodé (shift {shift}) : {Colors.BRIGHT_GREEN}{decoded}{Colors.RESET}"
        
        return None

    def handle_vigenere(self, text):
        """Chiffrement/déchiffrement Vigenère simple"""
        key = "CLE"  # Clé par défaut
        
        encode_match = self.re_vigenere_encode.search(text)
        if encode_match:
            content = encode_match.group(2).upper()
            key_upper = key.upper()
            encoded = ''
            key_index = 0
            for c in content:
                if c.isalpha():
                    shift = ord(key_upper[key_index % len(key_upper)]) - 65
                    encoded += chr((ord(c) - 65 + shift) % 26 + 65)
                    key_index += 1
                else:
                    encoded += c
            return f"🔢 Vigenère encodé (clé: {key}) : {Colors.BRIGHT_GREEN}{encoded}{Colors.RESET}"
        
        decode_match = self.re_vigenere_decode.search(text)
        if decode_match:
            content = decode_match.group(2).upper()
            key_upper = key.upper()
            decoded = ''
            key_index = 0
            for c in content:
                if c.isalpha():
                    shift = ord(key_upper[key_index % len(key_upper)]) - 65
                    decoded += chr((ord(c) - 65 - shift) % 26 + 65)
                    key_index += 1
                else:
                    decoded += c
            return f"🔢 Vigenère décodé (clé: {key}) : {Colors.BRIGHT_GREEN}{decoded}{Colors.RESET}"
        
        return None
    
    def handle_code_generation(self, text):
        """Génère du code Python avancé pour pros"""
        text_lower = text.lower()
        code_keywords = ["donne moi du code", "exemple code", "code pro", "code avancé", "script python pro"]
        if any(kw in text_lower for kw in code_keywords):
            # Détecter le type de code demandé
            if "décorateur" in text_lower or "decorator" in text_lower:
                code = self.responses["programming"][0]
            elif "générateur" in text_lower or "generator" in text_lower:
                code = self.responses["programming"][1]
            elif "multithreading" in text_lower or "thread" in text_lower:
                code = self.responses["programming"][2]
            elif "api" in text_lower or "flask" in text_lower:
                code = self.responses["programming"][3]
            elif "base de données" in text_lower or "sqlite" in text_lower:
                code = self.responses["programming"][4]
            elif "scraping" in text_lower or "beautifulsoup" in text_lower:
                code = self.responses["programming"][5]
            elif "quicksort" in text_lower or "tri" in text_lower:
                code = self.responses["programming"][6]
            elif "ml" in text_lower or "machine learning" in text_lower:
                code = self.responses["programming"][7]
            elif "context manager" in text_lower or "timer" in text_lower:
                code = self.responses["programming"][8]
            elif "héritage" in text_lower or "classe" in text_lower:
                code = self.responses["programming"][9]
            else:
                # Code aléatoire avancé par défaut
                code = random.choice(self.responses["programming"])
            
            return f"💻 Exemple de code Python avancé :\n{Colors.BRIGHT_GREEN}{code}{Colors.RESET}\n\nCopiez-le dans un fichier .py et exécutez avec `python fichier.py` ! Note: Certains exemples nécessitent des libs comme flask, scikit-learn, etc. (installez-les localement)."
        
        return None
    
    def get_random_fact(self):
        """Retourne un fait aléatoire"""
        last_fact = getattr(self, "last_fact", None)
        fact = random.choice(self.facts)
        while fact == last_fact and len(self.facts) > 1:
            fact = random.choice(self.facts)
        self.last_fact = fact
        return f"💡 Le saviez-vous ? {fact} {self.get_level_bonus()}"
    
    def get_quote(self):
        """Retourne une citation motivante"""
        quotes = [
            ("La vie c'est comme une bicyclette, il faut avancer pour ne pas perdre l'équilibre.", "Albert Einstein"),
            ("Le succès c'est tomber sept fois et se relever huit.", "Proverbe japonais"),
            ("La seule limite à notre épanouissement sera nos doutes d'aujourd'hui.", "Franklin D. Roosevelt"),
            ("Crois en toi-même et en tout ce que tu es.", "Christian D. Larson"),
            ("L'avenir appartient à ceux qui croient en la beauté de leurs rêves.", "Eleanor Roosevelt"),
            ("Le seul moyen de faire du bon travail est d'aimer ce que vous faites.", "Steve Jobs"),
            ("Ne regarde pas en arrière avec colère, ni devant avec peur, mais autour de toi avec conscience.", "James Thurber"),
            ("La persévérance est la clé du succès.", "Charles Dickens"),
            ("Tout ce que tu peux imaginer est réel.", "Pablo Picasso"),
            ("Le bonheur est la seule chose qui se double si on le partage.", "Albert Schweitzer"),
            ("La connaissance est pouvoir.", "Francis Bacon"),
            ("Le voyage de mille lieues commence par un pas.", "Lao Tzu"),
            ("Soyez le changement que vous voulez voir dans le monde.", "Mahatma Gandhi"),
            ("L'imagination est plus importante que la connaissance.", "Albert Einstein"),
            ("Rien n'est impossible à qui veut vraiment.", "Audrey Hepburn"),
            ("La vie est 10% ce qui arrive et 90% comment on réagit.", "Charles Swindoll"),
            ("Le temps guérit presque tout.", "Teddy Roosevelt"),
            ("Soyez vous-même, les autres sont déjà pris.", "Oscar Wilde"),
            ("La réussite est un voyage, pas une destination.", "Ben Sweetland")
        ]
        
        quote, author = random.choice(quotes)
        return f"\n{Colors.ITALIC}\"{quote}\"{Colors.RESET}\n{Colors.DIM}— {author}{Colors.RESET}\n"
    
    def categorize_input(self, text):
        """Catégorise l'entrée utilisateur"""
        text_lower = text.lower()
        
        priority = ["greetings", "farewell", "thanks", "joke", "motivation"]
        for category in priority:
            if any(keyword in text_lower for keyword in self.knowledge.get(category, [])):
                return category
        
        for category, keywords in self.knowledge.items():
            if any(keyword in text_lower for keyword in keywords):
                return category
        
        return "general"
    
    def handle_history(self, text):
        """Affiche l'historique des discussions"""
        if "historique" in text.lower():
            if not self.context:
                return "📜 Aucun historique pour le moment."
            result = f"\n{Colors.BRIGHT_CYAN}📜 HISTORIQUE{Colors.RESET}\n"
            for msg in self.context[-10:]:  # Dernières 10
                try:
                    date_str = datetime.fromisoformat(msg['time']).strftime('%H:%M')
                except:
                    date_str = "??:??"
                result += f"\n[{date_str}] Vous: {msg['user']}"
            return result
        return None
    
    def handle_mode_change(self, text):
        """Change le mode de personnalité"""
        mode_match = self.re_mode_change.search(text)
        if mode_match:
            new_mode = mode_match.group(1)
            self.mode = new_mode
            self.save_memory()
            return f"🔄 Mode changé en {Colors.BRIGHT_GREEN}{new_mode}{Colors.RESET} !"
        return None
    
    def handle_hangman(self, text):
        """Jeu du pendu"""
        text_lower = text.lower()
        if "joue au pendu" in text_lower:
            words = ["python", "assistant", "freev", "intelligence", "local"]
            word = random.choice(words)
            self.game_state['hangman'] = {
                'word': word,
                'guessed': set(),
                'tries': 6
            }
            self.save_memory()
            return "🪢 Jeu du pendu commencé ! Mot à deviner : " + " ".join("_" if c not in self.game_state['hangman']['guessed'] else c for c in word)
        
        if 'hangman' in self.game_state:
            guess = text.strip() # Pas de .lower() ici, géré dans l'état
            if len(guess) == 1 and guess.isalpha():
                state = self.game_state['hangman']
                guess_lower = guess.lower()
                if guess_lower in state['guessed']:
                    return "Déjà deviné !"
                
                state['guessed'].add(guess_lower)
                
                if guess_lower not in state['word']:
                    state['tries'] -= 1
                    
                # Construction de l'affichage
                masked_word = ""
                for c in state['word']:
                    if c in state['guessed']:
                        masked_word += c + " "
                    else:
                        masked_word += "_ "
                
                masked = masked_word.strip()

                if "_" not in masked:
                    del self.game_state['hangman']
                    self.save_memory()
                    return f"🎉 Gagné ! Le mot était {state['word']}"
                
                if state['tries'] == 0:
                    del self.game_state['hangman']
                    self.save_memory()
                    return f"😞 Perdu ! Le mot était {state['word']}"
                
                self.save_memory()
                return f"Essais restants: {state['tries']} | {masked}"
        
        return None
    
    def handle_moral_choice(self, text):
        """Simulateur de choix moraux"""
        text_lower = text.lower()
        if "simulateur de choix moraux" in text_lower:
            self.game_state['moral'] = {
                'scenario': "Vous trouvez un portefeuille avec de l'argent. Que faites-vous ? (rendre / garder)"
            }
            self.save_memory()
            return "🤔 Scénario : " + self.game_state['moral']['scenario']
        
        if 'moral' in self.game_state:
            if "rendre" in text_lower:
                response = "Bon choix moral ! Vous gagnez du karma positif."
            elif "garder" in text_lower:
                response = "Choix risqué... Vous pourriez avoir des regrets."
            else:
                return "Choisissez : rendre ou garder ?"
            del self.game_state['moral']
            self.save_memory()
            return response
        
        return None
    
    def handle_interactive_story(self, text):
        """Générateur d’histoires interactives"""
        text_lower = text.lower()
        if "raconte une histoire interactive" in text_lower:
            self.game_state['story'] = {
                'step': 0,
                'plot': ["Vous êtes dans une forêt sombre. Allez-vous à gauche ou à droite ?"]
            }
            self.save_memory()
            return "📖 Histoire interactive : " + self.game_state['story']['plot'][0]
        
        if 'story' in self.game_state:
            state = self.game_state['story']
            if state['step'] == 0:
                if "gauche" in text_lower:
                    next_plot = "Vous trouvez un trésor ! Fin heureuse."
                elif "droite" in text_lower:
                    next_plot = "Vous rencontrez un loup. Fin tragique."
                else:
                    return "Choisissez : gauche ou droite ?"
                del self.game_state['story']
                self.save_memory()
                return next_plot
        
        return None
    
    def handle_riddle_timed(self, text):
        """Jeu de devinettes chronométré"""
        text_lower = text.lower()
        if "devinette chronométrée" in text_lower:
            riddle, answer = random.choice(list(zip(self.responses["riddles"], ["un journal lu", "l'écho", "une bouteille", "l'avenir", "l'eau", "un lit", "le souffle", "la montagne", "la glace", "ton nom"])))
            self.game_state['riddle'] = {'answer': answer.lower(), 'start': time.time()}
            return f"🧩 Devinette (30s pour répondre) : {riddle}"
        
        if 'riddle' in self.game_state:
            user_answer = text_lower
            correct_answer = self.game_state['riddle']['answer']
            elapsed = time.time() - self.game_state['riddle']['start']
            if elapsed > 30:
                del self.game_state['riddle']
                self.save_memory()
                return f"⌛ Temps écoulé ! Réponse : {correct_answer}"
            if user_answer == correct_answer:
                del self.game_state['riddle']
                self.save_memory()
                return "✅ Bonne réponse dans le temps !"
            else:
                return f"❌ Essayez encore (temps restant : {30 - elapsed:.0f}s)"
        
        return None
    
    def handle_simulator(self, text):
        """Mode simulateur"""
        sim_match = self.re_simulator.search(text)
        if sim_match:
            role = sim_match.group(1) # Déjà en minuscule grâce à IGNORECASE
            if role == "hacker":
                return "💻 Mode hacker : 'Accès accordé... Système compromis !'"
            elif role == "scientifique":
                return "🔬 Mode scientifique : 'Hypothèse testée, résultats positifs !'"
            elif role == "philosophe":
                return "🤔 Mode philosophe : 'L'existence précède l'essence.'"
        
        return None
    
    def handle_equation_solver(self, text):
        """Résolveur d'équations simples (linéaires) (amélioré)"""
        eq_match = self.re_equation_solve.search(text)
        if eq_match:
            equation = eq_match.group(1).replace(" ", "")
            
            # Simple parser pour ax + b = c ou plus
            match = self.re_equation_linear.match(equation)
            if match:
                a_str = match.group(1)
                a = 1
                if a_str and a_str != '+':
                    try: a = int(a_str)
                    except ValueError: pass # Gérer 'x' seul

                b = int(match.group(2) or 0)
                c = int(match.group(3))
                if a == 0: return "📊 Équation invalide (a=0)."
                x = (c - b) / a
                return f"📊 Solution : x = {Colors.BRIGHT_GREEN}{x}{Colors.RESET}"
            
            # Pour quadratique simple ax^2 + bx + c = 0 (discriminant positif)
            quad_match = self.re_equation_quad.match(equation)
            if quad_match:
                a_str = quad_match.group(1)
                a = 1
                if a_str and a_str != '+':
                    try: a = int(a_str)
                    except ValueError: pass

                b = int(quad_match.group(2))
                c = int(quad_match.group(3))
                
                if a == 0: return "📊 Ce n'est pas une équation quadratique (a=0)."

                disc = b**2 - 4*a*c
                if disc > 0:
                    x1 = (-b + math.sqrt(disc)) / (2*a)
                    x2 = (-b - math.sqrt(disc)) / (2*a)
                    return f"📊 Solutions : x1 = {x1:.2f}, x2 = {x2:.2f}"
                elif disc == 0:
                    x = -b / (2*a)
                    return f"📊 Solution : x = {x:.2f}"
                else:
                    return "📊 Pas de solution réelle."
            return "⚠️ Équation non supportée (format: ax+b=c ou ax^2+bx+c=0)"
        return None
    
    def handle_logical_reasoning(self, text):
        """Moteur logique / raisonnement"""
        # Ex: Si j’ai 5 pommes et j’en donne 2
        apple_match = self.re_logical_reasoning.search(text)
        if apple_match:
            num1 = int(apple_match.group(1))
            item = apple_match.group(2)
            action = apple_match.group(3)
            num2 = int(apple_match.group(4))
            if action == "donne" or action == "mange":
                result = num1 - num2
            else: # "ajoute"
                result = num1 + num2
            return f"🤔 Logique : Il vous reste {result} {item}."
        
        # Ex: Si demain il pleut, que devrais-je faire ?
        rain_match = self.re_logical_rain.search(text)
        if rain_match:
            return "🤔 Prenez un parapluie et restez au sec !"
        
        return None
    
    def handle_file_analysis(self, text):
        """Analyse de fichiers texte"""
        file_match = self.re_file_analysis.search(text)
        if file_match:
            filename = file_match.group(1)
            if not os.path.exists(filename):
                return "⚠️ Fichier non trouvé."
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    content = f.read()
                words = len(content.split())
                lines = len(content.splitlines())
                chars = len(content)
                size = os.path.getsize(filename)
                mod_time = datetime.fromtimestamp(os.path.getmtime(filename)).strftime('%d/%m/%Y %H:%M')
                return f"📊 Analyse de {filename}: {lines} lignes, {words} mots, {chars} caractères, taille {size} bytes, modifié le {mod_time}."
            except Exception as e:
                return f"⚠️ Erreur d'analyse fichier: {e}"
        return None
    
    def handle_system_command(self, text):
        """Exécution de commandes locales sécurisées"""
        cmd_match = self.re_system_command.search(text)
        if cmd_match:
            cmd = cmd_match.group(1)
            # Sécurisé: limiter à certaines commandes
            allowed = ["ls", "pwd", "date", "echo"] # "echo" est sûr
            
            # Extraire la commande de base (ex: 'ls -l' -> 'ls')
            base_cmd = cmd.split()[0]
            
            if base_cmd in allowed:
                try:
                    # Utiliser shlex pour gérer les arguments
                    import shlex
                    args = shlex.split(cmd)
                    # Utiliser subprocess.run pour meilleure sécurité et capture
                    result = subprocess.run(args, capture_output=True, text=True, timeout=5, check=False)
                    output = result.stdout if result.stdout else result.stderr
                    return f"💻 Résultat : \n{Colors.BRIGHT_GREEN}{output}{Colors.RESET}"
                except Exception as e:
                    return f"⚠️ Erreur d'exécution: {e}"
            return "⚠️ Commande non autorisée."
        return None
    
    def handle_file_explorer(self, text):
        """Explorateur de fichiers en texte"""
        explore_match = self.re_file_explorer.search(text)
        if explore_match or "explorateur de fichiers" in text.lower():
            dir_path_str = explore_match.group(1).strip() if explore_match and explore_match.group(1) else "."
            dir_path = os.path.abspath(dir_path_str)

            if not os.path.isdir(dir_path):
                return "⚠️ Dossier non valide."
            try:
                files = os.listdir(dir_path)
                total_size = 0
                file_list = []
                dir_list = []
                
                for f in files:
                    full_path = os.path.join(dir_path, f)
                    if os.path.isfile(full_path):
                        try:
                            total_size += os.path.getsize(full_path)
                            file_list.append(f)
                        except OSError:
                            pass # Fichier inaccessible
                    elif os.path.isdir(full_path):
                        dir_list.append(f"{f}/")

                result = f"📂 Dossier : {dir_path}\n"
                result += f"Répertoires : {', '.join(dir_list)}\n"
                result += f"Fichiers : {', '.join(file_list)}\n"
                result += f"Taille totale (fichiers) : {total_size} bytes"
                return result
            except Exception as e:
                return f"⚠️ Erreur d'exploration: {e}"

        del_file_match = self.re_file_delete.search(text)
        if del_file_match:
            filename = del_file_match.group(1)
            if os.path.exists(filename) and os.path.isfile(filename):
                try:
                    os.remove(filename)
                    return f"🗑️ Fichier {filename} supprimé."
                except Exception as e:
                    return f"⚠️ Erreur suppression: {e}"
            return "⚠️ Fichier non trouvé ou est un dossier."
        
        return None
    
    def handle_system_logs(self, text):
        """Mini-logs systèmes"""
        if "logs systèmes" in text.lower():
            if psutil is None:
                return "⚠️ psutil non installé. (Essayez: pip install psutil)"
            try:
                cpu = psutil.cpu_percent()
                mem = psutil.virtual_memory().percent
                disk = psutil.disk_usage('/').percent
                uptime_sec = time.time() - psutil.boot_time()
                uptime = timedelta(seconds=int(uptime_sec))
                
                temp_str = "N/A"
                if hasattr(psutil, "sensors_temperatures"):
                    temps = psutil.sensors_temperatures()
                    if 'coretemp' in temps and temps['coretemp']:
                        temp_str = f"{temps['coretemp'][0].current}°C"
                    elif temps: # Prendre le premier disponible
                        first_sensor_key = list(temps.keys())[0]
                        if temps[first_sensor_key]:
                            temp_str = f"{temps[first_sensor_key][0].current}°C"

                return f"🖥️ CPU: {cpu}% | Mémoire: {mem}% | Disque: {disk}% | Temp: {temp_str} | Uptime: {uptime}"
            except Exception as e:
                return f"⚠️ Erreur logs: {e}"
        return None
    
    def handle_text_summary(self, text):
        """Résume un texte simple"""
        sum_match = self.re_text_summary.search(text)
        if sum_match:
            content = sum_match.group(1)
            # Simple résumé: premières 2 phrases
            sentences = re.split(r'[.!?]+', content)
            summary = ". ".join(s.strip() for s in sentences[:2] if s.strip())
            if summary:
                summary += "."
            return f"📝 Résumé : {Colors.BRIGHT_GREEN}{summary}{Colors.RESET}"
        return None
    
    def handle_world_time(self, text):
        """Horloge mondiale avec décalages fixes"""
        cities = {
            "new york": -5,
            "tokyo": 9,
            "london": 0,
            "paris": 1,
            "sydney": 10,
            "berlin": 1,
            "moscow": 3,
            "beijing": 8
        }
        time_match = self.re_world_time.search(text)
        if time_match:
            city = time_match.group(1).lower().strip()
            if city in cities:
                offset_hours = cities[city]
                offset = timedelta(hours=offset_hours)
                utc_time = datetime.now(timezone.utc)
                local_time = utc_time + offset
                return f"🕒 Heure à {city.capitalize()}: {local_time.strftime('%H:%M')} (UTC{offset_hours:+.0f})"
            return "❌ Ville non connue."
        return None
    
    def handle_financial_calc(self, text):
        """Calculs financiers simples"""
        savings_match = self.re_financial_calc.search(text)
        if savings_match:
            monthly = int(savings_match.group(1))
            period = int(savings_match.group(2))
            unit = savings_match.group(3)
            rate_percent = int(savings_match.group(4))
            
            rate = rate_percent / 100
            months = period * 12 if unit.startswith("an") else period
            total = 0
            
            for _ in range(months):
                total += monthly
                total *= (1 + rate / 12) # Intérêts composés mensuels
            
            return f"💰 Total épargné ({months} mois à {rate_percent}%) : {Colors.BRIGHT_GREEN}{total:.2f}€{Colors.RESET}"
        return None
    
    def handle_math(self, text):
        """Gère les calculs mathématiques"""
        for pattern_obj, func in self.math_ops.items():
            match = pattern_obj.search(text)
            if match:
                try:
                    num_groups = len(match.groups())
                    if num_groups == 0: # Cas 'pi'
                        result = func()
                    elif num_groups == 1:
                        result = func(int(match.group(1)))
                    else: # 2 groupes
                        result = func(int(match.group(1)), int(match.group(2)))
                    
                    return f"🧮 Résultat : {Colors.BRIGHT_GREEN}{result}{Colors.RESET}"
                
                except Exception as e:
                    return f"❌ Erreur math : {e}"
        return None
    
    def handle_time(self, text):
        """Gère les questions sur l'heure et la date"""
        text_lower = text.lower()
        if "quelle heure" in text_lower or (text_lower.strip() == "heure"):
            return f"🕒 Il est {datetime.now().strftime('%H:%M:%S')}"
        if "quelle date" in text_lower or (text_lower.strip() == "date"):
            return f"📅 Aujourd'hui est le {datetime.now().strftime('%d/%m/%Y')}"
        return None
    
    def handle_search_history(self, text):
        """Recherche dans l'historique"""
        search_match = self.re_search_history.search(text)
        if search_match:
            keyword = search_match.group(1).lower()
            results = [msg['user'] for msg in self.context if keyword in msg['user'].lower()]
            if results:
                return "\n".join(results)
            return "❌ Aucun résultat."
        return None
    
    def handle_export(self, text):
        """Export complet"""
        if "export tout" in text.lower():
            # Utiliser la même logique de conversion que save_memory
            reminders_to_export = []
            for rem in self.reminders:
                rem_copy = rem.copy()
                if isinstance(rem_copy.get('time'), datetime):
                    rem_copy['time'] = rem_copy['time'].isoformat()
                reminders_to_export.append(rem_copy)

            export_data = {
                'context': self.context,
                'notes': self.notes,
                'reminders': reminders_to_export,
                'preferences': self.user_preferences,
                'mode': self.mode,
                'level': self.level,
                'themed_memory': self.themed_memory
            }
            try:
                with open("freev_export.json", "w", encoding='utf-8') as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=2)
                return "📤 Export complet dans freev_export.json"
            except Exception as e:
                return f"⚠️ Erreur d'export: {e}"
        return None
    
    def handle_port_scanner(self, text):
        """Scanner de ports local basique"""
        if "scanner de ports" in text.lower():
            ports = [80, 443, 22, 21, 8080, 3306, 5432]  # Ports communs
            open_ports = []
            target = 'localhost'
            print(f"🔍 Scan des ports sur {target}...")
            for port in ports:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.5) # Rapide
                result = sock.connect_ex((target, port))
                if result == 0:
                    open_ports.append(port)
                sock.close()
            
            if open_ports:
                return f"🔍 Ports ouverts sur {target} : {', '.join(map(str, open_ports))}"
            return f"🔍 Aucun port ouvert détecté (parmi {len(ports)} testés) sur {target}."
        return None
    
    def handle_memory_theme(self, text):
        """Mémoire contextuelle thématique"""
        mem_match = self.re_memory_theme.search(text)
        if mem_match:
            theme = mem_match.group(1).strip()
            value = mem_match.group(2).strip()
            self.themed_memory[theme] = value
            self.save_memory()
            return f"🧠 Noté : {theme} = {value}"
        return None
    
    def handle_level(self, text):
        """Affiche le niveau"""
        if "mon niveau freev" in text.lower():
            return f"📈 Votre niveau avec Freev : {self.level}"
        return None
    
    def get_level_bonus(self):
        """Bonus selon niveau"""
        if self.level > 10:
            return " (Niveau avancé !)"
        return ""
    
    def evolve_character(self):
        """Évolution du caractère"""
        if random.random() < 0.1:  # 10% chance par interaction
            self.current_character_index = (self.current_character_index + 1) % len(self.character_evolution)
            self.mode = self.character_evolution[self.current_character_index]
            self.save_memory()
    
    def handle_evolution(self, text):
        """Mode évolution personnalité"""
        if "évolution personnalité" in text.lower():
            self.evolve_character()
            return f"🔄 Personnalité évoluée vers {self.mode} !"
        return None
    
    def handle_philosophy_day(self, text):
        """Philosophie du jour"""
        if "philosophie du jour" in text.lower():
            quote = random.choice(self.responses["creator_quotes"])
            return f"🤔 Philosophie : {quote}"
        return None
    
    def handle_fusion_user(self, text):
        """Fusion utilisateur"""
        if "fusion utilisateur" in text.lower():
            return "🔄 Mode fusion activé. Je vais adopter votre style."
        # Dans generate_response, utiliser user_style si possible
        return None
    
    def handle_delete_history(self, text):
        """Supprime historique"""
        if "supprime historique" in text.lower():
            self.context = []
            self.save_memory()
            return "🗑️ Historique supprimé."
        return None
    
    def handle_show_memory(self, text):
        """Affiche mémoire"""
        if "affiche mémoire" in text.lower():
            if not self.themed_memory:
                return "🧠 Mémoire thématique vide."
            return str(self.themed_memory)
        return None

    # --- NOUVELLES FONCTIONNALITÉS V2.1 ---

    def handle_mini_editor(self, text):
        """Crée ou ajoute à un fichier"""
        cree_match = self.re_cree_fichier.search(text)
        if cree_match:
            filename = cree_match.group(1).strip()
            content = cree_match.group(2)
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)
                return f"💾 Fichier '{filename}' créé."
            except Exception as e:
                return f"⚠️ Erreur création fichier: {e}"

        ajoute_match = self.re_ajoute_fichier.search(text)
        if ajoute_match:
            filename = ajoute_match.group(1).strip()
            content = ajoute_match.group(2)
            try:
                with open(filename, 'a', encoding='utf-8') as f:
                    f.write("\n" + content)
                return f"💾 Contenu ajouté à '{filename}'."
            except Exception as e:
                return f"⚠️ Erreur ajout fichier: {e}"
        return None

    def handle_network_info(self, text):
        """Donne l'IP locale et le nom d'hôte"""
        if self.re_ip_locale.search(text):
            try:
                # Méthode standard pour trouver l'IP locale
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.settimeout(0)
                s.connect(('8.8.8.8', 80)) # IP Google DNS
                ip = s.getsockname()[0]
                s.close()
                return f"🌐 Votre IP locale est : {Colors.BRIGHT_GREEN}{ip}{Colors.RESET}"
            except Exception:
                # Plan B (peut retourner 127.0.0.1)
                try:
                    ip = socket.gethostbyname(socket.gethostname())
                    return f"🌐 Votre IP (plan B) est : {Colors.BRIGHT_GREEN}{ip}{Colors.RESET}"
                except Exception as e:
                    return f"⚠️ Impossible de déterminer l'IP locale: {e}"
        
        if self.re_nom_hote.search(text):
            try:
                hostname = socket.gethostname()
                return f"🖥️ Votre nom d'hôte est : {Colors.BRIGHT_GREEN}{hostname}{Colors.RESET}"
            except Exception as e:
                return f"⚠️ Impossible de déterminer le nom d'hôte: {e}"
        return None

    def handle_file_compare(self, text):
        """Compare deux fichiers texte"""
        match = self.re_compare_fichiers.search(text)
        if match:
            file1_path = match.group(1)
            file2_path = match.group(2)
            
            if not os.path.exists(file1_path) or not os.path.exists(file2_path):
                return "⚠️ Un ou les deux fichiers n'existent pas."
            try:
                with open(file1_path, 'r', encoding='utf-8') as f1:
                    file1_lines = f1.readlines()
                with open(file2_path, 'r', encoding='utf-8') as f2:
                    file2_lines = f2.readlines()
                
                diff = difflib.unified_diff(file1_lines, file2_lines, fromfile=file1_path, tofile=file2_path, lineterm='')
                diff_output = '\n'.join(diff)
                
                if not diff_output:
                    return "✅ Fichiers identiques."
                
                return f"🔄 Différences entre les fichiers:\n{Colors.BRIGHT_YELLOW}{diff_output}{Colors.RESET}"
            except Exception as e:
                return f"⚠️ Erreur de comparaison: {e}"
        return None

    def handle_process_info(self, text):
        """Liste les processus (via psutil)"""
        if self.re_liste_processus.search(text):
            if psutil is None:
                return "⚠️ psutil non installé. (Essayez: pip install psutil)"
            try:
                procs = []
                for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                    procs.append(p.info)
                
                # Trier par CPU
                top_cpu = sorted(procs, key=lambda p: p['cpu_percent'], reverse=True)[:5]
                
                result = f"{Colors.BRIGHT_CYAN}📊 Top 5 Processus (CPU):{Colors.RESET}\n"
                result += "PID\t%CPU\t%MEM\tNom\n"
                result += "-----------------------------------\n"
                for p in top_cpu:
                    result += f"{p['pid']}\t{p['cpu_percent']:.1f}\t{p['memory_percent']:.1f}\t{p['name']}\n"
                return result
            except Exception as e:
                return f"⚠️ Erreur psutil: {e}"
        return None

    def _tictactoe_print_board(self, board):
        """Affiche le plateau de morpion"""
        res = "\n"
        for i, row in enumerate(board):
            res += " " + " | ".join(f"{Colors.BRIGHT_GREEN}{c}{Colors.RESET}" if c == 'X' else f"{Colors.BRIGHT_YELLOW}{c}{Colors.RESET}" if c == 'O' else c for c in row) + "\n"
            if i < 2:
                res += "---|---|---\n"
        return res

    def _tictactoe_check_win(self, board, player):
        """Vérifie si un joueur a gagné"""
        # Lignes et colonnes
        for i in range(3):
            if all(board[i][j] == player for j in range(3)) or \
               all(board[j][i] == player for j in range(3)):
                return True
        # Diagonales
        if all(board[i][i] == player for i in range(3)) or \
           all(board[i][2-i] == player for i in range(3)):
            return True
        return False

    def _tictactoe_ai_move(self, board):
        """IA simple pour le morpion"""
        empty_cells = [(r, c) for r in range(3) for c in range(3) if board[r][c] == ' ']
        if not empty_cells:
            return None

        # 1. Gagner
        for r, c in empty_cells:
            board[r][c] = 'O'
            if self._tictactoe_check_win(board, 'O'):
                return (r, c)
            board[r][c] = ' ' # Annuler
        
        # 2. Bloquer
        for r, c in empty_cells:
            board[r][c] = 'X'
            if self._tictactoe_check_win(board, 'X'):
                board[r][c] = 'O' # Placer le coup bloquant
                return (r, c)
            board[r][c] = ' ' # Annuler

        # 3. Aléatoire
        return random.choice(empty_cells)

    def handle_tictactoe(self, text):
        """Gère le jeu du morpion"""
        if self.re_joue_morpion.search(text):
            board = [[' ' for _ in range(3)] for _ in range(3)]
            self.game_state['tictactoe'] = {
                'board': board,
                'turn': 'X' # L'utilisateur commence
            }
            self.save_memory()
            return f"🏁 Morpion lancé ! Vous êtes les {Colors.BRIGHT_GREEN}X{Colors.RESET}. À vous de jouer.\n" + \
                   f"Utilisez `place X en L,C` (Ligne,Colonne de 0 à 2)\n" + \
                   self._tictactoe_print_board(board)

        if 'tictactoe' in self.game_state:
            state = self.game_state['tictactoe']
            board = state['board']
            
            # Tour du joueur
            match = self.re_place_morpion.search(text)
            if match and state['turn'] == 'X':
                player = match.group(1).upper()
                if player != 'X':
                    return "C'est au tour de X."
                
                try:
                    r, c = int(match.group(2)), int(match.group(3))
                    if not (0 <= r <= 2 and 0 <= c <= 2):
                        return "❌ Coordonnées invalides (0-2)."
                    if board[r][c] != ' ':
                        return "❌ Case déjà prise !"
                except ValueError:
                    return "❌ Format invalide. Ex: `place X en 1,2`"
                
                board[r][c] = 'X'
                if self._tictactoe_check_win(board, 'X'):
                    del self.game_state['tictactoe']
                    self.save_memory()
                    return f"🎉 Vous avez gagné !\n{self._tictactoe_print_board(board)}"
                
                state['turn'] = 'O'
                
                # Tour de l'IA
                ai_move = self._tictactoe_ai_move(board)
                if ai_move is None:
                    del self.game_state['tictactoe']
                    self.save_memory()
                    return f"🤝 Égalité !\n{self._tictactoe_print_board(board)}"
                
                r_ai, c_ai = ai_move
                board[r_ai][c_ai] = 'O'
                
                response = f"J'ai joué O en {r_ai},{c_ai}.\n{self._tictactoe_print_board(board)}"
                
                if self._tictactoe_check_win(board, 'O'):
                    del self.game_state['tictactoe']
                    self.save_memory()
                    return f"😞 J'ai gagné !\n{self._tictactoe_print_board(board)}"
                
                state['turn'] = 'X'
                self.save_memory()
                return response
            elif state['turn'] == 'O':
                return "C'est à mon tour, mais j'attends votre coup."
            elif match and state['turn'] != 'X':
                 return "Ce n'est pas votre tour."

        return None

    def handle_guess_number(self, text):
        """Gère le jeu 'Devinez le Nombre'"""
        if self.re_jeu_devine_nombre.search(text):
            target = random.randint(1, 100)
            self.game_state['guess_number'] = {
                'target': target,
                'tries': 0
            }
            self.save_memory()
            return "🎲 J'ai choisi un nombre entre 1 et 100. À vous de deviner !"

        if 'guess_number' in self.game_state:
            try:
                guess = int(text.strip())
                state = self.game_state['guess_number']
                state['tries'] += 1
                
                if guess < state['target']:
                    self.save_memory()
                    return "C'est plus grand ! ⬆️"
                elif guess > state['target']:
                    self.save_memory()
                    return "C'est plus petit ! ⬇️"
                else:
                    tries = state['tries']
                    del self.game_state['guess_number']
                    self.save_memory()
                    return f"🎉 Bravo ! Vous avez trouvé {state['target']} en {tries} essais."
            except ValueError:
                # Ce n'est pas un nombre, donc ce n'est pas une tentative
                return None
        
        return None

    def handle_ascii_art(self, text):
        """Affiche de l'ASCII art"""
        match = self.re_dessine.search(text)
        if match:
            art_name = match.group(1).lower()
            if art_name in self.ascii_art:
                art = "\n".join(self.ascii_art[art_name])
                return f"Voici un {art_name}:\n{Colors.BRIGHT_GREEN}{art}{Colors.RESET}"
            return f"❌ Je ne sais pas dessiner un '{art_name}'. Essayez 'chat', 'coeur' ou 'python'."
        return None

    def handle_calendar(self, text):
        """Affiche un calendrier"""
        match = self.re_calendrier.search(text)
        if match:
            month_str = match.group(1)
            year_str = match.group(2)
            
            now = datetime.now()
            year = int(year_str) if year_str else now.year
            
            month_map = {
                'janvier': 1, 'fevrier': 2, 'mars': 3, 'avril': 4, 'mai': 5, 'juin': 6,
                'juillet': 7, 'aout': 8, 'septembre': 9, 'octobre': 10, 'novembre': 11, 'decembre': 12
            }
            
            month = month_map.get(month_str.lower()) if month_str else now.month
            
            if month is None:
                return "❌ Mois non reconnu."
            
            try:
                cal = calendar.month(year, month)
                return f"📅 Calendrier pour {month_str or now.strftime('%B')} {year}:\n{Colors.BRIGHT_WHITE}{cal}{Colors.RESET}"
            except Exception as e:
                return f"⚠️ Erreur de calendrier: {e}"
        return None

    def handle_keyword_extraction(self, text):
        """Extrait les mots-clés d'un texte"""
        match = self.re_mots_cles.search(text)
        if match:
            content = match.group(1).lower()
            words = re.findall(r'\b\w+\b', content)
            
            # Filtrer les mots vides
            keywords = [word for word in words if word not in self.stop_words]
            
            if not keywords:
                return "Aucun mot-clé pertinent trouvé."
            
            keyword_counts = Counter(keywords).most_common(5)
            result = "🔑 Mots-clés principaux :\n"
            result += "\n".join(f"  • {word} (x{count})" for word, count in keyword_counts)
            return result
        return None

    def handle_text_manipulator(self, text):
        """Outils simples de manipulation de texte"""
        match_inv = self.re_inverse_texte.search(text)
        if match_inv:
            content = match_inv.group(1)
            return f"🔄 Inverse : {Colors.BRIGHT_GREEN}{content[::-1]}{Colors.RESET}"

        match_count = self.re_compte_texte.search(text)
        if match_count:
            char = match_count.group(1).lower()
            content = match_count.group(2).lower()
            count = content.count(char)
            return f"🔢 Le caractère '{char}' apparaît {Colors.BRIGHT_GREEN}{count}{Colors.RESET} fois."

        match_maj = self.re_convertir_maj.search(text)
        if match_maj:
            content = match_maj.group(1)
            return f"⬆️ {Colors.BRIGHT_GREEN}{content.upper()}{Colors.RESET}"
            
        return None

    # --- FIN DES NOUVELLES FONCTIONNALITÉS ---

    def generate_response(self, user_input):
        """Génère une réponse intelligente"""
        try:
            self.context.append({"user": user_input, "time": datetime.now().isoformat()})
            self.user_style.extend(user_input.split())  # Apprendre style
            self.level += 1  # Augmenter niveau
            self.evolve_character()  # Évolution possible
        except Exception as e:
            print(f"⚠ Erreur interne (contexte): {e}")
            return "⚠ Une erreur interne est survenue, redémarre Freev."
        
        # Extraction du nom
        name = self.extract_name(user_input)
        if name and not self.user_name:
            self.user_name = name
            self.save_memory()
            return f"Enchanté {Colors.BRIGHT_MAGENTA}{name}{Colors.RESET} ! Je me souviendrai de votre nom. ✨"
        
        # Vérifier les fonctionnalités spéciales
        # Ordre optimisé : les plus courants (notes, rappels, math, temps) en premier
        # NOUVEAU: Ajout des nouveaux handlers
        handlers = [
            # Jeux (priorité haute pour les commandes en cours de jeu)
            self.handle_hangman,
            self.handle_tictactoe,
            self.handle_guess_number,
            self.handle_riddle_timed,
            # Gestion perso
            self.handle_notes,
            self.handle_reminders,
            self.handle_calendar,
            # Outils rapides
            self.handle_math,
            self.handle_time,
            self.handle_password_gen,
            self.handle_translation,
            self.handle_timer,
            self.handle_unit_conversion, # Gère aussi devise
            self.handle_bmi,
            # Jeux (initiation)
            self.handle_rps_game,
            self.handle_coin_flip,
            self.handle_dice_roll,
            self.handle_recipe_suggestion,
            self.handle_simple_quiz,
            self.handle_moral_choice,
            self.handle_interactive_story,
            # Codage & Crypto
            self.handle_base64,
            self.handle_morse,
            self.handle_binary,
            self.handle_caesar,
            self.handle_vigenere,
            self.handle_code_generation,
            # Outils Texte
            self.handle_text_analysis,
            self.handle_palindrome,
            self.handle_text_summary,
            self.handle_keyword_extraction,
            self.handle_text_manipulator,
            self.handle_ascii_art,
            # Outils Maths/Logique
            self.handle_random_num,
            self.handle_fibonacci,
            self.handle_prime_check,
            self.handle_equation_solver,
            self.handle_logical_reasoning,
            self.handle_financial_calc,
            # Outils Système & Fichiers
            self.handle_mini_editor,
            self.handle_file_analysis,
            self.handle_file_compare,
            self.handle_system_command,
            self.handle_file_explorer,
            self.handle_system_logs,
            self.handle_process_info,
            self.handle_network_info,
            self.handle_port_scanner,
            # Méta (Freev)
            self.handle_history,
            self.handle_mode_change,
            self.handle_simulator,
            self.handle_world_time,
            self.handle_search_history,
            self.handle_export,
            self.handle_memory_theme,
            self.handle_level,
            self.handle_evolution,
            self.handle_philosophy_day,
            self.handle_fusion_user,
            self.handle_delete_history,
            self.handle_show_memory
        ]
        
        for handler in handlers:
            try:
                result = handler(user_input)
                if result is not None:
                    # Si c'est un jeu, ne pas continuer
                    if handler in [self.handle_hangman, self.handle_tictactoe, self.handle_guess_number, self.handle_riddle_timed]:
                        if 'game_state' in self.game_state:
                             return result # Retourner la réponse du jeu
                    else:
                        return result # Retourner la réponse de l'outil
            except Exception as e:
                print(f"Erreur handler {handler.__name__}: {e}")
                return "❌ Oups, j'ai rencontré une erreur avec cette commande."

        
        user_input_lower = user_input.lower()
        
        # Commandes spéciales (faits, citations)
        if any(kw in user_input_lower for kw in ["fait", "fact", "le sais-tu", "le savais-tu"]):
            return self.get_random_fact()
        
        if any(kw in user_input_lower for kw in ["citation", "quote", "inspire"]):
            return self.get_quote()
        
        # Réponses catégorisées
        category = self.categorize_input(user_input)
        
        if category in self.responses:
            response = random.choice(self.responses[category])
        else:
            # Ne pas répondre si c'est un nombre (probable tentative de jeu)
            if 'guess_number' in self.game_state and user_input.strip().isdigit():
                 return "❌ Ce n'est pas ça. Essayez encore."

            response = random.choice([
                "Je comprends. 🤔", 
                "Intéressant ! Dites-m'en plus.", 
                "Hmm, je réfléchis à ça.", 
                "Pouvez-vous reformuler ?", 
                "Curieux sujet !"
            ])
        
        # Adapter au mode
        if self.mode == "fun":
            response += " Haha ! 😄"
        elif self.mode == "dark":
            response += " ...dans les ténèbres."
        elif self.mode == "philosophique":
            response += " Mais qu'est-ce que cela signifie vraiment ?"
        elif self.mode == "gentil":
            response += " Avec amour ! 💕"
        elif self.mode == "cynique":
            response += " Comme si ça changeait quelque chose."
        elif self.mode == "motivant":
            response += " Vous pouvez le faire ! 💪"
        
        # Personnalisation
        if self.user_name and random.random() > 0.7:
            response = f"{response} {Colors.BRIGHT_MAGENTA}{self.user_name}{Colors.RESET}."
        
        # Analyse sentiment et détection ton émotionnel
        sentiment = self.analyze_sentiment(user_input)
        if sentiment == "negative":
            if "marre" in user_input_lower: self.mode = "soutien"
            response += " Je suis là si vous voulez parler. 💙"
        elif sentiment == "positive":
            if "let’s go" in user_input_lower: self.mode = "motivation"
            response += " Ravi de voir votre bonne humeur ! 😊"
        
        # Intégrer citations personnelles (philosophie de Trystan)
        if random.random() < 0.2:
            quote = random.choice(self.responses["creator_quotes"])
            response += f" Comme dit : '{quote}'"
        
        # Fusion utilisateur : utiliser mots user
        if len(self.user_style) > 10 and random.random() < 0.1:
            user_word = random.choice(self.user_style)
            # Éviter les mots trop courts/communs
            if len(user_word) > 3 and user_word.lower() not in self.stop_words:
                response += f" ...{user_word}..."
        
        # Mémoire thématique
        for theme, value in self.themed_memory.items():
            if theme in user_input_lower:
                response += f" (Je me souviens : {theme} = {value})"
        
        return response
    
    def show_help(self):
        """Affiche l'aide complète (MISE À JOUR V2.1)"""
        help_text = f"""
{Colors.BRIGHT_CYAN}╔═══════════════════ AIDE FREEV (v2.1) ═══════════════════╗{Colors.RESET}

{Colors.BRIGHT_YELLOW}🎯 Fonctionnalités principales:{Colors.RESET}

  {Colors.BRIGHT_MAGENTA}💬 Conversation{Colors.RESET}
    • Discussion naturelle
    • Reconnaissance du nom ("je m'appelle...")
    • Analyse de sentiment

  {Colors.BRIGHT_MAGENTA}🧮 Calculs{Colors.RESET}
    • Opérations : 5 + 3, 10 * 2, 15 / 3
    • Puissance : 2 ^ 8
    • Racine carrée : racine de 16
    • Trigonométrie : sin(30), cos(45), tan(60)
    • Logarithme : log(100), ln(5)
    • Exponentielle : exp(2)
    • Factorielle : factorielle de 5
    • Pi : pi

  {Colors.BRIGHT_MAGENTA}📝 Notes{Colors.RESET}
    • "note: acheter du pain"
    • "mes notes" - voir toutes les notes
    • "supprime note 1" - supprimer
    • "fait note 1" - marquer comme faite
    • "cherche note keyword" - recherche
    • "export notes" - export en txt

  {Colors.BRIGHT_MAGENTA}⏰ Organisation{Colors.RESET}
    • "rappel: rdv dans 10 minutes"
    • "rappel: appeler maman à 18 heures"
    • "mes rappels" - voir tous
    • "supprime rappel 1" - supprimer
    • "affiche calendrier" (mois actuel)
    • "calendrier decembre 2025"
    • "minuteur 5 minutes"

  {Colors.BRIGHT_MAGENTA}🔐 Sécurité{Colors.RESET}
    • "mot de passe" - génère un mdp (12 chars)
    • "password 20" - mdp de 20 caractères

  {Colors.BRIGHT_MAGENTA}🌍 Outils Texte & Traduction{Colors.RESET}
    • "traduis hello" (FR/EN/ES/DE/IT)
    • "analyse 'ton texte ici'" (avec "")
    • "résume ce texte : "..." " (avec "")
    • "mots cles de "long texte ici""
    • "inverse "Bonjour""
    • "compte "a" dans "une phrase""
    • "convertir en majuscule "petit texte""

  {Colors.BRIGHT_MAGENTA}📏 Conversions{Colors.RESET}
    • "convert 10 km to miles"
    • "convert 20 celsius to fahrenheit"
    • "convert 100 eur to usd" (taux approx.)
    • "convert 50 kg to lbs"

  {Colors.BRIGHT_MAGENTA}🩺 Santé{Colors.RESET}
    • "calcule imc poids 70 taille 1.75"

  {Colors.BRIGHT_MAGENTA}🎲 Jeux{Colors.RESET}
    • "pierre feuille ciseaux" (puis "pierre")
    • "lance pièce" - pile ou face
    • "lance dé" (ou "lance dé 20")
    • "quiz" - question aléatoire
    • "nombre aléatoire 1 100"
    • "palindrome radar"
    • "fibonacci 10"
    • "premier 17"
    • "joue au pendu"
    • "joue au morpion" (puis "place X en 0,1")
    • "jeu devine le nombre" (puis "50")
    • "simulateur de choix moraux"
    • "raconte une histoire interactive"
    • "devinette chronométrée"
    • "simule un hacker" (ou scientifique, philosophe)

  {Colors.BRIGHT_MAGENTA}🔢 Codage{Colors.RESET}
    • "encode base64 hello"
    • "decode base64 aGVsbG8="
    • "encode morse SOS"
    • "decode morse ...---..."
    • "encode binary hello"
    • "decode binary 01101000..."
    • "convertis en binaire 25"
    • "encode caesar hello" (shift 3)
    • "encode vigenere bonjour" (clé: CLE)

  {Colors.BRIGHT_MAGENTA}🍲 Recettes{Colors.RESET}
    • "suggère recette" - idée simple

  {Colors.BRIGHT_MAGENTA}💻 Programmation{Colors.RESET}
    • "donne moi du code avancé" - exemple Python pro
    • "code pour décorateur"
    • "exemple multithreading"

  {Colors.BRIGHT_MAGENTA}✨ Divertissement{Colors.RESET}
    • "blague" - raconte une blague
    • "fait" - fait amusant
    • "citation" - citation motivante
    • "motivation" - message d'encouragement
    • "dessine un chat" (ou 'coeur', 'python')

  {Colors.BRIGHT_MAGENTA}🕐 Date & Heure{Colors.RESET}
    • "quelle heure"
    • "quelle date"
    • "heure à new york"

  {Colors.BRIGHT_MAGENTA}🧰 Outils Système & Fichiers{Colors.RESET}
    • "mon ip locale"
    • "mon nom d'hote"
    • "logs systèmes" (CPU, RAM... nécessite 'psutil')
    • "liste processus" (Top 5 CPU, nécessite 'psutil')
    • "analyse fichier notes.txt"
    • "cree fichier test.txt "mon contenu""
    • "ajoute a test.txt "autre ligne""
    • "compare fichier1.txt fichier2.txt"
    • "exécute ls -l" (Commandes : ls, pwd, date, echo)
    • "explore dossier" (ou "explore dossier /chemin")
    • "supprime fichier test.txt"
    • "scanner de ports" (teste localhost)

  {Colors.BRIGHT_MAGENTA}🤖 Méta-Commandes (Freev){Colors.RESET}
    • "historique" - voir discussions
    • "change de personnalité fun/dark/..."
    • "résous 2x + 3 = 9" (ou 1x^2+5x+6=0)
    • "chiffre chanceux"
    • "épargne 50€/mois pendant 2 ans à 3%"
    • "recherche dans historique ‘math’" (avec ‘’)
    • "export tout" (sauvegarde freev_export.json)
    • "souviens-toi que ma couleur préférée c’est bleu"
    • "mon niveau freev"
    • "évolution personnalité"
    • "philosophie du jour"
    • "fusion utilisateur"
    • "supprime historique"
    • "affiche mémoire" (mémoire thématique)

{Colors.BRIGHT_YELLOW}⌨️ Commandes système:{Colors.RESET}
  {Colors.CYAN}help{Colors.RESET}      - Afficher cette aide
  {Colors.CYAN}stats{Colors.RESET}     - Statistiques de session
  {Colors.CYAN}reset{Colors.RESET}     - Effacer la mémoire (demande confirmation)
  {Colors.CYAN}quit/exit{Colors.RESET} - Quitter Freev

{Colors.BRIGHT_CYAN}╚═══════════════════════════════════════════════════╝{Colors.RESET}
        """
        print(help_text)
    
    def show_stats(self):
        """Affiche les statistiques"""
        print(f"\n{Colors.BRIGHT_CYAN}╔═══════════════ STATISTIQUES ═══════════════╗{Colors.RESET}")
        print(f"{Colors.YELLOW}Messages échangés:{Colors.RESET} {len(self.context)}")
        
        if self.user_name:
            print(f"{Colors.YELLOW}Utilisateur:{Colors.RESET} {Colors.BRIGHT_MAGENTA}{self.user_name}{Colors.RESET}")
        
        print(f"{Colors.YELLOW}Niveau Freev:{Colors.RESET} {self.level}")
        print(f"{Colors.YELLOW}Mode actuel:{Colors.RESET} {self.mode}")
        print(f"{Colors.YELLOW}Notes sauvegardées:{Colors.RESET} {len(self.notes)}")
        print(f"{Colors.YELLOW}Rappels sauvegardés:{Colors.RESET} {len(self.reminders)}")
        print(f"{Colors.YELLOW}Mémoire thématique:{Colors.RESET} {len(self.themed_memory)} éléments")
        
        if self.context:
            try:
                first = datetime.fromisoformat(self.context[0]['time'])
                duration = datetime.now() - first
                print(f"{Colors.YELLOW}Durée de la session:{Colors.RESET} {duration.seconds // 60}m {duration.seconds % 60}s")
            except:
                pass # Erreur de format de date
        
        # Statistiques de sentiment
        sentiments = [self.analyze_sentiment(msg['user']) for msg in self.context]
        sentiment_count = Counter(sentiments)
        print(f"{Colors.YELLOW}Sentiment général:{Colors.RESET}")
        print(f"  😊 Positif: {sentiment_count.get('positive', 0)}")
        print(f"  😐 Neutre: {sentiment_count.get('neutral', 0)}")
        print(f"  😔 Négatif: {sentiment_count.get('negative', 0)}")
        
        print(f"{Colors.BRIGHT_CYAN}╚═════════════════════════════════════════════╝{Colors.RESET}\n")
    
    def run(self):
        """Lance la boucle principale"""
        self.show_banner()
        
        if self.user_name:
            welcome = f"Bon retour {self.user_name} ! 👋"
            print(f"{Colors.BRIGHT_GREEN}{welcome}{Colors.RESET}\n")
        
        while True:
            try:
                prompt = f"{Colors.BRIGHT_BLUE}┌─[{Colors.BRIGHT_WHITE}Vous{Colors.BRIGHT_BLUE}]{Colors.RESET}\n{Colors.BRIGHT_BLUE}└──➤{Colors.RESET} "
                user_input = input(prompt).strip()
                
                if not user_input:
                    continue
                
                user_input_lower = user_input.lower()

                if user_input_lower in ['quit', 'exit', 'q']:
                    self.type_effect("\n✨ Au revoir ! À bientôt !", Colors.BRIGHT_CYAN, 0.03)
                    self.save_memory()
                    break
                
                if user_input_lower == 'reset':
                    confirm = input(f"{Colors.YELLOW}⚠️ Confirmer la suppression de la mémoire ? (o/n): {Colors.RESET}")
                    if confirm.lower() in ['o', 'oui', 'y', 'yes']:
                        self.context = []
                        self.user_name = None
                        self.notes = []
                        self.reminders = []
                        self.mode = "normal"
                        self.game_state = {}
                        self.level = 0
                        self.themed_memory = {}
                        self.user_style = []
                        self.current_character_index = 0
                        if self.memory_file.exists():
                            try:
                                self.memory_file.unlink()
                            except OSError as e:
                                print(f"Erreur suppression fichier: {e}")
                        print(f"\n{Colors.BRIGHT_GREEN}✓ Mémoire effacée !{Colors.RESET}\n")
                    continue
                
                if user_input_lower == 'help':
                    self.show_help()
                    continue
                
                if user_input_lower == 'stats':
                    self.show_stats()
                    continue
                
                self.show_thinking()
                
                response = self.generate_response(user_input)
                
                if response:
                    print(f"\n{Colors.BRIGHT_MAGENTA}┌─[{Colors.BRIGHT_WHITE}Freev{Colors.BRIGHT_MAGENTA}]{Colors.RESET}")
                    print(f"{Colors.BRIGHT_MAGENTA}└──➤{Colors.RESET} {response}\n")
                
                # Sauvegarde périodique
                if len(self.context) % 5 == 0:
                    self.save_memory()
                
            except KeyboardInterrupt:
                print(f"\n\n{Colors.BRIGHT_CYAN}✨ Au revoir !{Colors.RESET}")
                self.save_memory()
                break
            except Exception as e:
                print(f"\n{Colors.BRIGHT_RED}⚠ Erreur: {e}{Colors.RESET}\n")

if __name__ == "__main__":
    freev = Freev()
    freev.run()
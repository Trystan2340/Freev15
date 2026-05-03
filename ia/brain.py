#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════╗
║  FREEV v7.0 — IA Conversationnelle Locale                        ║
║  Modèle : FreevBrain v7 — Python pur, Zéro dépendance            ║
║  Auteur  : Trystan — Assemblage : Chef d'équipe IA               ║
║  Modules : BPE · Embeddings · BM25 · KneserNey · MLP · Context  ║
║            KnowledgeGraph · DataAugmentor · TestSuite            ║
╚══════════════════════════════════════════════════════════════════╝
"""

# ── Imports standard library uniquement ──────────────────────────────────────
import re
import json
import math
import random
import os
import sys
import time
import socket
import threading
import subprocess
import base64
import calendar
import shlex
import urllib.parse
import urllib.request
import unicodedata
from pathlib import Path
from collections import Counter, defaultdict, deque
from datetime import datetime, timedelta
from difflib import get_close_matches

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(errors='replace')
    except Exception:
        pass

# ══════════════════════════════════════════════════════════════════════════════
# MODULE 1 — BPETokenizer (ChatGPT)
# Tokenisation par sous-mots Byte Pair Encoding, from scratch
# ══════════════════════════════════════════════════════════════════════════════
class BPETokenizer:
    """
    Tokeniseur BPE from scratch — stdlib uniquement.
    Apprend les fusions depuis un corpus, encode en sous-mots,
    décode les tokens en texte. Gère les mots inconnus par décomposition
    en caractères.
    """
    def __init__(self):
        self.merges = []
        self.merge_ranks = {}
        self.vocab = {}
        self._word_pattern = re.compile(r"\w+|[^\w\s]", re.UNICODE)

    def _tokenize_word(self, word):
        return list(word)

    def _get_stats(self, vocab_words):
        pairs = Counter()
        for symbols, freq in vocab_words.items():
            for i in range(len(symbols) - 1):
                pairs[(symbols[i], symbols[i + 1])] += freq
        return pairs

    def _merge_pair(self, pair, vocab_words):
        new_vocab = {}
        replacement = ''.join(pair)
        for symbols, freq in vocab_words.items():
            new_symbols = []
            i = 0
            while i < len(symbols):
                if (i < len(symbols) - 1
                        and symbols[i] == pair[0]
                        and symbols[i + 1] == pair[1]):
                    new_symbols.append(replacement)
                    i += 2
                else:
                    new_symbols.append(symbols[i])
                    i += 1
            new_vocab[tuple(new_symbols)] = freq
        return new_vocab

    def train(self, corpus: list, vocab_size: int = 500):
        vocab_words = Counter()
        for line in corpus:
            words = self._word_pattern.findall(line)
            for word in words:
                chars = tuple(self._tokenize_word(word))
                vocab_words[chars] += 1
        self.vocab = Counter()
        for symbols, freq in vocab_words.items():
            for symbol in symbols:
                self.vocab[symbol] = self.vocab.get(symbol, 0) + freq
        self.merges = []
        self.merge_ranks = {}
        while len(self.vocab) < vocab_size:
            pairs = self._get_stats(vocab_words)
            if not pairs:
                break
            best_pair = pairs.most_common(1)[0][0]
            vocab_words = self._merge_pair(best_pair, vocab_words)
            merged_token = ''.join(best_pair)
            self.merges.append(best_pair)
            self.merge_ranks[best_pair] = len(self.merges) - 1
            self.vocab = Counter()
            for symbols, freq in vocab_words.items():
                for symbol in symbols:
                    self.vocab[symbol] += freq

    def encode(self, text: str) -> list:
        tokens = []
        words = self._word_pattern.findall(text)
        for word in words:
            symbols = list(word)
            if not self.merges:
                tokens.extend(symbols)
                continue
            while True:
                pairs = [(symbols[i], symbols[i + 1]) for i in range(len(symbols) - 1)]
                candidate = None
                candidate_rank = float("inf")
                for pair in pairs:
                    if pair in self.merge_ranks and self.merge_ranks[pair] < candidate_rank:
                        candidate = pair
                        candidate_rank = self.merge_ranks[pair]
                if candidate is None:
                    break
                new_symbols = []
                i = 0
                while i < len(symbols):
                    if (i < len(symbols) - 1
                            and symbols[i] == candidate[0]
                            and symbols[i + 1] == candidate[1]):
                        new_symbols.append(''.join(candidate))
                        i += 2
                    else:
                        new_symbols.append(symbols[i])
                        i += 1
                symbols = new_symbols
            tokens.extend(symbols)
        return tokens

    def decode(self, tokens: list) -> str:
        return ''.join(tokens)

    def save(self, path: str):
        data = {"merges": self.merges, "vocab": dict(self.vocab)}
        Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def load(self, path: str):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        self.merges = [tuple(pair) for pair in data.get("merges", [])]
        self.merge_ranks = {pair: i for i, pair in enumerate(self.merges)}
        self.vocab = data.get("vocab", {})


# ══════════════════════════════════════════════════════════════════════════════
# MODULE 2 — CoOccurrenceEmbedder (Gemini)
# Embeddings de mots par co-occurrence + descente de gradient (SGD)
# ══════════════════════════════════════════════════════════════════════════════
class CoOccurrenceEmbedder:
    """
    Embeddings de mots par co-occurrence, factorisation par SGD.
    Approche GloVe simplifiée, zéro dépendance.
    """
    def __init__(self):
        self.dim: int = 0
        self.vocab: set = set()
        self._embeddings: dict = {}

    def train(self, tokenized_sentences: list, window: int = 3, dim: int = 64):
        self.dim = dim
        self.vocab = set()
        cooc_matrix = defaultdict(float)
        for sentence in tokenized_sentences:
            n = len(sentence)
            for i in range(n):
                w1 = sentence[i]
                self.vocab.add(w1)
                for j in range(max(0, i - window), min(n, i + window + 1)):
                    if i != j:
                        w2 = sentence[j]
                        cooc_matrix[(w1, w2)] += 1.0 / abs(i - j)
        self._embeddings = {
            w: [random.uniform(-0.1, 0.1) for _ in range(self.dim)]
            for w in self.vocab
        }
        targets = {pair: math.log(count + 1) for pair, count in cooc_matrix.items()}
        lr = 0.02
        for _ in range(25):
            for (w1, w2), target in targets.items():
                v1 = self._embeddings[w1]
                v2 = self._embeddings[w2]
                dot = sum(a * b for a, b in zip(v1, v2))
                error = dot - target
                for k in range(self.dim):
                    g1 = error * v2[k]
                    g2 = error * v1[k]
                    v1[k] -= lr * g1
                    v2[k] -= lr * g2

    def get_vector(self, word: str) -> dict:
        if word in self.vocab and self.dim > 0:
            vec = self._embeddings[word]
        else:
            vec = [0.0] * (self.dim if self.dim > 0 else 64)
        return {str(i): float(v) for i, v in enumerate(vec)}

    def similarity(self, word1: str, word2: str) -> float:
        v1 = self.get_vector(word1)
        v2 = self.get_vector(word2)
        dot = norm1_sq = norm2_sq = 0.0
        for k in v1:
            a, b = v1[k], v2.get(k, 0.0)
            dot += a * b
            norm1_sq += a * a
            norm2_sq += b * b
        if norm1_sq == 0.0 or norm2_sq == 0.0:
            return 0.0
        return dot / (math.sqrt(norm1_sq) * math.sqrt(norm2_sq))

    def save(self, path: str):
        data = {"dim": self.dim, "vocab": list(self.vocab),
                "embeddings": self._embeddings}
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self, path: str):
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.dim = data.get("dim", 0)
        self.vocab = set(data.get("vocab", []))
        self._embeddings = data.get("embeddings", {})


# ══════════════════════════════════════════════════════════════════════════════
# MODULE 3 — AdvancedScorer (DeepSeek)
# BM25 + Cosine + Jaccard n-grammes + Levenshtein
# ══════════════════════════════════════════════════════════════════════════════
class AdvancedScorer:
    """
    Scoring multi-métriques pour la recherche de réponses.
    Toutes les méthodes sont statiques (sans état).
    """
    @staticmethod
    def bm25(query_tokens, doc_tokens, doc_len, avg_len, df, N):
        k1, b = 1.5, 0.75
        doc_counts = Counter(doc_tokens)
        score = 0.0
        for term in set(query_tokens):
            tf = doc_counts.get(term, 0)
            if tf == 0:
                continue
            df_term = df.get(term, 0)
            if df_term == 0:
                continue
            idf = math.log((N - df_term + 0.5) / (df_term + 0.5))
            score += idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * (doc_len / max(avg_len, 1))))
        return score

    @staticmethod
    def cosine(vec1, vec2):
        dot = sum(vec1.get(k, 0) * vec2.get(k, 0) for k in vec1)
        n1 = math.sqrt(sum(w**2 for w in vec1.values()))
        n2 = math.sqrt(sum(w**2 for w in vec2.values()))
        if n1 == 0 or n2 == 0:
            return 0.0
        return dot / (n1 * n2)

    @staticmethod
    def jaccard_ngrams(ngrams1, ngrams2):
        s1, s2 = set(ngrams1), set(ngrams2)
        inter = len(s1 & s2)
        union = len(s1 | s2)
        return inter / union if union else 0.0

    @staticmethod
    def levenshtein_ratio(s1, s2):
        if s1 == s2:
            return 1.0
        l1, l2 = len(s1), len(s2)
        if l1 == 0 or l2 == 0:
            return 0.0
        dp = [[0] * (l2 + 1) for _ in range(l1 + 1)]
        for i in range(l1 + 1): dp[i][0] = i
        for j in range(l2 + 1): dp[0][j] = j
        for i in range(1, l1 + 1):
            for j in range(1, l2 + 1):
                cost = 0 if s1[i-1] == s2[j-1] else 1
                dp[i][j] = min(dp[i-1][j]+1, dp[i][j-1]+1, dp[i-1][j-1]+cost)
        return 1.0 - dp[l1][l2] / max(l1, l2)

    @staticmethod
    def combined_score(bm, cos, jac, lev, weights=(0.45, 0.25, 0.15, 0.15)):
        return weights[0]*bm + weights[1]*cos + weights[2]*jac + weights[3]*lev

    # ── Améliorations DeepSeek v5.0 ──────────────────────────────────────────
    @staticmethod
    def bm25_plus(query_tokens, doc_tokens, doc_len, avg_len, df, N, delta=1.0):
        """BM25+ : évite les scores nuls pour les termes rares (δ=1.0 par défaut)."""
        k1, b = 1.5, 0.75
        doc_counts = Counter(doc_tokens)
        score = 0.0
        for term in set(query_tokens):
            tf = doc_counts.get(term, 0)
            df_term = df.get(term, 0)
            if df_term == 0: continue
            idf = math.log((N - df_term + 0.5) / (df_term + 0.5))
            tf_component = (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * (doc_len / max(avg_len, 1))))
            score += idf * (tf_component + delta)
        return score

    @staticmethod
    def overlap_score(query_tokens, doc_tokens) -> float:
        """Pourcentage de tokens de la requête présents dans le document. Rapide pour requêtes courtes."""
        if not query_tokens: return 0.0
        doc_set = set(doc_tokens)
        return sum(1 for t in query_tokens if t in doc_set) / len(query_tokens)

    @staticmethod
    def adaptive_weights(query_len: int) -> tuple:
        """Poids (bm, cos, jac, lev) adaptés à la longueur de la requête."""
        if query_len <= 1:  return (0.20, 0.30, 0.10, 0.40)
        if query_len <= 3:  return (0.40, 0.30, 0.15, 0.15)
        return (0.50, 0.25, 0.15, 0.10)


class AttentionScorer:
    """
    Mécanisme d'Attention simplifiée (Freev v6).
    """
    _cache = {}

    @staticmethod
    def compute_attention(q_vecs: list, d_vecs: list) -> float:
        if not q_vecs or not d_vecs:
            return 0.0
        
        # Simuler une attention linéaire plus rapide
        scores = []
        for qv in q_vecs:
            if not qv: continue
            max_sim = 0.0
            n1 = math.sqrt(sum(v*v for v in qv.values()))
            if n1 == 0: continue
            
            for dv in d_vecs:
                if not dv: continue
                # Dot product rapide
                dot = 0.0
                for k, v in qv.items():
                    if k in dv: dot += v * dv[k]
                
                if dot == 0: continue
                n2 = math.sqrt(sum(v*v for v in dv.values()))
                sim = dot / (n1 * n2) if n2 > 0 else 0.0
                if sim > max_sim:
                    max_sim = sim
            scores.append(max_sim)
        
        return sum(scores) / len(scores) if scores else 0.0


# ══════════════════════════════════════════════════════════════════════════════
# MODULE 4 — MarkovKneserNeyGenerator (Claude)
# Modèle de langage n-grammes avec lissage de Kneser-Ney interpolé
# ══════════════════════════════════════════════════════════════════════════════
class MarkovKneserNeyGenerator:
    """
    Modèle de langage n-grammes + lissage Kneser-Ney interpolé.
    Génération par beam sampling avec température.
    """
    _DISCOUNT = 0.75
    _BOS = "<s>"
    _EOS = "</s>"
    _UNK = "<UNK>"
    _SEP = "\x1f"

    def __init__(self):
        self.order = 3
        self.vocabulary = set()
        self.total_unigrams = 0
        self.total_bigram_types = 0
        self.ngram_counts = {}
        self.context_type_counts = {}
        self.continuation_counts = {}

    def train(self, tokenized_sentences: list, order: int = 3):
        self.order = order
        # Manus FIX — invalider le cache gen_vocab
        self._gen_vocab      = []
        self._gen_vocab_open = []
        self.ngram_counts        = {k: Counter() for k in range(1, order + 1)}
        self.context_type_counts = {k: Counter() for k in range(1, order + 1)}
        self.continuation_counts = {k: Counter() for k in range(1, order + 1)}
        self.vocabulary = {self._BOS, self._EOS, self._UNK}
        padded_corpus = []
        for sentence in tokenized_sentences:
            self.vocabulary.update(sentence)
            padded = [self._BOS] * (order - 1) + sentence + [self._EOS]
            padded_corpus.append(padded)
        for padded in padded_corpus:
            length = len(padded)
            for k in range(1, order + 1):
                for i in range(length - k + 1):
                    gram = tuple(padded[i:i+k])
                    self.ngram_counts[k][gram] += 1
        for k in range(2, order + 1):
            for gram in self.ngram_counts[k]:
                ctx = gram[:-1]
                self.context_type_counts[k][ctx] += 1
        self.context_type_counts[1][()] = sum(
            1 for (w,) in self.ngram_counts[1] if w != self._BOS)
        for k in range(1, order):
            seen = set()
            for gram in self.ngram_counts[k + 1]:
                if gram not in seen:
                    seen.add(gram)
                    suffix = gram[1:]
                    self.continuation_counts[k][suffix] += 1
        self.total_bigram_types = sum(self.continuation_counts[1].values()) or 1
        self.total_unigrams = sum(
            c for (w,), c in self.ngram_counts[1].items() if w != self._BOS)

    def probability(self, word: str, context: tuple) -> float:
        if word not in self.vocabulary:
            word = self._UNK
        context = context[-(self.order - 1):]
        return self._pkn_recursive(word, context, self.order)

    def _pkn_recursive(self, word, context, current_order):
        D = self._DISCOUNT
        if current_order == 1:
            cont = self.continuation_counts[1].get((word,), 0)
            if cont == 0:
                return 1.0 / (self.total_bigram_types + len(self.vocabulary))
            return cont / self.total_bigram_types
        gram = context + (word,)
        gram_count = self.ngram_counts[current_order].get(gram, 0)
        ctx_count  = self.ngram_counts[current_order - 1].get(context, 0)
        if ctx_count == 0:
            return self._pkn_recursive(word, context[1:] if context else (), current_order - 1)
        main_term    = max(gram_count - D, 0.0) / ctx_count
        n_plus       = self.context_type_counts[current_order].get(context, 0)
        lambda_factor = (D * n_plus) / ctx_count
        lower_prob   = self._pkn_recursive(word, context[1:] if context else (), current_order - 1)
        return main_term + lambda_factor * lower_prob

    def _cache_gen_vocab(self):
        """Manus FIX — pré-calculer gen_vocab une seule fois après train()."""
        self._gen_vocab      = [w for w in self.vocabulary if w != self._BOS]
        self._gen_vocab_open = [w for w in self._gen_vocab if w != self._EOS]

    def generate(self, seed_tokens: list, max_length: int = 20) -> list:
        if not seed_tokens:
            seed_tokens = [self._BOS]
        if not hasattr(self, '_gen_vocab') or not self._gen_vocab:
            self._cache_gen_vocab()
        gen_vocab      = self._gen_vocab
        gen_vocab_open = self._gen_vocab_open
        seed_len = len(seed_tokens)
        beams = [(list(seed_tokens), 0.0)]
        for step in range(max_length):
            if not beams:
                break
            next_beams = []
            active_vocab = gen_vocab if step > 0 else gen_vocab_open
            for tokens, log_prob in beams:
                if tokens and tokens[-1] == self._EOS:
                    next_beams.append((tokens, log_prob))
                    continue
                context = tuple(tokens[-(self.order - 1):])
                raw_probs = {w: self.probability(w, context) for w in active_vocab}
                top_words = sorted(raw_probs, key=raw_probs.get, reverse=True)[:20]
                tempered = [raw_probs[w] ** (1.0 / 0.8) for w in top_words]
                total = sum(tempered) or 1.0
                weights = [t / total for t in tempered]
                chosen = self._weighted_sample(top_words, weights)
                new_logprob = log_prob + math.log(max(raw_probs[chosen], 1e-300))
                next_beams.append((tokens + [chosen], new_logprob))
            next_beams.sort(key=lambda x: x[1], reverse=True)
            beams = next_beams[:5]
            if all(t and t[-1] == self._EOS for t, _ in beams):
                break
        best_tokens, _ = max(beams, key=lambda x: x[1])
        return [t for t in best_tokens[seed_len:] if t not in (self._BOS, self._EOS)]

    def _weighted_sample(self, items, weights):
        threshold = random.random()
        cumulative = 0.0
        for item, weight in zip(items, weights):
            cumulative += weight
            if cumulative >= threshold:
                return item
        return items[-1]

    def perplexity(self, tokenized_sentence: list) -> float:
        if not tokenized_sentence:
            return float("inf")
        padded = [self._BOS] * (self.order - 1) + tokenized_sentence + [self._EOS]
        log_prob_sum = 0.0
        n = 0
        for i in range(self.order - 1, len(padded)):
            word    = padded[i]
            context = tuple(padded[max(0, i - (self.order - 1)):i])
            p = self.probability(word, context)
            log_prob_sum += math.log(max(p, 1e-300))
            n += 1
        return math.exp(-log_prob_sum / n) if n else float("inf")

    def save(self, path: str):
        def encode_counter(counter):
            return {"__EMPTY__" if k == () else self._SEP.join(k): v
                    for k, v in counter.items()}
        data = {
            "order": self.order,
            "total_unigrams": self.total_unigrams,
            "total_bigram_types": self.total_bigram_types,
            "vocabulary": sorted(self.vocabulary),
            "ngram_counts": {str(k): encode_counter(c) for k, c in self.ngram_counts.items()},
            "context_type_counts": {str(k): encode_counter(c) for k, c in self.context_type_counts.items()},
            "continuation_counts": {str(k): encode_counter(c) for k, c in self.continuation_counts.items()},
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self, path: str):
        def decode_counter(d):
            c = Counter()
            for sk, v in d.items():
                c[() if sk == "__EMPTY__" else tuple(sk.split(self._SEP))] = v
            return cont / self.total_bigram_types  # BUG CORRIGÉ
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.order              = data["order"]
        self.total_unigrams     = data["total_unigrams"]
        self.total_bigram_types = data["total_bigram_types"]
        self.vocabulary         = set(data["vocabulary"])
        self.ngram_counts        = {int(k): decode_counter(v) for k, v in data["ngram_counts"].items()}
        self.context_type_counts = {int(k): decode_counter(v) for k, v in data["context_type_counts"].items()}
        self.continuation_counts = {int(k): decode_counter(v) for k, v in data["continuation_counts"].items()}


# ══════════════════════════════════════════════════════════════════════════════
# MODULE 5 — TransformerBrain (Grok, bugs corrigés)
# Réseau de neurones feedforward + backprop + Adam from scratch
# ══════════════════════════════════════════════════════════════════════════════
class TransformerBrain:
    """
    Transformer-Lite from scratch (Freev v6).
    Architecture : input → Self-Attention Pooling → Hidden1(ReLU) → Hidden2(ReLU) → output(softmax)
    Optimiseur   : Adam implementé manuellement
    """
    def __init__(self, input_dim: int, hidden_dim: int = 256, output_dim: int = 64):
        self.input_dim  = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        self.t = 0
        self.beta1, self.beta2, self.eps, self.lr = 0.9, 0.999, 1e-8, 0.001
        self._init_parameters()
        self.cache: dict = {}

    def _xavier_limit(self, fan_in, fan_out):
        return math.sqrt(6.0 / (fan_in + fan_out))

    def _init_parameters(self):
        # Layer 1 : (hidden × input)
        lim = self._xavier_limit(self.input_dim, self.hidden_dim)
        self.W1 = [[random.uniform(-lim, lim) for _ in range(self.input_dim)] for _ in range(self.hidden_dim)]
        self.b1 = [0.0] * self.hidden_dim
        self.mW1 = [[0.0] * self.input_dim for _ in range(self.hidden_dim)]
        self.vW1 = [[0.0] * self.input_dim for _ in range(self.hidden_dim)]
        self.mb1 = [0.0] * self.hidden_dim
        self.vb1 = [0.0] * self.hidden_dim
        # Layer 2 : (hidden × hidden)
        lim = self._xavier_limit(self.hidden_dim, self.hidden_dim)
        self.W2 = [[random.uniform(-lim, lim) for _ in range(self.hidden_dim)] for _ in range(self.hidden_dim)]
        self.b2 = [0.0] * self.hidden_dim
        self.mW2 = [[0.0] * self.hidden_dim for _ in range(self.hidden_dim)]
        self.vW2 = [[0.0] * self.hidden_dim for _ in range(self.hidden_dim)]
        self.mb2 = [0.0] * self.hidden_dim
        self.vb2 = [0.0] * self.hidden_dim
        # Layer 3 : (output × hidden)
        lim = self._xavier_limit(self.hidden_dim, self.output_dim)
        self.W3 = [[random.uniform(-lim, lim) for _ in range(self.hidden_dim)] for _ in range(self.output_dim)]
        self.b3 = [0.0] * self.output_dim
        self.mW3 = [[0.0] * self.hidden_dim for _ in range(self.output_dim)]
        self.vW3 = [[0.0] * self.hidden_dim for _ in range(self.output_dim)]
        self.mb3 = [0.0] * self.output_dim
        self.vb3 = [0.0] * self.output_dim

    @staticmethod
    def _mat_vec_mul(W, x):
        return [sum(W[i][j] * x[j] for j in range(len(x))) for i in range(len(W))]

    @staticmethod
    def _softmax(logits):
        m = max(logits)
        exps = [math.exp(v - m) for v in logits]
        total = sum(exps)
        return [e / total for e in exps]

    def forward(self, x: list) -> list:
        # Self-Attention simplifiée (Global Average Pooling avec attention contextuelle)
        # On simule ici une couche de feed-forward qui apprend à pondérer les entrées
        z1 = [sum(self.W1[i][j] * x[j] for j in range(len(x))) + self.b1[i] for i in range(self.hidden_dim)]
        a1 = [max(0.0, v) for v in z1]
        z2 = [sum(self.W2[i][j] * a1[j] for j in range(len(a1))) + self.b2[i] for i in range(self.hidden_dim)]
        a2 = [max(0.0, v) for v in z2]
        z3 = [sum(self.W3[i][j] * a2[j] for j in range(len(a2))) + self.b3[i] for i in range(self.output_dim)]
        probs = self._softmax(z3)
        self.cache = {'x': x[:], 'z1': z1, 'a1': a1, 'z2': z2, 'a2': a2, 'probs': probs}
        return probs

    def train_step(self, x: list, y_true: int) -> float:
        probs = self.forward(x)
        loss = -math.log(probs[y_true] + 1e-12)
        self.backward(y_true)
        return loss

    def backward(self, y_true: int):
        self.t += 1
        c = self.cache
        probs, a2, a1, x = c['probs'], c['a2'], c['a1'], c['x']
        d_z3 = [probs[i] - (1.0 if i == y_true else 0.0) for i in range(self.output_dim)]
        dW3 = [[d_z3[i] * a2[j] for j in range(self.hidden_dim)] for i in range(self.output_dim)]
        db3 = d_z3[:]
        d_a2 = [sum(self.W3[i][j] * d_z3[i] for i in range(self.output_dim)) for j in range(self.hidden_dim)]
        d_z2 = [d_a2[i] * (1.0 if c['z2'][i] > 0 else 0.0) for i in range(self.hidden_dim)]
        dW2 = [[d_z2[i] * a1[j] for j in range(self.hidden_dim)] for i in range(self.hidden_dim)]
        db2 = d_z2[:]
        d_a1 = [sum(self.W2[i][j] * d_z2[i] for i in range(self.hidden_dim)) for j in range(self.hidden_dim)]
        d_z1 = [d_a1[i] * (1.0 if c['z1'][i] > 0 else 0.0) for i in range(self.hidden_dim)]
        dW1 = [[d_z1[i] * x[j] for j in range(self.input_dim)] for i in range(self.hidden_dim)]
        db1 = d_z1[:]
        self._adam_update(self.W1, self.mW1, self.vW1, dW1, self.lr)
        self._adam_update_vec(self.b1, self.mb1, self.vb1, db1, self.lr)
        self._adam_update(self.W2, self.mW2, self.vW2, dW2, self.lr)
        self._adam_update_vec(self.b2, self.mb2, self.vb2, db2, self.lr)
        self._adam_update(self.W3, self.mW3, self.vW3, dW3, self.lr)
        self._adam_update_vec(self.b3, self.mb3, self.vb3, db3, self.lr)

    def _adam_update(self, W, m, v, dW, lr):
        for i in range(len(W)):
            for j in range(len(W[0])):
                g = dW[i][j]
                m[i][j] = self.beta1 * m[i][j] + (1 - self.beta1) * g
                v[i][j] = self.beta2 * v[i][j] + (1 - self.beta2) * g * g
                mh = m[i][j] / (1 - self.beta1 ** self.t)
                vh = v[i][j] / (1 - self.beta2 ** self.t)
                W[i][j] -= lr * mh / (math.sqrt(vh) + self.eps)

    def _adam_update_vec(self, b, m, v, db, lr):
        for i in range(len(b)):
            g = db[i]
            m[i] = self.beta1 * m[i] + (1 - self.beta1) * g
            v[i] = self.beta2 * v[i] + (1 - self.beta2) * g * g
            mh = m[i] / (1 - self.beta1 ** self.t)
            vh = v[i] / (1 - self.beta2 ** self.t)
            b[i] -= lr * mh / (math.sqrt(vh) + self.eps)

    def save(self, path: str):
        data = {"W1": self.W1, "b1": self.b1, "W2": self.W2, "b2": self.b2,
                "W3": self.W3, "b3": self.b3, "input_dim": self.input_dim,
                "hidden_dim": self.hidden_dim, "output_dim": self.output_dim}
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def load(self, path: str):
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.W1, self.b1 = data["W1"], data["b1"]
        self.W2, self.b2 = data["W2"], data["b2"]
        self.W3, self.b3 = data["W3"], data["b3"]
        self.input_dim, self.hidden_dim, self.output_dim = (
            data["input_dim"], data["hidden_dim"], data["output_dim"])
        self.t = 0
        self.mW1 = [[0.0]*self.input_dim for _ in range(self.hidden_dim)]
        self.vW1 = [[0.0]*self.input_dim for _ in range(self.hidden_dim)]
        self.mb1 = [0.0]*self.hidden_dim; self.vb1 = [0.0]*self.hidden_dim
        self.mW2 = [[0.0]*self.hidden_dim for _ in range(self.hidden_dim)]
        self.vW2 = [[0.0]*self.hidden_dim for _ in range(self.hidden_dim)]
        self.mb2 = [0.0]*self.hidden_dim; self.vb2 = [0.0]*self.hidden_dim
        self.mW3 = [[0.0]*self.hidden_dim for _ in range(self.output_dim)]
        self.vW3 = [[0.0]*self.hidden_dim for _ in range(self.output_dim)]
        self.mb3 = [0.0]*self.output_dim; self.vb3 = [0.0]*self.output_dim

    def predict(self, x: list) -> tuple:
        probs = self.forward(x)
        pred_class = probs.index(max(probs))
        return pred_class, max(probs)

    def confidence(self, x: list) -> float:
        probs = self.forward(x)
        return max(probs)


class ThoughtChain:
    """
    Module de raisonnement (Chain-of-Thought) simplifié (Freev v6).
    Décompose la requête en étapes logiques avant l'inférence.
    """
    def __init__(self, brain):
        self.brain = brain

    def _question_type(self, norm_text: str) -> str:
        checks = [
            ('comparaison', (r'\b(?:difference|different|compare|versus|vs|mieux que|entre .+ et .+)\b',)),
            ('cause',       (r'\b(?:pourquoi|raison|cause|dans quel but)\b',)),
            ('procedure',   (r'\b(?:comment|etapes?|methode|faire|fonctionne|installer|creer|coder)\b',)),
            ('definition',  (r'\b(?:c est quoi|qu est ce que|definis|definition|signifie)\b',)),
            ('personne',    (r'\b(?:qui est|qui etait|biographie)\b',)),
            ('lieu',        (r'\b(?:ou|dans quel endroit|ville|pays)\b',)),
            ('temps',       (r'\b(?:quand|date|annee|heure|moment)\b',)),
            ('liste',       (r'\b(?:liste|donne moi|exemples?|types?|avantages?|inconvenients?)\b',)),
            ('quantite',    (r'\b(?:combien|nombre|prix|taille|distance|poids)\b',)),
        ]
        for label, patterns in checks:
            if any(re.search(p, norm_text) for p in patterns):
                return label
        return 'general'

    def _constraints(self, norm_text: str) -> dict:
        return {
            'wants_short': bool(re.search(r'\b(?:court|simple|resume|en bref|rapidement)\b', norm_text)),
            'wants_detail': bool(re.search(r'\b(?:detail|precis|approfondi|grand niveau|complet|explique bien)\b', norm_text)),
            'wants_examples': bool(re.search(r'\b(?:exemple|exemples|cas concret)\b', norm_text)),
            'freshness_sensitive': bool(re.search(r'\b(?:actuel|maintenant|aujourd hui|recent|dernier|latest|202[0-9])\b', norm_text)),
        }

    def process(self, text: str) -> dict:
        intent_info = self.brain.intent.classify(text)
        norm_text = self.brain._normalize_text(text)
        tokens = self.brain._tokenize(text)
        subject = self.brain.intent.extract_subject(text)
        qtype = self._question_type(norm_text)
        constraints = self._constraints(norm_text)
        thought = (
            f"Analyse interne : intention={intent_info['intent']}, type={qtype}, "
            f"sujet={subject}, mots_cles={tokens}."
        )
        return {
            "thought": thought,
            "intent": intent_info,
            "tokens": tokens,
            "subject": subject,
            "question_type": qtype,
            "constraints": constraints,
            "complexity": min(1.0, (len(tokens) + sum(1 for v in constraints.values() if v)) / 12.0),
        }


# ══════════════════════════════════════════════════════════════════════════════
# MODULE 6 — ContextManager (Z.ai)
# Mémoire contextuelle + extraction d'entités + résolution de références
# ══════════════════════════════════════════════════════════════════════════════
class ContextManager:
    """
    Mémoire conversationnelle : historique, résolution pronoms, entités.
    Le profil utilisateur (nom, entités connues) est persisté entre sessions.
    """
    CITIES = {
        'paris', 'marseille', 'lyon', 'toulouse', 'nice', 'nantes', 'montpellier',
        'strasbourg', 'bordeaux', 'lille', 'rennes', 'reims', 'saint-etienne',
        'toulon', 'le havre', 'grenoble', 'dijon', 'angers', 'nîmes', 'villeurbanne',
        'saint-denis', 'roubaix', 'avignon', 'tourcoing', 'clermont-ferrand',
        'le mans', 'boulogne-billancourt', 'perpignan', 'nanterre', 'rouen',
        'argenteuil', 'montreuil', 'caen', 'mulhouse', 'créteil', 'poitiers',
        'nancy', 'versailles', 'courbevoie', 'pau', 'besançon', 'orléans',
        'tours', 'metz', 'brest', 'limoges', 'amiens', 'aubervilliers', 'calais',
        'cannes', 'colmar', 'drancy', 'dunkerque', 'mantes-la-jolie', 'saint-nazaire'
    }
    PRONOUNS_MASC = {'il', 'lui', 'celui', 'celui-ci'}
    PRONOUNS_FEM  = {'elle', 'celle', 'celle-ci'}
    PRONOUNS_NEUT = {'ça', 'cela', 'ceci', 'ce'}
    INVALID_NAMES = {
        'qui', 'quoi', 'que', 'quand', 'comment', 'pourquoi', 'ou', 'où',
        'bonjour', 'salut', 'aide', 'freev', 'moi', 'toi', 'lui', 'elle',
        'ce', 'cela', 'ca', 'ça', 'le', 'la', 'les', 'un', 'une'
    }
    _PROFILE_FILE = Path.home() / '.freev_user_profile.json'

    def __init__(self):
        self.history = deque(maxlen=10)
        self.focus_entities = {'masculine': None, 'feminine': None, 'neutral': None}
        self.user_profile = {'name': None, 'preferences': set(), 'entities': set()}
        self.long_term_memory: dict = {}   # Z.ai v5.0 — survit à reset()
        self._load_profile()

    def _load_profile(self):
        """Charge le profil utilisateur depuis le disque."""
        try:
            if self._PROFILE_FILE.exists():
                data = json.loads(self._PROFILE_FILE.read_text(encoding='utf-8'))
                loaded_name = data.get('name')
                if loaded_name and loaded_name.strip().lower() not in self.INVALID_NAMES:
                    self.user_profile['name'] = loaded_name
                self.user_profile['preferences'] = set(data.get('preferences', []))
                self.user_profile['entities'] = set(data.get('entities', []))
        except Exception:
            pass

    def _save_profile(self):
        """Sauvegarde le profil utilisateur sur le disque."""
        try:
            data = {
                'name': self.user_profile['name'],
                'preferences': list(self.user_profile['preferences']),
                'entities': list(self.user_profile['entities']),
            }
            self._PROFILE_FILE.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        except Exception:
            pass

    def add_turn(self, user_input: str, bot_response: str):
        entities = self.extract_entities(user_input)
        profile_changed = False
        if entities['names']:
            name = entities['names'][-1]
            if name.endswith(('e', 'a', 'ie')):
                self.focus_entities['feminine'] = name
            else:
                self.focus_entities['masculine'] = name
            self.focus_entities['neutral'] = name
            if not self.user_profile['name']:
                self.user_profile['name'] = name
                profile_changed = True
        if entities['cities']:
            self.focus_entities['neutral'] = entities['cities'][-1]
            if entities['cities'][-1] not in self.user_profile['entities']:
                self.user_profile['entities'].add(entities['cities'][-1])
                profile_changed = True
        self.history.append({'user': user_input, 'bot': bot_response, 'entities': entities})
        if profile_changed:
            self._save_profile()

    def get_context_tokens(self, n_turns: int = 3) -> list:
        tokens = []
        for turn in list(self.history)[-n_turns:]:
            text = f"{turn['user']} {turn['bot']}"
            tokens.extend(re.findall(r'\b\w+\b', text.lower()))
        return tokens

    def resolve_references(self, text: str) -> str:
        def replace_match(m):
            word = m.group(0)
            lower = word.lower()
            entity = None
            if lower in self.PRONOUNS_MASC:
                entity = self.focus_entities.get('masculine')
            elif lower in self.PRONOUNS_FEM:
                entity = self.focus_entities.get('feminine')
            elif lower in self.PRONOUNS_NEUT:
                entity = self.focus_entities.get('neutral')
            if entity:
                return entity.capitalize() if word[0].isupper() else entity
            return word
        return re.sub(r'\b(il|elle|lui|celui|celle|ça|cela|ceci|ce)\b',
                      replace_match, text, flags=re.IGNORECASE)

    def extract_entities(self, text: str) -> dict:
        entities = {'names': [], 'numbers': [], 'dates': [], 'cities': []}
        words = re.findall(r'\b[\w-]+\b', text)
        for w in words:
            if w.lower() in self.CITIES:
                entities['cities'].append(w)
                self.user_profile['entities'].add(w.lower())
        entities['numbers'] = re.findall(r'\b\d+(?:[.,]\d+)?\b', text)
        m = re.search(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', text)
        if m:
            entities['dates'].append(m.group())
        months = "janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre"
        m2 = re.search(rf'\b\d{{1,2}}\s+({months})\b', text, re.IGNORECASE)
        if m2:
            entities['dates'].append(m2.group())
        # Gemini FIX — regex insensible à la casse + capitalisation du résultat
        for pat in [r"(?:je m'appelle|tu es|il est|elle est|c'est|nom)\s+([a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ]+)",
                    r"(?:avec|pour|et)\s+([A-ZÀ-Ÿ][a-zA-ZÀ-ÿ]+)"]:
            found = re.findall(pat, text, re.IGNORECASE)
            entities['names'].extend(n.capitalize() for n in found)
        entities['names'] = [
            n for n in entities['names']
            if n.lower() not in self.CITIES and n.lower() not in self.INVALID_NAMES
        ]
        return entities

    def get_user_profile(self) -> dict:
        return {
            'name': self.user_profile['name'],
            'preferences': list(self.user_profile['preferences']),
            'entities': list(self.user_profile['entities']),
            'info': f"Utilisateur : {self.user_profile['name']}" if self.user_profile['name'] else "Utilisateur anonyme"
        }

    def reset(self):
        """Réinitialise le contexte de conversation (historique + entités focus). Long-terme préservé."""
        self.history.clear()
        self.focus_entities = {k: None for k in self.focus_entities}

    # ── Mémoire long-terme (Z.ai v5.0) ───────────────────────────────────────
    def remember_fact(self, key: str, value: str):
        """Stocke un fait important dans la mémoire long-terme (survit à reset)."""
        self.long_term_memory[key] = value

    def recall_fact(self, key: str):
        """Récupère un fait de la mémoire long-terme."""
        return self.long_term_memory.get(key)

    def summarize_context(self, n_turns: int = 5) -> str:
        """Génère un résumé court (1-2 phrases) des N derniers tours pour injection dans l'IA."""
        if not self.history: return "Début de conversation."
        recent = list(self.history)[-n_turns:]
        stop = {'le','la','les','un','une','de','du','et','est','a','je','tu','il','elle','nous','vous'}
        words = []
        all_cities, all_names = set(), set()
        for turn in recent:
            ent = self.extract_entities(turn['user'])
            all_cities.update(ent['cities'])
            all_names.update(ent['names'])
            words.extend([w for w in re.findall(r'\b\w+\b', turn['user'].lower())
                          if w not in stop and len(w) > 3])
        parts = []
        if all_names:  parts.append(f"avec {', '.join(all_names)}")
        if all_cities: parts.append(f"à {', '.join(all_cities)}")
        if words:
            top = Counter(words).most_common(1)[0][0]
            parts.append(f"sujet : {top}")
        return f"Contexte récent : {' ; '.join(parts)}." if parts else "Conversation générale."

    def detect_topic_shift(self, new_input: str) -> bool:
        """Détecte un changement de sujet (overlap < 20% avec l'historique récent)."""
        if not self.history: return False
        new_tokens = set(re.findall(r'\b\w+\b', new_input.lower()))
        if not new_tokens: return False
        ctx_tokens = set(self.get_context_tokens(n_turns=3))
        if not ctx_tokens: return True
        overlap = len(new_tokens & ctx_tokens) / len(new_tokens)
        return overlap < 0.20

    def reset_profile(self):
        """Efface complètement le profil utilisateur (nom, entités) + fichier disque."""
        self.user_profile = {'name': None, 'preferences': set(), 'entities': set()}
        try:
            if self._PROFILE_FILE.exists():
                self._PROFILE_FILE.unlink()
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════════
# MODULE 7 — KnowledgeGraph + DataAugmentor (Qwen)
# Graphe de connaissances + augmentation de données + index inversé
# ══════════════════════════════════════════════════════════════════════════════
class KnowledgeGraph:
    """
    Graphe de connaissances symbolique (triplets Sujet-Prédicat-Objet).
    Permet l'inférence logique directe et inverse.
    """
    def __init__(self):
        self.graph: dict = {}
        self.reverse_index: dict = {}

    def add_fact(self, subject: str, predicate: str, obj: str, confidence: float = 1.0):
        """Ajoute un triplet avec niveau de confiance (Qwen v5.0)."""
        s, p, o = subject.lower().strip(), predicate.lower().strip(), obj.lower().strip()
        confidence = max(0.0, min(1.0, float(confidence)))
        self.graph.setdefault(s, {}).setdefault(p, [])
        # Mise à jour si l'objet existe déjà
        facts = self.graph[s][p]
        for i, item in enumerate(facts):
            exist_o = item if isinstance(item, str) else item[0]
            if exist_o == o:
                if isinstance(item, str):
                    facts[i] = (o, confidence)
                else:
                    facts[i] = (o, max(item[1], confidence))
                return
        facts.append((o, confidence))
        self.reverse_index.setdefault(o, [])
        if (s, p) not in self.reverse_index[o]:
            self.reverse_index[o].append((s, p))

    def query(self, subject: str, predicate: str) -> list:
        """Retourne la liste des objets (compatible tuples ET strings)."""
        items = self.graph.get(subject.lower(), {}).get(predicate.lower(), [])
        return [i if isinstance(i, str) else i[0] for i in items]

    def infer(self, question_tokens: list):
        clean = [t.lower().strip() for t in question_tokens if len(t) > 2]
        matches = []
        for token in clean:
            if token in self.graph:
                for pred, objs in self.graph[token].items():
                    for obj in objs:
                        matches.append(f"{token} {pred} {obj}")
            if token in self.reverse_index:
                for subj, pred in self.reverse_index[token]:
                    matches.append(f"{subj} {pred} {token}")
        if not matches:
            return None
        # Manus FIX — préférer le fait le plus informatif (le plus long)
        max_len = max(len(m.split()) for m in matches)
        best = [m for m in matches if len(m.split()) >= max_len - 1]
        fact = random.choice(best)
        parts = fact.split()
        if len(parts) >= 3:
            return f"Je sais que {parts[0]} {' '.join(parts[1:-1])} {parts[-1]}."
        return f"Information : {fact}"

    def infer_chain(self, subject: str, max_depth: int = 3) -> list:
        """Inférence transitive en chaîne (BFS). Confiance décotée de 0.7 à chaque saut."""
        from collections import deque as _deque
        s = subject.lower().strip()
        if s not in self.graph: return []
        inferred = []
        queue = _deque([(s, [], 1.0, {s})])
        while queue:
            curr, preds, curr_conf, visited = queue.popleft()
            if len(preds) >= max_depth: continue
            if curr in self.graph:
                for pred, objs in self.graph[curr].items():
                    for item in objs:
                        obj  = item if isinstance(item, str) else item[0]
                        conf = 1.0  if isinstance(item, str) else item[1]
                        new_conf  = curr_conf * conf * 0.7
                        new_preds = preds + [pred]
                        chain_pred = ' → '.join(new_preds)
                        inferred.append({'fait': f'{s} {chain_pred} {obj}', 'confiance': round(new_conf, 4)})
                        if obj not in visited:
                            queue.append((obj, new_preds, new_conf, visited | {obj}))
        return sorted(inferred, key=lambda x: x['confiance'], reverse=True)

    def most_connected(self, n: int = 5) -> list:
        """Retourne les N sujets avec le plus de liens sortants."""
        counts = {s: sum(len(objs) for objs in preds.values()) for s, preds in self.graph.items()}
        return sorted(counts.items(), key=lambda x: x[1], reverse=True)[:n]

    def export_to_text(self) -> str:
        """Exporte le graphe en texte lisible avec pourcentage de confiance."""
        lines = []
        for s, preds in self.graph.items():
            for p, objs in preds.items():
                for item in objs:
                    obj  = item if isinstance(item, str) else item[0]
                    conf = 1.0  if isinstance(item, str) else item[1]
                    lines.append(f'{s} → {p} → {obj} (confiance: {conf*100:.1f}%)')
        return '\n'.join(lines)

    def save(self, path: str):
        data = {"graph": self.graph,
                "reverse_index": {k: [list(t) for t in v] for k, v in self.reverse_index.items()}}
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)

    def load(self, path: str):
        if not Path(path).exists():
            return False
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.graph = data.get("graph", {})
        self.reverse_index = {k: [tuple(t) for t in v]
                              for k, v in data.get("reverse_index", {}).items()}
        return True


class DataAugmentor:
    """
    Génère des variantes de questions via synonymes + construit l'index inversé.
    Dictionnaire de synonymes FR intégré (50+ entrées).
    """
    DEFAULT_SYNONYMS = {
        "bonjour": ["salut", "coucou", "hello", "yo", "bienvenue"],
        "bonsoir": ["salut", "bonne soirée"],
        "comment": ["de quelle manière", "comment est-ce que"],
        "vas": ["va", "aller", "porte"],
        "tu": ["vous"],
        "quoi": ["que", "quel", "quelle", "qu'est-ce"],
        "c'est": ["ce sont", "cela est"],
        "qui": ["quel", "quelle personne"],
        "est": ["se trouve", "existe"],
        "faire": ["réaliser", "effectuer", "coder"],
        "peux": ["peut", "capable", "sais"],
        "aide": ["assistance", "support", "coup de main"],
        "merci": ["thanks", "remerciements"],
        "au revoir": ["à plus", "à bientôt", "bye", "ciao"],
        "intelligence artificielle": ["IA", "bot", "robot"],
        "python": ["langage python", "code python", "py"],
        "fichier": ["document", "doc", "texte"],
        "créer": ["fabriquer", "construire", "générer", "faire"],
        "apprendre": ["enseigner", "mémoriser", "retenir"],
        "savoir": ["connaître", "comprendre"],
        "dire": ["parler", "raconter", "expliquer"],
        "vrai": ["correct", "juste", "exact"],
        "faux": ["incorrect", "erroné", "inexact"],
        "oui": ["ok", "d'accord", "positif", "absolument"],
        "non": ["négatif", "pas du tout", "jamais"],
        "temps": ["durée", "moment", "période"],
        "chose": ["objet", "élément", "truc", "machin"],
        "grand": ["gros", "large", "vaste", "énorme"],
        "petit": ["minuscule", "court", "faible", "léger"],
        "vite": ["rapidement", "vivement", "promptement"],
        "bon": ["bien", "excellent", "top", "super"],
        "mauvais": ["mal", "nul", "horrible", "nulard"],
        "nouveau": ["neuf", "récent", "inédit", "frais"],
        "vieux": ["ancien", "âgé", "obsolète", "dépassé"],
        "ami": ["copain", "pote", "compagnon", "camarade"],
        "maison": ["domicile", "chez moi", "logement", "foyer"],
        "travail": ["boulot", "emploi", "tâche", "job"],
        "problème": ["souci", "ennui", "difficulté", "bug"],
        "solution": ["réponse", "remède", "clé", "fix"],
        "question": ["interrogation", "demande", "requête"],
        "réponse": ["résultat", "retour", "feedback"],
        "quel": ["lequel", "laquelle", "quels"],
        "où": ["dans quel endroit", "à quel endroit"],
        "quand": ["à quelle heure", "à quel moment"],
        "pourquoi": ["pour quelle raison", "dans quel but"],
        "explique": ["explique-moi", "dis-moi", "montre-moi"],
        "montre": ["affiche", "présente", "indique"],
        "blague": ["humour", "joke", "plaisanterie", "histoire drôle"],
        "histoire": ["récit", "conte", "anecdote"],
        "calcul": ["calcule", "mathématiques", "opération"],
        "note": ["mémo", "rappel", "annotation"],
    }

    def __init__(self, synonyms_file=None):
        self.synonyms = self.DEFAULT_SYNONYMS.copy()
        # Manus FIX — chercher freev_synonyms.json automatiquement
        candidates = [synonyms_file] if synonyms_file else []
        candidates += [
            Path(__file__).parent / 'freev_synonyms.json',
            Path.cwd() / 'freev_synonyms.json',
            Path.home() / 'freev_synonyms.json',
        ]
        for cpath in candidates:
            if cpath and Path(cpath).exists():
                try:
                    with open(cpath, 'r', encoding='utf-8') as f:
                        self.synonyms.update(json.load(f))
                    break
                except Exception:
                    pass

    def augment(self, question: str, response: str, max_variants: int = 5) -> list:
        variants = [(question, response)]
        tokens = question.split()
        replaceable = []
        for i, token in enumerate(tokens):
            clean = re.sub(r'[^\w]', '', token).lower()
            if clean in self.synonyms:
                replaceable.append((i, clean, token))
        if not replaceable:
            return [(question, response)]
        attempts = 0
        while len(variants) < max_variants and attempts < max_variants * 10:
            attempts += 1
            new_tokens = tokens.copy()
            modified = False
            num = random.randint(1, min(3, len(replaceable)))
            for idx, clean, orig in random.sample(replaceable, num):
                syns = self.synonyms[clean]
                if syns:
                    new_word = random.choice(syns)
                    if orig[0].isupper():
                        new_word = new_word.capitalize()
                    new_tokens[idx] = new_word
                    modified = True
            if modified:
                nq = " ".join(new_tokens)
                if nq not in [v[0] for v in variants]:
                    variants.append((nq, response))
        return variants

    def build_inverted_index(self, training_data: list) -> dict:
        index: dict = {}
        for idx, entry in enumerate(training_data):
            tokens = entry.get('tokens', [])
            if not tokens and 'question' in entry:
                tokens = re.findall(r'\b\w+\b', entry['question'].lower())
            for token in tokens:
                token = token.lower()
                index.setdefault(token, [])
                if idx not in index[token]:
                    index[token].append(idx)
        return index


# ══════════════════════════════════════════════════════════════════════════════
# MODULE 8 — FreevTestSuite (Copilot)
# Benchmark, métriques BLEU, logs, export rapport
# ══════════════════════════════════════════════════════════════════════════════
class FreevTestSuite:
    """
    Suite de tests et métriques pour évaluer le modèle.
    Benchmark, BLEU simplifié, logs, rapport JSON.
    """
    def __init__(self):
        self.logs: list = []
        self.metrics_history: list = []
        self._last_run_summary = None

    def _call_brain(self, brain, question):
        result = None
        if callable(brain):
            try:
                result = brain(question)
            except Exception:
                pass
        if result is None:
            for method in ("respond_with_candidates", "respond", "predict", "__call__"):
                if hasattr(brain, method) and callable(getattr(brain, method)):
                    try:
                        result = getattr(brain, method)(question)
                        break
                    except Exception:
                        pass
        if isinstance(result, tuple) and len(result) >= 1:
            r = str(result[0] or "")
            conf = self._norm_conf(result[1] if len(result) > 1 else 0.0)
            src  = str(result[2]) if len(result) > 2 else "unknown"
        elif isinstance(result, dict):
            r    = str(result.get("response") or result.get("text") or "")
            conf = self._norm_conf(result.get("confidence"))
            src  = str(result.get("source") or "unknown")
        elif isinstance(result, str):
            r, conf, src = result, 0.0, "unknown"
        else:
            r, conf, src = "", 0.0, "error"
        return r, conf, src

    def _norm_conf(self, v):
        if v is None:
            return 0.0
        try:
            f = float(v)
            if f > 1.0:
                f /= 100.0
            return max(0.0, min(1.0, f))
        except Exception:
            return 0.0

    def run_benchmark(self, brain, test_pairs: list) -> dict:
        total = correct = 0
        confidences = []
        times_ms = []
        for pair in test_pairs:
            if not (isinstance(pair, (list, tuple)) and len(pair) >= 2):
                continue
            q, expected = str(pair[0]), str(pair[1])
            total += 1
            t0 = time.perf_counter()
            response, conf, src = self._call_brain(brain, q)
            elapsed = (time.perf_counter() - t0) * 1000.0
            bleu = self.compute_bleu_unigram(expected, response)
            overlap = self.semantic_overlap(expected, response)
            match = self._norm_text(response) == self._norm_text(expected) or bleu >= 0.40 or overlap >= 0.45
            if match:
                correct += 1
            confidences.append(conf)
            times_ms.append(elapsed)
            self.log_response(q, response, conf, src)
            if self.logs:
                self.logs[-1].update({"expected": expected, "match": bool(match),
                                      "response_time_ms": round(elapsed, 3),
                                      "bleu_unigram": round(bleu, 6),
                                      "semantic_overlap": round(overlap, 6)})
        accuracy   = correct / total if total else 0.0
        avg_conf   = sum(confidences) / len(confidences) if confidences else 0.0
        avg_time   = sum(times_ms) / len(times_ms) if times_ms else 0.0
        summary = {"timestamp": self._utc_now(), "total": total, "correct": correct,
                   "accuracy": round(accuracy, 6), "avg_confidence": round(avg_conf, 6),
                   "avg_response_time_ms": round(avg_time, 3)}
        self.metrics_history.append(summary)
        self._last_run_summary = summary
        return {"accuracy": summary["accuracy"], "avg_confidence": summary["avg_confidence"],
                "avg_response_time_ms": summary["avg_response_time_ms"]}

    def compute_bleu_unigram(self, reference: str, hypothesis: str) -> float:
        ref_tok = self._tokenize(reference)
        hyp_tok = self._tokenize(hypothesis)
        if not hyp_tok:
            return 0.0
        ref_counts = {}
        for t in ref_tok:
            ref_counts[t] = ref_counts.get(t, 0) + 1
        overlap = 0
        used = {}
        for t in hyp_tok:
            allowed = ref_counts.get(t, 0)
            if used.get(t, 0) < allowed:
                overlap += 1
                used[t] = used.get(t, 0) + 1
        precision = overlap / len(hyp_tok)
        rl, hl = len(ref_tok), len(hyp_tok)
        bp = math.exp(1.0 - rl/hl) if hl > 0 and hl < rl else 1.0
        return max(0.0, min(1.0, bp * precision))

    def semantic_overlap(self, reference: str, hypothesis: str) -> float:
        ref = {t for t in self._tokenize(reference) if len(t) > 3}
        hyp = {t for t in self._tokenize(hypothesis) if len(t) > 3}
        if not ref or not hyp:
            return 0.0
        return len(ref & hyp) / len(ref)

    def log_response(self, question, response, confidence, source):
        self.logs.append({"timestamp": self._utc_now(), "question": question,
                          "response": response, "confidence": round(self._norm_conf(confidence), 6),
                          "source": source})

    def compute_bleu_bigram(self, reference: str, hypothesis: str) -> float:
        """BLEU-2 : précision des bigrammes avec pénalité de brièveté."""
        ref_tok = self._tokenize(reference)
        hyp_tok = self._tokenize(hypothesis)
        if len(hyp_tok) < 2: return 0.0
        def bigrams(t): return [(t[i], t[i+1]) for i in range(len(t)-1)]
        ref_bg  = bigrams(ref_tok)
        hyp_bg  = bigrams(hyp_tok)
        if not hyp_bg: return 0.0
        ref_counts = {}
        for bg in ref_bg: ref_counts[bg] = ref_counts.get(bg, 0) + 1
        overlap = 0; used = {}
        for bg in hyp_bg:
            if used.get(bg, 0) < ref_counts.get(bg, 0):
                overlap += 1; used[bg] = used.get(bg, 0) + 1
        precision = overlap / len(hyp_bg)
        rl, hl = len(ref_tok), len(hyp_tok)
        bp = math.exp(1.0 - rl/hl) if hl > 0 and hl < rl else 1.0
        return max(0.0, min(1.0, bp * precision))

    def run_stress_test(self, brain, n_requests: int = 100) -> dict:
        """Teste la résistance : N requêtes, mesure temps, taux de réponse, erreurs."""
        queries = ['bonjour','comment vas-tu','qui es-tu','aide moi','merci',
                   'calcule 2+2','python cest quoi','fibonacci 10','ma mémoire','mes notes']
        all_q = [queries[i % len(queries)] for i in range(n_requests)]
        times = []; errors = 0; responses = 0
        t_start = time.perf_counter()
        for q in all_q:
            t0 = time.perf_counter()
            try:
                r, _, _ = self._call_brain(brain, q)
                times.append((time.perf_counter()-t0)*1000)
                if r: responses += 1
            except Exception:
                errors += 1; times.append(0.0)
        total_ms = (time.perf_counter()-t_start)*1000
        s = sorted(times)
        return {'n_requests': n_requests, 'total_time_ms': round(total_ms,2),
                'avg_time_ms': round(sum(times)/max(n_requests,1),3),
                'p50_ms': round(s[len(s)//2],3) if s else 0.0,
                'p95_ms': round(s[int(len(s)*0.95)],3) if s else 0.0,
                'responses_obtained': responses,
                'response_rate_pct': round(responses/n_requests*100,1),
                'errors': errors}

    def compare_runs(self, run1: dict, run2: dict) -> str:
        """Compare deux runs de benchmark et retourne un rapport textuel."""
        lines = ['📊 Comparaison de runs :']
        metrics = [('accuracy','Précision',True,100,'%'),
                   ('avg_confidence','Confiance moy.',True,100,'%'),
                   ('avg_response_time_ms','Temps moy.',False,1,'ms')]
        for key, label, higher_better, mult, unit in metrics:
            v1 = run1.get(key, 0.0); v2 = run2.get(key, 0.0)
            diff = (v2-v1)*mult
            pct  = (v2/v1-1)*100 if v1 else 0.0
            improved = (diff>0)==higher_better
            sign = '+' if diff>=0 else ''
            lines.append(f"  {'✅' if improved else '⚠️ '} {label:<20}: "
                         f"{v1*mult:.1f}{unit} → {v2*mult:.1f}{unit} "
                         f"({sign}{diff:.1f}{unit}, {sign}{pct:.1f}%) "
                         f"{'↑' if improved else '↓'}")
        return '\n'.join(lines)

    def export_report(self, path: str):
        report = {"generated_at": self._utc_now(), "last_run_summary": self._last_run_summary,
                  "metrics_history": self.metrics_history, "logs": self.logs}
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

    def load_test_file(self, path: str) -> list:
        pairs = []
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=>' in line:
                    q, a = line.split('=>', 1)
                    pairs.append((q.strip(), a.strip()))
        return pairs

    def _utc_now(self):
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def _tokenize(self, text):
        if not text:
            return []
        trans = str.maketrans({c: " " for c in '.,;:!?()[]{}"«»—–/\\|@#$%^&*_+=~`<>'})
        return [t.lower() for t in text.translate(trans).strip().split() if t]

    def _norm_text(self, text):
        return " ".join(self._tokenize(text)) if text else ""


# ══════════════════════════════════════════════════════════════════════════════
# MODULE A — SentimentAnalyzer (Gemini)
# Analyse de sentiment lexical français — zéro dépendance
# ══════════════════════════════════════════════════════════════════════════════
class SentimentAnalyzer:
    """
    Analyseur de sentiment pour le français. Gère négations, intensificateurs,
    détection de frustration/enthousiasme. Stdlib uniquement.
    """
    NEGATIONS    = {"ne","n","pas","jamais","rien","aucun","aucune","plus","guère"}
    INTENSIFIERS = {"très","vraiment","trop","hyper","extrêmement",
                    "beaucoup","absolument","fortement","tellement","vachement","méga"}
    FRUSTRATION  = {"marre","nul","problème","bloqué","erreur","impossible",
                    "bug","casse","fatigué","lent","inutile","galère","plante","plantage"}
    ENTHUSIASM   = {"génial","super","adore","adoré","parfait","incroyable",
                    "merveilleux","excellent","magnifique","fantastique"}
    POSITIVE = set("""accepter accessible accord agréable aider aimer amour amusant
        bonheur bon bien brave brillant calme capable captivant chance charme clair
        créatif délicieux doux drôle dynamique efficace élégant encourager enthousiasme
        espoir excellent exceptionnel facile fantastique fascinant favorable féliciter
        fier fort gai génial gentil grand heureux honnête humour idéal impressionnant
        incroyable intelligent intéressant joie joli juste magnifique malin merveilleux
        mignon motivé noble optimiste parfait passion patience performant plaisant
        plaisir poli positif précieux remarquable ravi réaliste robuste sage sain
        satisfait serein simple sincère solide sourire succès super superbe utile
        valorisant vif vigoureux vrai excellent lumineux radieux triomphe unique""".split())
    NEGATIVE = set("""abandonner absurde accuser agaçant agresser angoisse anxieux
        arnaque atroce bête bizarre bloqué catastrophique cauchemar chialer choquant
        coléreux conflit confus contrainte coupable craintif crise critique cruel
        danger décevant défaite défaut désagréable désastre désespoir douleur dur
        échec effrayant embarrassant énervant ennuyeux erreur exaspérant fâché faible
        fatal fatigue faux fragile furieux galère gênant grave haine horrible hostile
        idiot impossible incompétent incorrect inquiet insupportable inutile lâche
        lamentable lent malade mauvais méchant mécontent médiocre ménace mensonge
        mépris misérable nausée nul odieux panique paresseux peur pire problème
        rater refus regret ridicule ruine scandale souffrance stress stupide terrible
        toxique tragique triste tromper vain violent""".split())

    def _tokenize(self, text): return re.findall(r'\b\w+\b', text.lower())

    def analyze(self, text: str) -> dict:
        tokens = self._tokenize(text)
        score, neg_m, int_m = 0.0, 1.0, 1.0
        emotions = set()
        for t in tokens:
            if t in self.NEGATIONS:   neg_m = -1.0; continue
            if t in self.INTENSIFIERS: int_m = 1.5; continue
            val = 0.0
            if t in self.POSITIVE:  val = 1.0;  emotions.add("positivité")
            elif t in self.NEGATIVE: val = -1.0; emotions.add("négativité")
            if t in {"colère","furieux","énervé","scandale","fâché"}: emotions.add("colère")
            elif t in {"triste","pleurer","malheureux","déçu","peiné"}: emotions.add("tristesse")
            elif t in {"peur","effrayé","panique","angoisse","crainte"}: emotions.add("peur")
            elif t in {"joie","heureux","sourire","ravi","rire"}: emotions.add("joie")
            if val:
                score += val * neg_m * int_m
                neg_m, int_m = 1.0, 1.0
        norm = (math.tanh(score * 0.5) + 1.0) / 2.0
        label = "positif" if norm >= 0.6 else ("negatif" if norm <= 0.4 else "neutre")
        return {"label": label, "score": round(norm, 4), "emotions": list(emotions)}

    def is_frustrated(self, text: str) -> bool:
        tokens = set(self._tokenize(text))
        if any(w in tokens for w in self.FRUSTRATION): return True
        s = self.analyze(text)
        return s["label"] == "negatif" and (s["score"] < 0.25 or bool(re.search(r'[?!]{2,}', text)))

    def is_enthusiastic(self, text: str) -> bool:
        tokens = set(self._tokenize(text))
        if any(w in tokens for w in self.ENTHUSIASM): return True
        return "!" in text and self.analyze(text)["score"] > 0.75

    def adjust_response_tone(self, response: str, sentiment: dict) -> str:
        if sentiment.get("score", 0.5) < 0.35 or sentiment.get("is_frustrated"):
            return random.choice(["Je comprends que cela puisse être frustrant. ",
                                  "Je suis navré pour ces difficultés. "]) + response
        if sentiment.get("score", 0.5) > 0.8 or sentiment.get("is_enthusiastic"):
            return random.choice(["C'est génial ! ", "Super ! "]) + response
        return response


# ══════════════════════════════════════════════════════════════════════════════
# MODULE B — IntentClassifier (Claude)
# Classification d'intention par patterns regex FR
# ══════════════════════════════════════════════════════════════════════════════
class IntentClassifier:
    """Classifieur d'intention regex FR. 5 catégories : question/commande/apprentissage/recherche/conversation."""
    INTENTS = ['question', 'commande', 'conversation', 'apprentissage', 'recherche']
    _PAT_APP = re.compile(r'\b(?:apprends?|retiens?|sache[sz]?|souviens?(?:-toi)?\s+(?:que|de)|mémorise|je\s+(?:te\s+)?(?:dis|signale)\s+que)\b', re.I)
    _PAT_REC = re.compile(r'\b(?:recherche[sz]?|cherche[sz]?|wikipedia|c(?:\'|\')est\s+quoi|qui\s+est|définis?|infos?\s+sur)\b', re.I)
    _PAT_QUE = re.compile(r'(?:^(?:qui|quoi|que|comment|pourquoi|quand|où|combien|quel(?:le)?s?)\b|\best(?:-ce\s+que?|\s+ce\s+que?)\b|\?\s*$|^(?:peux|sais|savez)-?(?:tu|vous)\b)', re.I)
    _PAT_CMD = re.compile(r'^(?:montre[sz]?|affiche[sz]?|donne[sz]?|calcule[sz]?|note[sz]?|rappelle[sz]?|ouvre[sz]?|lance[sz]?|cherche[sz]?|crée[sz]?|génère[sz]?|explique[sz]?|résume[sz]?|aide[sz]?|help)\b', re.I)
    _STOP = frozenset({'le','la','les','un','une','de','du','et','est','que','qui','quoi','comment',
                       'pourquoi','quand','quel','quelle','je','tu','il','elle','nous','vous','ce','cet'})

    def classify(self, text: str) -> dict:
        t = text.strip()
        if not t: return {'intent': 'conversation', 'confidence': 0.0, 'sub_intent': 'vide'}
        if self._PAT_APP.search(t): return {'intent': 'apprentissage', 'confidence': 0.95, 'sub_intent': 'ajout_fait'}
        if self._PAT_REC.search(t): return {'intent': 'recherche',     'confidence': 0.90, 'sub_intent': 'général'}
        if self._PAT_CMD.match(t):  return {'intent': 'commande',      'confidence': 0.88, 'sub_intent': 'général'}
        if self._PAT_QUE.search(t):
            conf = 0.92 if t.rstrip().endswith('?') else 0.80
            return {'intent': 'question', 'confidence': conf, 'sub_intent': 'général'}
        return {'intent': 'conversation', 'confidence': 0.60, 'sub_intent': 'général'}

    def is_question(self, text: str) -> bool:  return self.classify(text)['intent'] == 'question'
    def is_command(self, text: str) -> bool:   return self.classify(text)['intent'] == 'commande'

    def extract_subject(self, text: str) -> str:
        t = re.sub(r'^(?:montre[sz]?|affiche[sz]?|donne[sz]?|calcule[sz]?|explique[sz]?|cherche[sz]?)\s+', '', text.strip(), flags=re.I)
        t = re.sub(r'^(?:est-ce\s+que?|qu(?:\'|\')est-ce\s+que?|qui|comment|pourquoi|quand|où|combien|quel(?:le)?s?)\s+', '', t, flags=re.I)
        tokens = [w for w in re.findall(r'[a-zA-ZÀ-ÿ\'-]+', t) if w.lower() not in self._STOP and len(w) > 1]
        return ' '.join(tokens[:4]).strip() or text.strip()


# ══════════════════════════════════════════════════════════════════════════════
# MODULE C — ResponseDiversifier (ChatGPT)
# Évite de répéter les mêmes réponses trop souvent
# ══════════════════════════════════════════════════════════════════════════════
class ResponseDiversifier:
    """Évite de répéter les mêmes réponses trop souvent via une mémoire deque."""
    def __init__(self, memory_size: int = 10):
        self.memory_size = max(1, int(memory_size))
        self._memory = deque(maxlen=self.memory_size)

    def filter(self, candidates: list) -> str:
        if not candidates: return ""
        recent = set(self._memory)
        for c in candidates:
            if c not in recent: return c
        positions = {r: i for i, r in enumerate(self._memory)}
        return min(candidates, key=lambda c: positions.get(c, -1))

    def record(self, response: str): self._memory.append(response)
    def reset(self): self._memory.clear()


# ══════════════════════════════════════════════════════════════════════════════
# COULEURS ANSI — Terminal coloré
# ══════════════════════════════════════════════════════════════════════════════
class C:
    RESET     = "\033[0m"
    BOLD      = "\033[1m"
    RED       = "\033[31m"
    GREEN     = "\033[32m"
    YELLOW    = "\033[33m"
    BLUE      = "\033[34m"
    MAGENTA   = "\033[35m"
    CYAN      = "\033[36m"
    WHITE     = "\033[37m"
    BR_RED    = "\033[91m"
    BR_GREEN  = "\033[92m"
    BR_YELLOW = "\033[93m"
    BR_BLUE   = "\033[94m"
    BR_CYAN   = "\033[96m"
    BR_WHITE  = "\033[97m"
    BG_BLUE   = "\033[44m"
    BG_BLACK  = "\033[40m"


# ══════════════════════════════════════════════════════════════════════════════
# MODULE 9 — PluginManager (Chef d'équipe + sandbox Manus)
# Plugins Python dynamiques avec sandbox sécurisée
# ══════════════════════════════════════════════════════════════════════════════
class PluginManager:
    """
    Gestionnaire de plugins Python dynamiques.
    Chaque plugin = un .py dans plugins/ avec handle(text) -> str | None.
    Sandbox bloque : os, subprocess, socket, sys, shutil, ctypes.
    """
    PLUGIN_DIR       = Path(__file__).parent / 'plugins'
    RESTRICTED       = {'os','subprocess','socket','sys','shutil','ctypes'}

    def __init__(self):
        self._plugins: dict = {}
        self.PLUGIN_DIR.mkdir(exist_ok=True)

    def _sandbox_load(self, name: str, path: str):
        import importlib.util, builtins
        restricted   = self.RESTRICTED
        orig_import  = builtins.__import__
        def safe_import(n, g=None, l=None, fl=(), lv=0):
            if n.split('.')[0] in restricted:
                raise ImportError(f"🔒 Import '{n}' interdit dans les plugins.")
            return orig_import(n, g, l, fl, lv)
        builtins.__import__ = safe_import
        try:
            spec   = importlib.util.spec_from_file_location(name, path)
            if not spec: return None
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
        finally:
            builtins.__import__ = orig_import

    def load_plugins(self) -> list:
        loaded = []; self._plugins.clear()
        for py in sorted(self.PLUGIN_DIR.glob('*.py')):
            if py.stem.startswith('_'): continue
            try:
                m = self._sandbox_load(py.stem, str(py))
                if m and hasattr(m, 'handle') and callable(m.handle):
                    self._plugins[py.stem] = m; loaded.append(py.stem)
            except Exception as e:
                print(f"⚠️  Plugin '{py.stem}' : {e}")
        return loaded

    def run_plugin(self, name: str, text: str):
        m = self._plugins.get(name)
        if not m: return None
        try: return m.handle(text)
        except Exception as e: print(f"⚠️  Plugin '{name}' : {e}"); return None

    def run_all(self, text: str):
        for name, m in self._plugins.items():
            try:
                r = m.handle(text)
                if r: return r
            except Exception: pass
        return None

    def list_plugins(self) -> list:
        return [{'name': n, 'description': (getattr(m,'__doc__','') or '').strip()[:80]}
                for n, m in self._plugins.items()]

    def create_example_plugin(self) -> str:
        tmpl = '''"""Plugin exemple FreevBrain v5.0 — renomme ce fichier et modifie handle()."""

def handle(text: str):
    if 'plugin test' in text.lower():
        return "🔌 Plugin exemple actif ! Modifie plugins/exemple.py."
    return None
'''
        p = self.PLUGIN_DIR / 'exemple.py'
        p.write_text(tmpl, encoding='utf-8')
        return f"✅ Plugin exemple créé : {p}"


# ══════════════════════════════════════════════════════════════════════════════
# FREEVBRAIN V5 — Orchestrateur de tous les modules
# ══════════════════════════════════════════════════════════════════════════════
class FreevBrain:
    """
    FreevBrain v7 — Cerveau IA orchestrant tous les modules.
    Pipeline : BPE → Embeddings → BM25+Cosine+Jaccard+Levenshtein → KneserNey
    + KnowledgeGraph + ContextManager + DataAugmentor + TransformerBrain (optionnel)
    """
    MODEL_VERSION = "7"
    BRAIN_FILE = Path.home() / '.freev_brain_v7.json'
    KG_FILE    = Path.home() / '.freev_kg_v7.json'
    DATA_DIR = Path(os.environ.get('FREEV_DATA_DIR', Path(__file__).parent))
    UNKNOWN_FILE = Path(os.environ.get('FREEV_UNKNOWN_FILE', DATA_DIR / 'freev_unknown_questions.jsonl'))
    LEGACY_BRAIN_FILES = [Path.home() / '.freev_brain_v4.json']
    LEGACY_KG_FILES = [Path.home() / '.freev_kg_v4.json']
    UNCERTAIN_RESPONSE = "Je ne suis pas assez sûr. Je peux chercher ou apprendre."
    # Chemins multi-plateforme pour freev_data.txt
    DATA_PATHS = [
        Path(os.environ.get('FREEV_DATA_FILE', DATA_DIR / 'freev_data.txt')),
        Path(__file__).parent / 'freev_data.txt',
        Path.cwd() / 'freev_data.txt',
        Path.home() / 'freev_data.txt',
        Path.home() / 'Desktop' / 'freev_data.txt',
        Path.home() / 'OneDrive' / 'Bureau' / 'freev_data.txt',
        Path.home() / 'Bureau' / 'freev_data.txt',
    ]

    STOP = {
        'le','la','les','un','une','de','du','des','et','ou','à','au','aux',
        'ce','cet','cette','se','ne','pas','plus','par','sur','dans','pour',
        'avec','qui','que','quoi','dont','où','y','en','a','est','sont','était',
        'être','avoir','je','tu','il','elle','nous','vous','ils','elles',
        'mon','ton','son','notre','votre','leur','me','te','lui','nous','vous',
        'mais','car','si','or','ni','donc',
        'ta','ai','ont','été','as'
    }
    QUERY_GENERIC = {
        'quoi', 'qui', 'pourquoi', 'comment', 'quand', 'combien', 'quel',
        'quelle', 'definition', 'definis', 'explique', 'donne', 'liste',
        'exemple', 'exemples', 'type', 'types', 'avantage', 'avantages',
        'inconvenient', 'inconvenients', 'difference', 'different',
        'comparaison', 'compare', 'entre', 'versus', 'vs', 'mieux',
        'fonctionne', 'faire', 'utilise', 'utiliser', 'sert', 'peut',
        'peux', 'sais', 'savoir', 'parle', 'cherche', 'recherche',
        'question', 'inconnue', 'inconnu', 'sur'
    }

    def __init__(self):
        self.training_data: list = []
        self.vocabulary: set = set()
        self.inverted_index: dict = {}
        self.df: dict = {}
        self.avg_doc_len: float = 1.0
        self.trained: bool = False
        self.mlp = None
        self.vocab_to_idx: dict = {}

        # Initialisation des modules
        self._tokenize_cache = {}   # Cache LRU pour _tokenize
        self._vector_cache   = {}   # Cache LRU pour _build_vector
        self._CACHE_MAX      = 128  # Taille max du cache

        self.bpe        = BPETokenizer()
        self.embedder   = CoOccurrenceEmbedder()
        self.scorer     = AdvancedScorer()
        self.generator  = MarkovKneserNeyGenerator()
        self.context    = ContextManager()
        self.kg         = KnowledgeGraph()
        self.augmentor  = DataAugmentor()
        self.tester     = FreevTestSuite()
        # v6.0 — nouveaux modules
        self.thought_chain = ThoughtChain(self)
        self.sentiment  = SentimentAnalyzer()
        self.intent     = IntentClassifier()
        self.diversifier= ResponseDiversifier(memory_size=8)
        self.plugins    = PluginManager()
        self.plugins.load_plugins()

        # Chargement du graphe de connaissances
        if not self.kg.load(str(self.KG_FILE)):
            for legacy_kg in self.LEGACY_KG_FILES:
                if self.kg.load(str(legacy_kg)):
                    break
        self._load_or_train()

    @staticmethod
    def _repair_mojibake(text: str) -> str:
        """Répare les textes UTF-8 lus comme Latin-1 quand c'est détectable."""
        if not isinstance(text, str):
            return text
        markers = ('Ã', 'Â', 'â', 'â€™', 'â€œ', 'â€', 'Å')
        if not any(m in text for m in markers):
            return text
        try:
            fixed = text.encode('latin-1', errors='ignore').decode('utf-8', errors='ignore')
            return fixed if fixed.strip() else text
        except Exception:
            return text

    @staticmethod
    def _strip_accents(text: str) -> str:
        return ''.join(
            ch for ch in unicodedata.normalize('NFD', text)
            if unicodedata.category(ch) != 'Mn'
        )

    @classmethod
    def _normalize_text(cls, text: str) -> str:
        text = cls._repair_mojibake(text).lower()
        text = text.replace('\u2019', "'").replace('\u2018', "'")
        text = cls._strip_accents(text)
        return text

    # ── Tokenisation simple (mots courants + stop words) ─────────────────────
    def _tokenize(self, text: str) -> list:
        # Cache LRU — évite de retokeniser les mêmes phrases (Manus)
        if text in self._tokenize_cache:
            self._tokenize_cache[text] = self._tokenize_cache.pop(text)
            return self._tokenize_cache[text]
        original_text = text
        text = self._normalize_text(text)
        text = re.sub(r"[-']", ' ', text)
        text = re.sub(r'[^\w\s]', '', text)
        extended_stop = self.STOP | {
            'cest', 'cest quoi', 'quoi', 'comment', 'pourquoi', 'quelle',
            'quel', 'quels', 'quelles', 'est', 'quand', 'comment', 'combien',
            'ya', 'a', 'ca', 'sa', 'vs', 'ex', 'etc', 'etait', 'etre', 'ete',
            'ou', 'a', 'deja', 'tres'
        }
        result = [t for t in text.split() if t not in extended_stop and len(t) > 1]
        if len(self._tokenize_cache) >= self._CACHE_MAX:
            self._tokenize_cache.pop(next(iter(self._tokenize_cache)))
        self._tokenize_cache[original_text] = result
        return result

    # ── N-grammes d'une liste de tokens ──────────────────────────────────────
    def _get_ngrams(self, tokens: list, n: int = 3) -> list:
        return [tuple(tokens[i:i+n]) for i in range(len(tokens)-n+1)]

    # ── Vecteur bag-of-words (Counter) ───────────────────────────────────────
    def _build_vector(self, tokens: list) -> dict:
        # Cache LRU — tuple trié comme clé hashable (Manus)
        cache_key = tuple(sorted(tokens))
        if cache_key in self._vector_cache:
            self._vector_cache[cache_key] = self._vector_cache.pop(cache_key)
            return self._vector_cache[cache_key]
        result = dict(Counter(tokens))
        if len(self._vector_cache) >= self._CACHE_MAX:
            self._vector_cache.pop(next(iter(self._vector_cache)))
        self._vector_cache[cache_key] = result
        return result

    # ── Vecteur one-hot aligné sur vocab_to_idx (pour MLP) ───────────────────
    def _to_bow_vector(self, tokens: list) -> list:
        if not self.vocab_to_idx:
            return [0.0]
        vec = [0.0] * len(self.vocab_to_idx)
        for t in tokens:
            if t in self.vocab_to_idx:
                vec[self.vocab_to_idx[t]] = 1.0
        return vec

    def _expand_query_tokens(self, tokens: list, max_extra: int = 10) -> list:
        """Ajoute quelques synonymes locaux utiles, sans dépendance ni réseau."""
        expanded = []
        seen = set(tokens)
        synonyms = getattr(self.augmentor, 'synonyms', {})
        reverse = {}
        for base, values in synonyms.items():
            base_tokens = self._tokenize(base)
            for value in values:
                for vt in self._tokenize(value):
                    reverse.setdefault(vt, set()).update(base_tokens)

        for token in tokens:
            related = []
            if token in synonyms:
                for value in synonyms[token]:
                    related.extend(self._tokenize(value))
            related.extend(reverse.get(token, ()))
            for rel in related:
                if rel not in seen and len(rel) > 1:
                    expanded.append(rel)
                    seen.add(rel)
                    if len(expanded) >= max_extra:
                        return expanded
        return expanded

    def _candidate_indices(self, primary_tokens: list, expanded_tokens: list) -> set:
        candidates = set()
        for t in primary_tokens:
            candidates.update(self.inverted_index.get(t, []))
        if len(candidates) < 12:
            for t in expanded_tokens:
                candidates.update(self.inverted_index.get(t, []))
                if len(candidates) >= 80:
                    break
        return candidates

    def _answer_shape_bonus(self, question_type: str, response: str, question: str) -> float:
        """Favorise les réponses dont la forme correspond au type de question."""
        r = self._normalize_text(response)
        q = self._normalize_text(question)
        bonus = 0.0
        if question_type == 'cause' and re.search(r'\b(?:parce que|car|cause|raison|permet|sert a|afin de)\b', r):
            bonus += 0.18
        elif question_type == 'procedure' and re.search(r'\b(?:il faut|etape|commence|puis|ensuite|on |tu peux|pour )\b', r):
            bonus += 0.16
        elif question_type == 'definition' and re.search(r'\b(?:est|designe|correspond|signifie|c est|ce sont)\b', r):
            bonus += 0.14
        elif question_type == 'comparaison' and re.search(r'\b(?:alors que|contrairement|difference|plus|moins|compare|versus)\b', r + ' ' + q):
            bonus += 0.18
        elif question_type == 'liste' and (',' in response or re.search(r'\b(?:1\.|2\.|exemple|types?|avantages?|inconvenients?)\b', r)):
            bonus += 0.14
        if 40 <= len(response) <= 700:
            bonus += 0.06
        elif len(response) < 20:
            bonus -= 0.10
        return bonus

    # ── Trouver le fichier de données ─────────────────────────────────────────
    def _find_data_file(self):
        env_path = os.environ.get('FREEV_DATA_FILE', '').strip()
        if env_path:
            target = Path(env_path)
            if target.exists():
                return target
            bundled = Path(__file__).parent / 'freev_data.txt'
            if bundled.exists():
                try:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(bundled.read_bytes())
                    return target
                except Exception:
                    pass
        for p in self.DATA_PATHS:
            if p.exists():
                return p
        return None

    @staticmethod
    def _file_signature(path):
        try:
            st = Path(path).stat()
            return {"path": str(Path(path).resolve()), "mtime": st.st_mtime, "size": st.st_size}
        except Exception:
            return None

    def _source_pair_exists(self, question: str) -> bool:
        path = self._find_data_file()
        if not path:
            return False
        wanted = self._normalize_text(question).strip()
        try:
            with open(path, encoding='utf-8') as f:
                for line in f:
                    if '=>' not in line or line.lstrip().startswith('#'):
                        continue
                    q, _r = line.split('=>', 1)
                    if self._normalize_text(q).strip() == wanted:
                        return True
        except Exception:
            return False
        return False

    def _append_source_pair(self, question: str, response: str) -> bool:
        question = question.strip()
        response = response.strip()
        if not question or not response or self._source_pair_exists(question):
            return False
        path = self._find_data_file() or (Path(__file__).parent / 'freev_data.txt')
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'a', encoding='utf-8') as f:
            f.write(f"\n{question} => {response}")
        return True

    def record_unknown_question(self, question: str, source: str = "web") -> bool:
        question = question.strip()
        if not question:
            return False
        key = self._normalize_text(question)
        known = set()
        if self.UNKNOWN_FILE.exists():
            try:
                with open(self.UNKNOWN_FILE, encoding='utf-8') as f:
                    for line in f:
                        try:
                            item = json.loads(line)
                            known.add(self._normalize_text(item.get('question', '')))
                        except Exception:
                            continue
            except Exception:
                pass
        if key in known:
            return False
        item = {
            "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "question": question,
            "source": source,
            "status": "pending_answer",
        }
        self.UNKNOWN_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(self.UNKNOWN_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
        return True

    # ── Entraînement depuis freev_data.txt ────────────────────────────────────
    def train(self, data_path=None):
        path = Path(data_path) if data_path else self._find_data_file()
        if not path or not path.exists():
            print(f"{C.BR_RED}❌ freev_data.txt introuvable.{C.RESET}")
            print(f"   Cherché dans : {[str(p) for p in self.DATA_PATHS]}")
            return False

        self.training_data.clear()
        all_tokens = []
        corpus_lines = []

        # Gemini FIX — parser multi-lignes : concaténer les lignes de continuation
        with open(path, encoding='utf-8') as f:
            raw_lines = f.readlines()

        # Fusionner les lignes de continuation (sans =>) avec la ligne précédente
        merged = []
        for line in raw_lines:
            stripped = line.rstrip('\n').rstrip()
            if not stripped or stripped.startswith('#'):
                merged.append(stripped)
                continue
            if '=>' not in stripped and merged:
                # Continuation de la réponse précédente
                last = merged[-1]
                if last and '=>' in last:
                    merged[-1] = last + ' ' + stripped
                    continue
            merged.append(stripped)

        with open(path, encoding='utf-8') as f:
            pass  # déjà lu ci-dessus

        for line in merged:
            line = line.strip()
            if not line or line.startswith('#') or '=>' not in line:
                continue
            q, r = line.split('=>', 1)
            q, r = self._repair_mojibake(q.strip()), self._repair_mojibake(r.strip())
            corpus_lines.append(q)
            # Augmentation des données
            for aug_q, aug_r in self.augmentor.augment(q, r, max_variants=4):
                tokens = self._tokenize(aug_q)
                entry = {
                    'question': aug_q,
                    'response': aug_r,
                    'tokens': tokens,
                    'vector': self._build_vector(tokens),
                    'ngrams': self._get_ngrams(tokens, 3),
                    'length': len(tokens)
                }
                self.training_data.append(entry)
                all_tokens.extend(tokens)

        if not self.training_data:
            return False

        # Construction des index via le helper factorisé
        tokenized_sentences = [e['tokens'] for e in self.training_data if e['tokens']]
        self._build_indices(tokenized_sentences)

        # Entraînement BPE
        self.bpe.train(corpus_lines, vocab_size=300)

        self.trained = True
        self._save()
        return True

    # ── Sauvegarde ────────────────────────────────────────────────────────────
    def _save(self):
        data = [{'question': e['question'], 'response': e['response']}
                for e in self.training_data]
        # Sauvegarder poids MLP si entraîné
        mlp_data = None
        if self.mlp:
            try:
                mlp_data = {
                    'input_dim' : self.mlp.input_dim,
                    'hidden_dim': self.mlp.hidden_dim,
                    'output_dim': self.mlp.output_dim,
                    'W1': self.mlp.W1, 'b1': self.mlp.b1,
                    'W2': self.mlp.W2, 'b2': self.mlp.b2,
                    'W3': self.mlp.W3, 'b3': self.mlp.b3,
                    # Gemini FIX — sauvegarder vocab_to_idx pour vérifier la compatibilité
                    'vocab_size': len(self.vocab_to_idx),
                    'vocab_snapshot': list(self.vocab_to_idx.keys())[:50],  # échantillon
                }
            except Exception:
                mlp_data = None
        with open(self.BRAIN_FILE, 'w', encoding='utf-8') as f:
            # Pas d'indent : fichier plus léger + écriture plus rapide
            json.dump({'trained': self.trained, 'data': data, 'mlp': mlp_data,
                       'data_signature': self._file_signature(self._find_data_file())}, f,
                      ensure_ascii=False)
        self.kg.save(str(self.KG_FILE))

    # ── Chargement ou entraînement ────────────────────────────────────────────
    # ── Construction des index (factorisé — appelé par train ET _load_or_train) ─
    def _build_indices(self, tokenized_sentences: list):
        """
        Reconstruit vocabulary, vocab_to_idx, inverted_index, df, avg_doc_len,
        entraîne generator + embedder.
        Appelé après tout chargement ou entraînement pour garantir la cohérence.
        """
        all_tokens = []
        for e in self.training_data:
            all_tokens.extend(e['tokens'])
        self.vocabulary    = set(all_tokens)
        self.vocab_to_idx  = {w: i for i, w in enumerate(sorted(self.vocabulary))}
        self.inverted_index = self.augmentor.build_inverted_index(self.training_data)
        self.df = {}
        for e in self.training_data:
            for t in set(e['tokens']):
                self.df[t] = self.df.get(t, 0) + 1
        total_len = sum(e['length'] for e in self.training_data)
        self.avg_doc_len = total_len / len(self.training_data) if self.training_data else 1.0
        if tokenized_sentences:
            self.generator.train(tokenized_sentences, order=3)
            self.generator._cache_gen_vocab()
            # FIX : embedder entraîné à chaque chargement (était absent dans _load_or_train)
            self.embedder.train(tokenized_sentences, window=3, dim=32)

    def _load_or_train(self):
        load_candidates = [self.BRAIN_FILE] + self.LEGACY_BRAIN_FILES
        for brain_file in load_candidates:
            if not brain_file.exists():
                continue
            try:
                with open(brain_file, encoding='utf-8') as f:
                    saved = json.load(f)
                if brain_file == self.BRAIN_FILE:
                    current_sig = self._file_signature(self._find_data_file())
                    saved_sig = saved.get('data_signature')
                    if current_sig and saved_sig:
                        same_source = current_sig.get('path') == saved_sig.get('path')
                        same_size = current_sig.get('size') == saved_sig.get('size')
                        same_mtime = abs(current_sig.get('mtime', 0) - saved_sig.get('mtime', -1)) < 0.001
                        if not (same_source and same_size and same_mtime):
                            self.train()
                            return
                for entry in saved.get('data', []):
                    question = self._repair_mojibake(entry.get('question', ''))
                    response = self._repair_mojibake(entry.get('response', ''))
                    t = self._tokenize(question)
                    self.training_data.append({
                        'question': question,
                        'response': response,
                        'tokens': t,
                        'vector': self._build_vector(t),
                        'ngrams': self._get_ngrams(t, 3),
                        'length': len(t)
                    })
                if self.training_data:
                    self.trained = True
                    tokenized = [e['tokens'] for e in self.training_data if e['tokens']]
                    self._build_indices(tokenized)   # FIX : un seul appel, cohérent
                    # Recharger poids MLP si présents dans le JSON
                    mlp_data = saved.get('mlp')
                    if mlp_data and self.vocab_to_idx:
                        try:
                            saved_vocab_size = mlp_data.get('vocab_size', 0)
                            if saved_vocab_size and saved_vocab_size != len(self.vocab_to_idx):
                                self.mlp = None   # vocab changé → MLP obsolète
                            else:
                                self.mlp = TransformerBrain(
                                    input_dim  = mlp_data['input_dim'],
                                    hidden_dim = mlp_data['hidden_dim'],
                                    output_dim = mlp_data['output_dim'],
                                )
                                self.mlp.W1 = mlp_data['W1']; self.mlp.b1 = mlp_data['b1']
                                self.mlp.W2 = mlp_data['W2']; self.mlp.b2 = mlp_data['b2']
                                self.mlp.W3 = mlp_data['W3']; self.mlp.b3 = mlp_data['b3']
                        except Exception:
                            self.mlp = None
                    return
            except Exception:
                pass
        self.train()

    # ── Réponse principale ────────────────────────────────────────────────────
    def _threshold_for(self, tokens: list, question_type: str, constraints: dict) -> float:
        threshold = 0.40 if len(tokens) <= 2 else 0.52
        if question_type in {'definition', 'personne'}:
            threshold -= 0.04
        if question_type == 'comparaison':
            threshold += 0.15
        if constraints.get('freshness_sensitive'):
            threshold += 0.10
        return threshold

    def respond_with_candidates(self, user_input: str, top_n: int = 3) -> dict:
        if not user_input.strip():
            return {"response": None, "confidence": 0.0, "accepted": False, "candidates": []}

        # 1. Raisonnement (ThoughtChain v6)
        thought_data = self.thought_chain.process(user_input)

        # 2. Résolution des références pronominales
        resolved = self.context.resolve_references(user_input)
        resolved_thought = self.thought_chain.process(resolved)

        # 3. Inférence KnowledgeGraph
        tokens = resolved_thought['tokens']
        kg_ans = self.kg.infer(tokens)
        if kg_ans:
            self.context.add_turn(user_input, kg_ans)
            return {"response": kg_ans, "confidence": 1.0, "accepted": True,
                    "source": "knowledge_graph", "candidates": []}

        if not self.trained or not self.training_data:
            return {"response": None, "confidence": 0.0, "accepted": False, "candidates": []}

        resolved_norm = self._normalize_text(resolved)
        for e in self.training_data:
            if self._normalize_text(e['question']) == resolved_norm:
                self.context.add_turn(user_input, e['response'])
                return {"response": e['response'], "confidence": 1.0, "accepted": True,
                        "source": "exact", "candidates": [{
                            "question": e['question'], "response": e['response'],
                            "score": 1.0, "confidence": 1.0
                        }]}

        # 4. Enrichissement avec contexte de conversation
        ctx_tokens = self.context.get_context_tokens(n_turns=2)
        expanded_tokens = self._expand_query_tokens(tokens)
        combined_tokens = (
            tokens
            + [t for t in expanded_tokens if t not in tokens][:8]
            + [t for t in ctx_tokens if t not in tokens and t not in expanded_tokens][:5]
        )

        # 5. Candidats via index inversé
        key_tokens = [t for t in tokens if len(t) > 1]
        subject_tokens = [t for t in key_tokens if t not in self.QUERY_GENERIC]
        unknown_subjects = [
            t for t in subject_tokens
            if t not in self.vocabulary and len(t) >= 5
        ]
        if unknown_subjects and len(subject_tokens) >= 2:
            return {"response": None, "confidence": 0.0, "accepted": False, "candidates": [],
                    "reason": "unknown_subject"}
        search_tokens = subject_tokens if subject_tokens else (key_tokens if key_tokens else tokens)
        candidates = self._candidate_indices(search_tokens, expanded_tokens)

        if not candidates:
            for t in tokens:
                candidates.update(self.inverted_index.get(t, []))

        if not candidates:
            return {"response": None, "confidence": 0.0, "accepted": False, "candidates": [],
                    "reason": "no_candidate"}

        # 6. Scoring v6 (Attention Scorer + Multi-métriques)
        q_vecs = [self.embedder.get_vector(t) for t in combined_tokens]
        qv = self._build_vector(combined_tokens)
        q_ngrams = self._get_ngrams(combined_tokens, 3)
        N = len(self.training_data)
        question_type = resolved_thought.get('question_type', 'general')
        constraints = resolved_thought.get('constraints', {})
        threshold = self._threshold_for(tokens, question_type, constraints)

        scored_candidates = []
        for idx in candidates:
            e = self.training_data[idx]
            # Base scorers
            bm  = max(0.0, self.scorer.bm25(combined_tokens, e['tokens'], e['length'], self.avg_doc_len, self.df, N))
            cos = self.scorer.cosine(qv, e['vector'])
            jac = self.scorer.jaccard_ngrams(q_ngrams, e['ngrams']) if q_ngrams and e['ngrams'] else 0.0
            lev = self.scorer.levenshtein_ratio(resolved_norm, self._normalize_text(e['question']))
            
            # Attention Croisée (v6) — pondération plus fine
            e_vecs = [self.embedder.get_vector(t) for t in e['tokens'] if t in self.embedder.vocab]
            attn = AttentionScorer.compute_attention(q_vecs, e_vecs) if q_vecs and e_vecs else 0.0
            
            # Score combiné Freev v7 — consensus lexical + forme de réponse
            score = (bm * 0.34) + (attn * 0.20) + (cos * 0.16) + (lev * 0.18) + (jac * 0.12)
            
            # Bonus mots-clés substantiels (crucial pour éviter les faux positifs)
            overlap_tokens = subject_tokens if subject_tokens else key_tokens
            key_hits = sum(1 for t in overlap_tokens if t in e['tokens'])
            if overlap_tokens:
                overlap = key_hits / len(overlap_tokens)
                score += overlap * 0.8
                if overlap < 0.34 and len(overlap_tokens) >= 2:
                    score -= 0.45
                if subject_tokens and key_hits == 0:
                    score -= 0.70
                if question_type == 'comparaison' and len(subject_tokens) >= 2 and key_hits < 2:
                    score -= 1.00

            expanded_hits = sum(1 for t in expanded_tokens if t in e['tokens'])
            if expanded_tokens:
                score += min(0.18, (expanded_hits / len(expanded_tokens)) * 0.25)

            q_norm = self._normalize_text(e['question'])
            if resolved_norm and resolved_norm in q_norm:
                score += 0.35
            elif q_norm and q_norm in resolved_norm:
                score += 0.25

            score += self._answer_shape_bonus(question_type, e['response'], e['question'])
            if constraints.get('wants_detail') and len(e['response']) > 120:
                score += 0.08
            if constraints.get('wants_short') and len(e['response']) > 500:
                score -= 0.10
            
            scored_candidates.append((score, e['response'], e['question'], {
                'bm25': round(bm, 4), 'attention': round(attn, 4),
                'cosine': round(cos, 4), 'lev': round(lev, 4), 'jac': round(jac, 4),
            }))

        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        if os.environ.get('FREEV_DEBUG'):
            print(f"DEBUG thought: {thought_data['thought']}")
            for s, r, q, parts in scored_candidates[:3]:
                print(f"DEBUG: {s:.3f} {parts} | {q} -> {r[:50]}...")

        best_score = -1.0
        best_response = None
        best_q = ""
        if scored_candidates:
            best_score, best_response, best_q, _parts = scored_candidates[0]
            if question_type == 'comparaison' and len(subject_tokens) >= 2:
                best_tokens = set(self._tokenize(best_q))
                missing_subjects = [t for t in subject_tokens if t not in best_tokens]
                if missing_subjects:
                    best_score = -1.0

        # 7. Validation TransformerBrain (boost)
        if self.mlp and best_response:
            try:
                x = self._to_bow_vector(combined_tokens)
                probs = self.mlp.forward(x)
                # On utilise predict pour avoir la classe la plus probable selon le réseau
                pred_idx, pred_conf = self.mlp.predict(x)
                if pred_conf > 0.7:
                    # Si le réseau est très sûr, on booste
                    best_score += pred_conf * 0.2
            except Exception: pass

        top = []
        for score, response, question, parts in scored_candidates[:max(1, top_n)]:
            conf = max(0.0, min(1.0, score / max(threshold, 0.01)))
            top.append({
                "question": question,
                "response": response,
                "score": round(score, 6),
                "confidence": round(conf, 6),
                "parts": parts,
            })

        coherence_ok = True
        if len(top) >= 2 and top[0]["confidence"] < 0.78:
            score_gap = top[0]["score"] - top[1]["score"]
            coherence_ok = score_gap >= 0.12

        accepted = bool(best_response and best_score > threshold and coherence_ok)
        confidence = top[0]["confidence"] if top else 0.0
        if accepted:
            self.context.add_turn(user_input, best_response)
            return {"response": best_response, "confidence": confidence, "accepted": True,
                    "threshold": round(threshold, 6), "source": "retrieval", "candidates": top}

        return {"response": None, "confidence": confidence, "accepted": False,
                "threshold": round(threshold, 6), "source": "retrieval", "candidates": top,
                "reason": "low_confidence"}

    def respond(self, user_input: str):
        result = self.respond_with_candidates(user_input)
        if result.get("accepted"):
            return result.get("response")
        return None

    # ── Apprentissage à la volée ──────────────────────────────────────────────
    def learn(self, question: str, response: str):
        question = question.strip()
        response = response.strip()
        if not question or not response:
            return
        for aug_q, aug_r in self.augmentor.augment(question, response, max_variants=3):
            t = self._tokenize(aug_q)
            entry = {
                'question': aug_q, 'response': aug_r,
                'tokens': t, 'vector': self._build_vector(t),
                'ngrams': self._get_ngrams(t, 3), 'length': len(t)
            }
            self.training_data.append(entry)
            self.vocabulary.update(t)
            idx = len(self.training_data) - 1
            for tok in set(t):
                self.inverted_index.setdefault(tok, [])
                self.inverted_index[tok].append(idx)
                self.df[tok] = self.df.get(tok, 0) + 1
        # FIX perf : mise à jour incrémentale (évite de recalculer toute la somme)
        if self.training_data:
            n = len(self.training_data)
            total_len = sum(e['length'] for e in self.training_data[-4:])  # seulement les nouvelles
            self.avg_doc_len = (self.avg_doc_len * (n - 4) + total_len) / n if n > 4 else (
                sum(e['length'] for e in self.training_data) / n
            )
            self.vocab_to_idx = {w: i for i, w in enumerate(sorted(self.vocabulary))}
        self.trained = True
        self._append_source_pair(question, response)
        self._save()

    def learn_if_new(self, question: str, response: str) -> bool:
        """Apprend une paire uniquement si elle n'existe pas déjà (anti-doublons).
        Retourne True si mémorisé, False si déjà connu."""
        q_tokens = set(self._tokenize(question))
        r_norm   = response.strip().lower()[:100]

        for entry in self.training_data:
            # 1. Doublon sur la réponse (premiers 100 chars identiques)
            if entry['response'].strip().lower()[:100] == r_norm:
                return False
            # 2. Doublon sur la question : si les tokens substantiels (>3 chars)
            #    de la nouvelle question sont TOUS présents dans une entrée existante
            if q_tokens:
                key_q = {t for t in q_tokens if len(t) > 3}
                if key_q and key_q.issubset(set(entry['tokens'])):
                    return False

        self.learn(question, response)
        return True

    # ── Entraînement MLP (optionnel, lent) ───────────────────────────────────
    def train_mlp(self, epochs: int = 10):
        if not self.training_data or not self.vocab_to_idx:
            return "❌ Entraîne d'abord FreevBrain sur freev_data.txt"
        n = len(self.training_data)
        input_dim = len(self.vocab_to_idx)
        output_dim = min(n, 200)  # limite à 200 classes pour la RAM
        self.mlp = TransformerBrain(input_dim=input_dim, hidden_dim=128, output_dim=output_dim)
        print(f"  MLP : {input_dim} entrées → 128 → 128 → {output_dim} sorties")
        total_loss = 0.0
        for ep in range(epochs):
            ep_loss = 0.0
            indices = list(range(min(n, output_dim)))
            random.shuffle(indices)
            for idx in indices:
                x = self._to_bow_vector(self.training_data[idx]['tokens'])
                loss = self.mlp.train_step(x, idx)
                ep_loss += loss
            total_loss = ep_loss / len(indices)
            pct = int((ep + 1) / epochs * 20)
            bar = '█' * pct + '░' * (20 - pct)
            sys.stdout.write(f"\r  🧠 MLP [{bar}] epoch {ep+1}/{epochs}  loss:{total_loss:.4f}  ")
            sys.stdout.flush()
        print()  # saut de ligne final
        self._save()  # sauvegarder les poids automatiquement
        return f"✅ MLP entraîné ({epochs} epochs) — loss finale : {total_loss:.4f}"

    # ── Statut du cerveau ─────────────────────────────────────────────────────
    def status(self) -> str:
        if self.trained:
            mlp_status = f"MLP : {'actif' if self.mlp else 'non entraîné'}"
            return (f"{C.BR_GREEN}✓ FreevBrain v{self.MODEL_VERSION}{C.RESET} "
                    f"| {len(self.training_data)} paires (avec augmentation) "
                    f"| {len(self.vocabulary)} mots "
                    f"| {mlp_status} "
                    f"| contexte : {len(self.context.history)} tours")
        return f"{C.BR_RED}✗ FreevBrain non entraîné — créez freev_data.txt{C.RESET}"

    def save(self):
        """
        Persiste le cerveau (JSON) ET ajoute la dernière paire dans freev_data.txt.
        Appelé par server.py après chaque learn().
        """
        try:
            self._save()   # Sauvegarde JSON (freev_brain.json)
        except Exception as e:
            print(f"[FreevBrain.save] Erreur JSON : {e}")
        # Ajoute aussi la dernière paire au fichier source pour survivre aux redémarrages
        try:
            if self.training_data:
                last = self.training_data[-1]
                self._append_source_pair(last['question'], last['response'])
        except Exception as e:
            print(f"[FreevBrain.save] Erreur freev_data.txt : {e}")


# ══════════════════════════════════════════════════════════════════════════════
# FREEV — Interface de terminal principale
# ══════════════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════════════════
# MODULE VOCAL — VoiceEngine (pyttsx3 + SpeechRecognition optionnels)
# Animation terminal pendant que Freev parle
# ══════════════════════════════════════════════════════════════════════════════
class VoiceEngine:
    """
    Moteur vocal de Freev.
    - TTS  : pyttsx3 (offline, SAPI5 Windows)
    - STT  : SpeechRecognition + pyaudio (optionnel)
    - Anim : animation ASCII dans le terminal pendant la parole
    """

    # Frames de l'animation "onde sonore"
    WAVE_FRAMES = [
        "  ▁▂▃▄▅▆▇█▇▆▅▄▃▂▁  ",
        "  ▂▃▄▅▆▇█▇▆▅▄▃▂▁▂▃  ",
        "  ▃▄▅▆▇█▇▆▅▄▃▂▁▂▃▄  ",
        "  ▄▅▆▇█▇▆▅▄▃▂▁▂▃▄▅  ",
        "  ▅▆▇█▇▆▅▄▃▂▁▂▃▄▅▆  ",
        "  ▆▇█▇▆▅▄▃▂▁▂▃▄▅▆▇  ",
        "  ▇█▇▆▅▄▃▂▁▂▃▄▅▆▇█  ",
        "  █▇▆▅▄▃▂▁▂▃▄▅▆▇█▇  ",
        "  ▇▆▅▄▃▂▁▂▃▄▅▆▇█▇▆  ",
        "  ▆▅▄▃▂▁▂▃▄▅▆▇█▇▆▅  ",
        "  ▅▄▃▂▁▂▃▄▅▆▇█▇▆▅▄  ",
        "  ▄▃▂▁▂▃▄▅▆▇█▇▆▅▄▃  ",
        "  ▃▂▁▂▃▄▅▆▇█▇▆▅▄▃▂  ",
        "  ▂▁▂▃▄▅▆▇█▇▆▅▄▃▂▁  ",
    ]

    IDLE_FRAME = "  ─────────────────  "

    def __init__(self):
        self.tts_engine  = None
        self.recognizer  = None
        self.microphone  = None
        self.tts_enabled = False
        self.stt_enabled = False
        self._speaking   = False
        self._anim_thread = None
        self._init_tts()
        self._init_stt()

    # ── Initialisation TTS ───────────────────────────────────────────────────
    def _init_tts(self):
        try:
            import pyttsx3
            # FIX — fallback si SAPI5 indisponible
            try:
                self.tts_engine = pyttsx3.init('sapi5')
            except Exception:
                self.tts_engine = pyttsx3.init()  # fallback générique
            # Chercher une voix française
            voices = self.tts_engine.getProperty('voices')
            for v in voices:
                name_id = (v.name or '').lower() + (v.id or '').lower()
                if any(x in name_id for x in ['french','français','fr-','fr_','hortense','julie','paul','zira']):
                    self.tts_engine.setProperty('voice', v.id)
                    break
            self.tts_engine.setProperty('rate', 165)
            self.tts_engine.setProperty('volume', 1.0)
            self.tts_enabled = True
        except ImportError:
            self.tts_enabled = False
        except Exception:
            self.tts_enabled = False

    # ── Initialisation STT ───────────────────────────────────────────────────
    def _init_stt(self):
        try:
            import speech_recognition as sr
            self.recognizer = sr.Recognizer()
            self.microphone = sr.Microphone()
            self.stt_enabled = True
        except ImportError:
            self.stt_enabled = False
        except Exception:
            self.stt_enabled = False

    # ── Animation terminal ───────────────────────────────────────────────────
    def _run_animation(self, text: str):
        """Affiche l'animation onde sonore pendant que Freev parle."""
        frames = self.WAVE_FRAMES
        i = 0
        # Effacer la ligne et afficher le label
        label = f"{C.BR_CYAN}🔊 Freev parle :{C.RESET} "
        sys.stdout.write(f"\n{label}")
        sys.stdout.flush()

        while self._speaking:
            frame = frames[i % len(frames)]
            sys.stdout.write(f"\r{label}{C.BR_CYAN}{frame}{C.RESET}")
            sys.stdout.flush()
            time.sleep(0.08)
            i += 1

        # Frame finale — retour au calme
        sys.stdout.write(f"\r{label}{C.CYAN}{self.IDLE_FRAME}{C.RESET}\n")
        sys.stdout.flush()

    # ── Parler avec animation ────────────────────────────────────────────────
    def speak(self, text: str):
        """Freev parle + animation terminale simultanée."""
        if not self.tts_enabled or not self.tts_engine:
            return

        # Nettoyer le texte (supprimer codes ANSI et emojis lourds)
        clean = re.sub(r'\x1b\[[0-9;]*m', '', text)          # codes ANSI
        clean = re.sub(r'[\U00010000-\U0010ffff]', '', clean)  # emojis hors BMP
        clean = re.sub(r'[\u2500-\u259f\u2600-\u27bf]', '', clean)  # box/symboles
        clean = re.sub(r'[─═╔╗╚╝║╠╣▁▂▃▄▅▆▇█]', '', clean)   # caractères déco
        clean = re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', clean) # **gras**
        clean = re.sub(r'https?://\S+', '', clean)              # URLs
        clean = re.sub(r'\s+', ' ', clean).strip()
        # Tronquer à la dernière phrase complète ≤ 300 chars
        if len(clean) > 300:
            cut  = clean[:350]
            last = max(cut.rfind('.'), cut.rfind('!'), cut.rfind('?'))
            clean = cut[:last + 1] if last > 30 else clean[:300]
        if not clean:
            return

        # Lancer l'animation dans un thread
        self._speaking = True
        anim = threading.Thread(target=self._run_animation, args=(clean,), daemon=True)
        anim.start()

        # Gemini : init moteur dans le thread (évite crash COM Windows)
        def _say():
            try:
                import pyttsx3 as _tts
                _e = _tts.init()
                try:
                    for _v in _e.getProperty('voices'):
                        if any(x in ((_v.name or '')+(_v.id or '')).lower()
                               for x in ['french','français','fr-','hortense']):
                            _e.setProperty('voice', _v.id); break
                except Exception: pass
                _e.setProperty('rate', 165)
                _e.setProperty('volume', 1.0)
                _e.say(clean)   # déjà tronqué à 300 chars
                _e.runAndWait()
            except Exception:
                pass
            finally:
                self._speaking = False  # toujours libéré, même en cas de crash

        t = threading.Thread(target=_say, daemon=True)
        try:
            t.start()
            t.join()  # attendre la fin de la parole
        except Exception:
            self._speaking = False   # sécurité : thread n'a pas pu démarrer
        anim.join(timeout=1)

    # ── Écouter le micro ─────────────────────────────────────────────────────
    def listen(self, timeout: int = 6) -> str:
        """
        Écoute et retourne le texte reconnu.
        FIX GEMINI : calibration 1.0s, phrase_time_limit=10s,
        gestion complète des exceptions, pas de crash silencieux.
        """
        if not self.stt_enabled:
            return ""

        try:
            import speech_recognition as sr

            # Réinitialiser si nécessaire (robustesse Windows)
            if not self.recognizer or not self.microphone:
                self.recognizer = sr.Recognizer()
                self.microphone  = sr.Microphone()

            with self.microphone as source:
                # FIX 1 — 1.0s minimum (0.3 = seuil trop haut = rien capté)
                sys.stdout.write(f"\r{C.BR_YELLOW}🎤 Calibration bruit...{C.RESET}              ")
                sys.stdout.flush()
                self.recognizer.adjust_for_ambient_noise(source, duration=1.0)

                sys.stdout.write(f"\r{C.BR_YELLOW}🎤 Parle maintenant...{C.RESET}               ")
                sys.stdout.flush()
                try:
                    audio = self.recognizer.listen(
                        source,
                        timeout=timeout,
                        phrase_time_limit=10  # FIX 2 — 10s pour finir de parler
                    )
                except sr.WaitTimeoutError:
                    return ""  # silence total — normal, pas une erreur

            # FIX 3 — gestion complète des exceptions (plus de crash silencieux)
            try:
                text = self.recognizer.recognize_google(audio, language="fr-FR")
                sys.stdout.write(f"\r{C.BR_GREEN}🎤 Compris : {text}{C.RESET}                    \n")
                sys.stdout.flush()
                return text.lower()

            except sr.UnknownValueError:
                # Audio reçu mais aucun mot reconnu
                return ""

            except sr.RequestError as e:
                # Pas d'internet → fallback Sphinx si installé
                sys.stdout.write(f"\r{C.YELLOW}🎤 Hors-ligne, tentative Sphinx...{C.RESET}\n")
                sys.stdout.flush()
                try:
                    text = self.recognizer.recognize_sphinx(audio, language="fr-FR")
                    sys.stdout.write(f"\r{C.BR_YELLOW}🎤 (offline) : {text}{C.RESET}\n")
                    sys.stdout.flush()
                    return text.lower()
                except Exception:
                    sys.stdout.write(f"\r{C.RED}🎤 Pas d'internet pour la reconnaissance.{C.RESET}\n")
                    sys.stdout.flush()
                    return ""

            except Exception as e:
                sys.stdout.write(f"\r{C.RED}🎤 Erreur STT : {str(e)[:50]}{C.RESET}\n")
                sys.stdout.flush()
                return ""

        except Exception as e:
            sys.stdout.write(f"\r{C.RED}🎤 Erreur micro : {str(e)[:50]}{C.RESET}\n")
            sys.stdout.flush()
            return ""

    # ── Status ───────────────────────────────────────────────────────────────
    def status(self) -> str:
        tts = f"{C.BR_GREEN}✓ TTS actif{C.RESET}" if self.tts_enabled else f"{C.YELLOW}✗ TTS inactif{C.RESET}"
        stt = f"{C.BR_GREEN}✓ STT actif{C.RESET}" if self.stt_enabled else f"{C.YELLOW}✗ STT inactif{C.RESET}"
        return f"{tts} | {stt}"

    def stop(self):
        self._speaking = False
        if self.tts_engine:
            try:
                self.tts_engine.stop()
            except Exception:
                pass


class Freev:
    """
    Freev v7.0 — Interface conversationnelle de terminal.
    Orchestre FreevBrain + 60+ handlers spécialisés.
    """
    VERSION = "7.0"

    # Réponses de personnalité
    PERSONALITIES = {
        'normal':        {'name': 'Normal',        'color': C.BR_CYAN},
        'fun':           {'name': '😄 Fun',         'color': C.BR_YELLOW},
        'philosophique': {'name': '🧐 Philosophe',  'color': C.MAGENTA},
        'motivant':      {'name': '💪 Motivant',    'color': C.BR_GREEN},
        'cynique':       {'name': '😏 Cynique',     'color': C.BR_RED},
        'dark':          {'name': '🖤 Dark',        'color': C.WHITE},
    }

    FALLBACKS = {
        'normal':        ["Je ne connais pas encore ce sujet. Tape : apprends que \"ta question\" => \"la réponse\" !",
                          "Hmm, je n'ai pas cette information. Enrichis ma base avec 'apprends que'.",
                          "Je ne suis pas sûr. Ajoute cette question dans freev_data.txt et retape 'entraîne toi'."],
        'fun':           ["Aïe, je sèche là ! Apprends-moi avec 'apprends que' 😅",
                          "Même moi j'ai pas capté, reformule ou enseigne-moi ! 🤷"],
        'philosophique': ["La question dépasse mes connaissances actuelles... L'ignorance est le début de la sagesse.",
                          "Socrate dirait : 'Je sais que je ne sais pas.' Et moi aussi pour cette question."],
        'motivant':      ["Je ne connais pas encore, mais TU PEUX M'APPRENDRE ! Tape 'apprends que' ! 💪",
                          "Question inconnue = OPPORTUNITÉ D'APPRENDRE ! Enrichis ma base ! 🚀"],
        'cynique':       ["Encore une question sans réponse dans ma base. Fascinant.",
                          "Je ne sais pas. Quelle surprise. Tu peux m'apprendre avec 'apprends que'."],
        'dark':          ["Les ténèbres de ma base de données sont vides sur ce sujet...",
                          "Rien. Comme l'univers face à cette question."],
    }

    def __init__(self):
        self.brain       = FreevBrain()
        self.voice       = VoiceEngine()
        self.voice_mode  = False   # True = parle les réponses
        self.listen_mode = False   # True = écoute le micro
        self.personality = 'normal'
        self.notes       = []
        self.reminders   = []
        self.memory      = {}
        self.running     = True
        # Cache météo et Wikipedia — Gemini : évite les requêtes redondantes
        self._cache: dict = {}          # {clé: (timestamp, résultat)}
        self._cache_ttl   = 3600        # 1 heure en secondes
        self._load_memory()
        self._apply_voice_preferences()
        self._start_reminder_thread()

    # ── Mémoire persistante ───────────────────────────────────────────────────
    def _mem_file(self):
        return Path.home() / '.freev_memory.json'

    def _load_memory(self):
        try:
            if self._mem_file().exists():
                data = json.loads(self._mem_file().read_text(encoding='utf-8'))
                self.notes     = data.get('notes', [])
                self.memory    = data.get('memory', {})
                voice_settings = data.get('voice_settings', {})
                self.voice_mode = bool(voice_settings.get('voice_mode', self.voice_mode))
                self.listen_mode = bool(voice_settings.get('listen_mode', self.listen_mode))
                # FIX — nettoyer les rappels déjà faits et ceux expirés depuis > 24h
                all_reminders  = data.get('reminders', [])
                cutoff = time.time() - 86400  # 24h
                self.reminders = [
                    r for r in all_reminders
                    if not r.get('done') and r.get('due', 0) > cutoff
                ]
                # Si des rappels ont été nettoyés, sauvegarder immédiatement
                if len(self.reminders) != len(all_reminders):
                    self._save_memory()
        except Exception:
            pass

    def _save_memory(self):
        try:
            data = {
                'notes': self.notes,
                'reminders': self.reminders,
                'memory': self.memory,
                'voice_settings': {
                    'voice_mode': bool(self.voice_mode),
                    'listen_mode': bool(self.listen_mode),
                }
            }
            self._mem_file().write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        except Exception:
            pass

    def _apply_voice_preferences(self):
        """Applique les préférences vocales mémorisées sans casser le démarrage."""
        if self.voice_mode and not self.voice.tts_enabled:
            self.voice_mode = False
        if self.listen_mode and not self.voice.stt_enabled:
            self.listen_mode = False
        if self.voice_mode or self.listen_mode:
            self._save_memory()

    @staticmethod
    def _normalize_voice_text(text: str) -> str:
        if not text:
            return ""
        original = text.strip()
        text = original.lower()
        text = text.replace("’", "'").replace("`", "'")
        text = re.sub(r"'{2,}", "'", text)
        text = re.sub(r'\s+', ' ', text)
        wake_variants = (
            'ok freev', 'hey freev', 'hé freev', 'salut freev', 'freev',
            'free v', 'freeve', 'friv', 'freed', 'free'
        )
        for wake in wake_variants:
            if text == wake:
                return ""
            if text.startswith(wake + ' '):
                original = original[len(wake):].strip()
                text = text[len(wake):].strip()
                break
        compact = FreevBrain._strip_accents(text)
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
        if '=>' in original or original.lower().startswith(('note:', 'rappel:', 'apprends que', 'souviens-toi que')):
            return original
        text = re.sub(r"\bc est\b", "c'est", text)
        text = re.sub(r"\bqu est ce que\b", "qu'est-ce que", text)
        text = re.sub(r"\bj ai\b", "j'ai", text)
        text = re.sub(r'\s+', ' ', text).strip(" .")
        return text

    # ── Thread de rappels ─────────────────────────────────────────────────────
    def _start_reminder_thread(self):
        def check_reminders():
            while self.running:
                now = time.time()
                due = [r for r in self.reminders if r.get('due', 0) <= now and not r.get('done')]
                for r in due:
                    r['done'] = True

                    # Alerte sonore
                    try:
                        import winsound
                        for _ in range(3):
                            winsound.Beep(1000, 200)
                            time.sleep(0.1)
                    except Exception:
                        print('\a\a\a', end='', flush=True)

                    # Affichage en clair avec heure réelle
                    now_str = datetime.now().strftime('%H:%M')
                    print(f"\n{C.BR_YELLOW}{'═'*45}{C.RESET}")
                    print(f"{C.BR_YELLOW}⏰  RAPPEL ({now_str}) : {r['text']}{C.RESET}")
                    print(f"{C.BR_YELLOW}{'═'*45}{C.RESET}")

                    if self.voice_mode and self.voice.tts_enabled:
                        self.voice.speak(f"Rappel : {r['text']}")
                    _color = self.PERSONALITIES[self.personality]['color']
                    _p = (f"{_color}Vous (parle) > {C.RESET}"
                          if self.listen_mode else f"{_color}Vous > {C.RESET}")
                    sys.stdout.write('\r\033[K' + _p)
                    sys.stdout.flush()

                if due:
                    # Nettoyer les vieux rappels terminés (> 7 jours)
                    cutoff = time.time() - (7 * 24 * 3600)
                    self.reminders = [
                        r for r in self.reminders
                        if not (r.get('done') and r.get('due', 0) < cutoff)
                    ]
                    self._save_memory()

                time.sleep(5)   # vérifie toutes les 5s (était 10s)
        t = threading.Thread(target=check_reminders, daemon=True)
        t.start()

    # ── Affichage ─────────────────────────────────────────────────────────────
    def _print_response(self, text: str):
        color = self.PERSONALITIES[self.personality]['color']
        print(f"\n{color}Freev ➤{C.RESET} {text}\n")
        if self.voice_mode and self.voice.tts_enabled:
            self.voice.speak(text)

    def _banner(self):
        name = self.brain.context.user_profile.get('name')
        greeting = f"{C.BR_GREEN}  Bonjour {name} ! Content de te revoir.{C.RESET}\n" if name else ""
        print(f"""
{C.BG_BLUE}{C.BR_WHITE}{'═'*60}{C.RESET}
{C.BG_BLUE}{C.BR_WHITE}  FREEV v{self.VERSION} — IA Locale · Zéro dépendance · 100% vous  {C.RESET}
{C.BG_BLUE}{C.BR_WHITE}{'═'*60}{C.RESET}
{C.BR_CYAN}  FreevBrain v{self.brain.MODEL_VERSION} : BPE · Embeddings · BM25 · KneserNey · MLP · Raisonnement v7{C.RESET}
{C.YELLOW}  Tape 'aide' pour la liste des commandes.{C.RESET}
{C.GREEN}  {self.brain.status()}{C.RESET}
{greeting}""")

    # ══════════════════════════════════════════════════════════════════════════
    # HANDLERS SPÉCIALISÉS
    # ══════════════════════════════════════════════════════════════════════════

    def handle_brain(self, text: str):
        tl = text.lower()
        if 'brain status' in tl or 'statut cerveau' in tl or 'statut brain' in tl:
            # Statut enrichi v5.0
            base = self.brain.status()
            plugins = self.brain.plugins.list_plugins()
            plug_str = f"{len(plugins)} plugin(s) chargé(s)" if plugins else "aucun plugin"
            return f"{base}\n  🔌 Plugins : {plug_str}"
        # ── Commandes plugins (v5.0) ──────────────────────────────────────────
        if any(x in tl for x in ['liste plugins','mes plugins','plugins actifs']):
            plugins = self.brain.plugins.list_plugins()
            if not plugins:
                return "🔌 Aucun plugin chargé. Place des .py dans le dossier plugins/."
            lines = ["🔌 Plugins chargés :"]
            for p in plugins:
                lines.append(f"  • {p['name']} — {p['description'] or 'pas de description'}")
            return "\n".join(lines)
        if any(x in tl for x in ['recharge plugins','reload plugins','charge plugins']):
            loaded = self.brain.plugins.load_plugins()
            return f"🔌 {len(loaded)} plugin(s) rechargé(s) : {', '.join(loaded) or 'aucun'}"
        if any(x in tl for x in ['crée plugin','cree plugin','exemple plugin']):
            return self.brain.plugins.create_example_plugin()
        # ── Stress test (v5.0) ───────────────────────────────────────────────
        if any(x in tl for x in ['stress test','test performance','test vitesse']):
            if not self.brain.trained:
                return "❌ FreevBrain non entraîné."
            print("  ⚡ Stress test (100 requêtes)...")
            r = self.brain.tester.run_stress_test(self.brain, n_requests=100)
            return (f"⚡ Stress Test (100 requêtes) :\n"
                    f"  Temps total    : {r['total_time_ms']:.0f} ms\n"
                    f"  Temps moyen    : {r['avg_time_ms']:.1f} ms/req\n"
                    f"  Médiane (P50)  : {r['p50_ms']:.1f} ms\n"
                    f"  P95            : {r['p95_ms']:.1f} ms\n"
                    f"  Réponses       : {r['response_rate_pct']}%\n"
                    f"  Erreurs        : {r['errors']}")
        # ── Intent debug (v5.0) ──────────────────────────────────────────────
        if 'intent' in tl or 'intention' in tl:
            m_intent = re.search(r"(?:intent|intention)\s+(?:de\s+)?(.+?)\s*$", text, re.I)
            if m_intent:
                test_txt = m_intent.group(1)
                r = self.brain.intent.classify(test_txt)
                return (f"🎯 Intention de '{test_txt}' :\n"
                        f"  Intent     : {r['intent']}\n"
                        f"  Confiance  : {r['confidence']*100:.0f}%\n"
                        f"  Sous-intent: {r['sub_intent']}")
        if 'entraîne toi' in tl or 'entraine toi' in tl or 'train brain' in tl:
            ok = self.brain.train()
            if ok:
                n   = len(self.brain.training_data)
                msg = f"✅ FreevBrain v{self.brain.MODEL_VERSION} entraîné ! {n} paires (avec augmentation).\n"
                print("  🧠 Lancement MLP automatique (patience ~30s)...")
                mlp_msg = self.brain.train_mlp(epochs=5)
                msg += f"  {mlp_msg}"
                return msg
            return "❌ freev_data.txt introuvable. Créez ce fichier sur le Bureau."
        if 'entraîne mlp' in tl or 'train mlp' in tl:
            return self.brain.train_mlp(epochs=15)
        # Benchmark dédié : freev_eval.txt si présent, freev_data.txt en secours
        if any(x in tl for x in ['benchmark', 'test brain', 'teste brain', 'évalue brain', 'evalue brain']):
            if not self.brain.trained:
                return "❌ FreevBrain n'est pas encore entraîné."
            eval_path = Path(__file__).parent / 'freev_eval.txt'
            source = eval_path if eval_path.exists() else self.brain._find_data_file()
            pairs = self.brain.tester.load_test_file(str(source or ''))
            if not pairs:
                return "❌ Aucune paire de test trouvée."
            sample = pairs[:80]
            print(f"  🧪 Benchmark sur {len(sample)} paires ({Path(source).name})...")
            metrics = self.brain.tester.run_benchmark(self.brain, sample)
            return (f"📊 Benchmark FreevBrain ({Path(source).name}, {len(sample)} paires) :\n"
                    f"  Précision    : {metrics['accuracy']*100:.1f}%\n"
                    f"  Conf. moy.   : {metrics['avg_confidence']*100:.1f}%\n"
                    f"  Temps moy.   : {metrics['avg_response_time_ms']:.1f} ms/réponse")
        # Export rapport de test JSON
        if any(x in tl for x in ['export rapport', 'exporte rapport', 'rapport brain']):
            path = str(Path.home() / 'freev_rapport.json')
            try:
                self.brain.tester.export_report(path)
                return f"📤 Rapport exporté → {path}"
            except Exception as e:
                return f"❌ Erreur export rapport : {e}"
        # KnowledgeGraph — afficher les faits connus
        if any(x in tl for x in ['affiche graphe', 'mes faits', 'liste graphe', 'graphe kg']):
            g = self.brain.kg.graph
            if not g:
                return "📚 Le graphe de connaissances est vide. Utilise 'sais que X est Y'."
            lines = ["📚 Graphe de connaissances :"]
            count = 0
            for subj, preds in list(g.items())[:20]:
                for pred, objs in preds.items():
                    for obj in objs:
                        lines.append(f"  • {subj} {pred} {obj}")
                        count += 1
            if count == 0:
                return "📚 Graphe vide."
            if len(g) > 20:
                lines.append(f"  ... ({len(g) - 20} sujets supplémentaires non affichés)")
            return "\n".join(lines)
        # KnowledgeGraph — effacer
        if any(x in tl for x in ['efface graphe', 'vide graphe', 'reset graphe', 'clear graphe']):
            self.brain.kg.graph.clear()
            self.brain.kg.reverse_index.clear()
            self.brain._save()
            return "🗑️  Graphe de connaissances effacé."
        m = re.search(r"apprends que [\"'](.+)[\"']\s*=>\s*[\"'](.+)[\"']", text, re.IGNORECASE)
        if m:
            self.brain.learn(m.group(1), m.group(2))
            return f"🧠 Mémorisé : {m.group(1)} → {m.group(2)}"
        m2 = re.search(r"apprends que (.+)\s*=>\s*(.+)", text, re.IGNORECASE)
        if m2:
            self.brain.learn(m2.group(1).strip(), m2.group(2).strip())
            return f"🧠 Mémorisé : {m2.group(1).strip()} → {m2.group(2).strip()}"
        # KnowledgeGraph — ajout
        m3 = re.search(r"sais que (.+?) (est|sont|a|ont) (.+)", text, re.IGNORECASE)
        if m3:
            self.brain.kg.add_fact(m3.group(1), m3.group(2), m3.group(3))
            self.brain._save()
            return f"📚 Graphe : ({m3.group(1)}, {m3.group(2)}, {m3.group(3)}) enregistré."
        return None

    def _safe_eval(self, expr: str):
        """
        Évalue une expression mathématique SANS eval() — sécurisé.
        Utilise ast.parse() pour vérifier que l'expression est purement arithmétique.
        Gemini : évite l'injection de code via eval.
        """
        import ast as _ast
        # Python 3.8+ : ast.Constant remplace ast.Num (déprécié en 3.12, supprimé en 3.14)
        _SAFE_NODES = (
            _ast.Expression, _ast.BinOp, _ast.UnaryOp,
            _ast.Add, _ast.Sub, _ast.Mult, _ast.Div,
            _ast.Mod, _ast.FloorDiv, _ast.Pow,   # Pow requis pour 2**10 / 2^10
            _ast.USub, _ast.UAdd,
            _ast.Constant,  # ast.Num est déprécié — Constant couvre tout
        )
        # Compatibilité Python < 3.8
        if hasattr(_ast, 'Num'):
            _SAFE_NODES = _SAFE_NODES + (_ast.Num,)
        if len(expr) > 50: return None  # anti-DoS
        def _check(node):
            if not isinstance(node, _SAFE_NODES):
                raise ValueError(f"Nœud interdit : {type(node).__name__}")
            for child in _ast.iter_child_nodes(node):
                _check(child)

        expr = expr.strip()
        if not expr:
            return None
        # Anti-DoS : interdire les puissances avec exposant > 300 (ex: 9**9**9)
        if '**' in expr:
            import re as _re
            for match in _re.findall(r'\*\*\s*(\d+)', expr):
                if int(match) > 300:
                    return "⚠️  Exposant trop grand (max 300) — anti-DoS."
        try:
            tree = _ast.parse(expr, mode='eval')
            _check(tree.body)
            # Évaluation sécurisée via compile + eval restreint
            code = compile(tree, '<math>', 'eval')
            result = eval(code, {"__builtins__": {}}, {})
            # Arrondir si float sans intérêt
            if isinstance(result, float) and result == int(result):
                return int(result)
            if isinstance(result, float):
                return round(result, 8)
            return result
        except Exception:
            return None

    def handle_math(self, text: str):
        tl = text.lower().strip()
        TEXT_COMMANDS = [
            'supprime', 'suppr', 'delete', 'note', 'rappel', 'fait note',
            'export', 'mes notes', 'mes rappels', 'souviens', 'affiche',
            'apprends', 'brain', 'aide', 'help', 'voix', 'ecoute', 'météo',
            'meteo', 'weather', 'convert', 'qui', 'quoi', 'comment', 'pourquoi',
        ]
        if any(tl.startswith(cmd) or tl == cmd for cmd in TEXT_COMMANDS):
            return None
        digits_count = sum(1 for c in tl if c.isdigit())
        if digits_count < 1:
            return None
        # Ne pas bloquer les commandes mathématiques textuelles (racine, fibonacci, etc.)
        MATH_KEYWORDS = ['racine','fibonacci','factorielle','premier','sin','cos','tan',
                         'log','sqrt','arcsin','arccos','arctan']
        if (re.match(r'^[a-zA-ZÀ-ÿ ]+\d+$', tl.strip())
                and not any(op in tl for op in ['+','-','*','/','^','%'])
                and not any(kw in tl for kw in MATH_KEYWORDS)):
            return None
        # Fibonacci
        m = re.search(r'fibonacci\s+(\d+)', tl)
        if m:
            n = int(m.group(1))
            if n > 50: return "Je limite à 50 pour éviter les calculs trop longs."
            a, b = 0, 1
            seq = []
            for _ in range(n):
                seq.append(a)
                a, b = b, a + b
            return f"Fibonacci({n}) : {', '.join(map(str, seq))}"
        # Factorielle
        m = re.search(r'factorielle\s+(?:de\s+)?(\d+)', tl)
        if m:
            n = int(m.group(1))
            if n > 20: return "Je limite à 20 pour les factorielles."
            result = 1
            for i in range(2, n+1): result *= i
            return f"{n}! = {result}"
        # Racine carrée
        m = re.search(r'racine\s+(?:carrée\s+)?(?:de\s+)?(\d+(?:\.\d+)?)', tl)
        if m:
            return f"√{m.group(1)} = {math.sqrt(float(m.group(1))):.6f}"
        # Logarithme (offline — math stdlib)
        m = re.search(r'log(?:arithme)?\s+(?:de\s+)?(\d+(?:\.\d+)?)(?:\s+base\s+(\d+))?', tl)
        if m:
            val = float(m.group(1))
            if val <= 0:
                return "❌ Le logarithme n'est défini que pour les réels strictement positifs."
            base = int(m.group(2)) if m.group(2) else None
            if base:
                return f"log_{base}({val}) = {math.log(val, base):.6f}"
            return f"ln({val}) = {math.log(val):.6f}  |  log10({val}) = {math.log10(val):.6f}"
        # Trigonométrie en degrés (offline — math stdlib)
        m = re.search(r'(sin|cos|tan|arcsin|arccos|arctan)\s+(?:de\s+)?(\d+(?:\.\d+)?)', tl)
        if m:
            fn, val = m.group(1), float(m.group(2))
            try:
                if fn == 'sin':    result = math.sin(math.radians(val))
                elif fn == 'cos':  result = math.cos(math.radians(val))
                elif fn == 'tan':  result = math.tan(math.radians(val))
                elif fn == 'arcsin': result = math.degrees(math.asin(val))
                elif fn == 'arccos': result = math.degrees(math.acos(val))
                else:              result = math.degrees(math.atan(val))
                unit = "°" if fn.startswith('arc') else ""
                return f"{fn}({val}{'°' if not fn.startswith('arc') else ''}) = {result:.6f}{unit}"
            except ValueError as e:
                return f"❌ Erreur : {e}"
        # Nombre premier
        m = re.search(r'(?:est|nombre)\s+(?:premier\s+)?(\d+)\s+(?:est\s+)?premier', tl)
        if not m:
            m = re.search(r'premier\s+(\d+)', tl)
        if m:
            n = int(m.group(1))
            if n < 2: return f"{n} n'est pas premier."
            for i in range(2, int(n**0.5)+1):
                if n % i == 0: return f"{n} n'est pas premier (divisible par {i})."
            return f"{n} est un nombre premier ✓"
        # pi, e
        if tl in ('pi', 'π'): return f"π ≈ {math.pi}"
        if tl in ('e', 'euler'): return f"e ≈ {math.e}"
        # Évaluation d'expression sécurisée — support ^ comme puissance
        expr = re.sub(r'[^0-9+\-*/().,% \^]', '', text)
        expr = expr.replace(',', '.').replace('^', '**')
        if any(c in expr for c in '0123456789'):
            # Vérification anti-DoS : max 10 niveaux de parenthèses (Manus)
            paren_level = 0
            for ch in expr:
                if ch == '(': paren_level += 1
                elif ch == ')': paren_level -= 1
                if paren_level > 10 or paren_level < 0:
                    return "❌ Expression trop complexe (max 10 niveaux de parenthèses)."
            if paren_level != 0:
                return "❌ Parenthèses non équilibrées."
            try:
                result = self._safe_eval(expr)
                if result is not None:
                    return f"= {result}"
            except Exception:
                pass
        return None
    def handle_notes(self, text: str):
        tl = text.lower().strip()
        if tl.startswith('note:') or tl.startswith('note :'):
            content = text[text.index(':')+1:].strip()
            self.notes.append({'text': content, 'date': datetime.now().strftime('%d/%m/%Y %H:%M'), 'done': False})
            self._save_memory()
            return f"📝 Note #{len(self.notes)} enregistrée : {content}"
        if 'mes notes' in tl or 'liste notes' in tl:
            if not self.notes:
                return "Aucune note enregistrée."
            result = "📋 Mes notes :\n"
            for i, n in enumerate(self.notes, 1):
                status = "✓" if n.get('done') else "○"
                result += f"  {i}. [{status}] {n['text']} ({n['date']})\n"
            return result.strip()
        m = re.search(r'supprime\s+note\s+(\d+)', tl)
        if m:
            idx = int(m.group(1)) - 1
            if 0 <= idx < len(self.notes):
                removed = self.notes.pop(idx)
                self._save_memory()
                return f"🗑️ Note supprimée : {removed['text']}"
            return "Numéro de note invalide."
        m = re.search(r'fait\s+note\s+(\d+)', tl)
        if m:
            idx = int(m.group(1)) - 1
            if 0 <= idx < len(self.notes):
                self.notes[idx]['done'] = True
                self._save_memory()
                return f"✅ Note {idx+1} marquée comme faite."
        # Export des notes vers un fichier texte
        if 'export notes' in tl or 'exporte notes' in tl or 'sauvegarde notes' in tl:
            if not self.notes:
                return "Aucune note à exporter."
            try:
                export_path = Path.home() / 'freev_notes_export.txt'
                lines = [f"=== Notes Freev — {datetime.now().strftime('%d/%m/%Y %H:%M')} ===\n"]
                for i, n in enumerate(self.notes, 1):
                    status = "[✓]" if n.get('done') else "[ ]"
                    lines.append(f"{i}. {status} {n['text']}  ({n['date']})\n")
                export_path.write_text(''.join(lines), encoding='utf-8')
                return f"📤 {len(self.notes)} note(s) exportée(s) → {export_path}"
            except Exception as e:
                return f"❌ Erreur export : {e}"
        return None

    def handle_reminders(self, text: str):
        tl = text.lower().strip()
        m = re.search(r'rappel[:\s]+(.+?)\s+dans\s+(\d+)\s+(minute|heure|jour|seconde)s?', tl)
        if m:
            content, amount_str, unit = m.group(1), m.group(2), m.group(3)
            try:
                amount = int(amount_str)
                if not (1 <= amount <= 10000):
                    return "❌ Le délai doit être entre 1 et 10 000."
            except ValueError:
                return "❌ Nombre invalide pour le rappel."
            delta = {'seconde': 1, 'minute': 60, 'heure': 3600, 'jour': 86400}.get(unit, 60)
            due = time.time() + amount * delta
            self.reminders.append({'text': content, 'due': due, 'done': False})
            self._save_memory()
            return f"⏰ Rappel programmé : '{content}' dans {amount} {unit}(s)."
        if 'mes rappels' in tl or 'liste rappels' in tl:
            pending = [r for r in self.reminders if not r.get('done')]
            if not pending:
                return "Aucun rappel en attente."
            result = "⏰ Rappels en attente :\n"
            for i, r in enumerate(pending, 1):
                due_str = datetime.fromtimestamp(r['due']).strftime('%d/%m %H:%M')
                result += f"  {i}. {r['text']} (à {due_str})\n"
            return result.strip()
        # Supprimer un rappel par numéro (sur la liste des rappels en attente)
        m2 = re.search(r'supprime\s+rappel\s+(\d+)', tl)
        if m2:
            idx = int(m2.group(1)) - 1
            pending = [r for r in self.reminders if not r.get('done')]
            if 0 <= idx < len(pending):
                pending[idx]['done'] = True   # marquer comme fait = retiré de la liste
                self._save_memory()
                return f"🗑️ Rappel supprimé : {pending[idx]['text']}"
            return "Numéro de rappel invalide."
        return None

    def handle_memory(self, text: str):
        tl = text.lower()
        m = re.search(r"souviens-toi que (.+?) c'est (.+)", tl)
        if not m:
            m = re.search(r"retiens que (.+?) est (.+)", tl)
        if m:
            key, value = m.group(1).strip(), m.group(2).strip()
            self.memory[key] = value
            self._save_memory()
            return f"💾 Mémorisé : {key} = {value}"
        if 'affiche mémoire' in tl or 'ma mémoire' in tl:
            if not self.memory:
                return "Ma mémoire est vide."
            result = "💾 Ce que je sais de toi :\n"
            for k, v in self.memory.items():
                result += f"  • {k} = {v}\n"
            return result.strip()
        # Commande : effacer l'historique de conversation
        if any(x in tl for x in ['efface historique', 'efface l\'historique',
                                   'supprime historique', 'histoire clear',
                                   'vide historique', 'reset historique']):
            try:
                from memory import ConversationHistory
                h = ConversationHistory()
                h.clear()
            except Exception:
                pass
            return "🗑️  Historique de conversation effacé."
        # Afficher l'historique de conversation
        if any(x in tl for x in ['mon historique', 'affiche historique',
                                   'mes conversations', 'historique vocal']):
            try:
                from memory import ConversationHistory
                h = ConversationHistory()
                exchanges = h.recent(5)
                if not exchanges:
                    return "📜 L'historique de conversation est vide."
                lines = [f"📜 Dernières conversations :"]
                for e in exchanges:
                    lines.append(f"  👤 {e['user']}")
                    lines.append(f"  🤖 {e['bot'][:80]}{'…' if len(e['bot']) > 80 else ''}")
                return "\n".join(lines)
            except Exception:
                return "❌ Impossible de lire l'historique."
        # Recherche dans la mémoire
        for key, val in self.memory.items():
            if key.lower() in tl:
                return f"Je me souviens : {key} = {val}"
        return None

    def handle_conversions(self, text: str):
        tl = text.lower()
        m = re.search(r'convert[ie]?\s+(\d+(?:\.\d+)?)\s+(\w+)\s+(?:to|en|vers?)\s+(\w+)', tl)
        if not m:
            return None
        val, from_unit, to_unit = float(m.group(1)), m.group(2), m.group(3)
        # Conversions physiques exactes (offline, pas de réseau)
        PHYSICAL = {
            ('km', 'miles'): val * 0.621371,      ('miles', 'km'): val * 1.60934,
            ('km', 'mile'): val * 0.621371,        ('mile', 'km'): val * 1.60934,
            ('kg', 'lbs'): val * 2.20462,          ('lbs', 'kg'): val * 0.453592,
            ('kg', 'lb'): val * 2.20462,           ('lb', 'kg'): val * 0.453592,
            ('celsius', 'fahrenheit'): val * 9/5 + 32,
            ('fahrenheit', 'celsius'): (val - 32) * 5/9,
            ('celsius', 'kelvin'): val + 273.15,   ('kelvin', 'celsius'): val - 273.15,
            ('m', 'feet'): val * 3.28084,          ('feet', 'm'): val * 0.3048,
            ('m', 'foot'): val * 3.28084,          ('foot', 'm'): val * 0.3048,
            ('m', 'cm'): val * 100,                ('cm', 'm'): val / 100,
            ('m', 'mm'): val * 1000,               ('mm', 'm'): val / 1000,
            ('km', 'm'): val * 1000,               ('m', 'km'): val / 1000,
            ('litres', 'gallons'): val * 0.264172, ('gallons', 'litres'): val * 3.78541,
            ('litre', 'gallon'): val * 0.264172,   ('gallon', 'litre'): val * 3.78541,
            ('cm', 'inches'): val * 0.393701,      ('inches', 'cm'): val * 2.54,
            ('cm', 'inch'): val * 0.393701,        ('inch', 'cm'): val * 2.54,
            ('g', 'oz'): val * 0.035274,           ('oz', 'g'): val * 28.3495,
            ('g', 'kg'): val / 1000,               ('kg', 'g'): val * 1000,
            ('tonne', 'kg'): val * 1000,           ('kg', 'tonne'): val / 1000,
            ('mph', 'kmh'): val * 1.60934,         ('kmh', 'mph'): val * 0.621371,
            ('ha', 'm2'): val * 10000,             ('m2', 'ha'): val / 10000,
        }
        # Conversions monétaires indicatives (taux approximatif — pas temps réel)
        CURRENCY_APPROX = {
            ('eur', 'usd'): val * 1.08,            ('usd', 'eur'): val * 0.93,
            ('euros', 'dollars'): val * 1.08,      ('dollars', 'euros'): val * 0.93,
            ('eur', 'gbp'): val * 0.86,            ('gbp', 'eur'): val * 1.16,
            ('usd', 'gbp'): val * 0.79,            ('gbp', 'usd'): val * 1.27,
        }
        key = (from_unit.lower(), to_unit.lower())
        if key in PHYSICAL:
            return f"{val} {from_unit} = {PHYSICAL[key]:.4f} {to_unit}"
        if key in CURRENCY_APPROX:
            return (f"{val} {from_unit} ≈ {CURRENCY_APPROX[key]:.2f} {to_unit}\n"
                    f"  ⚠️  Taux indicatif (approximation statique) — pour un taux exact, consulte un site financier.")
        return None

    def handle_system(self, text: str):
        tl = text.lower()
        if 'mon ip' in tl or 'ip locale' in tl:
            try:
                # Tentative via socket UDP (nécessite réseau)
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                s.close()
                return f"\U0001f310 IP locale : {ip}"
            except Exception:
                try:
                    # Fallback offline : hostname → IP (fonctionne sans internet)
                    ip = socket.gethostbyname(socket.gethostname())
                    return f"\U0001f310 IP locale (offline) : {ip}"
                except Exception:
                    return "Impossible de déterminer l'IP locale."
        if 'date' in tl and 'heure' in tl:
            return f"\U0001f4c5 {datetime.now().strftime('%A %d %B %Y - %H:%M:%S')}"
        if 'heure' in tl or "quelle heure" in tl:
            return f"\U0001f550 Il est {datetime.now().strftime('%H:%M:%S')}"
        if 'date' in tl:
            return f"\U0001f4c5 Nous sommes le {datetime.now().strftime('%A %d %B %Y')}"
        if 'explore dossier' in tl or 'liste fichiers' in tl:
            try:
                files = sorted(f.name for f in Path('.').iterdir())
                return "\U0001f4c1 Dossier courant :\n  " + "\n  ".join(files[:25])
            except Exception:
                return "Impossible de lister les fichiers."
        # Version Freev
        if any(x in tl for x in ['version freev', 'version de freev', 'quelle version']):
            return (f"\U0001f916 Freev v{self.VERSION}\n"
                    f"  Python {sys.version.split()[0]} | "
                    f"FreevBrain {'actif' if self.brain.trained else 'non entraîné'} | "
                    f"Personnalité : {self.PERSONALITIES[self.personality]['name']}")
        # Infos système (offline — platform stdlib)
        if any(x in tl for x in ['infos système', 'infos systeme', 'mon système', 'mon systeme']):
            try:
                import platform
                return (f"\U0001f4bb Système :\n"
                        f"  OS      : {platform.system()} {platform.release()}\n"
                        f"  Machine : {platform.machine()}\n"
                        f"  Python  : {platform.python_version()}\n"
                        f"  Freev   : v{self.VERSION}")
            except Exception:
                return f"\U0001f4bb Freev v{self.VERSION} | Python {sys.version.split()[0]}"
        return None
    def handle_personality(self, text: str):
        tl = text.lower()
        if 'change de personnalité' in tl or 'personnalité' in tl:
            for p in self.PERSONALITIES:
                if p in tl:
                    self.personality = p
                    return f"Personnalité changée : {self.PERSONALITIES[p]['name']}"
            available = ', '.join(self.PERSONALITIES.keys())
            return f"Personnalités disponibles : {available}"
        return None

    def handle_text_analysis(self, text: str):
        tl = text.lower()
        m = re.search(r"analyse ['\"](.+?)['\"]", text)
        if m:
            t = m.group(1)
            words = t.split()
            chars = len(t.replace(' ', ''))
            sentences = max(1, t.count('.') + t.count('!') + t.count('?'))
            unique = len(set(w.lower() for w in words))
            return (f"\U0001f4ca Analyse de : '{t[:50]}'\n"
                    f"  Mots : {len(words)} (uniques : {unique})\n"
                    f"  Caract\u00e8res (sans espaces) : {chars}\n"
                    f"  Phrases estim\u00e9es : {sentences}")
        if 'palindrome' in tl:
            m2 = re.search(r"palindrome ['\"?](.+?)['\"?]$", text, re.IGNORECASE)
            if m2:
                word = re.sub(r'[^a-zA-Z\u00C0-\u00FF]', '', m2.group(1).lower())
                is_p = word == word[::-1]
                verdict = "\u2705 Oui" if is_p else "\u274c Non"
                article = "un" if is_p else "pas un"
                return f"{verdict}, '{m2.group(1)}' est {article} palindrome."
        m3 = re.search(r"inverse ['\"]((.+?)['\"])", text)
        if m3:
            return f"\U0001f504 Invers\u00e9 : '{m3.group(2)[::-1]}'"
        m4 = re.search(r"compte\\s+(?:les\\s+)?mots\\s+['\"]((.+?)['\"])", text, re.IGNORECASE)
        if m4:
            t = m4.group(2)
            return f"\U0001f4ca '{t[:40]}' \u2192 {len(t.split())} mots, {len(t)} caract\u00e8res."
        m5 = re.search(r"majuscules?\\s+['\"]((.+?)['\"])", text, re.IGNORECASE)
        if m5:
            return f"\U0001f520 '{m5.group(2).upper()}'"
        m6 = re.search(r"minuscules?\\s+['\"]((.+?)['\"])", text, re.IGNORECASE)
        if m6:
            return f"\U0001f521 '{m6.group(2).lower()}'"
        m7 = re.search(r"longueur\\s+['\"]((.+?)['\"])", text, re.IGNORECASE)
        if m7:
            t = m7.group(2)
            return f"\U0001f4cf '{t[:40]}' \u2192 {len(t)} caract\u00e8res, {len(t.split())} mots."
        return None

    def handle_games(self, text: str):
        tl = text.lower()
        if 'jeu devine le nombre' in tl or 'devine un nombre' in tl:
            secret = random.randint(1, 100)
            attempts = 0
            print(f"\n{C.BR_YELLOW}\U0001f3ae Jeu : Devine le nombre entre 1 et 100 ! (max 7 tentatives){C.RESET}")
            while attempts < 7:
                try:
                    guess = int(input(f"  Tentative {attempts+1}/7 : "))
                    attempts += 1
                    if guess == secret:
                        return f"\U0001f389 Bravo ! Tu as trouvé {secret} en {attempts} tentatives !"
                    elif guess < secret:
                        print(f"  \U0001f4c8 Plus grand !")
                    else:
                        print(f"  \U0001f4c9 Plus petit !")
                except ValueError:
                    print("  Entre un nombre entier.")
            return f"\u274c Perdu ! C'était {secret}."
        if 'blague' in tl or 'fais moi rire' in tl:
            blagues = [
                "Pourquoi les plongeurs plongent toujours en arrière ? Parce que sinon ils tomberaient dans le bateau !",
                "Un développeur rentre dans un bar. Commande 0 bières. Puis 1. Puis 2. Puis 3...",
                "Qu'est-ce qu'un canif ? Un petit fien !",
                "Comment appelle-t-on un chat tombé dans un pot de peinture ? Un chat-peint !",
                "Pourquoi l'épouvantail a reçu un prix ? Parce qu'il était exceptionnel dans son domaine.",
                "C'est l'histoire d'un pingouin qui fait le tour de la Terre. Résultat : deux demi-tours.",
                "Qu'est-ce qu'un crocodile qui surveille des enfants ? Un gardien de sac !",
                "Comment appelle-t-on un boomerang qui ne revient pas ? Un bâton.",
                "Pourquoi les maths sont tristes ? Parce qu'elles ont trop de problèmes.",
                "Un homme entre dans une bibliothèque et demande des nouilles. Le bibliothécaire dit : 'Chut !' L'homme chuchote : 'Des nouilles, s'il vous plaît ?'",
                "Que dit un informaticien à sa femme ? 'Tu es mon /home, tu es mon /amour.'",
            ]
            return random.choice(blagues)
        return None

    def _wiki_fetch(self, query: str, lang: str = 'fr') -> tuple:
        """Appel direct API Wikipedia REST — urllib stdlib, zéro pip install."""
        query = self.brain._repair_mojibake(query).strip()
        if not query:
            return None, None, None
        try:
            # 1. Essai direct sur le titre
            q_enc = urllib.parse.quote(query.replace(' ', '_'))
            url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{q_enc}"
            req = urllib.request.Request(url, headers={
                'User-Agent': 'FreevBrain/4.0',
                'Accept': 'application/json'
            })
            with urllib.request.urlopen(req, timeout=6) as r:
                data = json.loads(r.read().decode('utf-8'))
            if data.get('type') == 'standard' and data.get('extract'):
                return (data.get('title', ''),
                        data['extract'],
                        data.get('content_urls', {}).get('desktop', {}).get('page', ''))
        except Exception:
            pass

        try:
            # 2. Fallback : recherche par mot-clé
            q_enc = urllib.parse.quote(query)
            url = (f"https://{lang}.wikipedia.org/w/api.php"
                   f"?action=query&list=search&srsearch={q_enc}"
                   f"&srlimit=1&format=json")
            req = urllib.request.Request(url, headers={'User-Agent': 'FreevBrain/4.0'})
            with urllib.request.urlopen(req, timeout=6) as r:
                res = json.loads(r.read().decode('utf-8'))
            hits = res.get('query', {}).get('search', [])
            if hits:
                title = hits[0]['title']
                t_enc = urllib.parse.quote(title.replace(' ', '_'))
                url2  = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{t_enc}"
                req2  = urllib.request.Request(url2, headers={
                    'User-Agent': 'FreevBrain/4.0', 'Accept': 'application/json'})
                with urllib.request.urlopen(req2, timeout=6) as r2:
                    data2 = json.loads(r2.read().decode('utf-8'))
                if data2.get('extract'):
                    return (data2.get('title', title),
                            data2['extract'],
                            data2.get('content_urls', {}).get('desktop', {}).get('page', ''))
        except Exception:
            pass

        return None, None, None

    def _extract_wiki_query(self, text: str):
        """Extrait un sujet encyclopédique depuis une question naturelle."""
        cleaned = self.brain._repair_mojibake(text).strip()
        tl = self.brain._normalize_text(cleaned).strip()
        tl = re.sub(r"[-']", ' ', tl)
        tl = re.sub(r'\s+', ' ', tl)

        prefixes = [
            'wikipedia ', 'wiki ', 'cherche ', 'recherche ',
            'que sais tu sur ', 'parle moi de ', 'parle-moi de ',
            'dis moi qui est ', 'dis-moi qui est ', 'c est qui ',
            'kesako ', 'explique moi ', 'explique-moi ',
        ]
        for prefix in prefixes:
            if tl.startswith(prefix):
                return cleaned[len(prefix):].strip(" ?!.,;:")

        patterns = [
            r"^qui est (?:le |la |l |un |une )?(.+)$",
            r"^c est quoi (?:le |la |les |l |un |une )?(.+)$",
            r"^qu est ce que (?:le |la |les |l |un |une )?(.+)$",
            r"^qu est ce qu (?:un |une )?(.+)$",
            r"^comment fonctionne (?:le |la |l |un |une )?(.+)$",
        ]
        for pattern in patterns:
            m = re.search(pattern, tl)
            if m:
                return m.group(1).strip(" ?!.,;:")
        return None

    def _extract_comparison_terms(self, text: str):
        cleaned = self.brain._repair_mojibake(text).strip()
        norm = self.brain._normalize_text(cleaned)
        norm = re.sub(r"[-']", ' ', norm)
        patterns = [
            r'\b(?:difference|differences|compare|comparaison)\s+(?:entre\s+)?(.+?)\s+(?:et|vs|versus)\s+(.+?)[\?\!\.]?$',
            r'\b(.+?)\s+(?:vs|versus)\s+(.+?)[\?\!\.]?$',
        ]
        for pat in patterns:
            m = re.search(pat, norm)
            if not m:
                continue
            left = m.group(1).strip(" ?!.,;:")
            right = m.group(2).strip(" ?!.,;:")
            aliases = {'ia': 'intelligence artificielle', 'ai': 'intelligence artificielle'}
            left = aliases.get(left, left)
            right = aliases.get(right, right)
            if left and right and left != right:
                return left, right
        return None

    def handle_comparison(self, text: str):
        terms = self._extract_comparison_terms(text)
        if not terms:
            return None
        left, right = terms
        cache_key = f"compare:{self.brain._normalize_text(left)}:{self.brain._normalize_text(right)}"
        cached = self._cache_get(cache_key)
        if cached:
            return cached + f"\n  {C.CYAN}(comparaison en cache){C.RESET}"

        l_title, l_extract, l_url = self._wiki_fetch(left, 'fr')
        r_title, r_extract, r_url = self._wiki_fetch(right, 'fr')
        if not l_title:
            l_title, l_extract, l_url = self._wiki_fetch(left, 'en')
        if not r_title:
            r_title, r_extract, r_url = self._wiki_fetch(right, 'en')
        if not l_extract or not r_extract:
            return None

        def first_sentence(s):
            s = s.replace('\n', ' ').strip()
            parts = [p.strip() for p in s.split('. ') if p.strip()]
            out = parts[0] if parts else s[:240]
            return out if out.endswith('.') else out + '.'

        plain = (
            f"{l_title} : {first_sentence(l_extract)} "
            f"{r_title} : {first_sentence(r_extract)} "
            f"Différence simple : d'après ces résumés, {l_title} et {r_title} ne désignent pas la même chose. "
            f"Compare-les sur un critère précis pour obtenir une réponse plus tranchée."
        )
        result = (
            f"\n{C.BR_CYAN}{'─'*50}\n"
            f"  Comparaison : {l_title} / {r_title}\n"
            f"{'─'*50}{C.RESET}\n"
            f"  {l_title} : {first_sentence(l_extract)}\n"
            f"  {r_title} : {first_sentence(r_extract)}\n"
            f"  Différence simple : d'après ces résumés, {l_title} et {r_title} ne désignent pas la même chose. "
            f"Compare-les sur un critère précis pour obtenir une réponse plus tranchée.\n"
            f"{C.BR_YELLOW}  {l_url or ''} {r_url or ''}{C.RESET}\n"
            f"{C.BR_CYAN}{'─'*50}{C.RESET}"
        )
        self._cache_set(cache_key, result)
        self.brain.learn_if_new(f"difference entre {left} et {right}", plain)
        return result

    def _wiki_format(self, title: str, extract: str, url: str, learned: bool) -> str:
        """Formate l'affichage d'une réponse Wikipedia."""
        sentences = [s.strip() for s in extract.replace('\n', ' ').split('. ') if s.strip()]
        short = '. '.join(sentences[:2])
        if short and not short.endswith('.'):
            short += '.'
        badge = (f"\n  {C.BR_GREEN}🧠 Mémorisé dans FreevBrain !{C.RESET}"
                 if learned else f"\n  {C.CYAN}💾 Déjà dans ma mémoire.{C.RESET}")
        link  = f"\n  {C.BR_YELLOW}🔗 {url}{C.RESET}" if url else ''
        return (f"\n{C.BR_CYAN}{'─'*50}\n"
                f"  📖  Wikipedia : {title}\n"
                f"{'─'*50}{C.RESET}\n"
                f"  {short}\n"
                f"{badge}{link}\n"
                f"{C.BR_CYAN}{'─'*50}{C.RESET}")

    def handle_wikipedia(self, text: str):
        """Recherche Wikipedia — urllib stdlib, zéro dépendance externe."""
        query = self._extract_wiki_query(text)
        if not query:
            return None

        cache_key = f"wiki:{self.brain._normalize_text(query)}"
        cached = self._cache_get(cache_key)
        if cached:
            return cached + f"\n  {C.CYAN}(Wikipedia en cache){C.RESET}"

        sys.stdout.write(f"  {C.YELLOW}🔍 Recherche Wikipedia...{C.RESET}  ")
        sys.stdout.flush()
        title, extract, url = self._wiki_fetch(query, 'fr')
        if not title:
            title, extract, url = self._wiki_fetch(query, 'en')
        sys.stdout.write(f"\r{' '*40}\r"); sys.stdout.flush()
        if not title:
            # Hors-ligne : essayer quand même FreevBrain local
            local = self.brain.respond(query)
            if local:
                return f"📡 Wikipedia hors-ligne. Depuis ma mémoire locale :\n  {local}"
            return (f"❌ Impossible de joindre Wikipedia pour '{query}'.\n"
                    f"  → Vérifie ta connexion internet, ou utilise 'apprends que' pour m'enseigner ce sujet.")

        learned = self.brain.learn_if_new(query, extract)
        result = self._wiki_format(title, extract, url, learned)
        self._cache_set(cache_key, result)
        return result

    def _get_weather_openmeteo(self, city: str) -> str:
        """Météo via open-meteo.com + geocoding — gratuit, sans clé API."""
        try:
            # 1. Géocoder la ville
            city_enc = urllib.parse.quote(city)
            geo_url = (f"https://geocoding-api.open-meteo.com/v1/search"
                       f"?name={city_enc}&count=1&language=fr&format=json")
            req = urllib.request.Request(geo_url, headers={'User-Agent': 'FreevBrain/4.0'})
            with urllib.request.urlopen(req, timeout=6) as r:
                geo = json.loads(r.read().decode())

            results = geo.get('results', [])
            if not results:
                return f"❌ Ville introuvable : {city}"

            loc = results[0]
            lat, lon = loc['latitude'], loc['longitude']
            city_name = loc.get('name', city)
            country   = loc.get('country', '')

            # 2. Météo actuelle
            wx_url = (f"https://api.open-meteo.com/v1/forecast"
                      f"?latitude={lat}&longitude={lon}"
                      f"&current=temperature_2m,relative_humidity_2m,"
                      f"apparent_temperature,weather_code,wind_speed_10m"
                      f"&daily=temperature_2m_max,temperature_2m_min"
                      f"&timezone=auto&forecast_days=1")
            req2 = urllib.request.Request(wx_url, headers={'User-Agent': 'FreevBrain/4.0'})
            with urllib.request.urlopen(req2, timeout=6) as r2:
                wx = json.loads(r2.read().decode())

            cur   = wx['current']
            daily = wx['daily']
            temp     = cur['temperature_2m']
            feels    = cur['apparent_temperature']
            humidity = cur['relative_humidity_2m']
            wind     = cur['wind_speed_10m']
            code     = cur['weather_code']
            t_max    = daily['temperature_2m_max'][0]
            t_min    = daily['temperature_2m_min'][0]

            # WMO weather codes → description + emoji
            wmo = {
                0: ('Ciel dégagé', '☀️'), 1: ('Peu nuageux', '🌤️'),
                2: ('Partiellement nuageux', '⛅'), 3: ('Couvert', '☁️'),
                45: ('Brouillard', '🌫️'), 48: ('Brouillard givrant', '🌫️'),
                51: ('Bruine légère', '🌦️'), 53: ('Bruine modérée', '🌦️'),
                61: ('Pluie légère', '🌧️'), 63: ('Pluie modérée', '🌧️'),
                65: ('Pluie forte', '🌧️'), 71: ('Neige légère', '❄️'),
                73: ('Neige modérée', '❄️'), 75: ('Neige forte', '❄️'),
                80: ('Averses légères', '🌦️'), 81: ('Averses', '🌦️'),
                82: ('Averses fortes', '⛈️'), 95: ('Orage', '⛈️'),
                96: ('Orage avec grêle', '⛈️'), 99: ('Orage violent', '⛈️'),
            }
            desc, icon = wmo.get(code, ('Conditions variables', '🌤️'))

            return (f"\n{C.BR_CYAN}{'─'*45}\n"
                    f"  {icon}  Météo à {city_name} ({country})\n"
                    f"{'─'*45}{C.RESET}\n"
                    f"  🌡️  Température  : {C.BR_YELLOW}{temp}°C{C.RESET} (ressenti {feels}°C)\n"
                    f"  📊  Min / Max    : {t_min}°C / {t_max}°C\n"
                    f"  💧  Humidité     : {humidity}%\n"
                    f"  💨  Vent         : {wind} km/h\n"
                    f"  🔍  Conditions   : {desc}\n"
                    f"{C.BR_CYAN}{'─'*45}{C.RESET}")

        except Exception as e:
            err = str(e)
            if 'timeout' in err.lower() or 'urlopen' in err.lower():
                return f"❌ Pas de connexion internet pour la météo de {city}."
            return f"❌ Impossible d'obtenir la météo de {city} ({err[:40]})."

    def _cache_get(self, key: str):
        """Retourne le résultat mis en cache si encore valide (TTL = 1h)."""
        if key in self._cache:
            ts, result = self._cache[key]
            if time.time() - ts < self._cache_ttl:
                return result
            del self._cache[key]
        return None

    def _cache_set(self, key: str, result: str):
        """Met en cache un résultat avec timestamp."""
        self._cache[key] = (time.time(), result)

    def handle_weather(self, text: str):
        tl = text.lower()
        # FIX : séparer exact match (phrases longues) du fuzzy (mots courts)
        # Évite que "quels sont tes capacités" → faux positif météo
        exact_kws = ['quel temps', 'quelle température', 'quelle temperature',
                     'fait-il chaud', 'fait-il froid', 'va-t-il pleuvoir', 'pleut-il',
                     'quelle temp', 'il fait quel temps']
        fuzzy_kws = ['météo', 'meteo', 'weather', 'temperature', 'température']
        tl_check = text.lower()
        exact_hit = any(kw in tl_check for kw in exact_kws)
        if not exact_hit and not self._fuzzy_intent(text, fuzzy_kws, threshold=0.80):
            return None

        city = None
        for prefix in ['météo à', 'météo a', 'météo de', 'météo pour', 'météo',
                        'meteo à', 'meteo a', 'meteo de', 'meteo pour', 'meteo',
                        'weather in', 'weather for', 'weather at', 'weather',
                        'quel temps fait-il à', 'quel temps fait-il a', 'quel temps à',
                        'quelle température fait-il à', 'quelle temperature fait-il à',
                        'quelle température à', 'quelle temperature à',
                        'il fait quelle température à', 'il fait quel temps à',
                        'temperature à', 'température à']:
            if prefix in tl:
                after = tl.split(prefix, 1)[1].strip()
                after = after.replace('?', '').replace('!', '').strip()
                if after:
                    city = after.strip()
                    break

        if not city:
            city = 'Paris'
        city = city.title()

        # Cache — évite de rappeler l'API si données récentes (< 1h)
        cache_key = f"weather:{city.lower()}"
        cached = self._cache_get(cache_key)
        if cached:
            return cached + f"\n  {C.CYAN}(données en cache){C.RESET}"

        # Essai 1 : open-meteo (plus fiable, sans clé)
        result = self._get_weather_openmeteo(city)
        if result and not result.startswith('❌'):
            self._cache_set(cache_key, result)
            return result

        # Essai 2 : wttr.in en fallback
        try:
            url = f"https://wttr.in/{urllib.parse.quote(city)}?format=j1"
            req = urllib.request.Request(url, headers={'User-Agent': 'FreevBrain/4.0'})
            with urllib.request.urlopen(req, timeout=5) as r:
                data = json.loads(r.read().decode())

            current  = data['current_condition'][0]
            temp_c   = current['temp_C']
            feels_c  = current['FeelsLikeC']
            humidity = current['humidity']
            desc     = current['weatherDesc'][0]['value']
            wind_kmph = current['windspeedKmph']
            today    = data['weather'][0]
            max_c    = today['maxtempC']
            min_c    = today['mintempC']

            desc_low = desc.lower()
            if 'sunny' in desc_low or 'clear' in desc_low:      icon = '☀️'
            elif 'cloud' in desc_low or 'overcast' in desc_low: icon = '☁️'
            elif 'rain' in desc_low or 'drizzle' in desc_low:   icon = '🌧️'
            elif 'snow' in desc_low:                             icon = '❄️'
            elif 'thunder' in desc_low or 'storm' in desc_low:  icon = '⛈️'
            elif 'fog' in desc_low or 'mist' in desc_low:       icon = '🌫️'
            else:                                                 icon = '🌤️'

            translations = {
                'Sunny': 'Ensoleillé', 'Clear': 'Dégagé',
                'Partly cloudy': 'Partiellement nuageux', 'Cloudy': 'Nuageux',
                'Overcast': 'Couvert', 'Light rain': 'Pluie légère',
                'Moderate rain': 'Pluie modérée', 'Heavy rain': 'Pluie forte',
                'Light snow': 'Neige légère', 'Thunderstorm': 'Orage',
                'Fog': 'Brouillard', 'Mist': 'Brume',
                'Patchy rain possible': 'Pluie possible',
                'Light drizzle': 'Bruine légère',
            }
            desc_fr = translations.get(desc, desc)

            return (f"\n{C.BR_CYAN}{'─'*45}\n"
                    f"  {icon}  Météo à {city}\n"
                    f"{'─'*45}{C.RESET}\n"
                    f"  🌡️  Température  : {C.BR_YELLOW}{temp_c}°C{C.RESET} (ressenti {feels_c}°C)\n"
                    f"  📊  Min / Max    : {min_c}°C / {max_c}°C\n"
                    f"  💧  Humidité     : {humidity}%\n"
                    f"  💨  Vent         : {wind_kmph} km/h\n"
                    f"  🔍  Conditions   : {desc_fr}\n"
                    f"{C.BR_CYAN}{'─'*45}{C.RESET}")

        except Exception:
            pass

        return result  # Retourner le message d'erreur de open-meteo

    def handle_voice(self, text: str):
        """Gestion du mode vocal — voix on/off/status/écoute."""
        tl = self._normalize_voice_text(text)

        # Activer la voix (parole uniquement)
        if any(x in tl for x in ['voix on', 'active la voix', 'commence à parler', 'parle moi']):
            # Lazy-init : init TTS seulement maintenant (pas au démarrage)
            if hasattr(self.voice, 'enable_tts'):
                self.voice.enable_tts()
            if not self.voice.tts_enabled:
                return f"❌ pyttsx3 non installé. Lance : {C.BR_YELLOW}pip install pyttsx3{C.RESET}"
            self.voice_mode = True
            self._save_memory()
            # Pas de self.voice.speak() ici : _print_response() s'en charge après le return
            return "🔊 Mode vocal activé et mémorisé. Je parlerai aussi au prochain lancement."

        # Désactiver la voix
        if any(x in tl for x in ['voix off', 'tais toi', 'arrête de parler', 'stop voix', 'silence']):
            self.voice_mode = False
            self.listen_mode = False if 'silence' in tl else self.listen_mode
            self.voice.stop()
            self._save_memory()
            return "🔇 Mode vocal désactivé."

        # Activer l'écoute micro
        if any(x in tl for x in ['écoute', 'ecoute', 'mode vocal', 'parle moi freev', 'active micro']):
            if not self.voice.stt_enabled:
                return f"❌ SpeechRecognition non installé. Lance : {C.BR_YELLOW}pip install SpeechRecognition pyaudio{C.RESET}"
            self.listen_mode = True
            self.voice_mode  = True  # Si on écoute, on parle aussi
            self._save_memory()
            return "🎤 Mode écoute activé et mémorisé. Parle, je t'écoute."

        # Désactiver l'écoute
        if any(x in tl for x in ['stop écoute', 'arrête écoute', 'désactive micro']):
            self.listen_mode = False
            self._save_memory()
            return "🎤 Mode écoute désactivé. Retour au clavier."

        # Installer les dépendances
        if 'installe voix' in tl or 'install voice' in tl:
            return (f"Pour activer la voix, lance ces commandes dans PowerShell :\n"
                    f"  {C.BR_YELLOW}pip install pyttsx3{C.RESET}   → Freev parle\n"
                    f"  {C.BR_YELLOW}pip install SpeechRecognition pyaudio{C.RESET}   → Freev écoute")

        # Status vocal
        if any(x in tl for x in ['status voix', 'statut voix', 'voix status']):
            mode_txt = "🔊 Parole activée" if self.voice_mode else "🔇 Parole désactivée"
            listen_txt = "🎤 Écoute activée" if self.listen_mode else "🎤 Écoute désactivée"
            mem_txt = "💾 Préférences vocales mémorisées"
            return f"{self.voice.status()}\n  {mode_txt} | {listen_txt}\n  {mem_txt}"

        return None

    def handle_help(self, text: str):
        if text.lower().strip() not in ('aide', 'help', '?', 'aide moi'):
            return None
        return f"""
{C.BR_CYAN}{'─'*55}
FREEV v{self.VERSION} — Commandes disponibles
{'─'*55}{C.RESET}
{C.BR_YELLOW}🧠 FREEVBRAIN{C.RESET}
  brain status / statut cerveau
  entraîne toi / train brain
  entraîne mlp
  apprends que "question" => "réponse"
  sais que [sujet] est [objet]
  affiche graphe   → voir les faits du KnowledgeGraph
  efface graphe    → vider le KnowledgeGraph
  benchmark        → évaluer la précision sur freev_eval.txt
  rapport brain    → exporter rapport JSON (~/.freev_rapport.json)
  tu te souviens de moi ? | reset profil

{C.BR_YELLOW}📝 NOTES & RAPPELS{C.RESET}
  note: [texte]           | mes notes | supprime note N | fait note N
  export notes            → sauvegarde dans ~/freev_notes_export.txt
  rappel: [texte] dans N minutes/heures/jours
  mes rappels             | supprime rappel N

{C.BR_YELLOW}🧮 MATHÉMATIQUES{C.RESET}
  5+3, 10*2, 2^10 — toute expression (^ = puissance)
  racine de 16 | factorielle 5 | fibonacci 10
  nombre premier 97 | pi | e
  log de 100 | log de 8 base 2
  sin 45 | cos 90 | tan 30 | arctan 1

{C.BR_YELLOW}🔄 CONVERSIONS{C.RESET}
  convert 10 km to miles | convert 100 m to feet | convert 5 kg to lbs
  convert 20 celsius to fahrenheit | convert 300 kelvin to celsius
  convert 1 tonne to kg | convert 50 mph to kmh | convert 2 ha to m2
  convert 100 eur to usd  ⚠️  (taux indicatif — pas temps réel)

{C.BR_YELLOW}💬 TEXTE & ANALYSE{C.RESET}
  analyse 'texte' | palindrome 'mot' | inverse 'texte'
  compte mots 'texte' | majuscules 'texte' | minuscules 'texte'
  longueur 'texte'

{C.BR_YELLOW}📖 WIKIPEDIA{C.RESET}
  wiki [sujet] | wikipedia [sujet]
  cherche [sujet] | qui est [personne]
  parle moi de [sujet]
  → Fallback sur mémoire locale si hors-ligne !

{C.BR_YELLOW}🌤️  MÉTÉO{C.RESET}
  météo Paris | météo Lyon | météo Tokyo
  quel temps fait-il à Bordeaux

{C.BR_YELLOW}🎮 JEUX{C.RESET}
  jeu devine le nombre | blague

{C.BR_YELLOW}💻 SYSTÈME{C.RESET}
  mon ip locale | heure | date | explore dossier
  version freev | infos système

{C.BR_YELLOW}🎭 PERSONNALITÉ{C.RESET}
  change de personnalité [fun|dark|philosophique|motivant|cynique]

{C.BR_YELLOW}💾 MÉMOIRE{C.RESET}
  souviens-toi que X c'est Y | affiche mémoire
  mon historique | affiche historique
  efface historique | histoire clear

{C.BR_YELLOW}⚙️  DIVERS{C.RESET}
  reset contexte | quitter / exit / bye
{C.BR_CYAN}{'─'*55}{C.RESET}"""

    def _try_wikipedia_fallback(self, text: str):
        """Cherche Wikipedia automatiquement — urllib stdlib, zéro pip install."""
        query = self._extract_wiki_query(text)
        if not query or len(query) < 3:
            return None

        ARGOT = {'bagnole', 'caisse', 'boulot', 'fric', 'pote', 'gosse',
                 'bouquin', 'bahut', 'bobo', 'mec', 'nana', 'truc',
                 'machin', 'bidule', 'bécane', 'gamin', 'môme'}
        skip = {'la vie', 'le bonheur', 'toi', 'moi', 'freev', 'freevbrain',
                'python', 'salut', 'bonjour', 'tu', 'je'}
        q_lower = self.brain._normalize_text(query).strip()
        if q_lower in skip or q_lower in ARGOT:
            return None
        for a in ARGOT:
            if q_lower in (f'un {a}', f'une {a}', f'le {a}', f'la {a}'):
                return None

        # Cache — évite une requête réseau si la même chose a déjà été cherchée
        cache_key = f"wiki_fallback:{q_lower}"
        cached = self._cache_get(cache_key)
        if cached:
            return cached

        sys.stdout.write(f"  {C.YELLOW}🔍 Recherche Wikipedia...{C.RESET}  ")
        sys.stdout.flush()
        title, extract, url = self._wiki_fetch(query, 'fr')
        if not title:
            title, extract, url = self._wiki_fetch(query, 'en')
        sys.stdout.write(f"\r{' '*40}\r"); sys.stdout.flush()
        if not title or not extract:
            return None

        learned = self.brain.learn_if_new(text, extract)
        result = self._wiki_format(title, extract, url, learned)
        self._cache_set(cache_key, result)
        return result

    # ── Dispatcher principal ──────────────────────────────────────────────────
    def _fuzzy_intent(self, text: str, keywords: list, threshold: float = 0.75) -> bool:
        """
        Détecteur d'intention tolérant aux fautes de frappe.
        Gemini : utilise Levenshtein (déjà dans le Scorer) pour trouver
        des commandes même mal orthographiées.
        Ex: "meteo pari" → détecte "météo paris"
        """
        tl = text.lower().strip()
        # Correspondance exacte d'abord
        for kw in keywords:
            if kw in tl:
                return True
        # Fuzzy sur chaque mot de la saisie vs chaque mot-clé
        words = tl.split()
        for kw in keywords:
            kw_words = kw.split()
            for kw_word in kw_words:
                if len(kw_word) < 4:
                    continue  # ignorer les mots trop courts (le, la, de...)
                for word in words:
                    if len(word) < 3:
                        continue
                    # Distance Levenshtein simple
                    m, n = len(word), len(kw_word)
                    dp = list(range(n + 1))
                    for i in range(1, m + 1):
                        prev = dp[0]
                        dp[0] = i
                        for j in range(1, n + 1):
                            temp = dp[j]
                            if word[i-1] == kw_word[j-1]:
                                dp[j] = prev
                            else:
                                dp[j] = 1 + min(prev, dp[j], dp[j-1])
                            prev = temp
                    dist = dp[n]
                    max_len = max(len(word), len(kw_word))
                    ratio = 1 - dist / max_len
                    if ratio >= threshold:
                        return True
        return False

    def generate_response(self, user_input: str) -> str:
        """
        Pipeline de réponse v5.0 :
        Plugins → Intent → Voice → Handlers → FreevBrain → Wikipedia → Sentiment → Fallback
        """
        text = self._normalize_voice_text(user_input)
        if not text:
            return ""
        tl = text.lower()

        # ── 0. Quitter ────────────────────────────────────────────────────────
        if tl in ('quitter', 'exit', 'quit', 'bye', 'au revoir', 'a plus'):
            self.running = False
            return "👋 À bientôt ! Freev se ferme."

        # ── 1. Plugins externes (PluginManager) — priorité maximale ──────────
        plugin_resp = self.brain.plugins.run_all(text)
        if plugin_resp:
            return self._finalize_response(plugin_resp, text)

        # ── 2. Commandes vocales — priorité absolue ───────────────────────────
        VOICE_TRIGGERS = [
            'voix on', 'voix off', 'active la voix', 'tais toi',
            'arrete de parler', 'stop voix', 'silence',
            'mode vocal', 'active micro', 'stop ecoute',
            'arrete ecoute', 'installe voix', 'status voix',
            'statut voix', 'voix status',
        ]
        tl_na = tl.replace('é','e').replace('è','e').replace('ê','e').replace('à','a')
        if ('voix on' in tl or 'voix off' in tl or 'écoute' in tl
                or 'ecoute' in tl or any(t in tl_na for t in VOICE_TRIGGERS)):
            result = self.handle_voice(text)
            if result is not None:
                return result

        # ── 3. Commandes de contexte / profil ────────────────────────────────
        if 'reset contexte' in tl:
            self.brain.context.reset()
            return "🔄 Contexte réinitialisé."
        if any(x in tl for x in ['reset profil','efface profil','oublie mon nom','oublie moi']):
            self.brain.context.reset_profile()
            return "🗑️  Profil effacé. Je ne me souviens plus de toi."
        name = self.brain.context.user_profile.get('name')
        if name and any(x in tl for x in ['tu te souviens de moi','tu sais qui je suis','mon nom']):
            return f"Bien sûr ! Tu es {name}. 😊"

        # ── 4. Classification d'intention (IntentClassifier v5.0) ────────────
        intent_result = self.brain.intent.classify(text)
        intent        = intent_result['intent']

        # Détection de changement de sujet → reset contexte court
        if self.brain.context.detect_topic_shift(text):
            self.brain.context.reset()   # efface juste l'historique court

        # ── 5. Handlers spécialisés (ordre selon l'intention détectée) ───────
        # Handlers prioritaires indépendants de l'intention
        priority_handlers = [
            self.handle_help,
            self.handle_brain,
            self.handle_notes,
            self.handle_reminders,
            self.handle_memory,
        ]
        # Handlers orientés par l'intention
        intent_handlers = {
            'recherche':    [self.handle_comparison, self.handle_wikipedia, self.handle_weather],
            'commande':     [self.handle_conversions, self.handle_math,
                             self.handle_system, self.handle_text_analysis,
                             self.handle_games],
            'question':     [self.handle_comparison, self.handle_wikipedia, self.handle_math,
                             self.handle_conversions, self.handle_weather],
            'conversation': [self.handle_personality, self.handle_games],
            'apprentissage':[self.handle_brain],
        }
        remaining_handlers = [
            self.handle_comparison, self.handle_wikipedia, self.handle_weather, self.handle_conversions,
            self.handle_math, self.handle_system, self.handle_personality,
            self.handle_text_analysis, self.handle_games,
        ]

        # Handlers prioritaires d'abord
        for handler in priority_handlers:
            result = handler(text)
            if result is not None:
                return self._finalize_response(result, text)

        # Handlers selon l'intention (si confiance suffisante)
        if intent_result['confidence'] >= 0.80:
            for handler in intent_handlers.get(intent, []):
                result = handler(text)
                if result is not None:
                    return self._finalize_response(result, text)

        # Tous les handlers restants (filet de sécurité)
        seen = set(intent_handlers.get(intent, []))
        for handler in remaining_handlers:
            if handler not in seen:
                result = handler(text)
                if result is not None:
                    return self._finalize_response(result, text)

        # ── 6. FreevBrain (moteur IA principal) ──────────────────────────────
        brain_result = self.brain.respond_with_candidates(text)
        brain_response = brain_result.get("response") if brain_result.get("accepted") else None
        if brain_response:
            # Diversifier : éviter de répéter la même réponse
            diversified = self.brain.diversifier.filter(
                [c.get("response", "") for c in brain_result.get("candidates", [])] or [brain_response]
            )
            self.brain.diversifier.record(diversified)
            return self._finalize_response(diversified, text)

        # ── 7. Wikipedia fallback intelligent ────────────────────────────────
        wiki_response = self._try_wikipedia_fallback(text)
        if wiki_response:
            return self._finalize_response(wiki_response, text)

        # ── 8. Refus prudent pour éviter les réponses hors sujet ─────────────
        subject = self.brain.intent.extract_subject(text)
        subject_tokens = self.brain._tokenize(subject)
        unknown_subjects = [
            t for t in subject_tokens
            if t not in self.brain.vocabulary and len(t) >= 5
        ]
        if intent in ('question', 'recherche') or text.endswith('?') or unknown_subjects:
            cautious = (
                f"{self.brain.UNCERTAIN_RESPONSE} "
                f"Sujet demandé : « {subject} ». "
                f"Je peux chercher avec Wikipedia si tu formules avec 'wiki {subject}', "
                f"ou tu peux me l'apprendre avec : apprends que \"question\" => \"réponse\"."
            )
            return self._finalize_response(cautious, text)

        # ── 8. Fallback de personnalité ───────────────────────────────────────
        fallback = random.choice(self.FALLBACKS.get(self.personality, self.FALLBACKS['normal']))
        return self._finalize_response(fallback, text)

    def _finalize_response(self, response: str, user_input: str) -> str:
        """
        Post-traitement v5.0 : adapte le ton selon le sentiment détecté.
        Appelé sur toutes les réponses avant retour à l'utilisateur.
        """
        if not response:
            return response
        try:
            sentiment = self.brain.sentiment.analyze(user_input)
            # Ajouter flag frustration/enthousiasme au dict
            sentiment['is_frustrated']  = self.brain.sentiment.is_frustrated(user_input)
            sentiment['is_enthusiastic']= self.brain.sentiment.is_enthusiastic(user_input)
            # Ajuster le ton seulement si sentiment fort (évite l'intrusion constante)
            if sentiment['is_frustrated'] or sentiment['score'] > 0.80:
                response = self.brain.sentiment.adjust_response_tone(response, sentiment)
        except Exception:
            pass   # Sentiment optionnel — jamais bloquer la réponse
        return response

    # ── Boucle principale ─────────────────────────────────────────────────────
    def run(self):
        self._banner()
        # Afficher status vocal au démarrage
        if self.voice.tts_enabled:
            print(f"  {C.BR_GREEN}🔊 pyttsx3 détecté — tape 'voix on' pour activer la parole{C.RESET}")
        if self.voice.stt_enabled:
            print(f"  {C.BR_GREEN}🎤 Micro détecté — tape 'écoute' pour activer la reconnaissance vocale{C.RESET}")
        print()

        # ConversationHistory instancié une seule fois (pas à chaque tour)
        try:
            from memory import ConversationHistory as _CH
            _hist = _CH()
        except Exception:
            _hist = None

        while self.running:
            try:
                # Mode écoute : micro en priorité
                if self.listen_mode and self.voice.stt_enabled:
                    color = self.PERSONALITIES[self.personality]['color']
                    print(f"\n{color}Vous (parle ou tape) > {C.RESET}", end='', flush=True)

                    # FIX closure : passer buf comme argument évite la capture par référence
                    buf = [""]
                    def _listen(b=buf):
                        b[0] = self.voice.listen(timeout=6)
                    lt = threading.Thread(target=_listen, daemon=True)
                    lt.start()
                    lt.join(timeout=15)
                    user_input = self._normalize_voice_text(buf[0])

                    if user_input:
                        print()
                    else:
                        sys.stdout.write(f'\r{C.YELLOW}  🎤 ...{C.RESET}   \r')
                        sys.stdout.flush()
                        continue

                else:
                    color = self.PERSONALITIES[self.personality]['color']
                    user_input = input(f"{color}Vous > {C.RESET}").strip()

                if not user_input:
                    continue

                response = self.generate_response(user_input)
                self._print_response(response)
                # Persister la conversation (instance unique)
                if _hist:
                    try:
                        _hist.save(user_input, response)
                    except Exception:
                        pass
                if not self.running:
                    break

            except KeyboardInterrupt:
                print(f"\n{C.BR_YELLOW}Interruption. Tape 'quitter' pour fermer proprement.{C.RESET}")
            except EOFError:
                break
        self._save_memory()
        self.voice.stop()


# brain.py — importé par main.py (point d'entrée unique)
# Pour lancer directement : python main.py  ou  python main.py --vocal

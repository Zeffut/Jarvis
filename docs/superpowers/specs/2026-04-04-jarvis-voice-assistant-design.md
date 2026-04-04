# Jarvis — Assistant vocal v1

## Résumé

Assistant vocal inspiré de Jarvis (Iron Man) pour macOS. Détection du wake word "Jarvis", transcription en temps réel via Whisper, réponse via Claude Haiku 4.5, et synthèse vocale native macOS.

## Architecture

```
Micro 🎙️ → Pvporcupine (wake word "Jarvis")
         → Enregistrement + transcription streaming EN PARALLÈLE
           (mots affichés en temps réel dans le terminal)
         → Silence détecté → texte final envoyé à Claude Haiku 4.5
         → Réponse affichée dans le terminal + lue par macOS `say`
         → Mode conversation : écoute directe ~5s sans wake word
         → Silence prolongé → retour en écoute wake word
```

## Composants

### 1. Wake word listener

- **Lib** : Pvporcupine (free tier, clé API gratuite)
- Écoute en continu avec quasi zéro CPU
- Détecte le mot "Jarvis" et déclenche le mode enregistrement
- Feedback visuel dans le terminal à la détection

### 2. Audio recorder + streaming STT

- **Capture audio** : `sounddevice` — capture le micro en continu par chunks
- **STT** : `faster-whisper` (basé sur CTranslate2, optimisé puces M)
- Traitement par fenêtres audio glissantes (~1-2s)
- Transcription partielle affichée en temps réel dans le terminal
- Détection de silence par seuil d'énergie audio (RMS) pour savoir quand l'utilisateur a fini de parler
- Seuil de silence : ~1.5s sans parole = fin d'énoncé

### 3. LLM — Claude Haiku 4.5

- **Lib** : `anthropic` SDK Python
- **Modèle** : `claude-haiku-4-5-20241001`
- **Prompt système** : personnalité Jarvis — concis, utile, léger touche d'humour
- **Historique** : conversation maintenue en mémoire pendant la session active
- L'historique est reset quand Jarvis revient en mode wake word (fin de conversation)

### 4. Text-to-speech

- **Outil** : macOS `say` via `subprocess`
- **Voix** : Thomas (voix française intégrée)
- Commande : `say -v Thomas "<réponse>"`
- Gratuit, zéro dépendance externe

### 5. Boucle de conversation

- Après la réponse vocale, Jarvis reste en mode écoute directe (pas besoin de redire "Jarvis")
- Timeout : ~5s de silence continu = fin de conversation
- Si l'utilisateur reparle avant le timeout → nouvelle transcription → nouvelle réponse
- Fin de conversation → reset historique → retour écoute wake word

## Stack technique

| Besoin | Solution | Coût |
|--------|----------|------|
| Wake word | `pvporcupine` | Gratuit (free tier) |
| Audio capture | `sounddevice` + `numpy` | Gratuit |
| STT streaming | `faster-whisper` (modèle `small`) | Gratuit, local |
| LLM | `anthropic` SDK → Claude Haiku 4.5 | Payant (API) |
| TTS | macOS `say` (voix Thomas) | Gratuit |
| Config | `.env` + `python-dotenv` | — |

## Flux détaillé

1. Jarvis démarre → affiche "🟢 En écoute..." dans le terminal
2. Pvporcupine écoute en continu le wake word
3. "Jarvis" détecté → feedback visuel ("🎙️ Je vous écoute...") + démarrage enregistrement
4. Audio capturé par chunks → envoyé à `faster-whisper` → transcription partielle affichée en temps réel
5. Silence détecté (~1.5s) → transcription finale figée
6. Texte envoyé à Claude Haiku 4.5 (avec prompt système + historique conversation)
7. Réponse affichée dans le terminal + lue par `say -v Thomas`
8. Mode conversation : écoute directe sans wake word, timeout 5s
9. Si parole détectée → retour à l'étape 4
10. Si silence prolongé (5s) → affiche "🟢 En écoute..." → retour à l'étape 2

## Structure du projet

```
jarvis/
├── main.py              # Point d'entrée, boucle principale
├── wake_word.py         # Détection wake word via Pvporcupine
├── audio.py             # Capture audio + détection silence
├── transcriber.py       # STT streaming via faster-whisper
├── assistant.py         # Intégration Claude Haiku 4.5
├── speaker.py           # TTS via macOS say
├── config.py            # Chargement config / clés API
├── .env                 # Clés API (ANTHROPIC_API_KEY, PICOVOICE_API_KEY)
├── .env.example         # Template des clés
└── requirements.txt     # Dépendances Python
```

## Dépendances Python

```
pvporcupine
sounddevice
numpy
faster-whisper
anthropic
python-dotenv
```

## Variables d'environnement

```
ANTHROPIC_API_KEY=sk-...
PICOVOICE_API_KEY=...
```

## Contraintes

- macOS uniquement (dépendance `say` + optimisation puces M)
- Python 3.10+
- Micro fonctionnel requis
- Connexion internet requise (API Claude)
- Seul coût : API Anthropic (Claude Haiku 4.5)

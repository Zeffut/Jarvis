# Jarvis UI — Interface Swift avec nuage de points Metal

**Date :** 2026-04-11  
**Statut :** Approuvé

---

## Résumé

Ajout d'une interface graphique native macOS à Jarvis : une fenêtre qui s'ouvre depuis le notch avec une animation fluide et affiche une sphère 3D animée en temps réel selon l'état vocal. Purement visuelle — aucun texte affiché, tout se fait à l'oral. L'UI terminal (`ui.py`) reste en fallback si Swift n'est pas disponible.

---

## Architecture

```
main.py (Python)
  │
  ├── détecte état (standby / listening / thinking / speaking)
  ├── mesure amplitude audio (mic ou Kokoro-82M)
  │
  └──(Unix socket /tmp/jarvis-ui.sock)──▶ JarvisUI.app (Swift)
                                            ├── NSPanel frameless
                                            ├── Animation notch → fenêtre
                                            ├── MTKView (Metal renderer)
                                            └── CoreAnimation (transitions)
```

### Protocole socket

Messages JSON envoyés par Python, ~30x/sec pendant les états actifs :

```json
{"state": "listening", "amplitude": 0.72}
{"state": "speaking",  "amplitude": 0.45}
{"state": "thinking",  "amplitude": 0.0}
{"state": "standby",   "amplitude": 0.0}
```

Envoi fire-and-forget : si la socket échoue, Python continue sans interruption.

---

## Rendu Metal

### Nuage de points

- **1500 points** répartis sur une sphère en coordonnées sphériques (θ, φ)
- **Taille des points** : 2–3px avec bloom pass léger
- **Couleur** : `#00D4FF` (cyan), opacité 0.2–1.0 selon profondeur Z
- **Rotation** : 0.1 rad/s en standby, s'accélère en speaking

### Calcul de position (vertex shader)

```
position finale = position de base sur sphère
                + déplacement radial  (amplitude × sin(phase + time))
                + rotation lente      (time × vitesse_état)
```

### États visuels

| État      | Énergie pulsation | Vitesse rotation | Amplitude max |
|-----------|-------------------|------------------|---------------|
| Standby   | 5%                | lente            | 5px           |
| Listening | 60–90% (mic)      | normale          | 30px          |
| Thinking  | 25%               | lente            | 10px          |
| Speaking  | 70–95% (TTS)      | rapide           | 30px          |

---

## Animation notch → fenêtre

**Fenêtre :** `NSPanel` frameless (`NSBorderlessWindowMask`), niveau `.floating`, taille cible 800×600px.

**Positionnement :** centre du notch = `x = (screenWidth - notchWidth) / 2`, `y = 0`. La fenêtre s'ouvre vers le bas depuis ce point.

**Séquence d'ouverture (~400ms) :**
1. 0ms — fenêtre au centre du notch, scale 0.05, opacité 0
2. 0→150ms — scale 0.05→1.0 + translation vers le bas (CoreAnimation spring, damping 0.7)
3. 150→300ms — opacité 0→1, points apparaissent en stagger aléatoire
4. 300→400ms — léger overshoot de la sphère (rebond en place)

**Séquence de fermeture (~250ms) :** séquence inverse, contraction vers le notch.

**Déclencheurs :**
- Ouverture : wake word détecté
- Fermeture : fin de conversation (`send_state("standby")` après `show_end_conversation`)

---

## Structure des fichiers

```
Jarvis/
├── ui/
│   ├── Package.swift
│   └── Sources/JarvisUI/
│       ├── main.swift              ← point d'entrée NSApplication
│       ├── AppDelegate.swift       ← cycle de vie, démarre socket listener
│       ├── JarvisPanel.swift       ← NSPanel, positionnement notch, animations
│       ├── MetalRenderer.swift     ← MTKView, gestion états visuels
│       ├── Shaders.metal           ← vertex + fragment shaders
│       └── SocketListener.swift    ← écoute socket, parse JSON, dispatch états
├── ui_socket.py                    ← module Python pour envoyer les états
├── main.py                         ← intègre ui_socket
├── ui.py                           ← UI terminal (fallback inchangé)
└── ...
```

---

## Intégration Python

### Nouveau module `ui_socket.py`

```python
import socket, json, subprocess

SOCKET_PATH = "/tmp/jarvis-ui.sock"

def launch_ui():
    subprocess.Popen(["ui/.build/release/JarvisUI"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def send_state(state: str, amplitude: float = 0.0):
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.connect(SOCKET_PATH)
            s.sendall(json.dumps({"state": state, "amplitude": amplitude}).encode())
    except Exception:
        pass  # UI optionnelle, jamais bloquante
```

### Points d'appel dans `main.py`

| Moment | Appel |
|--------|-------|
| Wake word détecté | `send_state("listening")` |
| Boucle preview mic | `send_state("listening", amplitude)` |
| Claude réfléchit | `send_state("thinking")` |
| TTS joue | `send_state("speaking", amplitude)` |
| Fin de conversation | `send_state("standby")` |

---

## Contraintes

- L'app Swift doit être compilée (`swift build -c release`) avant utilisation — à documenter dans le README
- ElevenLabs remplacé par **Kokoro-82M** (TTS local, Apple Silicon via ONNX) — l'amplitude sera calculée via RMS sur le buffer `numpy` du callback `sounddevice` pendant la lecture : `np.sqrt(np.mean(chunk**2))` passé à `send_state`
- Pas d'icône Dock, pas de menu bar icon — l'app est purement utilitaire
- Compatible macOS 13+ (Ventura) minimum pour les APIs notch

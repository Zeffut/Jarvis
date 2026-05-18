# UI Vibe Island — Refonte interface Jarvis

**Date** : 2026-05-18
**Auteur** : Thomas + Claude
**Statut** : Design validé, prêt pour plan d'implémentation

## Résumé

Refonte complète de l'interface Swift de Jarvis. L'UI actuelle (overlay plein écran noir avec sphère Metal centrée) est remplacée par **Vibe Island** — une pilule ambient permanente ancrée sous la notch macOS, style Dynamic Island d'iPhone avec un rendu visuel Arc Reactor d'Iron Man (cyan glow, scan lines, flicker holographique).

Trois modes de taille, avec animations spring soignées, et interception du tool natif `AskUserQuestion` de Claude Code pour des choix cliquables intégrés.

## 1. Concept et philosophie

**Présence** : ambient permanente. La pilule reste visible en toutes circonstances (même en standby) — c'est le « pilote allumé » de Jarvis.

**Position** : centrée horizontalement sur la notch, ancrée tout en haut de l'écran. La forme arrondie en bas se prolonge sous la notch, donnant l'illusion d'intégration native (Vibe Island).

**Philosophie d'affichage** : Jarvis reste **vocal-first**. Le panneau ne sert PAS à afficher transcription, réponses streamées, ou résultats structurés (mails listés, code, etc.). Il sert uniquement à :
1. Indiquer visuellement l'état courant (Arc Reactor animé)
2. Montrer l'outil en cours d'exécution (« Gmail · search threads… »)
3. Afficher des choix cliquables quand Claude pose une question via `AskUserQuestion`

**Trois modes de taille** :

| Mode | Dimensions | Contenu | Quand |
|---|---|---|---|
| Compact | 160×30px | Arc Reactor 18px + label état | Standby + transitions courtes |
| Étendu | 340×34px | Arc Reactor 22px + nom outil + mini spinner | Pendant exécution d'outils |
| Panel | 380×variable | Arc Reactor 80-90px + question + boutons cliquables | `AskUserQuestion` actif |

## 2. Anatomie visuelle Arc Reactor

Référence : réacteur Arc d'Iron Man, version holographique imparfaite (scan lines + flicker pour casser la perfection).

### Couches (extérieur → intérieur)

1. **Anneau extérieur** — cercle dashed `stroke-dasharray: 20,3,4,3`, cyan `#5cf`, rotation lente 20s/tour
2. **Anneau intérieur** — cercle dashed fin `2,2`, opacité 40%, statique
3. **Particules orbitales** — 2 points blancs opposés (12h / 6h), rotation inverse 9s/tour
4. **Cœur** — gradient radial `#fff → #9ef → #125`, breathe scale 1↔1.05 toutes 2.5s
5. **Scan lines** — repeating-linear-gradient horizontales (1px sur 3px), opacité 8%, blend `screen`
6. **Flicker global** — opacity `100→40→100` sur 100ms, déclenché aléatoirement toutes 3-5s

### Tailles et détails actifs

| Contexte | Diamètre | Couches actives |
|---|---|---|
| Compact (pilule) | 18px | Anneau ext + cœur (scan/particules trop petits pour être lisibles) |
| Étendu | 22px | Anneau ext + cœur, légèrement plus visible |
| Panel large | 80-90px | Toutes les couches actives |

### Variations par état

| État | Couleur | Glow | Comportement spécifique |
|---|---|---|---|
| Standby | `#5cf` dim 40% | Soft halo 8px | Breathe très lent (4s), pas de scan ni flicker |
| Listening | `#5cf` 100% | Strong halo 16px | Breathe rapide (1.2s), scan actif, rotation accélérée 8s/tour |
| Thinking | `#fa5` orange | Medium halo 12px | Particules tournent 2× plus vite, scan plus dense |
| Speaking | `#9ef` blanc-cyan | Pulse synchronisé TTS | Breathe synchronisé sur amplitude audio, scan léger |

L'état **thinking** vire orange volontairement — la charge de Claude Code est perceptible visuellement.

## 3. Modes d'expansion détaillés

### Compact (160×30px)
```
┌─ Arc 18px ─┬── "Jarvis" / "Listening" / "Thinking" / "Speaking" ─┐
│      ●     │                                                       │
└────────────┴───────────────────────────────────────────────────────┘
```

### Étendu (340×34px)
```
┌─ Arc 22px ─┬── "Gmail · search threads…" ──┬── mini spinner ──┐
│     ●      │                                │       ◌          │
└────────────┴────────────────────────────────┴──────────────────┘
```
- Label de l'outil : extrait du `tool_use` event (Gmail, Calendar, Drive, web_search, etc.) + sous-action si dispo
- Mini-spinner : cercle dashed cyan tournant 1.5s/tour
- Apparaît dès le `tool_use`, disparaît au `tool_result`

### Panel (380×variable)
```
┌──────────── Arc Reactor 80-90px ─────────────┐
│                                                │
│             ●  (toutes couches actives)        │
│                                                │
├────────────────────────────────────────────────┤
│  ❓ Mail à Sarah ou Pierre ?                    │
├────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐                  │
│  │  Sarah   │  │  Pierre  │                  │
│  └──────────┘  └──────────┘                  │
└────────────────────────────────────────────────┘
```
- Hauteur calculée selon le nombre d'options (max 4 par question)
- Boutons : flat dark, bordure cyan 1px, hover glow

## 4. Protocole AskUserQuestion natif

Claude Code dispose nativement du tool `AskUserQuestion`. On l'intercepte côté backend pour afficher les choix dans Vibe Island et renvoyer la réponse par clic.

### Flux complet

1. Claude Code émet dans son stream-json :
   ```json
   {"type": "tool_use", "id": "toolu_abc",
    "name": "AskUserQuestion",
    "input": {"questions": [{
       "question": "Mail à Sarah ou Pierre ?",
       "options": [{"label": "Sarah", "description": "..."},
                   {"label": "Pierre", "description": "..."}]
    }]}}
   ```

2. `assistant.py` détecte `name == "AskUserQuestion"` dans son parser de stream, met en pause son émission TTS, et envoie sur le socket UI :
   ```json
   {"state": "question",
    "tool_use_id": "toolu_abc",
    "question": "Mail à Sarah ou Pierre ?",
    "choices": [{"id": "0", "label": "Sarah"}, {"id": "1", "label": "Pierre"}]}
   ```

3. UI Swift passe en mode Panel avec spring expansion.

4. Au clic, l'UI envoie sur `/tmp/jarvis-ui-events.sock` :
   ```json
   {"type": "choice", "tool_use_id": "toolu_abc", "label": "Sarah"}
   ```

5. `assistant.py` injecte dans Claude Code via stream-json input :
   ```json
   {"type": "user", "message": {"content": [
      {"type": "tool_result", "tool_use_id": "toolu_abc", "content": "Sarah"}
   ]}}
   ```

6. Claude Code continue son flux normalement.

### Cas limites

- **Timeout 30s sans clic** : l'UI envoie `{"type": "choice", "tool_use_id": "...", "label": "[timeout]"}`. Le tool_result transmis à Claude est `"[timeout]"` — Claude saura quoi répondre.
- **Plusieurs questions** (`questions[]` array contient 2+ entrées) : V1 ne prend que `questions[0]`, log un warning. V2 future si besoin avéré.
- **Réponse libre** : non géré dans cette V1. Si Claude permet "Other" via l'API standard, ce sera ignoré (l'utilisateur doit cliquer un bouton listé).

## 5. Animations

**Principe** : chaque transition est une animation spring (jamais linéaire), timing 60-500ms calé sur la perception humaine.

### Courbes de référence

- **Spring expansion** : `mass=1.0, stiffness=180, damping=18` — léger overshoot
- **Spring retraction** : `mass=0.8, stiffness=240, damping=22` — plus rapide, peu de rebond
- **Ease morphing** : `cubicBezier(0.4, 0.0, 0.2, 1.0)` pour crossfades de contenu

### Transitions critiques

| De → Vers | Durée | Comportement |
|---|---|---|
| Boot (apparition initiale) | 700ms | Pilule descend depuis derrière la notch avec spring overshoot, Arc Reactor s'allume progressivement (cœur → anneaux) |
| Compact → Étendu (outil) | 350ms | Élargissement horizontal spring, label "Jarvis" crossfade vers "Gmail · …", mini-spinner fade-in 200ms |
| Étendu → Panel (question) | 500ms | 2-phases : élargissement horizontal 200ms PUIS descente verticale spring 300ms. Boutons cascade fade-in 50ms entre chacun |
| Panel → Compact (post-clic) | 400ms | Bouton cliqué pulse blanc 100ms, autres choix fade-out, rétraction hauteur puis largeur |
| Changement d'état (listening→thinking) | 250ms | Lerp couleur du glow, vitesse breathe interpolée, particules accélèrent |

### Détails fins

- Bouton cliqué : effet `scale 1.0 → 0.95 → 1.05 → 1.0` sur 200ms (rebond visuel haptique)
- Scan-line désactivé pendant transitions de taille (sinon clipping bizarre)
- Flicker désynchronisé entre Arc Reactor et contenu texte (2 hologrammes distincts)
- Hover boutons panel : glow cyan léger 200ms, scale 1.02

### Performance

- Tout en SwiftUI + Core Animation natif (60fps macOS garanti)
- Pas de Metal pour le rendu UI — un Arc Reactor 18-90px ne justifie pas le GPU overhead
- Le `MetalRenderer.swift` actuel est supprimé

## 6. Architecture du code

### Côté Swift

```
ui/Sources/JarvisUI/
├── main.swift                    (6 lignes — entry point inchangé)
├── AppDelegate.swift             (~100 lignes — bootstrap + cleanup)
│
├── VibeIsland/                   (NOUVEAU)
│   ├── VibeIslandPanel.swift     (~150 lignes — NSPanel hôte, positionnement notch, lifecycle)
│   ├── VibeIslandView.swift      (~120 lignes — SwiftUI root, gère mode Compact/Étendu/Panel)
│   ├── ArcReactorView.swift      (~180 lignes — SwiftUI Canvas, anneaux/cœur/particules/scan)
│   ├── ArcReactorState.swift     (~80 lignes  — enum + couleurs/vitesses par état)
│   ├── QuestionPanelView.swift   (~100 lignes — panel avec boutons cliquables)
│   └── ToolIndicatorView.swift   (~60 lignes  — label outil + mini-spinner)
│
├── IPC/                          (NOUVEAU)
│   ├── SocketListener.swift      (~120 lignes — refonte légère, ajoute parsing question)
│   └── EventSender.swift         (~80 lignes  — NOUVEAU : envoi clic vers events.sock)
│
└── (supprimés)
    ├── JarvisPanel.swift         (523 lignes — remplacé)
    ├── MetalRenderer.swift       (336 lignes — Metal plus utilisé)
    ├── BrowserPanel.swift        (151 lignes — feature non utilisée)
    └── InfoPanel.swift           (158 lignes — feature non utilisée)
```

### Côté Python

| Fichier | Modification |
|---|---|
| `assistant.py` | Parser `tool_use` `AskUserQuestion` → envoie state question UI → attend réponse via future → injecte tool_result dans stream input |
| `ui_socket.py` | Ajouter `send_question(payload)` + `EventListener` thread qui lit `/tmp/jarvis-ui-events.sock` |
| `main.py` | Brancher EventListener au démarrage, expose `wait_for_choice(tool_use_id, timeout=30)` |

### Justifications architecturales

- **SwiftUI au lieu de NSView+CALayer manuels** : déclaratif, animations plus simples, moins de bugs threading
- **Canvas SwiftUI pour Arc Reactor** : contrôle pixel-perfect des anneaux/scan/glow, anime via `.animation(.spring)`
- **Suppression Metal** : non justifié pour 18-90px. Économie ~336 lignes + GPU overhead évité
- **Suppression Browser/Info panels** : features non utilisées, repartent dans le panel principal si besoin réel
- **Séparation IPC/** : isole code socket, facilite tests et évolution du protocole

## 7. Stratégie d'implémentation (8 étapes)

| # | Étape | Livrable | Validation |
|---|---|---|---|
| 1 | Squelette panneau | `VibeIslandPanel.swift` + `VibeIslandView.swift` minimal (rectangle noir centré sous la notch) | `JARVIS_UI=1` → rectangle noir bien positionné |
| 2 | Arc Reactor statique | `ArcReactorView.swift` Canvas SwiftUI, état standby uniquement | Arc Reactor visible dans la pilule, rotation lente |
| 3 | États + animations | `ArcReactorState.swift` + transitions 4 états | Envoyer 4 états via socket, vérifier crossfades couleurs |
| 4 | Mode Étendu | `ToolIndicatorView.swift` + transition Compact↔Étendu | `{"state":"thinking","tool_name":"Gmail"}` → pilule s'élargit |
| 5 | Mode Panel | `QuestionPanelView.swift` + transition Étendu↔Panel | Payload question → panel descend, boutons cliquables |
| 6 | Socket bidirectionnel | `EventSender.swift` Swift + `EventListener` Python | Clic → réponse arrive dans terminal Python |
| 7 | Intégration AskUserQuestion | Parser `tool_use` dans `assistant.py` + injection `tool_result` | Demande complète Jarvis → question posée → clic → réponse vocale |
| 8 | Nettoyage | Suppression fichiers obsolètes + revue imports | Build clean, zéro warning |

### Tests

- **Pas de tests unitaires Swift** : pour de l'UI macOS pure, l'effort/valeur est trop déséquilibré.
- **Validation manuelle systématique** à chaque étape (colonne droite ci-dessus).
- **Test backend Python** : script `test_question.py` qui envoie un payload question via socket et lit la réponse — permet de tester sans lancer Whisper/Kokoro.

### Risques et mitigations

| Risque | Mitigation |
|---|---|
| Macs sans notch (MBA M2, Mac mini, écrans externes) | Détecter `screen.safeAreaInsets.top` — si 0, fallback : positionner la pilule à `y = screen.maxY - 4` (collé au bord haut sans intégration notch) |
| Latence socket de quelques ms qui casse la fluidité | Animations triggered côté Swift en réponse à l'état local, pas côté Python. Le socket ne fait que pousser l'état brut |
| `AskUserQuestion` avec plusieurs questions (`questions[]` array) | V1 : ne prendre que `questions[0]`, logger un warning. V2 future si nécessaire |
| Interférence avec apps fullscreen | NSPanel `collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]` — déjà en place dans le code actuel |

### Définition de "done"

- Les 8 étapes passent leur validation manuelle individuelle
- Au moins une conversation complète Jarvis en démo : wake → écoute → outil affiché en Étendu → question posée en Panel → clic utilisateur → réponse vocale → retour Compact
- Aucun warning de compilation Swift
- Aucun import résiduel vers les fichiers supprimés (`JarvisPanel`, `MetalRenderer`, `BrowserPanel`, `InfoPanel`)

## 8. Hors-périmètre (V2 / plus tard)

Volontairement exclus de cette V1 pour rester focalisé :

- Affichage transcription Whisper temps réel (volonté explicite : vocal-first)
- Affichage réponse markdown streamée (volonté explicite)
- Listes de mails / résultats structurés affichés (peuvent être lus à voix haute par Jarvis)
- Multi-questions `AskUserQuestion` simultanées
- Réponse libre type "Other" sur les choix
- Drag de la pilule (position fixe centrée notch)
- Thèmes / personnalisation couleurs (Arc Reactor cyan fixe)
- Support Macs sans notch optimisé (fallback fonctionnel uniquement)

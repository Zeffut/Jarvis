# UI Vibe Island — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remplacer l'UI Swift actuelle (overlay plein écran + sphère Metal) par Vibe Island — pilule ambient permanente sous la notch macOS, rendu Arc Reactor holographique, choix cliquables via interception du tool `AskUserQuestion` natif de Claude Code.

**Architecture:** NSPanel unique transparent positionné sous la notch, contenu rendu en SwiftUI (Canvas + ZStack). Communication backend ↔ UI via deux Unix domain sockets : `/tmp/jarvis-ui.sock` (Python → Swift) et `/tmp/jarvis-ui-events.sock` (Swift → Python pour les clics).

**Tech Stack:** Swift 5.9, SwiftUI macOS 13+, AppKit (NSPanel), Python 3, `claude` CLI stream-json.

**Spec source:** `docs/superpowers/specs/2026-05-18-ui-vibe-island-design.md`

---

## Carte des fichiers

**À créer**
- `ui/Sources/JarvisUI/VibeIsland/VibeIslandPanel.swift` — NSPanel hôte, positionnement notch, lifecycle
- `ui/Sources/JarvisUI/VibeIsland/VibeIslandView.swift` — SwiftUI root, switche Compact/Étendu/Panel
- `ui/Sources/JarvisUI/VibeIsland/ArcReactorView.swift` — rendu Arc Reactor SwiftUI (anneaux + cœur + scan + flicker)
- `ui/Sources/JarvisUI/VibeIsland/ArcReactorState.swift` — enum + couleurs/vitesses par état
- `ui/Sources/JarvisUI/VibeIsland/QuestionPanelView.swift` — panel avec boutons cliquables
- `ui/Sources/JarvisUI/VibeIsland/ToolIndicatorView.swift` — label outil + mini-spinner
- `ui/Sources/JarvisUI/IPC/SocketListener.swift` — refonte légère (extension du protocole)
- `ui/Sources/JarvisUI/IPC/EventSender.swift` — envoi clic vers `/tmp/jarvis-ui-events.sock`

**À modifier**
- `ui/Sources/JarvisUI/AppDelegate.swift` — remplace `JarvisPanel` par `VibeIslandPanel`
- `ui_socket.py` — ajoute `send_question()` + thread `EventListener` côté Python
- `assistant.py` — intercepte tool_use `AskUserQuestion`, attend réponse, injecte tool_result
- `main.py` — branche `EventListener` au démarrage

**À supprimer (Task 8)**
- `ui/Sources/JarvisUI/JarvisPanel.swift` (523 lignes)
- `ui/Sources/JarvisUI/MetalRenderer.swift` (336 lignes)
- `ui/Sources/JarvisUI/BrowserPanel.swift` (151 lignes)
- `ui/Sources/JarvisUI/InfoPanel.swift` (158 lignes)
- `ui/Sources/JarvisUI/SocketListener.swift` (déplacé vers `IPC/`)

---

## Tests : approche

- **Swift UI** : pas de tests unitaires (effort/valeur trop déséquilibré pour de l'UI macOS pure). Validation manuelle systématique via `JARVIS_UI=1` + envoi de payloads via un script.
- **Python** : tests unitaires avec `pytest` pour `EventListener` et l'interception `AskUserQuestion` dans `assistant.py`.
- **Script de validation manuelle** : `scripts/test_vibe.py` (créé en Task 1) qui pousse des payloads sur `/tmp/jarvis-ui.sock` pour exercer chaque mode sans lancer Whisper/Kokoro.

---

## Task 1 : Squelette VibeIslandPanel + activation

**Files:**
- Create: `ui/Sources/JarvisUI/VibeIsland/VibeIslandPanel.swift`
- Create: `ui/Sources/JarvisUI/VibeIsland/VibeIslandView.swift`
- Create: `scripts/test_vibe.py`
- Modify: `ui/Sources/JarvisUI/AppDelegate.swift`

- [ ] **Step 1: Créer `VibeIslandPanel.swift`**

```swift
import AppKit
import SwiftUI

/// NSPanel hôte de Vibe Island. Toujours visible, ancré sous la notch.
final class VibeIslandPanel: NSPanel {

    private let model = VibeIslandModel()

    convenience init() {
        self.init(
            contentRect: NSRect(origin: .zero, size: NSSize(width: 200, height: 60)),
            styleMask: [.borderless, .nonactivatingPanel],
            backing: .buffered,
            defer: false
        )
        configurePanel()
        installSwiftUIView()
    }

    private func configurePanel() {
        isOpaque = false
        backgroundColor = .clear
        level = NSWindow.Level(rawValue: Int(CGWindowLevelForKey(.statusWindow)) + 1)
        hasShadow = false
        isMovable = false
        ignoresMouseEvents = false       // on a besoin des clics pour les boutons
        collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
    }

    private func installSwiftUIView() {
        let hosting = NSHostingView(rootView: VibeIslandView(model: model))
        hosting.autoresizingMask = [.width, .height]
        contentView = hosting
    }

    /// Positionne le panel centré horizontalement, ancré tout en haut (sous la notch
    /// si présente, sinon collé au bord supérieur).
    func anchorToNotch() {
        guard let screen = NSScreen.main else { return }
        let panelSize = NSSize(width: 200, height: 60)
        let sf = screen.frame
        let notchInset = screen.safeAreaInsets.top   // 0 si pas de notch
        let x = sf.origin.x + (sf.width - panelSize.width) / 2
        let y = sf.origin.y + sf.height - panelSize.height + max(notchInset - 4, 0)
        setFrame(NSRect(x: x, y: y, width: panelSize.width, height: panelSize.height),
                 display: true)
    }

    func show() {
        anchorToNotch()
        orderFront(nil)
    }

    // Expose le modèle pour qu'AppDelegate puisse pousser des états.
    var stateModel: VibeIslandModel { model }
}
```

- [ ] **Step 2: Créer `VibeIslandView.swift`**

```swift
import SwiftUI

/// Source de vérité pour l'UI Vibe Island. Mis à jour depuis AppDelegate.
@MainActor
final class VibeIslandModel: ObservableObject {
    @Published var state: String = "standby"
    @Published var toolName: String? = nil
    @Published var question: VibeQuestion? = nil
}

struct VibeQuestion: Equatable {
    let toolUseId: String
    let prompt: String
    let choices: [Choice]

    struct Choice: Equatable, Identifiable {
        let id: String
        let label: String
    }
}

struct VibeIslandView: View {
    @ObservedObject var model: VibeIslandModel

    var body: some View {
        // V1 minimale : rectangle noir arrondi avec label texte du state.
        // Sera étoffé dans les tasks suivantes.
        RoundedRectangle(cornerRadius: 18)
            .fill(Color.black)
            .frame(width: 160, height: 30)
            .overlay(
                Text(model.state)
                    .font(.system(size: 11, weight: .medium))
                    .foregroundColor(.white)
            )
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
    }
}
```

- [ ] **Step 3: Modifier `AppDelegate.swift` pour utiliser VibeIslandPanel**

Remplacer le contenu intégralement par :

```swift
import AppKit

final class AppDelegate: NSObject, NSApplicationDelegate {
    private var panel: VibeIslandPanel?

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.accessory)

        panel = VibeIslandPanel()
        panel?.show()

        SocketListener.shared.start()

        NotificationCenter.default.addObserver(
            self,
            selector: #selector(handleMessage(_:)),
            name: SocketListener.messageNotification,
            object: nil
        )
    }

    @objc private func handleMessage(_ notification: Notification) {
        guard let msg = notification.object as? JarvisMessage else { return }
        // V1 : on synchronise juste le state.
        Task { @MainActor in
            self.panel?.stateModel.state = msg.state
        }
    }

    func applicationWillTerminate(_ notification: Notification) {
        NotificationCenter.default.removeObserver(self)
        unlink("/tmp/jarvis-ui.sock")
    }
}
```

- [ ] **Step 4: Créer `scripts/test_vibe.py` pour la validation manuelle**

```python
#!/usr/bin/env python3
"""Pousse des payloads sur /tmp/jarvis-ui.sock pour tester Vibe Island
sans lancer Whisper/Kokoro. Usage : python3 scripts/test_vibe.py <state>"""

import json
import socket
import sys
import time

SOCK = "/tmp/jarvis-ui.sock"

def send(payload: dict) -> None:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.connect(SOCK)
        s.sendall(json.dumps(payload).encode())

if __name__ == "__main__":
    state = sys.argv[1] if len(sys.argv) > 1 else "standby"
    payload = {"state": state, "amplitude": 0.0}
    print(f"→ {payload}")
    send(payload)
```

Rendre exécutable :

```bash
chmod +x scripts/test_vibe.py
```

- [ ] **Step 5: Build et validation manuelle**

```bash
cd ui && swift build -c release && cd ..
JARVIS_UI=1 ui/.build/release/JarvisUI &
sleep 1
python3 scripts/test_vibe.py listening
```

Attendu : rectangle noir arrondi centré sous la notch (160×30), affichant "listening". Le rectangle reste visible (pas de fermeture automatique).

Tuer ensuite : `pkill -f JarvisUI`

- [ ] **Step 6: Commit**

```bash
git add ui/Sources/JarvisUI/VibeIsland/ ui/Sources/JarvisUI/AppDelegate.swift scripts/test_vibe.py
git commit -m "feat(ui): squelette VibeIslandPanel sous la notch"
```

---

## Task 2 : ArcReactorState + ArcReactorView statique (état standby)

**Files:**
- Create: `ui/Sources/JarvisUI/VibeIsland/ArcReactorState.swift`
- Create: `ui/Sources/JarvisUI/VibeIsland/ArcReactorView.swift`
- Modify: `ui/Sources/JarvisUI/VibeIsland/VibeIslandView.swift`

- [ ] **Step 1: Créer `ArcReactorState.swift`**

```swift
import SwiftUI

/// État courant de l'Arc Reactor. Source de vérité pour les couleurs,
/// vitesses d'animation et intensités du glow.
enum ArcReactorState: String, CaseIterable {
    case standby
    case listening
    case thinking
    case speaking

    /// Couleur dominante de l'anneau et du glow.
    var color: Color {
        switch self {
        case .standby:   return Color(red: 0.36, green: 0.78, blue: 1.00).opacity(0.4)
        case .listening: return Color(red: 0.36, green: 0.78, blue: 1.00)
        case .thinking:  return Color(red: 1.00, green: 0.66, blue: 0.33)
        case .speaking:  return Color(red: 0.60, green: 0.93, blue: 1.00)
        }
    }

    /// Rayon du halo glow en pixels (à scaler avec la taille du reactor).
    var glowRadius: CGFloat {
        switch self {
        case .standby:   return 8
        case .listening: return 16
        case .thinking:  return 12
        case .speaking:  return 14
        }
    }

    /// Durée d'un cycle de "breathe" (scale 1 ↔ 1.05).
    var breatheDuration: Double {
        switch self {
        case .standby:   return 4.0
        case .listening: return 1.2
        case .thinking:  return 1.8
        case .speaking:  return 0.9
        }
    }

    /// Durée d'une rotation complète de l'anneau extérieur.
    var rotationDuration: Double {
        switch self {
        case .standby:   return 20.0
        case .listening: return 8.0
        case .thinking:  return 5.0
        case .speaking:  return 10.0
        }
    }

    /// Active scan lines + flicker ? (off en standby pour rester discret)
    var hasHologramEffects: Bool {
        self != .standby
    }
}
```

- [ ] **Step 2: Créer `ArcReactorView.swift`**

```swift
import SwiftUI

/// Rendu de l'Arc Reactor — anneaux, cœur, particules, scan lines, flicker.
struct ArcReactorView: View {
    let state: ArcReactorState
    let size: CGFloat

    @State private var ringRotation: Double = 0
    @State private var particleRotation: Double = 0
    @State private var breatheScale: CGFloat = 1.0
    @State private var flickerOpacity: Double = 1.0

    private var showFullDetails: Bool { size >= 40 }

    var body: some View {
        ZStack {
            // Anneau extérieur : dashed, rotation lente
            Circle()
                .strokeBorder(
                    state.color,
                    style: StrokeStyle(
                        lineWidth: max(1, size / 18),
                        lineCap: .round,
                        dash: [size * 0.25, size * 0.04, size * 0.05, size * 0.04]
                    )
                )
                .rotationEffect(.degrees(ringRotation))
                .shadow(color: state.color.opacity(0.8), radius: state.glowRadius / 2)

            // Anneau intérieur : dashed fin, statique
            if showFullDetails {
                Circle()
                    .strokeBorder(
                        state.color.opacity(0.4),
                        style: StrokeStyle(lineWidth: 0.8, dash: [2, 2])
                    )
                    .padding(size * 0.10)
            }

            // Particules orbitales (12h / 6h)
            if showFullDetails {
                ParticlesOrbit(color: state.color, size: size)
                    .rotationEffect(.degrees(particleRotation))
            }

            // Cœur : gradient radial
            Circle()
                .fill(
                    RadialGradient(
                        colors: [.white, state.color, Color(red: 0.07, green: 0.14, blue: 0.33)],
                        center: .center,
                        startRadius: 0,
                        endRadius: size * 0.18
                    )
                )
                .frame(width: size * 0.4, height: size * 0.4)
                .scaleEffect(breatheScale)
                .shadow(color: state.color, radius: state.glowRadius)

            // Scan lines holographiques
            if showFullDetails && state.hasHologramEffects {
                ScanLinesOverlay()
                    .clipShape(Circle())
                    .blendMode(.screen)
                    .opacity(0.5)
            }
        }
        .frame(width: size, height: size)
        .opacity(flickerOpacity)
        .onAppear { startAnimations() }
        .onChange(of: state) { _ in restartAnimations() }
    }

    private func startAnimations() {
        // Rotation continue anneau extérieur
        withAnimation(.linear(duration: state.rotationDuration).repeatForever(autoreverses: false)) {
            ringRotation = 360
        }
        // Rotation inverse particules
        withAnimation(.linear(duration: state.rotationDuration * 0.45).repeatForever(autoreverses: false)) {
            particleRotation = -360
        }
        // Breathe du cœur
        withAnimation(.easeInOut(duration: state.breatheDuration).repeatForever(autoreverses: true)) {
            breatheScale = 1.05
        }
        // Flicker holographique aléatoire
        if state.hasHologramEffects {
            scheduleNextFlicker()
        }
    }

    private func restartAnimations() {
        // Stop animations (reset des valeurs) puis relancer avec nouvelles durées.
        ringRotation = 0
        particleRotation = 0
        breatheScale = 1.0
        flickerOpacity = 1.0
        // Léger délai pour laisser SwiftUI propager le reset avant de réanimer.
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.05) {
            startAnimations()
        }
    }

    private func scheduleNextFlicker() {
        let delay = Double.random(in: 3.0...5.0)
        DispatchQueue.main.asyncAfter(deadline: .now() + delay) {
            guard state.hasHologramEffects else { return }
            withAnimation(.linear(duration: 0.05)) { flickerOpacity = 0.4 }
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.05) {
                withAnimation(.linear(duration: 0.05)) { flickerOpacity = 1.0 }
                scheduleNextFlicker()
            }
        }
    }
}

/// 2 points lumineux opposés sur l'anneau, à 12h et 6h.
private struct ParticlesOrbit: View {
    let color: Color
    let size: CGFloat

    var body: some View {
        ZStack {
            Circle()
                .fill(Color.white)
                .frame(width: size * 0.06, height: size * 0.06)
                .shadow(color: color, radius: 4)
                .offset(y: -size * 0.42)
            Circle()
                .fill(Color.white)
                .frame(width: size * 0.06, height: size * 0.06)
                .shadow(color: color, radius: 4)
                .offset(y: size * 0.42)
        }
    }
}

/// Scan lines horizontales (effet CRT/holographique).
private struct ScanLinesOverlay: View {
    var body: some View {
        Canvas { ctx, size in
            let lineSpacing: CGFloat = 3
            var y: CGFloat = 0
            while y < size.height {
                ctx.fill(
                    Path(CGRect(x: 0, y: y, width: size.width, height: 1)),
                    with: .color(Color(red: 0.36, green: 0.78, blue: 1.00).opacity(0.15))
                )
                y += lineSpacing
            }
        }
    }
}
```

- [ ] **Step 3: Intégrer ArcReactorView dans VibeIslandView**

Remplacer le corps de `VibeIslandView` dans `VibeIslandView.swift` par :

```swift
struct VibeIslandView: View {
    @ObservedObject var model: VibeIslandModel

    private var arcState: ArcReactorState {
        ArcReactorState(rawValue: model.state) ?? .standby
    }

    var body: some View {
        HStack(spacing: 8) {
            ArcReactorView(state: arcState, size: 18)
                .padding(.leading, 8)
            Text(label)
                .font(.system(size: 11, weight: .medium))
                .foregroundColor(.white.opacity(0.85))
            Spacer()
        }
        .frame(width: 160, height: 30)
        .background(
            RoundedRectangle(cornerRadius: 15)
                .fill(Color.black)
        )
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
    }

    private var label: String {
        switch arcState {
        case .standby:   return "Jarvis"
        case .listening: return "Listening"
        case .thinking:  return "Thinking"
        case .speaking:  return "Speaking"
        }
    }
}
```

- [ ] **Step 4: Build et validation visuelle**

```bash
cd ui && swift build -c release && cd ..
JARVIS_UI=1 ui/.build/release/JarvisUI &
sleep 1
python3 scripts/test_vibe.py standby
```

Attendu : pilule noire avec un mini Arc Reactor cyan animé (rotation lente de l'anneau dashed) à gauche du label "Jarvis". Halo cyan doux visible.

Tester aussi `listening`, `thinking`, `speaking` :
```bash
for s in listening thinking speaking standby; do
  python3 scripts/test_vibe.py $s
  sleep 2
done
```

À chaque changement, vérifier que la couleur de l'Arc Reactor change avec un crossfade fluide (pas de jump), et que la vitesse de rotation s'adapte.

Tuer : `pkill -f JarvisUI`

- [ ] **Step 5: Commit**

```bash
git add ui/Sources/JarvisUI/VibeIsland/
git commit -m "feat(ui): ArcReactor SwiftUI avec 4 états animés"
```

---

## Task 3 : Mode Étendu + ToolIndicatorView

**Files:**
- Create: `ui/Sources/JarvisUI/VibeIsland/ToolIndicatorView.swift`
- Modify: `ui/Sources/JarvisUI/VibeIsland/VibeIslandView.swift`
- Modify: `ui/Sources/JarvisUI/SocketListener.swift` (ajoute champ `toolName`)
- Modify: `ui/Sources/JarvisUI/AppDelegate.swift` (relaie `toolName`)
- Modify: `scripts/test_vibe.py` (support `--tool`)
- Modify: `ui_socket.py` (ajoute paramètre `tool_name`)

- [ ] **Step 1: Créer `ToolIndicatorView.swift`**

```swift
import SwiftUI

struct ToolIndicatorView: View {
    let toolName: String
    @State private var spinnerRotation: Double = 0

    var body: some View {
        HStack(spacing: 6) {
            Text(toolName)
                .font(.system(size: 11, weight: .medium))
                .foregroundColor(.white.opacity(0.85))
                .lineLimit(1)
                .truncationMode(.tail)
            MiniSpinner()
        }
    }
}

private struct MiniSpinner: View {
    @State private var rotation: Double = 0

    var body: some View {
        Circle()
            .trim(from: 0.0, to: 0.7)
            .stroke(
                Color(red: 0.36, green: 0.78, blue: 1.00),
                style: StrokeStyle(lineWidth: 1.2, lineCap: .round)
            )
            .frame(width: 10, height: 10)
            .rotationEffect(.degrees(rotation))
            .onAppear {
                withAnimation(.linear(duration: 1.0).repeatForever(autoreverses: false)) {
                    rotation = 360
                }
            }
    }
}
```

- [ ] **Step 2: Ajouter `toolName` au modèle SocketListener**

Modifier `JarvisMessage` dans `SocketListener.swift` :

```swift
struct JarvisMessage {
    let state: String
    let amplitude: Float
    let displayContent: [String: Any]?
    let token: String?
    let url: String?
    let toolName: String?           // NOUVEAU
}
```

Dans `handleClient(fd:)`, après les autres extractions :

```swift
let toolName = json["tool_name"] as? String
let msg = JarvisMessage(state: state, amplitude: amplitude,
                        displayContent: displayContent, token: token, url: url,
                        toolName: toolName)
```

- [ ] **Step 3: Étendre le modèle UI et la vue**

Dans `VibeIslandView.swift`, modifier `VibeIslandModel` pour publier `toolName` (déjà présent dans la définition du Task 1 — vérifier que c'est bien là, sinon ajouter `@Published var toolName: String? = nil`).

Remplacer le corps de `VibeIslandView` par :

```swift
struct VibeIslandView: View {
    @ObservedObject var model: VibeIslandModel

    private var arcState: ArcReactorState {
        ArcReactorState(rawValue: model.state) ?? .standby
    }

    private var isExpanded: Bool { model.toolName != nil }

    var body: some View {
        HStack(spacing: 8) {
            ArcReactorView(state: arcState, size: isExpanded ? 22 : 18)
                .padding(.leading, 10)

            if let tool = model.toolName {
                ToolIndicatorView(toolName: tool)
                    .transition(.opacity.combined(with: .move(edge: .leading)))
            } else {
                Text(stateLabel)
                    .font(.system(size: 11, weight: .medium))
                    .foregroundColor(.white.opacity(0.85))
                    .transition(.opacity)
            }
            Spacer(minLength: 0)
        }
        .frame(width: isExpanded ? 340 : 160,
               height: isExpanded ? 34 : 30)
        .background(
            RoundedRectangle(cornerRadius: isExpanded ? 17 : 15)
                .fill(Color.black)
        )
        .animation(.spring(response: 0.35, dampingFraction: 0.78), value: isExpanded)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
    }

    private var stateLabel: String {
        switch arcState {
        case .standby:   return "Jarvis"
        case .listening: return "Listening"
        case .thinking:  return "Thinking"
        case .speaking:  return "Speaking"
        }
    }
}
```

- [ ] **Step 4: Relayer `toolName` dans AppDelegate**

Dans `handleMessage(_:)` de `AppDelegate.swift`, remplacer par :

```swift
@objc private func handleMessage(_ notification: Notification) {
    guard let msg = notification.object as? JarvisMessage else { return }
    Task { @MainActor in
        self.panel?.stateModel.state = msg.state
        self.panel?.stateModel.toolName = msg.toolName
    }
}
```

- [ ] **Step 5: Étendre `scripts/test_vibe.py` pour pousser un toolName**

Remplacer le contenu par :

```python
#!/usr/bin/env python3
"""Pousse des payloads sur /tmp/jarvis-ui.sock pour tester Vibe Island.
Usage :
  python3 scripts/test_vibe.py <state>
  python3 scripts/test_vibe.py <state> --tool "Gmail · search threads…"
"""

import argparse
import json
import socket

SOCK = "/tmp/jarvis-ui.sock"

def send(payload: dict) -> None:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.connect(SOCK)
        s.sendall(json.dumps(payload).encode())

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("state")
    ap.add_argument("--tool", default=None)
    args = ap.parse_args()
    payload = {"state": args.state, "amplitude": 0.0}
    if args.tool:
        payload["tool_name"] = args.tool
    print(f"→ {payload}")
    send(payload)
```

- [ ] **Step 6: Ajouter le paramètre `tool_name` côté Python (`ui_socket.py`)**

Modifier la fonction `send_state` dans `ui_socket.py` :

```python
def send_state(state: str, amplitude: float = 0.0, tool_name: str | None = None) -> None:
    """Envoie l'état courant à l'UI Swift. Fire-and-forget, jamais bloquant."""
    if state not in _VALID_STATES:
        return
    _send_to(SOCKET_PATH, state, amplitude, tool_name=tool_name)
```

Modifier `_send_to` pour propager `tool_name` dans le payload JSON :

```python
def _send_to(
    path: str,
    state: str,
    amplitude: float,
    content: dict | None = None,
    token: str | None = None,
    url: str | None = None,
    tool_name: str | None = None,
) -> None:
    if not UI_ENABLED:
        return
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(0.15)
            s.connect(path)
            payload: dict = {"state": state, "amplitude": round(amplitude, 3)}
            if content is not None:
                payload["content"] = content
            if token is not None:
                payload["token"] = token
            if url is not None:
                payload["url"] = url
            if tool_name is not None:
                payload["tool_name"] = tool_name
            s.sendall(json.dumps(payload).encode())
    except Exception:
        pass
```

- [ ] **Step 7: Build et validation**

```bash
cd ui && swift build -c release && cd ..
JARVIS_UI=1 ui/.build/release/JarvisUI &
sleep 1
python3 scripts/test_vibe.py thinking --tool "Gmail · search threads…"
sleep 3
python3 scripts/test_vibe.py thinking
sleep 2
python3 scripts/test_vibe.py standby
```

Attendu :
1. La pilule s'élargit avec une animation spring (160→340px) et affiche le label outil + mini-spinner cyan tournant.
2. Sans le `--tool`, elle se rétracte (340→160px) et revient au label "Thinking".
3. Retour à "Jarvis" en standby.

Tuer : `pkill -f JarvisUI`

- [ ] **Step 8: Commit**

```bash
git add ui/Sources/JarvisUI/VibeIsland/ToolIndicatorView.swift \
        ui/Sources/JarvisUI/VibeIsland/VibeIslandView.swift \
        ui/Sources/JarvisUI/SocketListener.swift \
        ui/Sources/JarvisUI/AppDelegate.swift \
        scripts/test_vibe.py \
        ui_socket.py
git commit -m "feat(ui): mode étendu avec ToolIndicator + protocole tool_name"
```

---

## Task 4 : Mode Panel + QuestionPanelView

**Files:**
- Create: `ui/Sources/JarvisUI/VibeIsland/QuestionPanelView.swift`
- Modify: `ui/Sources/JarvisUI/VibeIsland/VibeIslandView.swift`
- Modify: `ui/Sources/JarvisUI/SocketListener.swift` (parse payload question)
- Modify: `ui/Sources/JarvisUI/VibeIsland/VibeIslandPanel.swift` (taille dynamique du panel NSWindow)
- Modify: `ui/Sources/JarvisUI/AppDelegate.swift` (relaie question)
- Modify: `scripts/test_vibe.py` (option `--question`)

- [ ] **Step 1: Créer `QuestionPanelView.swift`**

```swift
import SwiftUI

struct QuestionPanelView: View {
    let question: VibeQuestion
    let arcState: ArcReactorState
    let onChoice: (VibeQuestion.Choice) -> Void

    var body: some View {
        VStack(spacing: 0) {
            // Arc Reactor en grand au-dessus
            ArcReactorView(state: arcState, size: 80)
                .padding(.top, 18)
                .padding(.bottom, 14)

            // Prompt
            Text(question.prompt)
                .font(.system(size: 12, weight: .medium))
                .foregroundColor(.white.opacity(0.85))
                .multilineTextAlignment(.center)
                .padding(.horizontal, 18)
                .padding(.bottom, 14)

            // Boutons cliquables
            VStack(spacing: 8) {
                ForEach(Array(question.choices.enumerated()), id: \.element.id) { idx, choice in
                    ChoiceButton(label: choice.label) {
                        onChoice(choice)
                    }
                    .transition(.asymmetric(
                        insertion: .opacity.combined(with: .move(edge: .top))
                            .animation(.spring(response: 0.4, dampingFraction: 0.7).delay(Double(idx) * 0.05)),
                        removal: .opacity
                    ))
                }
            }
            .padding(.horizontal, 14)
            .padding(.bottom, 16)
        }
        .frame(width: 380)
        .background(
            RoundedRectangle(cornerRadius: 22)
                .fill(Color.black)
        )
    }
}

private struct ChoiceButton: View {
    let label: String
    let action: () -> Void

    @State private var hovering = false
    @State private var clickScale: CGFloat = 1.0

    var body: some View {
        Button(action: triggerAction) {
            Text(label)
                .font(.system(size: 12, weight: .medium))
                .foregroundColor(.white)
                .frame(maxWidth: .infinity)
                .frame(height: 36)
                .background(
                    RoundedRectangle(cornerRadius: 10)
                        .fill(Color(white: 0.08))
                        .overlay(
                            RoundedRectangle(cornerRadius: 10)
                                .stroke(Color(red: 0.36, green: 0.78, blue: 1.00).opacity(hovering ? 0.85 : 0.45),
                                        lineWidth: 1)
                        )
                        .shadow(color: Color(red: 0.36, green: 0.78, blue: 1.00).opacity(hovering ? 0.5 : 0),
                                radius: hovering ? 8 : 0)
                )
        }
        .buttonStyle(.plain)
        .scaleEffect(hovering ? 1.02 : clickScale)
        .animation(.easeInOut(duration: 0.18), value: hovering)
        .animation(.easeInOut(duration: 0.1), value: clickScale)
        .onHover { hovering = $0 }
    }

    private func triggerAction() {
        // Rebond visuel : 1.0 → 0.95 → 1.05 → 1.0 sur ~200ms
        clickScale = 0.95
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.08) { clickScale = 1.05 }
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.18) {
            clickScale = 1.0
            action()
        }
    }
}
```

- [ ] **Step 2: Ajouter le parsing question dans SocketListener**

Dans `SocketListener.swift`, étendre `JarvisMessage` et `handleClient` :

```swift
struct JarvisMessage {
    let state: String
    let amplitude: Float
    let displayContent: [String: Any]?
    let token: String?
    let url: String?
    let toolName: String?
    let question: VibeQuestion?     // NOUVEAU
}
```

Dans `handleClient(fd:)`, après les extractions existantes :

```swift
var parsedQuestion: VibeQuestion? = nil
if state == "question",
   let prompt = json["question"] as? String,
   let toolUseId = json["tool_use_id"] as? String,
   let choicesArr = json["choices"] as? [[String: Any]] {
    let choices: [VibeQuestion.Choice] = choicesArr.compactMap { dict in
        guard let id = dict["id"] as? String,
              let label = dict["label"] as? String else { return nil }
        return VibeQuestion.Choice(id: id, label: label)
    }
    parsedQuestion = VibeQuestion(toolUseId: toolUseId, prompt: prompt, choices: choices)
}

let msg = JarvisMessage(state: state, amplitude: amplitude,
                        displayContent: displayContent, token: token, url: url,
                        toolName: toolName, question: parsedQuestion)
```

- [ ] **Step 3: Étendre VibeIslandView pour gérer le mode Panel**

Remplacer le corps de `VibeIslandView` par :

```swift
struct VibeIslandView: View {
    @ObservedObject var model: VibeIslandModel

    private var arcState: ArcReactorState {
        ArcReactorState(rawValue: model.state) ?? .standby
    }

    private var mode: Mode {
        if model.question != nil { return .panel }
        if model.toolName != nil { return .extended }
        return .compact
    }

    var body: some View {
        Group {
            switch mode {
            case .compact:
                compactBar
            case .extended:
                extendedBar
            case .panel:
                if let q = model.question {
                    QuestionPanelView(
                        question: q,
                        arcState: arcState,
                        onChoice: { choice in
                            handleChoice(q, choice)
                        }
                    )
                }
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
        .animation(.spring(response: 0.5, dampingFraction: 0.75), value: mode)
    }

    private var compactBar: some View {
        HStack(spacing: 8) {
            ArcReactorView(state: arcState, size: 18).padding(.leading, 10)
            Text(stateLabel)
                .font(.system(size: 11, weight: .medium))
                .foregroundColor(.white.opacity(0.85))
            Spacer(minLength: 0)
        }
        .frame(width: 160, height: 30)
        .background(RoundedRectangle(cornerRadius: 15).fill(Color.black))
    }

    private var extendedBar: some View {
        HStack(spacing: 8) {
            ArcReactorView(state: arcState, size: 22).padding(.leading, 10)
            if let tool = model.toolName {
                ToolIndicatorView(toolName: tool)
            }
            Spacer(minLength: 0)
        }
        .frame(width: 340, height: 34)
        .background(RoundedRectangle(cornerRadius: 17).fill(Color.black))
    }

    private var stateLabel: String {
        switch arcState {
        case .standby:   return "Jarvis"
        case .listening: return "Listening"
        case .thinking:  return "Thinking"
        case .speaking:  return "Speaking"
        }
    }

    private func handleChoice(_ q: VibeQuestion, _ choice: VibeQuestion.Choice) {
        // Sera implémenté en Task 5 (EventSender). Pour V1 : juste clear le model.
        EventSender.shared.sendChoice(toolUseId: q.toolUseId, label: choice.label)
        model.question = nil
    }

    enum Mode: Equatable { case compact, extended, panel }
}
```

> **Note :** `EventSender.shared.sendChoice` est ajouté en Task 5. Pour valider Task 4 isolément, commenter temporairement la ligne `EventSender.shared.sendChoice(...)` ou ajouter un stub vide. La validation ci-dessous accepte que le clic ne fasse que reset le panel localement.

- [ ] **Step 4: Ajuster la taille du NSPanel dynamiquement**

Modifier `VibeIslandPanel.swift` pour permettre une hauteur plus grande quand un panel est affiché. Remplacer `anchorToNotch()` par :

```swift
func anchorToNotch(panelHeight: CGFloat = 60) {
    guard let screen = NSScreen.main else { return }
    let panelWidth: CGFloat = 400
    let sf = screen.frame
    let notchInset = screen.safeAreaInsets.top
    let x = sf.origin.x + (sf.width - panelWidth) / 2
    let y = sf.origin.y + sf.height - panelHeight + max(notchInset - 4, 0)
    setFrame(NSRect(x: x, y: y, width: panelWidth, height: panelHeight),
             display: true)
}
```

Puis dans `installSwiftUIView()`, observer le modèle pour redimensionner :

```swift
private func installSwiftUIView() {
    let hosting = NSHostingView(rootView: VibeIslandView(model: model))
    hosting.autoresizingMask = [.width, .height]
    contentView = hosting

    // Observer changements de mode → redimensionne le NSPanel
    model.onModeChange = { [weak self] mode in
        let h: CGFloat = (mode == .panel) ? 260 : 60
        self?.anchorToNotch(panelHeight: h)
    }
}
```

Ajouter à `VibeIslandModel` (dans `VibeIslandView.swift`) :

```swift
@MainActor
final class VibeIslandModel: ObservableObject {
    @Published var state: String = "standby" {
        didSet { notifyModeChange() }
    }
    @Published var toolName: String? = nil {
        didSet { notifyModeChange() }
    }
    @Published var question: VibeQuestion? = nil {
        didSet { notifyModeChange() }
    }

    var onModeChange: ((VibeIslandView.Mode) -> Void)?

    private func notifyModeChange() {
        let mode: VibeIslandView.Mode
        if question != nil { mode = .panel }
        else if toolName != nil { mode = .extended }
        else { mode = .compact }
        onModeChange?(mode)
    }
}
```

- [ ] **Step 5: Relayer la question dans AppDelegate**

Modifier `handleMessage(_:)` :

```swift
@objc private func handleMessage(_ notification: Notification) {
    guard let msg = notification.object as? JarvisMessage else { return }
    Task { @MainActor in
        self.panel?.stateModel.state = msg.state
        self.panel?.stateModel.toolName = msg.toolName
        self.panel?.stateModel.question = msg.question
    }
}
```

- [ ] **Step 6: Étendre `scripts/test_vibe.py` pour pousser une question**

Ajouter au parser d'args :

```python
ap.add_argument("--question", default=None,
                help='JSON {"prompt":"...","choices":[{"id":"0","label":"Sarah"}]}')
ap.add_argument("--tool-use-id", default="toolu_test_123")
```

Et après `if args.tool: ...` :

```python
if args.question:
    q = json.loads(args.question)
    payload["state"] = "question"
    payload["tool_use_id"] = args.tool_use_id
    payload["question"] = q["prompt"]
    payload["choices"] = q["choices"]
```

- [ ] **Step 7: Stubber `EventSender.shared.sendChoice` (sera remplacé en Task 5)**

Dans `VibeIslandView.swift`, juste au-dessus de `struct VibeIslandView`, ajouter temporairement :

```swift
// Stub temporaire — remplacé par EventSender réel en Task 5.
enum EventSender {
    static let shared = EventSender.self
    static func sendChoice(toolUseId: String, label: String) {
        print("[stub] choice toolUseId=\(toolUseId) label=\(label)")
    }
}
```

- [ ] **Step 8: Build et validation**

```bash
cd ui && swift build -c release && cd ..
JARVIS_UI=1 ui/.build/release/JarvisUI &
sleep 1

# Pose une question
python3 scripts/test_vibe.py thinking --question '{"prompt":"Mail à Sarah ou Pierre ?","choices":[{"id":"0","label":"Sarah"},{"id":"1","label":"Pierre"}]}'
```

Attendu :
- Le panel descend avec animation spring (2 phases : élargissement horizontal puis descente verticale).
- Arc Reactor en grand (80px) visible avec toutes les couches (anneaux + cœur + particules + scan + flicker).
- 2 boutons "Sarah" / "Pierre" apparaissent en cascade (50ms entre chacun).
- Hover sur un bouton : glow cyan + scale 1.02.
- Clic sur un bouton : effet de rebond, panel disparaît, retour au compact. Console Swift affiche `[stub] choice toolUseId=toolu_test_123 label=...`.

Tuer : `pkill -f JarvisUI`

- [ ] **Step 9: Commit**

```bash
git add ui/Sources/JarvisUI/VibeIsland/QuestionPanelView.swift \
        ui/Sources/JarvisUI/VibeIsland/VibeIslandView.swift \
        ui/Sources/JarvisUI/VibeIsland/VibeIslandPanel.swift \
        ui/Sources/JarvisUI/SocketListener.swift \
        ui/Sources/JarvisUI/AppDelegate.swift \
        scripts/test_vibe.py
git commit -m "feat(ui): mode panel avec choix cliquables + animations cascade"
```

---

## Task 5 : Socket bidirectionnel — EventSender (Swift) + EventListener (Python)

**Files:**
- Create: `ui/Sources/JarvisUI/IPC/EventSender.swift`
- Modify: `ui/Sources/JarvisUI/VibeIsland/VibeIslandView.swift` (retire le stub)
- Modify: `ui_socket.py` (ajoute `EventListener` thread)
- Create: `tests/test_event_listener.py`

- [ ] **Step 1: Créer le dossier `IPC/` et `EventSender.swift`**

```swift
import Foundation

/// Envoie les événements UI (clics, timeouts) vers le backend Python
/// via /tmp/jarvis-ui-events.sock. Fire-and-forget, non-bloquant.
enum EventSender {
    static let socketPath = "/tmp/jarvis-ui-events.sock"

    static func sendChoice(toolUseId: String, label: String) {
        let payload: [String: Any] = [
            "type": "choice",
            "tool_use_id": toolUseId,
            "label": label,
        ]
        send(payload)
    }

    private static func send(_ payload: [String: Any]) {
        DispatchQueue.global(qos: .utility).async {
            guard let data = try? JSONSerialization.data(withJSONObject: payload) else { return }
            let fd = socket(AF_UNIX, SOCK_STREAM, 0)
            guard fd >= 0 else { return }
            defer { close(fd) }

            var addr = sockaddr_un()
            addr.sun_family = sa_family_t(AF_UNIX)
            withUnsafeMutableBytes(of: &addr.sun_path) { ptr in
                socketPath.withCString { cStr in
                    _ = strlcpy(
                        ptr.baseAddress!.assumingMemoryBound(to: CChar.self),
                        cStr, ptr.count
                    )
                }
            }

            let connResult = withUnsafePointer(to: &addr) {
                $0.withMemoryRebound(to: sockaddr.self, capacity: 1) {
                    connect(fd, $0, socklen_t(MemoryLayout<sockaddr_un>.size))
                }
            }
            guard connResult == 0 else { return }

            _ = data.withUnsafeBytes { bytes in
                write(fd, bytes.baseAddress, data.count)
            }
        }
    }
}
```

- [ ] **Step 2: Retirer le stub temporaire dans `VibeIslandView.swift`**

Supprimer le bloc `enum EventSender { ... static let shared = ... }` ajouté en Task 4 Step 7. Modifier l'appel dans `handleChoice` pour utiliser le vrai EventSender :

```swift
private func handleChoice(_ q: VibeQuestion, _ choice: VibeQuestion.Choice) {
    EventSender.sendChoice(toolUseId: q.toolUseId, label: choice.label)
    model.question = nil
}
```

- [ ] **Step 3: Écrire le test du EventListener Python (TDD)**

Créer `tests/test_event_listener.py` :

```python
"""Tests pour EventListener côté Python (lit /tmp/jarvis-ui-events.sock)."""
import json
import os
import socket
import threading
import time

import pytest

from ui_socket import EventListener


def test_event_listener_captures_choice(tmp_path):
    """EventListener doit recevoir un payload choice et le passer au callback."""
    sock_path = str(tmp_path / "events.sock")
    received: list[dict] = []
    done = threading.Event()

    def on_event(event: dict):
        received.append(event)
        done.set()

    listener = EventListener(socket_path=sock_path, callback=on_event)
    listener.start()
    try:
        # Attendre que le socket soit bind
        for _ in range(20):
            if os.path.exists(sock_path):
                break
            time.sleep(0.05)
        assert os.path.exists(sock_path), "EventListener n'a pas bind le socket"

        # Envoyer un payload
        payload = {"type": "choice", "tool_use_id": "tool_abc", "label": "Sarah"}
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.connect(sock_path)
            s.sendall(json.dumps(payload).encode())

        assert done.wait(timeout=2.0), "Callback non appelé"
        assert received == [payload]
    finally:
        listener.stop()
```

- [ ] **Step 4: Lancer le test pour vérifier qu'il échoue**

```bash
python3 -m pytest tests/test_event_listener.py -v
```

Attendu : `ImportError: cannot import name 'EventListener' from 'ui_socket'`.

- [ ] **Step 5: Implémenter `EventListener` dans `ui_socket.py`**

Ajouter en bas de `ui_socket.py` :

```python
import threading
from typing import Callable

EVENTS_SOCKET_PATH = "/tmp/jarvis-ui-events.sock"


class EventListener:
    """Thread daemon qui écoute /tmp/jarvis-ui-events.sock et appelle
    callback(event_dict) pour chaque message reçu (un par connexion).
    """

    def __init__(self, socket_path: str = EVENTS_SOCKET_PATH,
                 callback: Callable[[dict], None] = lambda e: None):
        self._path = socket_path
        self._callback = callback
        self._server: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._server is not None:
            try:
                self._server.close()
            except OSError:
                pass
        try:
            os.unlink(self._path)
        except FileNotFoundError:
            pass

    def _run(self) -> None:
        try:
            os.unlink(self._path)
        except FileNotFoundError:
            pass
        self._server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._server.bind(self._path)
        os.chmod(self._path, 0o600)
        self._server.listen(8)
        self._server.settimeout(0.5)
        while not self._stop.is_set():
            try:
                conn, _ = self._server.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            with conn:
                data = b""
                while True:
                    chunk = conn.recv(4096)
                    if not chunk:
                        break
                    data += chunk
            if not data:
                continue
            try:
                event = json.loads(data.decode())
            except Exception:
                continue
            try:
                self._callback(event)
            except Exception:
                pass
```

- [ ] **Step 6: Re-lancer le test**

```bash
python3 -m pytest tests/test_event_listener.py -v
```

Attendu : PASS.

- [ ] **Step 7: Validation manuelle end-to-end (UI → Python)**

Créer un petit script de validation `scripts/test_event_roundtrip.py` :

```python
#!/usr/bin/env python3
"""Lance EventListener, ouvre Vibe Island, pose une question, attend un clic."""
import json
import socket
import time
from ui_socket import EventListener

def on_choice(event):
    print(f"← Reçu : {event}")

listener = EventListener(callback=on_choice)
listener.start()

# Pousse une question vers l'UI
payload = {
    "state": "question",
    "tool_use_id": "toolu_test_roundtrip",
    "question": "Test roundtrip socket — choisis A ou B",
    "choices": [{"id": "0", "label": "A"}, {"id": "1", "label": "B"}],
    "amplitude": 0.0,
}
with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
    s.connect("/tmp/jarvis-ui.sock")
    s.sendall(json.dumps(payload).encode())

print("→ Question envoyée. Clique un bouton dans Vibe Island…")
time.sleep(30)
listener.stop()
```

Exécuter :

```bash
cd ui && swift build -c release && cd ..
JARVIS_UI=1 ui/.build/release/JarvisUI &
sleep 1
JARVIS_UI=1 python3 scripts/test_event_roundtrip.py
```

Attendu : la pilule descend, affiche les boutons A et B. Au clic, le terminal Python affiche `← Reçu : {'type': 'choice', 'tool_use_id': 'toolu_test_roundtrip', 'label': 'A'}` (ou 'B'). Le panel disparaît.

Tuer : `pkill -f JarvisUI`

- [ ] **Step 8: Commit**

```bash
git add ui/Sources/JarvisUI/IPC/EventSender.swift \
        ui/Sources/JarvisUI/VibeIsland/VibeIslandView.swift \
        ui_socket.py \
        tests/test_event_listener.py \
        scripts/test_event_roundtrip.py
git commit -m "feat(ipc): socket bidirectionnel Swift↔Python pour les clics"
```

---

## Task 6 : Déplacer SocketListener.swift dans IPC/

**Files:**
- Move: `ui/Sources/JarvisUI/SocketListener.swift` → `ui/Sources/JarvisUI/IPC/SocketListener.swift`

- [ ] **Step 1: Déplacer le fichier**

```bash
mv ui/Sources/JarvisUI/SocketListener.swift ui/Sources/JarvisUI/IPC/SocketListener.swift
```

- [ ] **Step 2: Build pour vérifier que rien ne casse**

```bash
cd ui && swift build -c release && cd ..
```

Attendu : build success (Swift Package Manager récupère automatiquement le nouveau path).

- [ ] **Step 3: Validation manuelle rapide**

```bash
JARVIS_UI=1 ui/.build/release/JarvisUI &
sleep 1
python3 scripts/test_vibe.py listening
sleep 1
python3 scripts/test_vibe.py standby
pkill -f JarvisUI
```

Attendu : changements d'état fonctionnels (socket toujours écouté correctement).

- [ ] **Step 4: Commit**

```bash
git add ui/Sources/JarvisUI/IPC/SocketListener.swift
git rm ui/Sources/JarvisUI/SocketListener.swift 2>/dev/null || true
git commit -m "refactor(ui): déplace SocketListener.swift dans IPC/"
```

---

## Task 7 : Intégration AskUserQuestion dans assistant.py

**Files:**
- Modify: `assistant.py` (intercepte tool_use AskUserQuestion + injecte tool_result)
- Modify: `ui_socket.py` (ajoute `send_question`)
- Modify: `main.py` (branche EventListener au démarrage)
- Create: `tests/test_askuserquestion.py`

- [ ] **Step 1: Ajouter `send_question` dans `ui_socket.py`**

```python
def send_question(tool_use_id: str, prompt: str, choices: list[dict]) -> None:
    """Envoie une question à l'UI. choices = [{"id": "0", "label": "Sarah"}, ...]"""
    if not UI_ENABLED:
        return
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(0.15)
            s.connect(SOCKET_PATH)
            payload = {
                "state": "question",
                "amplitude": 0.0,
                "tool_use_id": tool_use_id,
                "question": prompt,
                "choices": choices,
            }
            s.sendall(json.dumps(payload).encode())
    except Exception:
        pass
```

- [ ] **Step 2: Écrire le test d'interception AskUserQuestion**

Créer `tests/test_askuserquestion.py` :

```python
"""Test : assistant.py intercepte un tool_use AskUserQuestion et attend
une réponse via EventListener avant d'injecter tool_result."""
import json
import socket
import threading
import time

from assistant import Assistant


def test_intercept_askuserquestion_injects_tool_result(monkeypatch):
    """Quand un tool_use AskUserQuestion arrive, le wrapper doit :
    1. Envoyer la question sur le socket UI
    2. Attendre une réponse via EventListener (mockée ici)
    3. Injecter un tool_result dans le stream Claude
    """
    sent_to_ui: list[dict] = []
    injected_to_claude: list[dict] = []

    monkeypatch.setattr(
        "ui_socket.send_question",
        lambda tid, prompt, choices: sent_to_ui.append(
            {"tool_use_id": tid, "prompt": prompt, "choices": choices}
        ),
    )

    # Simuler une réponse utilisateur 0.3s après l'envoi
    def fake_wait(tool_use_id: str, timeout: float) -> str:
        time.sleep(0.3)
        return "Sarah"

    monkeypatch.setattr(Assistant, "_wait_for_choice", fake_wait, raising=False)

    a = Assistant.__new__(Assistant)
    a._stdin_write_capture = injected_to_claude.append  # type: ignore
    a._handle_askuserquestion(
        tool_id="toolu_xyz",
        question="Mail à Sarah ou Pierre ?",
        options=[
            {"label": "Sarah", "description": "x"},
            {"label": "Pierre", "description": "y"},
        ],
    )

    assert len(sent_to_ui) == 1
    assert sent_to_ui[0]["prompt"] == "Mail à Sarah ou Pierre ?"
    assert sent_to_ui[0]["choices"] == [
        {"id": "0", "label": "Sarah"},
        {"id": "1", "label": "Pierre"},
    ]
    assert len(injected_to_claude) == 1
    parsed = json.loads(injected_to_claude[0].strip())
    assert parsed["type"] == "user"
    content = parsed["message"]["content"][0]
    assert content["type"] == "tool_result"
    assert content["tool_use_id"] == "toolu_xyz"
    assert content["content"] == "Sarah"
```

- [ ] **Step 3: Lancer le test pour vérifier qu'il échoue**

```bash
python3 -m pytest tests/test_askuserquestion.py -v
```

Attendu : `AttributeError: ... '_handle_askuserquestion'`.

- [ ] **Step 4: Implémenter `_handle_askuserquestion` dans `assistant.py`**

Ajouter en haut du fichier :

```python
import ui_socket
```

Ajouter dans `Assistant.__init__` :

```python
# Map tool_use_id → Event qui sera set quand la réponse arrive du UI.
self._pending_choices: dict[str, str] = {}
self._choice_events: dict[str, threading.Event] = {}
self._choice_lock = threading.Lock()
# Lance le EventListener une seule fois pour recevoir les clics UI.
self._event_listener = ui_socket.EventListener(callback=self._on_ui_event)
self._event_listener.start()
```

Ajouter les méthodes :

```python
def _on_ui_event(self, event: dict) -> None:
    if event.get("type") != "choice":
        return
    tool_use_id = event.get("tool_use_id", "")
    label = event.get("label", "")
    with self._choice_lock:
        self._pending_choices[tool_use_id] = label
        evt = self._choice_events.get(tool_use_id)
    if evt is not None:
        evt.set()

def _wait_for_choice(self, tool_use_id: str, timeout: float = 30.0) -> str:
    evt = threading.Event()
    with self._choice_lock:
        self._choice_events[tool_use_id] = evt
        if tool_use_id in self._pending_choices:
            return self._pending_choices.pop(tool_use_id)
    received = evt.wait(timeout)
    with self._choice_lock:
        self._choice_events.pop(tool_use_id, None)
        label = self._pending_choices.pop(tool_use_id, None)
    if not received or label is None:
        return "[timeout]"
    return label

def _handle_askuserquestion(self, tool_id: str, question: str,
                            options: list[dict]) -> None:
    """Intercepte un tool_use AskUserQuestion :
       1. Envoie la question sur le socket UI
       2. Attend une réponse via EventListener
       3. Injecte un tool_result dans le stream stdin de claude
    """
    choices = [{"id": str(i), "label": opt.get("label", f"opt{i}")}
               for i, opt in enumerate(options)]
    jlog.info("CLAUDE", f"? AskUserQuestion: {jlog.trunc(question, 80)} → {len(choices)} choix")
    ui_socket.send_question(tool_id, question, choices)
    label = self._wait_for_choice(tool_id, timeout=30.0)
    jlog.info("CLAUDE", f"? AskUserQuestion ← {label!r}")

    tool_result_msg = json.dumps({
        "type": "user",
        "message": {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": label,
                }
            ],
        },
    })
    self._write_to_stdin(tool_result_msg + "\n")
    # Reset l'UI au compact (la question est résolue).
    ui_socket.send_state("standby")

def _write_to_stdin(self, data: str) -> None:
    """Centralise l'écriture sur stdin pour permettre le test/mock."""
    if hasattr(self, "_stdin_write_capture"):
        self._stdin_write_capture(data)
        return
    assert self._proc and self._proc.stdin
    self._proc.stdin.write(data)
    self._proc.stdin.flush()
```

- [ ] **Step 5: Brancher l'interception dans `ask_stream`**

Dans `ask_stream`, dans la branche `elif etype == "assistant":`, juste après l'extraction de `tool_name = block.get("name", "")` et avant `tools_log.append(tool_name)`, ajouter :

```python
if tool_name == "AskUserQuestion":
    questions_list = tool_input.get("questions", [])
    if questions_list:
        q = questions_list[0]
        if len(questions_list) > 1:
            jlog.warn("CLAUDE", f"AskUserQuestion: {len(questions_list)} questions, V1 ne prend que la première")
        self._handle_askuserquestion(
            tool_id=tool_id,
            question=q.get("question", ""),
            options=q.get("options", []),
        )
    # On ne yield PAS de TOOL_USE pour AskUserQuestion : le main loop ne doit
    # pas afficher cet outil comme un appel externe, c'est une interaction utilisateur.
    continue
```

- [ ] **Step 6: Re-lancer le test**

```bash
python3 -m pytest tests/test_askuserquestion.py -v
```

Attendu : PASS.

- [ ] **Step 7: Validation manuelle end-to-end avec Jarvis complet**

Modifier le profil Jarvis (`jarvis_profile/CLAUDE.md`) pour suggérer l'usage de `AskUserQuestion` dans certains cas, OU plus simple : tester via une question explicite.

Avec Vibe Island actif et Jarvis lancé :

```bash
JARVIS_UI=1 python3 main.py
```

Dire (ou simuler) à Jarvis quelque chose qui devrait déclencher une question : par exemple « envoie un mail mais je sais pas si à Sarah ou Pierre, demande moi ». Vérifier dans les logs :
- `[CLAUDE] ? AskUserQuestion: ... → N choix`
- La pilule descend en mode Panel avec les choix
- Au clic : `[CLAUDE] ? AskUserQuestion ← 'Sarah'`
- Jarvis continue vocalement après le clic

Si Claude ne décide pas spontanément d'utiliser le tool, ajouter temporairement dans le prompt utilisateur explicite : « utilise AskUserQuestion pour me proposer Sarah ou Pierre ».

- [ ] **Step 8: Brancher dans main.py (rien à faire si Assistant est déjà instancié au démarrage)**

Vérifier que `main.py` instancie bien `Assistant()` au démarrage (déjà le cas). L'EventListener est lancé automatiquement dans `__init__`. Si `main.py` initialise `Assistant` après `ui_socket.launch_ui()`, c'est OK ; sinon, vérifier l'ordre. Lire les lignes pertinentes pour confirmer :

```bash
grep -n "Assistant()" main.py
grep -n "launch_ui" main.py
```

- [ ] **Step 9: Commit**

```bash
git add assistant.py ui_socket.py tests/test_askuserquestion.py
git commit -m "feat(assistant): intercepte AskUserQuestion → UI cliquable → tool_result"
```

---

## Task 8 : Nettoyage — suppression des fichiers obsolètes

**Files:**
- Delete: `ui/Sources/JarvisUI/JarvisPanel.swift`
- Delete: `ui/Sources/JarvisUI/MetalRenderer.swift`
- Delete: `ui/Sources/JarvisUI/BrowserPanel.swift`
- Delete: `ui/Sources/JarvisUI/InfoPanel.swift`
- Modify: `ui/Package.swift` (retirer le linkage WebKit qui n'est plus nécessaire)

- [ ] **Step 1: Vérifier qu'aucun fichier ne référence les anciens types**

```bash
grep -rn "JarvisPanel\|MetalRenderer\|BrowserPanel\|InfoPanel\|InfoBuilder" \
  ui/Sources/JarvisUI/ \
  --exclude-dir=.build
```

Attendu : aucune référence (sinon corriger les imports résiduels).

- [ ] **Step 2: Supprimer les 4 fichiers**

```bash
rm ui/Sources/JarvisUI/JarvisPanel.swift
rm ui/Sources/JarvisUI/MetalRenderer.swift
rm ui/Sources/JarvisUI/BrowserPanel.swift
rm ui/Sources/JarvisUI/InfoPanel.swift
```

- [ ] **Step 3: Retirer WebKit du Package.swift**

Remplacer le contenu de `ui/Package.swift` par :

```swift
// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "JarvisUI",
    platforms: [.macOS(.v13)],
    targets: [
        .executableTarget(
            name: "JarvisUI",
            path: "Sources/JarvisUI"
        )
    ]
)
```

- [ ] **Step 4: Clean build pour s'assurer que rien n'est cassé**

```bash
cd ui && rm -rf .build && swift build -c release && cd ..
```

Attendu : build success sans warning lié à des imports manquants. Note : un warning du compilateur Swift sans rapport (ex : sur SwiftUI deprecation) peut rester — ne pas chercher à le supprimer.

- [ ] **Step 5: Validation manuelle finale full-flow**

```bash
JARVIS_UI=1 ui/.build/release/JarvisUI &
sleep 1

# Compact
python3 scripts/test_vibe.py standby
sleep 1

# Listening
python3 scripts/test_vibe.py listening
sleep 1

# Étendu (outil)
python3 scripts/test_vibe.py thinking --tool "Gmail · search threads…"
sleep 2

# Panel question
python3 scripts/test_vibe.py thinking --question '{"prompt":"Mail à qui ?","choices":[{"id":"0","label":"Sarah"},{"id":"1","label":"Pierre"}]}'

# Cliquer un bouton manuellement dans l'UI
sleep 5

# Retour standby
python3 scripts/test_vibe.py standby
pkill -f JarvisUI
```

Attendu : toutes les transitions sont fluides, animations spring partout, aucun jump, l'UI ne se ferme jamais (ambient permanent).

- [ ] **Step 6: Commit final**

```bash
git add -u
git commit -m "refactor(ui): supprime JarvisPanel/MetalRenderer/Browser/InfoPanel obsolètes"
```

---

## Post-implémentation : vérification de la définition de "done"

Après Task 8, vérifier :

- [ ] Les 8 tasks ont leur validation manuelle passée
- [ ] Démo complète : `JARVIS_UI=1 python3 main.py` → wake → écoute → outil affiché en Étendu → question posée en Panel → clic utilisateur → réponse vocale → retour Compact
- [ ] `swift build -c release` ne produit aucun warning lié au code projet
- [ ] `grep -r "JarvisPanel\|MetalRenderer\|BrowserPanel\|InfoPanel" ui/Sources/` retourne vide
- [ ] `pytest tests/test_event_listener.py tests/test_askuserquestion.py` PASS

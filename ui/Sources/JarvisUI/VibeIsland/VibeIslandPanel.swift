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

    var stateModel: VibeIslandModel { model }
}

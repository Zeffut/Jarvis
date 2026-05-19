import AppKit
import SwiftUI

/// NSPanel hôte de Vibe Island. Toujours visible, ancré sous la notch.
final class VibeIslandPanel: NSPanel {

    private let model = VibeIslandModel()

    convenience init() {
        self.init(
            contentRect: NSRect(origin: .zero, size: NSSize(width: 400, height: 60)),
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

        model.onModeChange = { [weak self] mode in
            let h: CGFloat = (mode == .panel) ? 260 : 60
            self?.anchorToNotch(panelHeight: h)
        }
    }

    /// Positionne le panel centré horizontalement, top juste sous la barre de menus
    /// (ou sous la notch sur les Macs qui en ont une). Le content SwiftUI est
    /// top-aligned, donc le pill apparaît collé sous la menu bar.
    func anchorToNotch(panelHeight: CGFloat = 60) {
        guard let screen = NSScreen.main else { return }
        let panelWidth: CGFloat = 400
        let sf = screen.frame
        // Hauteur réelle de la barre de menus système :
        // - Mac avec notch  → safeAreaInsets.top ≈ 32-38px
        // - Mac sans notch  → fallback 24px (barre de menus standard)
        let notchInset = screen.safeAreaInsets.top
        let menuBarHeight: CGFloat = notchInset > 0 ? notchInset : 24
        let x = sf.origin.x + (sf.width - panelWidth) / 2
        // Top du panel = bas de la menu bar → pill visible juste dessous.
        let y = sf.origin.y + sf.height - panelHeight - menuBarHeight
        setFrame(NSRect(x: x, y: y, width: panelWidth, height: panelHeight),
                 display: true)
    }

    func show() {
        anchorToNotch()
        orderFront(nil)
    }

    var stateModel: VibeIslandModel { model }
}

import AppKit
import SwiftUI

/// NSPanel hôte de Vibe Island. Toujours visible, ancré sous la notch.
final class VibeIslandPanel: NSPanel {

    private let model = VibeIslandModel()

    convenience init() {
        self.init(
            contentRect: NSRect(origin: .zero, size: NSSize(width: 480, height: 32)),
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
            let h: CGFloat
            switch mode {
            case .compact:  h = 32
            case .extended: h = 40
            case .panel:    h = 300
            }
            self?.anchorToNotch(panelHeight: h)
        }
    }

    /// Positionne le panel centré horizontalement avec son TOP au niveau du top
    /// de l'écran — chevauche donc la zone de la notch. La notch physique (trou
    /// dans l'écran) masque la partie centrale du pill, ne laissant visibles que
    /// les "ailes" de chaque côté = effet Dynamic Island.
    ///
    /// Sur un Mac sans notch (écran externe, MBA M2…), le pill est placé sous la
    /// menu bar standard pour rester visible.
    func anchorToNotch(panelHeight: CGFloat = 32) {
        guard let screen = NSScreen.main else { return }
        let panelWidth: CGFloat = 480
        let sf = screen.frame
        let notchInset = screen.safeAreaInsets.top
        let x = sf.origin.x + (sf.width - panelWidth) / 2
        let y: CGFloat
        if notchInset > 0 {
            // Mac avec notch : top du panel = top de l'écran
            y = sf.origin.y + sf.height - panelHeight
        } else {
            // Mac sans notch : sous la menu bar standard 24px
            y = sf.origin.y + sf.height - panelHeight - 24
        }
        setFrame(NSRect(x: x, y: y, width: panelWidth, height: panelHeight),
                 display: true)
    }

    func show() {
        anchorToNotch()
        orderFront(nil)
    }

    var stateModel: VibeIslandModel { model }
}

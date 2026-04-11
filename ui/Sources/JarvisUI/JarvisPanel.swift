import AppKit
import MetalKit

final class JarvisPanel: NSPanel {
    private(set) var renderer: MetalRenderer?
    private var mtkView: MTKView!

    private let panelSize = NSSize(width: 220, height: 220)

    convenience init() {
        self.init(
            contentRect: NSRect(origin: .zero, size: NSSize(width: 220, height: 220)),
            styleMask: [.borderless, .nonactivatingPanel],
            backing: .buffered,
            defer: false
        )
        configurePanel()
        configureMetal()
    }

    private func configurePanel() {
        isOpaque = false
        backgroundColor = .clear
        level = .floating
        hasShadow = false
        isMovable = false
        collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        alphaValue = 0
    }

    private func configureMetal() {
        guard let device = MTLCreateSystemDefaultDevice() else { return }

        mtkView = MTKView(frame: contentView!.bounds, device: device)
        mtkView.autoresizingMask = [.width, .height]
        mtkView.clearColor = MTLClearColorMake(0.0, 0.0, 0.0, 1.0)
        mtkView.colorPixelFormat = .bgra8Unorm
        mtkView.isPaused = false
        mtkView.enableSetNeedsDisplay = false
        mtkView.preferredFramesPerSecond = 60
        mtkView.wantsLayer = true
        mtkView.layer?.cornerRadius = 10
        mtkView.layer?.masksToBounds = true

        renderer = MetalRenderer(mtkView: mtkView)
        mtkView.delegate = renderer
        contentView?.addSubview(mtkView)
    }

    // MARK: - Notch / screen positioning

    /// Vrai si l'écran est l'écran intégré du Mac (possède un notch).
    private func isBuiltinScreen(_ screen: NSScreen) -> Bool {
        guard let id = screen.deviceDescription[
            NSDeviceDescriptionKey("NSScreenNumber")
        ] as? CGDirectDisplayID else { return false }
        return CGDisplayIsBuiltin(id) != 0
    }

    /// Y du bord haut utilisable : sous le menu bar sur écran externe, sommet absolu sur l'écran interne.
    private func topEdge(screen: NSScreen) -> CGFloat {
        isBuiltinScreen(screen) ? screen.frame.maxY : screen.visibleFrame.maxY
    }

    /// Retourne le NSRect cible centré sous le notch (interne) ou sous le menu bar (externe).
    private func targetFrame(screen: NSScreen) -> NSRect {
        let sf = screen.frame
        return NSRect(
            x: sf.minX + (sf.width - panelSize.width) / 2,
            y: topEdge(screen: screen) - panelSize.height,
            width: panelSize.width,
            height: panelSize.height
        )
    }

    /// Petit rect de départ de l'animation (notch ou bord menu bar).
    private func notchFrame(screen: NSScreen) -> NSRect {
        let sf = screen.frame
        return NSRect(
            x: sf.minX + (sf.width - 180) / 2,
            y: topEdge(screen: screen) - 6,
            width: 180,
            height: 6
        )
    }

    // MARK: - Animations

    func open() {
        guard !isVisible, let screen = NSScreen.main else { return }

        mtkView.isPaused = false
        renderer?.triggerAppear()

        setFrame(notchFrame(screen: screen), display: false)
        alphaValue = 0
        orderFront(nil)

        // Ressort : cubic-bezier avec léger dépassement (overshoot ~6%)
        NSAnimationContext.runAnimationGroup { ctx in
            ctx.duration = 0.48
            ctx.timingFunction = CAMediaTimingFunction(controlPoints: 0.34, 1.28, 0.64, 1.0)
            animator().setFrame(targetFrame(screen: screen), display: true)
            animator().alphaValue = 1.0
        }
    }

    func close(completion: (() -> Void)? = nil) {
        guard isVisible, let screen = NSScreen.main else {
            completion?()
            return
        }

        renderer?.triggerDisappear()

        // Phase 1 : légère rétraction ("prise d'élan"), 80 ms
        NSAnimationContext.runAnimationGroup({ ctx in
            ctx.duration = 0.08
            ctx.timingFunction = CAMediaTimingFunction(name: .easeIn)
            animator().setFrame(targetFrame(screen: screen).insetBy(dx: 7, dy: 7), display: true)
            animator().alphaValue = 0.92
        }, completionHandler: {
            // Phase 2 : collapsing vers le notch + fade, 220 ms
            NSAnimationContext.runAnimationGroup({ ctx in
                ctx.duration = 0.22
                ctx.timingFunction = CAMediaTimingFunction(name: .easeIn)
                self.animator().setFrame(self.notchFrame(screen: screen), display: true)
                self.animator().alphaValue = 0.0
            }, completionHandler: { [weak self] in
                self?.orderOut(nil)
                self?.mtkView.isPaused = true
                completion?()
            })
        })
    }

    func update(state: String, amplitude: Float) {
        renderer?.setState(state, amplitude: amplitude)
    }
}

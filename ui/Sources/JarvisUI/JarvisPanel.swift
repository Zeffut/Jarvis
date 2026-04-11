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

        // Fenêtre positionnée d'emblée à sa position finale, invisible
        setFrame(targetFrame(screen: screen), display: false)
        alphaValue = 0
        orderFront(nil)

        // Ancrer la layer en haut au centre → le spring "jaillit" depuis le notch
        if let layer = mtkView.layer {
            layer.anchorPoint = CGPoint(x: 0.5, y: 1.0)
            layer.position    = CGPoint(x: mtkView.bounds.midX, y: mtkView.bounds.maxY)
        }

        // Spring CAAnimation : scale 0.001 → 1.0 avec oscillations (underdamped)
        let spring = CASpringAnimation(keyPath: "transform.scale")
        spring.fromValue  = 0.001
        spring.toValue    = 1.0
        spring.mass       = 0.9
        spring.stiffness  = 260
        spring.damping    = 11        // ζ ≈ 0.36 → ~2.5 oscillations
        spring.duration   = spring.settlingDuration
        spring.isRemovedOnCompletion = true
        mtkView.layer?.add(spring, forKey: "scaleIn")
        mtkView.layer?.transform = CATransform3DIdentity  // valeur modèle finale

        // Fade in window (plus rapide que le spring, sinon on voit un fond noir)
        NSAnimationContext.runAnimationGroup { ctx in
            ctx.duration = 0.18
            ctx.timingFunction = CAMediaTimingFunction(name: .easeOut)
            animator().alphaValue = 1.0
        }
    }

    func close(completion: (() -> Void)? = nil) {
        guard isVisible else { completion?(); return }

        renderer?.triggerDisappear()

        // Collapse rapide sans rebond (overdamped)
        let collapse = CABasicAnimation(keyPath: "transform.scale")
        collapse.fromValue              = 1.0
        collapse.toValue                = 0.001
        collapse.duration               = 0.25
        collapse.timingFunction         = CAMediaTimingFunction(controlPoints: 0.4, 0.0, 1.0, 0.6)
        collapse.isRemovedOnCompletion  = false
        collapse.fillMode               = .forwards
        mtkView.layer?.add(collapse, forKey: "scaleOut")

        // Fade out window en parallèle
        NSAnimationContext.runAnimationGroup({ ctx in
            ctx.duration = 0.25
            ctx.timingFunction = CAMediaTimingFunction(name: .easeIn)
            animator().alphaValue = 0.0
        }, completionHandler: { [weak self] in
            self?.mtkView.layer?.removeAllAnimations()
            self?.mtkView.layer?.transform = CATransform3DIdentity
            self?.orderOut(nil)
            self?.mtkView.isPaused = true
            completion?()
        })
    }

    func update(state: String, amplitude: Float) {
        renderer?.setState(state, amplitude: amplitude)
    }
}

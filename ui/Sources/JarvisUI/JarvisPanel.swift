import AppKit
import MetalKit

final class JarvisPanel: NSPanel {
    private(set) var renderer: MetalRenderer?
    private var mtkView: MTKView!

    private let panelSize = NSSize(width: 800, height: 600)

    convenience init() {
        self.init(
            contentRect: NSRect(origin: .zero, size: NSSize(width: 800, height: 600)),
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
        hasShadow = true
        isMovable = false
        collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        alphaValue = 0
    }

    private func configureMetal() {
        guard let device = MTLCreateSystemDefaultDevice() else { return }

        mtkView = MTKView(frame: contentView!.bounds, device: device)
        mtkView.autoresizingMask = [.width, .height]
        mtkView.clearColor = MTLClearColorMake(0.0, 0.03, 0.08, 0.97)
        mtkView.colorPixelFormat = .bgra8Unorm
        mtkView.isPaused = false
        mtkView.enableSetNeedsDisplay = false
        mtkView.preferredFramesPerSecond = 60
        mtkView.wantsLayer = true
        mtkView.layer?.cornerRadius = 20
        mtkView.layer?.masksToBounds = true

        renderer = MetalRenderer(mtkView: mtkView)
        mtkView.delegate = renderer
        contentView?.addSubview(mtkView)
    }

    // MARK: - Notch positioning

    /// Retourne le NSRect cible (800x600) centre sous le notch.
    private func targetFrame(screen: NSScreen) -> NSRect {
        let sf = screen.frame
        return NSRect(
            x: (sf.width - panelSize.width) / 2,
            y: sf.maxY - panelSize.height,
            width: panelSize.width,
            height: panelSize.height
        )
    }

    /// Petit rect au niveau du notch (point de depart de l'animation).
    private func notchFrame(screen: NSScreen) -> NSRect {
        let sf = screen.frame
        return NSRect(
            x: (sf.width - 180) / 2,
            y: sf.maxY - 6,
            width: 180,
            height: 6
        )
    }

    // MARK: - Animations

    func open() {
        guard !isVisible, let screen = NSScreen.main else { return }

        setFrame(notchFrame(screen: screen), display: false)
        alphaValue = 0
        orderFront(nil)

        NSAnimationContext.runAnimationGroup { ctx in
            ctx.duration = 0.4
            ctx.timingFunction = CAMediaTimingFunction(name: .easeOut)
            animator().setFrame(targetFrame(screen: screen), display: true)
            animator().alphaValue = 1.0
        }
    }

    func close(completion: (() -> Void)? = nil) {
        guard isVisible, let screen = NSScreen.main else {
            completion?()
            return
        }

        NSAnimationContext.runAnimationGroup({ ctx in
            ctx.duration = 0.25
            ctx.timingFunction = CAMediaTimingFunction(name: .easeIn)
            animator().setFrame(notchFrame(screen: screen), display: true)
            animator().alphaValue = 0.0
        }, completionHandler: { [weak self] in
            self?.orderOut(nil)
            completion?()
        })
    }

    func update(state: String, amplitude: Float) {
        renderer?.setState(state, amplitude: amplitude)
    }
}

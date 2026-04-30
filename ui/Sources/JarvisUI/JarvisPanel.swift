import AppKit
import MetalKit

final class JarvisPanel: NSPanel {
    private(set) var renderer: MetalRenderer?
    private var mtkView: MTKView!
    private var panelBG: NSView!

    // Timer de fermeture automatique après standby
    private var closeTimer: Timer?

    // Mini-panneau compagnon pour le bouton kill (ignoresMouseEvents = false)
    private var killPanel: NSPanel?
    var killAction: (() -> Void)?

    // Zone gauche (listes) — s'affiche APRÈS le speech
    private var listZoneView: NSView?
    private let listZoneWidth: CGFloat = 320

    // Zone droite (texte markdown) — streame EN TEMPS RÉEL pendant le speech
    private var textScrollView: NSScrollView?
    private var textView: NSTextView?
    private var textBuffer = ""
    private var renderTimer: Timer?
    private let textZoneWidth: CGFloat = 320

    private let sphereSize = NSSize(width: 380, height: 380)

    // MARK: - Init

    convenience init() {
        self.init(
            contentRect: NSRect(origin: .zero, size: NSSize(width: 100, height: 100)),
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
        ignoresMouseEvents = true
        collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        alphaValue = 0

        panelBG = NSView(frame: NSRect(x: 0, y: 0, width: 100, height: 100))
        panelBG.wantsLayer = true          // nécessaire pour addSublayer(_:) des séparateurs
        panelBG.autoresizingMask = [.width, .height]

        // NSBox garantit un fond noir uniforme, fiable dans tous les contextes
        // (layer?.backgroundColor est nil avant le premier affichage — NSBox dessine dès l'init)
        let bgBox = NSBox(frame: panelBG.bounds)
        bgBox.boxType = .custom
        bgBox.fillColor = .black
        bgBox.borderWidth = 0
        bgBox.autoresizingMask = [.width, .height]
        panelBG.addSubview(bgBox)

        contentView?.addSubview(panelBG)
    }

    private func configureMetal() {
        guard let device = MTLCreateSystemDefaultDevice() else { return }

        mtkView = MTKView(frame: NSRect(origin: .zero, size: sphereSize), device: device)
        mtkView.autoresizingMask = []
        mtkView.clearColor = MTLClearColorMake(0, 0, 0, 1)
        mtkView.colorPixelFormat = .bgra8Unorm
        mtkView.isPaused = true
        mtkView.enableSetNeedsDisplay = false
        mtkView.preferredFramesPerSecond = 60

        renderer = MetalRenderer(mtkView: mtkView)
        mtkView.delegate = renderer
        renderer?.sphereScale = 1.25

        panelBG.addSubview(mtkView)
    }

    // MARK: - Screen helpers

    private var mainScreen: NSScreen { NSScreen.main ?? NSScreen.screens[0] }

    /// Origine de la sphère dans les coordonnées locales de panelBG.
    private func sphereOriginInPanel(for screen: NSScreen) -> NSPoint {
        let sf = screen.frame
        return NSPoint(
            x: (sf.width - sphereSize.width) / 2,
            y: sf.height * 0.56 - sphereSize.height / 2
        )
    }

    // MARK: - Zone gauche (listes)

    func showList(content: [String: Any]) {
        DispatchQueue.main.async { [self] in
            guard isVisible else { return }
            _removeListZone()

            guard let view = InfoBuilder.buildView(
                content: content,
                width: listZoneWidth,
                height: sphereSize.height
            ) else { return }

            let sphereOrigin = sphereOriginInPanel(for: mainScreen)
            let targetX = max(60, sphereOrigin.x - listZoneWidth - 40)
            let targetY = sphereOrigin.y

            // Démarre hors-écran à gauche
            view.frame = NSRect(x: -listZoneWidth - 20, y: targetY,
                                width: listZoneWidth, height: sphereSize.height)
            view.alphaValue = 0
            listZoneView = view
            panelBG.addSubview(view)

            NSAnimationContext.runAnimationGroup { ctx in
                ctx.duration = 0.35
                ctx.timingFunction = CAMediaTimingFunction(name: .easeOut)
                view.animator().setFrameOrigin(NSPoint(x: targetX, y: targetY))
                view.animator().alphaValue = 1
            }
        }
    }

    func hideList() {
        DispatchQueue.main.async { [self] in
            guard let view = listZoneView else { return }
            listZoneView = nil
            NSAnimationContext.runAnimationGroup({ ctx in
                ctx.duration = 0.22
                ctx.timingFunction = CAMediaTimingFunction(name: .easeIn)
                view.animator().setFrameOrigin(NSPoint(x: -listZoneWidth - 20, y: view.frame.origin.y))
                view.animator().alphaValue = 0
            }, completionHandler: {
                view.removeFromSuperview()
            })
        }
    }

    private func _removeListZone() {
        listZoneView?.removeFromSuperview()
        listZoneView = nil
    }

    // MARK: - Zone droite (texte markdown)

    func openTextZone() {
        DispatchQueue.main.async { [self] in
            guard isVisible, textScrollView == nil else { return }

            textBuffer = ""

            let sf = mainScreen.frame
            let sphereOrigin = sphereOriginInPanel(for: mainScreen)
            let sphereRight = sphereOrigin.x + sphereSize.width
            let targetX = sphereRight + 40
            let targetY = sphereOrigin.y
            let zoneW = min(textZoneWidth, sf.width - targetX - 60)

            // Démarre hors-écran à droite
            let sv = NSScrollView(frame: NSRect(x: sf.width, y: targetY,
                                                width: zoneW, height: sphereSize.height))
            sv.hasVerticalScroller = false
            sv.hasHorizontalScroller = false
            sv.drawsBackground = false
            sv.borderType = .noBorder
            sv.autoresizingMask = []

            let tv = NSTextView(frame: sv.bounds)
            tv.isEditable = false
            tv.isSelectable = false
            tv.drawsBackground = false
            tv.backgroundColor = .clear
            tv.textColor = NSColor(calibratedWhite: 0.85, alpha: 1)
            tv.font = .systemFont(ofSize: 13)
            tv.textContainerInset = NSSize(width: 16, height: 14)
            tv.textContainer?.widthTracksTextView = true
            tv.textContainer?.heightTracksTextView = false
            tv.isVerticallyResizable = true
            tv.isHorizontallyResizable = false
            tv.alphaValue = 0

            sv.documentView = tv
            textScrollView = sv
            textView = tv
            panelBG.addSubview(sv)

            NSAnimationContext.runAnimationGroup { ctx in
                ctx.duration = 0.30
                ctx.timingFunction = CAMediaTimingFunction(name: .easeOut)
                sv.animator().setFrameOrigin(NSPoint(x: targetX, y: targetY))
                tv.animator().alphaValue = 1
            }

            _addSeparator(at: targetX - 20, y: targetY)
        }
    }

    func appendTextToken(_ token: String) {
        DispatchQueue.main.async { [self] in
            guard let tv = textView else { return }
            textBuffer += token
            tv.textStorage?.append(NSAttributedString(
                string: token,
                attributes: [
                    .foregroundColor: NSColor(calibratedWhite: 0.85, alpha: 1),
                    .font: NSFont.systemFont(ofSize: 13),
                ]
            ))
            tv.scrollToEndOfDocument(nil)
        }
    }

    func finalizeTextZone() {
        DispatchQueue.main.async { [self] in
            guard let tv = textView else { return }
            _renderMarkdown(in: tv)
        }
    }

    func closeTextZone() {
        DispatchQueue.main.async { [self] in
            renderTimer?.invalidate()
            renderTimer = nil
            guard let sv = textScrollView else { return }
            textScrollView = nil
            textView = nil
            textBuffer = ""

            let sf = mainScreen.frame
            NSAnimationContext.runAnimationGroup({ ctx in
                ctx.duration = 0.22
                ctx.timingFunction = CAMediaTimingFunction(name: .easeIn)
                sv.animator().setFrameOrigin(NSPoint(x: sf.width, y: sv.frame.origin.y))
                sv.animator().alphaValue = 0
            }, completionHandler: {
                sv.removeFromSuperview()
            })
        }
    }

    // MARK: - Markdown rendering

    private func _renderMarkdown(in tv: NSTextView) {
        var opts = AttributedString.MarkdownParsingOptions()
        opts.allowsExtendedAttributes = true
        opts.interpretedSyntax = .inlineOnlyPreservingWhitespace

        var attributed: NSAttributedString
        if let attrStr = try? AttributedString(markdown: textBuffer, options: opts) {
            let ns = NSMutableAttributedString(attrStr)
            let full = NSRange(location: 0, length: ns.length)
            ns.addAttribute(.foregroundColor,
                             value: NSColor(calibratedWhite: 0.88, alpha: 1), range: full)
            ns.addAttribute(.font,
                             value: NSFont.systemFont(ofSize: 13), range: full)
            ns.enumerateAttribute(.font, in: full) { val, range, _ in
                if let f = val as? NSFont, f.fontDescriptor.symbolicTraits.contains(.monoSpace) {
                    ns.addAttribute(.foregroundColor,
                                     value: NSColor(calibratedRed: 0.55, green: 0.85, blue: 1.0, alpha: 1),
                                     range: range)
                    ns.addAttribute(.font,
                                     value: NSFont.monospacedSystemFont(ofSize: 12, weight: .regular),
                                     range: range)
                }
            }
            attributed = ns
        } else {
            attributed = NSAttributedString(
                string: textBuffer,
                attributes: [
                    .foregroundColor: NSColor(calibratedWhite: 0.85, alpha: 1),
                    .font: NSFont.systemFont(ofSize: 13),
                ]
            )
        }

        tv.textStorage?.setAttributedString(attributed)
        tv.scrollToEndOfDocument(nil)
    }

    // MARK: - Separators

    private var separatorLayers: [CALayer] = []

    private func _addSeparator(at x: CGFloat, y: CGFloat) {
        guard let bgLayer = panelBG.layer else { return }
        let sep = CALayer()
        sep.backgroundColor = NSColor(calibratedWhite: 1.0, alpha: 0.10).cgColor
        sep.frame = CGRect(x: x, y: y + 20, width: 0.5, height: sphereSize.height - 40)
        bgLayer.addSublayer(sep)
        separatorLayers.append(sep)
    }

    private func _removeAllSeparators() {
        separatorLayers.forEach { $0.removeFromSuperlayer() }
        separatorLayers.removeAll()
    }

    // MARK: - Kill button (minimaliste : croix discrète au hover)

    private static let killSize: CGFloat = 24
    private static let killMargin: CGFloat = 16

    private func makeKillPanel() -> NSPanel {
        let s = Self.killSize
        let p = NSPanel(
            contentRect: NSRect(origin: .zero, size: NSSize(width: s, height: s)),
            styleMask: [.borderless, .nonactivatingPanel],
            backing: .buffered,
            defer: false
        )
        p.isOpaque = false
        p.backgroundColor = .clear
        p.hasShadow = false
        p.level = NSWindow.Level(rawValue: NSWindow.Level.floating.rawValue + 2)
        p.ignoresMouseEvents = false
        p.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        p.alphaValue = 0

        let view = MinimalKillButton(frame: NSRect(x: 0, y: 0, width: s, height: s))
        view.action = { [weak self] in self?.killAction?() }
        p.contentView?.addSubview(view)
        return p
    }

    private func _showKillButton(for screen: NSScreen) {
        if killPanel == nil { killPanel = makeKillPanel() }
        guard let kp = killPanel else { return }
        let sf = screen.frame
        let s = Self.killSize
        let m = Self.killMargin
        kp.setFrameOrigin(NSPoint(x: sf.maxX - s - m, y: sf.maxY - s - m))
        kp.alphaValue = 0
        kp.orderFront(nil)
        NSAnimationContext.runAnimationGroup { ctx in
            ctx.duration = 0.25
            kp.animator().alphaValue = 1.0
        }
    }

    private func _hideKillButton() {
        guard let kp = killPanel, kp.isVisible else { return }
        NSAnimationContext.runAnimationGroup({ ctx in
            ctx.duration = 0.15
            kp.animator().alphaValue = 0.0
        }, completionHandler: {
            kp.orderOut(nil)
        })
    }

    // MARK: - Open / Close

    /// Ferme automatiquement après un délai — 20s si des infos sont affichées, 4s sinon.
    func scheduleClose() {
        closeTimer?.invalidate()
        let delay: TimeInterval = (listZoneView != nil || textScrollView != nil) ? 20 : 4
        closeTimer = Timer.scheduledTimer(withTimeInterval: delay, repeats: false) { [weak self] _ in
            self?.close()
        }
    }

    func open() {
        closeTimer?.invalidate()   // annule toute fermeture programmée en cours
        closeTimer = nil
        guard !isVisible, let screen = NSScreen.main else { return }
        let sf = screen.frame

        // Fenêtre plein écran
        setFrame(sf, display: false)

        let sphereOrigin = sphereOriginInPanel(for: screen)
        mtkView.frame = NSRect(origin: sphereOrigin, size: sphereSize)

        mtkView.isPaused = false
        renderer?.triggerAppear()

        alphaValue = 0
        orderFront(nil)

        // Animation ressort depuis le centre de la sphère
        if let layer = mtkView.layer {
            layer.anchorPoint = CGPoint(x: 0.5, y: 0.5)
            layer.position = CGPoint(
                x: sphereOrigin.x + sphereSize.width / 2,
                y: sphereOrigin.y + sphereSize.height / 2
            )
        }

        let spring = CASpringAnimation(keyPath: "transform.scale")
        spring.fromValue = 0.001
        spring.toValue   = 1.0
        spring.mass      = 0.9
        spring.stiffness = 260
        spring.damping   = 11
        spring.duration  = spring.settlingDuration
        spring.isRemovedOnCompletion = true
        mtkView.layer?.add(spring, forKey: "scaleIn")
        mtkView.layer?.transform = CATransform3DIdentity

        NSAnimationContext.runAnimationGroup { ctx in
            ctx.duration = 0.20
            ctx.timingFunction = CAMediaTimingFunction(name: .easeOut)
            animator().alphaValue = 1.0
        }

        _showKillButton(for: screen)
    }

    func close(completion: (() -> Void)? = nil) {
        closeTimer?.invalidate()
        closeTimer = nil
        guard isVisible else { completion?(); return }

        _removeListZone()
        _removeAllSeparators()
        if let sv = textScrollView { sv.removeFromSuperview() }
        textScrollView = nil; textView = nil; textBuffer = ""
        renderTimer?.invalidate(); renderTimer = nil

        renderer?.triggerDisappear()

        let collapse = CABasicAnimation(keyPath: "transform.scale")
        collapse.fromValue             = 1.0
        collapse.toValue               = 0.001
        collapse.duration              = 0.25
        collapse.timingFunction        = CAMediaTimingFunction(controlPoints: 0.4, 0.0, 1.0, 0.6)
        collapse.isRemovedOnCompletion = false
        collapse.fillMode              = .forwards
        mtkView.layer?.add(collapse, forKey: "scaleOut")

        _hideKillButton()

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
        // Tout state actif (listening/thinking/speaking…) annule un closeTimer
        // pending d'un standby précédent — sinon le panel se ferme au milieu
        // d'une nouvelle conversation.
        closeTimer?.invalidate()
        closeTimer = nil
        renderer?.setState(state, amplitude: amplitude)
    }
}

// MARK: - MinimalKillButton

/// Croix discrète (✕) — opacité 0.35 au repos, 0.85 au hover, curseur main, click → action.
private final class MinimalKillButton: NSView {
    var action: (() -> Void)?
    private let label = NSTextField(labelWithString: "✕")
    private var trackingArea: NSTrackingArea?

    override init(frame: NSRect) {
        super.init(frame: frame)
        wantsLayer = true
        alphaValue = 0.35

        label.font = .systemFont(ofSize: 14, weight: .regular)
        label.textColor = NSColor.white
        label.alignment = .center
        label.frame = bounds
        label.autoresizingMask = [.width, .height]
        label.drawsBackground = false
        label.isBordered = false
        addSubview(label)
    }

    required init?(coder: NSCoder) { fatalError("init(coder:) not implemented") }

    override func updateTrackingAreas() {
        super.updateTrackingAreas()
        if let ta = trackingArea { removeTrackingArea(ta) }
        let ta = NSTrackingArea(
            rect: bounds,
            options: [.mouseEnteredAndExited, .activeAlways, .cursorUpdate],
            owner: self,
            userInfo: nil
        )
        addTrackingArea(ta)
        trackingArea = ta
    }

    override func mouseEntered(with event: NSEvent) {
        NSAnimationContext.runAnimationGroup { ctx in
            ctx.duration = 0.15
            animator().alphaValue = 0.85
        }
    }

    override func mouseExited(with event: NSEvent) {
        NSAnimationContext.runAnimationGroup { ctx in
            ctx.duration = 0.15
            animator().alphaValue = 0.35
        }
    }

    override func cursorUpdate(with event: NSEvent) {
        NSCursor.pointingHand.set()
    }

    override func mouseDown(with event: NSEvent) {
        action?()
    }
}

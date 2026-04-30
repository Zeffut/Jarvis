import AppKit
import WebKit

/// Panneau flottant avec WKWebView — affiché sur demande de Jarvis via [BROWSER]url[/BROWSER].
/// Interactif (ignoresMouseEvents = false) et positionné au-dessus de JarvisPanel.
final class BrowserPanel: NSPanel {
    private var webView: WKWebView!
    private var topBar: NSView!
    private var urlLabel: NSTextField!
    private var closeBtn: NSButton!

    convenience init() {
        self.init(
            contentRect: NSRect(origin: .zero, size: NSSize(width: 1100, height: 760)),
            styleMask: [.borderless, .nonactivatingPanel],
            backing: .buffered,
            defer: false
        )
        configure()
    }

    private func configure() {
        isOpaque = false
        backgroundColor = .clear
        level = NSWindow.Level(rawValue: NSWindow.Level.floating.rawValue + 1)
        hasShadow = true
        isMovable = true
        ignoresMouseEvents = false
        collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        alphaValue = 0

        let cv = contentView!
        cv.wantsLayer = true
        cv.layer?.backgroundColor = NSColor(calibratedWhite: 0.07, alpha: 1).cgColor
        cv.layer?.cornerRadius = 14
        cv.layer?.masksToBounds = true

        setupTopBar(in: cv)
        setupWebView(in: cv)
    }

    private func setupTopBar(in cv: NSView) {
        let barH: CGFloat = 48

        topBar = NSView(frame: NSRect(x: 0, y: cv.bounds.height - barH,
                                     width: cv.bounds.width, height: barH))
        topBar.wantsLayer = true
        topBar.layer?.backgroundColor = NSColor(calibratedWhite: 0.12, alpha: 1).cgColor
        topBar.autoresizingMask = [.width, .minYMargin]
        cv.addSubview(topBar)

        // Bouton fermer
        closeBtn = NSButton(frame: NSRect(x: 16, y: (barH - 24) / 2, width: 24, height: 24))
        closeBtn.bezelStyle = .circular
        closeBtn.title = "✕"
        closeBtn.font = .systemFont(ofSize: 10, weight: .semibold)
        closeBtn.target = self
        closeBtn.action = #selector(hideSelf)
        topBar.addSubview(closeBtn)

        // Label URL
        urlLabel = NSTextField(labelWithString: "")
        urlLabel.frame = NSRect(x: 52, y: (barH - 20) / 2,
                                width: topBar.bounds.width - 68, height: 20)
        urlLabel.font = .systemFont(ofSize: 11.5)
        urlLabel.textColor = NSColor(calibratedWhite: 0.55, alpha: 1)
        urlLabel.alignment = .left
        urlLabel.lineBreakMode = .byTruncatingTail
        urlLabel.autoresizingMask = [.width]
        topBar.addSubview(urlLabel)

        // Séparateur bas de la barre
        let sep = CALayer()
        sep.backgroundColor = NSColor(calibratedWhite: 1.0, alpha: 0.07).cgColor
        sep.frame = CGRect(x: 0, y: 0, width: cv.bounds.width, height: 0.5)
        topBar.layer?.addSublayer(sep)
    }

    private func setupWebView(in cv: NSView) {
        let barH: CGFloat = 48
        let config = WKWebViewConfiguration()
        config.preferences.javaScriptCanOpenWindowsAutomatically = false

        webView = WKWebView(
            frame: NSRect(x: 0, y: 0, width: cv.bounds.width, height: cv.bounds.height - barH),
            configuration: config
        )
        webView.autoresizingMask = [.width, .height]
        webView.navigationDelegate = self
        cv.addSubview(webView)
    }

    // MARK: - Public API

    func show(url urlString: String) {
        guard let screen = NSScreen.main else { return }
        let sf = screen.frame

        let panelW = min(1100, sf.width  * 0.78)
        let panelH = min(760,  sf.height * 0.78)
        let panelX = sf.minX + (sf.width  - panelW) / 2
        let panelY = sf.minY + (sf.height - panelH) / 2

        setFrame(NSRect(x: panelX, y: panelY, width: panelW, height: panelH), display: false)

        if let url = URL(string: urlString) {
            webView.load(URLRequest(url: url))
            urlLabel.stringValue = urlString
        }

        if !isVisible {
            alphaValue = 0
            orderFront(nil)
        }

        NSAnimationContext.runAnimationGroup { ctx in
            ctx.duration = 0.28
            ctx.timingFunction = CAMediaTimingFunction(name: .easeOut)
            animator().alphaValue = 1.0
        }
    }

    func hide() {
        guard isVisible else { return }
        NSAnimationContext.runAnimationGroup({ ctx in
            ctx.duration = 0.20
            ctx.timingFunction = CAMediaTimingFunction(name: .easeIn)
            animator().alphaValue = 0.0
        }, completionHandler: { [weak self] in
            self?.orderOut(nil)
            self?.webView.stopLoading()
        })
    }

    @objc private func hideSelf() { hide() }
}

// MARK: - WKNavigationDelegate

extension BrowserPanel: WKNavigationDelegate {
    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        if let url = webView.url?.absoluteString {
            urlLabel.stringValue = url
        }
    }

    func webView(_ webView: WKWebView,
                 didFail navigation: WKNavigation!, withError error: Error) {
        // Ignorer les erreurs de navigation silencieusement
    }
}

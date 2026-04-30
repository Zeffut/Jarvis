import AppKit

final class AppDelegate: NSObject, NSApplicationDelegate {
    private var panel: JarvisPanel?
    private var browserPanel: BrowserPanel?

    func applicationDidFinishLaunching(_ notification: Notification) {
        // Pas d'icône dans le Dock
        NSApp.setActivationPolicy(.accessory)

        panel = JarvisPanel()
        browserPanel = BrowserPanel()

        panel?.killAction = {
            // Tuer le processus Python via PID file + fallback pkill, puis quitter l'UI
            DispatchQueue.global().async {
                let task = Process()
                task.launchPath = "/bin/sh"
                task.arguments = ["-c",
                    "pid=$(cat /tmp/jarvis.pid 2>/dev/null); " +
                    "[ -n \"$pid\" ] && kill -9 \"$pid\" 2>/dev/null; " +
                    "pkill -9 -f 'python.*main.py' 2>/dev/null; " +
                    "true"
                ]
                try? task.run()
                task.waitUntilExit()
                DispatchQueue.main.async {
                    NSApp.terminate(nil)
                }
            }
        }

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

        switch msg.state {

        // ── Zone gauche : liste structurée (après speech) ──────────────────
        case "display":
            if let content = msg.displayContent {
                panel?.showList(content: content)
            }

        // ── Zone droite : texte markdown en streaming ───────────────────────
        case "text_start":
            panel?.openTextZone()

        case "text_token":
            if let tok = msg.token {
                panel?.appendTextToken(tok)
            }

        case "text_end":
            panel?.finalizeTextZone()

        // ── Navigateur web ──────────────────────────────────────────────────
        case "browser_open":
            if let url = msg.url {
                browserPanel?.show(url: url)
            }

        case "browser_close":
            browserPanel?.hide()

        // ── États sphère ────────────────────────────────────────────────────
        case "standby":
            browserPanel?.hide()
            panel?.scheduleClose()   // ferme dans 4s (20s si infos affichées)

        default:
            if panel?.isVisible == false {
                panel?.open()
            }
            panel?.update(state: msg.state, amplitude: msg.amplitude)
        }
    }

    func applicationWillTerminate(_ notification: Notification) {
        NotificationCenter.default.removeObserver(self)
        unlink("/tmp/jarvis-ui.sock")
    }
}

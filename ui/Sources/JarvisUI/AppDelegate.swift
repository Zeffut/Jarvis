import AppKit

final class AppDelegate: NSObject, NSApplicationDelegate {
    private var panel: JarvisPanel?

    func applicationDidFinishLaunching(_ notification: Notification) {
        // Pas d'icône dans le Dock
        NSApp.setActivationPolicy(.accessory)

        panel = JarvisPanel()
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

        if msg.state == "standby" {
            panel?.close()
        } else if panel?.isVisible == false {
            panel?.open()
        }

        panel?.update(state: msg.state, amplitude: msg.amplitude)
    }

    func applicationWillTerminate(_ notification: Notification) {
        NotificationCenter.default.removeObserver(self)
        unlink("/tmp/jarvis-ui.sock")
    }
}

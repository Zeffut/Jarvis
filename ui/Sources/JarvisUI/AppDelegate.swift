import AppKit

final class AppDelegate: NSObject, NSApplicationDelegate {
    private var panel: VibeIslandPanel?

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.accessory)

        panel = VibeIslandPanel()
        panel?.show()

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
        Task { @MainActor in
            self.panel?.stateModel.state = msg.state
            self.panel?.stateModel.toolName = msg.toolName
        }
    }

    func applicationWillTerminate(_ notification: Notification) {
        NotificationCenter.default.removeObserver(self)
        unlink("/tmp/jarvis-ui.sock")
    }
}

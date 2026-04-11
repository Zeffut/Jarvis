import Foundation

struct JarvisMessage {
    let state: String      // "standby" | "listening" | "thinking" | "speaking"
    let amplitude: Float   // 0.0–1.0
}

/// Écoute /tmp/jarvis-ui.sock, parse les messages JSON et les diffuse via NotificationCenter.
final class SocketListener {
    static let shared = SocketListener()
    static let messageNotification = Notification.Name("JarvisMessage")

    private let socketPath = "/tmp/jarvis-ui.sock"
    private let queue = DispatchQueue(label: "jarvis.socket", qos: .background)

    private init() {}

    func start() {
        queue.async { self.runLoop() }
    }

    private func runLoop() {
        unlink(socketPath)

        let serverFd = socket(AF_UNIX, SOCK_STREAM, 0)
        guard serverFd >= 0 else { return }
        defer { close(serverFd) }

        var addr = sockaddr_un()
        addr.sun_family = sa_family_t(AF_UNIX)
        withUnsafeMutableBytes(of: &addr.sun_path) { ptr in
            socketPath.withCString { cStr in
                _ = strlcpy(
                    ptr.baseAddress!.assumingMemoryBound(to: CChar.self),
                    cStr,
                    ptr.count
                )
            }
        }

        let bindResult = withUnsafePointer(to: &addr) {
            $0.withMemoryRebound(to: sockaddr.self, capacity: 1) {
                bind(serverFd, $0, socklen_t(MemoryLayout<sockaddr_un>.size))
            }
        }
        guard bindResult == 0 else { return }
        listen(serverFd, 10)

        while true {
            let clientFd = accept(serverFd, nil, nil)
            guard clientFd >= 0 else { continue }
            handleClient(fd: clientFd)
            close(clientFd)
        }
    }

    private func handleClient(fd: Int32) {
        var buffer = [UInt8](repeating: 0, count: 4096)
        let n = read(fd, &buffer, buffer.count)
        guard n > 0 else { return }

        let data = Data(buffer.prefix(n))
        guard
            let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
            let state = json["state"] as? String
        else { return }

        let amplitude = (json["amplitude"] as? Double).map { Float($0) } ?? 0.0
        let msg = JarvisMessage(state: state, amplitude: amplitude)

        DispatchQueue.main.async {
            NotificationCenter.default.post(
                name: Self.messageNotification,
                object: msg
            )
        }
    }
}

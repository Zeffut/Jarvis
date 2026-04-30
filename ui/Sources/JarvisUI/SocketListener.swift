import Foundation

struct JarvisMessage {
    let state: String               // standby | listening | thinking | speaking
                                    // display | text_start | text_token | text_end
                                    // browser_open | browser_close
    let amplitude: Float            // 0.0–1.0
    let displayContent: [String: Any]?  // présent si state == "display"
    let token: String?              // présent si state == "text_token"
    let url: String?                // présent si state == "browser_open"
}

/// Écoute /tmp/jarvis-ui.sock, parse les messages JSON et les diffuse via NotificationCenter.
final class SocketListener {
    static let shared = SocketListener()
    static let messageNotification = Notification.Name("JarvisMessage")

    private let socketPath = "/tmp/jarvis-ui.sock"
    private let queue = DispatchQueue(label: "jarvis.socket", qos: .background)
    private var isRunning = false

    private init() {}

    func start() {
        guard !isRunning else { return }
        isRunning = true
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

        // Restreindre l'accès au propriétaire uniquement (évite injection externe)
        fchmod(serverFd, 0o600)

        listen(serverFd, 10)

        while true {
            let clientFd = accept(serverFd, nil, nil)
            guard clientFd >= 0 else {
                // EINTR = signal reçu, retry normal ; autre erreur = pause courte
                if errno != EINTR {
                    Thread.sleep(forTimeInterval: 0.05)
                }
                continue
            }
            handleClient(fd: clientFd)
            close(clientFd)
        }
    }

    private func handleClient(fd: Int32) {
        var data = Data()
        var buffer = [UInt8](repeating: 0, count: 4096)
        while true {
            let n = read(fd, &buffer, buffer.count)
            if n <= 0 { break }
            data.append(contentsOf: buffer.prefix(n))
        }
        guard !data.isEmpty else { return }
        guard
            let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
            let state = json["state"] as? String
        else { return }

        let amplitude      = (json["amplitude"] as? Double).map { Float($0) } ?? 0.0
        let displayContent = json["content"] as? [String: Any]
        let token          = json["token"]   as? String
        let url            = json["url"]     as? String
        let msg = JarvisMessage(state: state, amplitude: amplitude,
                                displayContent: displayContent, token: token, url: url)

        DispatchQueue.main.async {
            NotificationCenter.default.post(
                name: Self.messageNotification,
                object: msg
            )
        }
    }
}

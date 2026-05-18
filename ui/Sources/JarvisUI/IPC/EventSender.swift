import Foundation

/// Envoie les événements UI (clics, timeouts) vers le backend Python
/// via /tmp/jarvis-ui-events.sock. Fire-and-forget, non-bloquant.
enum EventSender {
    static let socketPath = "/tmp/jarvis-ui-events.sock"

    static func sendChoice(toolUseId: String, label: String) {
        let payload: [String: Any] = [
            "type": "choice",
            "tool_use_id": toolUseId,
            "label": label,
        ]
        send(payload)
    }

    private static func send(_ payload: [String: Any]) {
        DispatchQueue.global(qos: .utility).async {
            guard let data = try? JSONSerialization.data(withJSONObject: payload) else { return }
            let fd = socket(AF_UNIX, SOCK_STREAM, 0)
            guard fd >= 0 else { return }
            defer { close(fd) }

            var addr = sockaddr_un()
            addr.sun_family = sa_family_t(AF_UNIX)
            withUnsafeMutableBytes(of: &addr.sun_path) { ptr in
                socketPath.withCString { cStr in
                    _ = strlcpy(
                        ptr.baseAddress!.assumingMemoryBound(to: CChar.self),
                        cStr, ptr.count
                    )
                }
            }

            let connResult = withUnsafePointer(to: &addr) {
                $0.withMemoryRebound(to: sockaddr.self, capacity: 1) {
                    connect(fd, $0, socklen_t(MemoryLayout<sockaddr_un>.size))
                }
            }
            guard connResult == 0 else { return }

            _ = data.withUnsafeBytes { bytes in
                write(fd, bytes.baseAddress, data.count)
            }
        }
    }
}

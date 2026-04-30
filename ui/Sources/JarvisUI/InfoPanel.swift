import AppKit

/// Construit les NSView de contenu adaptatif intégrées dans JarvisPanel.
/// Ne gère pas de fenêtre propre — JarvisPanel étend sa frame pour accueillir ces vues.
enum InfoBuilder {

    // MARK: - Factory

    static func buildView(content: [String: Any], width: CGFloat, height: CGFloat) -> NSView? {
        guard
            let type  = content["type"]  as? String,
            let title = content["title"] as? String
        else { return nil }
        return buildContentView(type: type, title: title, content: content,
                                width: width, height: height)
    }

    static func computeHeight(for content: [String: Any]) -> CGFloat {
        guard let type = content["type"] as? String else { return 120 }
        let headerH: CGFloat = 46
        let itemH:   CGFloat = 26
        let vPad:    CGFloat = 32

        switch type {
        case "list":
            let n = (content["items"] as? [String])?.count ?? 0
            return vPad + headerH + CGFloat(n) * itemH
        case "events":
            let n = (content["items"] as? [[String: Any]])?.count ?? 0
            return vPad + headerH + CGFloat(n) * itemH
        case "kv":
            let n = (content["pairs"] as? [[String]])?.count ?? 0
            return vPad + headerH + CGFloat(n) * itemH
        case "text":
            let body = (content["body"] as? String) ?? ""
            let lines = max(2, Int(ceil(Double(body.count) / 32.0)))
            return vPad + headerH + CGFloat(lines) * 19
        default:
            return 120
        }
    }

    // MARK: - View construction

    private static func buildContentView(
        type: String, title: String, content: [String: Any],
        width: CGFloat, height: CGFloat
    ) -> NSView {
        let container = NSView(frame: NSRect(x: 0, y: 0, width: width, height: height))

        let pad: CGFloat = 16
        let contentW = width - pad * 2
        var cursorY = height - pad

        // Séparateur vertical gauche
        let sepLine = CALayer()
        sepLine.backgroundColor = NSColor(calibratedWhite: 1.0, alpha: 0.07).cgColor
        sepLine.frame = CGRect(x: 0, y: 12, width: 0.5, height: height - 24)
        container.wantsLayer = true
        container.layer?.addSublayer(sepLine)

        // Titre
        cursorY -= 18
        let titleField = makeLabel(title, size: 12, weight: .semibold,
                                   color: NSColor(calibratedWhite: 1.0, alpha: 0.88))
        titleField.frame = NSRect(x: pad, y: cursorY, width: contentW, height: 18)
        container.addSubview(titleField)
        cursorY -= 10

        // Séparateur horizontal sous le titre
        let hSep = CALayer()
        hSep.backgroundColor = NSColor(calibratedWhite: 1.0, alpha: 0.09).cgColor
        hSep.frame = CGRect(x: pad, y: cursorY - 0.5, width: contentW, height: 0.5)
        container.layer?.addSublayer(hSep)
        cursorY -= 10

        // Contenu adaptatif
        switch type {

        case "list":
            for item in (content["items"] as? [String] ?? []) {
                cursorY -= 4
                let bullet = makeLabel("·", size: 15, weight: .medium,
                                       color: NSColor(calibratedWhite: 0.42, alpha: 1))
                bullet.frame = NSRect(x: pad, y: cursorY - 18, width: 10, height: 18)
                let text = makeLabel(item, size: 12,
                                     color: NSColor(calibratedWhite: 0.83, alpha: 1))
                text.frame = NSRect(x: pad + 14, y: cursorY - 18, width: contentW - 14, height: 18)
                container.addSubview(bullet)
                container.addSubview(text)
                cursorY -= 22
            }

        case "events":
            for ev in (content["items"] as? [[String: Any]] ?? []) {
                cursorY -= 4
                let time    = ev["time"]  as? String ?? ""
                let evTitle = ev["title"] as? String ?? ""
                let timeL = makeLabel(time, size: 11, weight: .medium,
                                      color: NSColor(calibratedRed: 0.42, green: 0.70, blue: 1.0, alpha: 1))
                timeL.frame = NSRect(x: pad, y: cursorY - 18, width: 46, height: 18)
                let titleL = makeLabel(evTitle, size: 12,
                                       color: NSColor(calibratedWhite: 0.83, alpha: 1))
                titleL.frame = NSRect(x: pad + 52, y: cursorY - 18, width: contentW - 52, height: 18)
                container.addSubview(timeL)
                container.addSubview(titleL)
                cursorY -= 22
            }

        case "kv":
            for pair in (content["pairs"] as? [[String]] ?? []) where pair.count >= 2 {
                cursorY -= 4
                let keyL = makeLabel(pair[0], size: 11, weight: .medium,
                                     color: NSColor(calibratedWhite: 0.45, alpha: 1))
                keyL.frame = NSRect(x: pad, y: cursorY - 18, width: 82, height: 18)
                let valL = makeLabel(pair[1], size: 12,
                                     color: NSColor(calibratedWhite: 0.83, alpha: 1))
                valL.frame = NSRect(x: pad + 88, y: cursorY - 18, width: contentW - 88, height: 18)
                container.addSubview(keyL)
                container.addSubview(valL)
                cursorY -= 22
            }

        case "text":
            let body = content["body"] as? String ?? ""
            let bodyH = cursorY - pad
            let bodyField = makeLabel(body, size: 12,
                                      color: NSColor(calibratedWhite: 0.80, alpha: 1))
            bodyField.maximumNumberOfLines = 0
            bodyField.lineBreakMode = .byWordWrapping
            bodyField.frame = NSRect(x: pad, y: pad, width: contentW, height: max(bodyH, 0))
            container.addSubview(bodyField)

        default:
            break
        }

        return container
    }

    // MARK: - Helpers

    private static func makeLabel(
        _ string: String,
        size: CGFloat,
        weight: NSFont.Weight = .regular,
        color: NSColor = .white
    ) -> NSTextField {
        let tf = NSTextField(labelWithString: string)
        tf.font = .systemFont(ofSize: size, weight: weight)
        tf.textColor = color
        tf.backgroundColor = .clear
        tf.isBezeled = false
        tf.isEditable = false
        tf.lineBreakMode = .byTruncatingTail
        return tf
    }
}

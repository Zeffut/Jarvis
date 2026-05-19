import SwiftUI

/// Source de vérité pour l'UI Vibe Island. Mis à jour depuis AppDelegate.
@MainActor
final class VibeIslandModel: ObservableObject {
    @Published var state: String = "standby"
    @Published var toolName: String? = nil
    @Published var question: VibeQuestion? = nil

    var onModeChange: ((VibeIslandView.Mode) -> Void)?

    /// Met à jour les trois champs en bloc et notifie le changement de mode
    /// une seule fois — évite trois redimensionnements consécutifs du NSPanel.
    func apply(state: String, toolName: String?, question: VibeQuestion?) {
        self.state = state
        self.toolName = toolName
        self.question = question
        notifyModeChange()
    }

    private func notifyModeChange() {
        let mode: VibeIslandView.Mode
        if question != nil { mode = .panel }
        else if toolName != nil { mode = .extended }
        else { mode = .compact }
        onModeChange?(mode)
    }
}

struct VibeQuestion: Equatable {
    let toolUseId: String
    let prompt: String
    let choices: [Choice]

    struct Choice: Equatable, Identifiable {
        let id: String
        let label: String
    }
}

struct VibeIslandView: View {
    @ObservedObject var model: VibeIslandModel

    private var arcState: ArcReactorState {
        ArcReactorState(rawValue: model.state) ?? .standby
    }

    private var mode: Mode {
        if model.question != nil { return .panel }
        if model.toolName != nil { return .extended }
        return .compact
    }

    var body: some View {
        Group {
            switch mode {
            case .compact:
                compactBar
            case .extended:
                extendedBar
            case .panel:
                if let q = model.question {
                    QuestionPanelView(
                        question: q,
                        arcState: arcState,
                        onChoice: { choice in
                            handleChoice(q, choice)
                        }
                    )
                }
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
        .animation(.spring(response: 0.5, dampingFraction: 0.75), value: mode)
    }

    // Largeur estimée de la notch MBP M2/M3 (~185-200px). Le contenu central
    // dans cette zone est masqué physiquement par le trou de la notch.
    private static let notchWidth: CGFloat = 200

    private var compactBar: some View {
        HStack(spacing: 0) {
            // Aile gauche : Arc Reactor (seul élément visuel — pas de texte)
            OrbView(state: arcState, size: 24)
                .frame(width: 60, alignment: .center)
            // Centre masqué par la notch
            Spacer().frame(width: Self.notchWidth)
            // Aile droite : vide (symétrie de la forme avec la notch)
            Color.clear
                .frame(width: 60)
        }
        .frame(width: 320, height: 32)
        .background(
            UnevenRoundedRectangle(
                cornerRadii: .init(topLeading: 0, bottomLeading: 18,
                                   bottomTrailing: 18, topTrailing: 0)
            ).fill(Color.black)
        )
    }

    private var extendedBar: some View {
        HStack(spacing: 0) {
            // Aile gauche : Arc Reactor
            OrbView(state: arcState, size: 22)
                .frame(width: 130, alignment: .center)
            // Centre masqué par la notch
            Spacer().frame(width: Self.notchWidth)
            // Aile droite : tool name + spinner
            Group {
                if let tool = model.toolName {
                    ToolIndicatorView(toolName: tool)
                }
            }
            .frame(width: 130, alignment: .center)
        }
        .frame(width: 460, height: 40)
        .background(
            UnevenRoundedRectangle(
                cornerRadii: .init(topLeading: 0, bottomLeading: 22,
                                   bottomTrailing: 22, topTrailing: 0)
            ).fill(Color.black)
        )
    }

    private var stateLabel: String {
        switch arcState {
        case .standby:   return "Jarvis"
        case .listening: return "Listening"
        case .thinking:  return "Thinking"
        case .speaking:  return "Speaking"
        }
    }

    private func handleChoice(_ q: VibeQuestion, _ choice: VibeQuestion.Choice) {
        EventSender.sendChoice(toolUseId: q.toolUseId, label: choice.label)
        model.apply(state: model.state, toolName: model.toolName, question: nil)
    }

    enum Mode: Equatable { case compact, extended, panel }
}

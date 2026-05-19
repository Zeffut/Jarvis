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
        // Mini pill carré juste à gauche de la notch. Bord droit collé à la notch
        // (corner top/bottom trailing = 0), bord gauche arrondi (extrémité).
        let pillWidth: CGFloat = 36
        return ZStack {
            Color.clear
            OrbView(state: arcState, size: 24)
                .frame(width: pillWidth, height: 32)
                .background(
                    UnevenRoundedRectangle(
                        cornerRadii: .init(topLeading: 0, bottomLeading: 14,
                                           bottomTrailing: 0, topTrailing: 0)
                    ).fill(Color.black)
                )
                .offset(x: -(Self.notchWidth / 2 + pillWidth / 2))
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
    }

    private var extendedBar: some View {
        // Pill plus longue qui s'étire à gauche depuis la notch. Bord droit
        // collé à la notch (avec orbe), tool name à gauche.
        let pillWidth: CGFloat = 220
        return ZStack {
            Color.clear
            HStack(spacing: 10) {
                if let tool = model.toolName {
                    ToolIndicatorView(toolName: tool)
                }
                OrbView(state: arcState, size: 22)
            }
            .padding(.leading, 14)
            .padding(.trailing, 8)
            .frame(width: pillWidth, height: 38)
            .background(
                UnevenRoundedRectangle(
                    cornerRadii: .init(topLeading: 0, bottomLeading: 18,
                                       bottomTrailing: 0, topTrailing: 0)
                ).fill(Color.black)
            )
            .offset(x: -(Self.notchWidth / 2 + pillWidth / 2))
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
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

import SwiftUI

/// Source de vérité pour l'UI Vibe Island. Mis à jour depuis AppDelegate.
@MainActor
final class VibeIslandModel: ObservableObject {
    @Published var state: String = "standby" {
        didSet { notifyModeChange() }
    }
    @Published var toolName: String? = nil {
        didSet { notifyModeChange() }
    }
    @Published var question: VibeQuestion? = nil {
        didSet { notifyModeChange() }
    }

    var onModeChange: ((VibeIslandView.Mode) -> Void)?

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

    private var compactBar: some View {
        HStack(spacing: 8) {
            ArcReactorView(state: arcState, size: 18).padding(.leading, 10)
            Text(stateLabel)
                .font(.system(size: 11, weight: .medium))
                .foregroundColor(.white.opacity(0.85))
            Spacer(minLength: 0)
        }
        .frame(width: 160, height: 30)
        .background(RoundedRectangle(cornerRadius: 15).fill(Color.black))
    }

    private var extendedBar: some View {
        HStack(spacing: 8) {
            ArcReactorView(state: arcState, size: 22).padding(.leading, 10)
            if let tool = model.toolName {
                ToolIndicatorView(toolName: tool)
            }
            Spacer(minLength: 0)
        }
        .frame(width: 340, height: 34)
        .background(RoundedRectangle(cornerRadius: 17).fill(Color.black))
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
        // Sera complété en Task 5 (EventSender). V1 : stub + clear question.
        EventSenderStub.sendChoice(toolUseId: q.toolUseId, label: choice.label)
        model.question = nil
    }

    enum Mode: Equatable { case compact, extended, panel }
}

// Stub temporaire — remplacé par le vrai EventSender en Task 5.
private enum EventSenderStub {
    static func sendChoice(toolUseId: String, label: String) {
        print("[stub] choice toolUseId=\(toolUseId) label=\(label)")
    }
}

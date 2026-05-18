import SwiftUI

/// Source de vérité pour l'UI Vibe Island. Mis à jour depuis AppDelegate.
@MainActor
final class VibeIslandModel: ObservableObject {
    @Published var state: String = "standby"
    @Published var toolName: String? = nil
    @Published var question: VibeQuestion? = nil
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

    private var isExpanded: Bool { model.toolName != nil }

    var body: some View {
        HStack(spacing: 8) {
            ArcReactorView(state: arcState, size: isExpanded ? 22 : 18)
                .padding(.leading, 10)

            if let tool = model.toolName {
                ToolIndicatorView(toolName: tool)
                    .transition(.opacity.combined(with: .move(edge: .leading)))
            } else {
                Text(stateLabel)
                    .font(.system(size: 11, weight: .medium))
                    .foregroundColor(.white.opacity(0.85))
                    .transition(.opacity)
            }
            Spacer(minLength: 0)
        }
        .frame(width: isExpanded ? 340 : 160,
               height: isExpanded ? 34 : 30)
        .background(
            RoundedRectangle(cornerRadius: isExpanded ? 17 : 15)
                .fill(Color.black)
        )
        .animation(.spring(response: 0.35, dampingFraction: 0.78), value: isExpanded)
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
}

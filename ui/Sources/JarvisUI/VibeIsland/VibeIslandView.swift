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

    var body: some View {
        HStack(spacing: 8) {
            ArcReactorView(state: arcState, size: 18)
                .padding(.leading, 8)
            Text(label)
                .font(.system(size: 11, weight: .medium))
                .foregroundColor(.white.opacity(0.85))
            Spacer()
        }
        .frame(width: 160, height: 30)
        .background(
            RoundedRectangle(cornerRadius: 15)
                .fill(Color.black)
        )
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
    }

    private var label: String {
        switch arcState {
        case .standby:   return "Jarvis"
        case .listening: return "Listening"
        case .thinking:  return "Thinking"
        case .speaking:  return "Speaking"
        }
    }
}

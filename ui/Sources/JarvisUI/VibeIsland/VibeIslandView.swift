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

    var body: some View {
        RoundedRectangle(cornerRadius: 18)
            .fill(Color.black)
            .frame(width: 160, height: 30)
            .overlay(
                Text(model.state)
                    .font(.system(size: 11, weight: .medium))
                    .foregroundColor(.white)
            )
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
    }
}

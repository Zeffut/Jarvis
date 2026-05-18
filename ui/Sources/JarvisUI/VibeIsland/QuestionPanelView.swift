import SwiftUI

struct QuestionPanelView: View {
    let question: VibeQuestion
    let arcState: ArcReactorState
    let onChoice: (VibeQuestion.Choice) -> Void

    var body: some View {
        VStack(spacing: 0) {
            ArcReactorView(state: arcState, size: 80)
                .padding(.top, 18)
                .padding(.bottom, 14)

            Text(question.prompt)
                .font(.system(size: 12, weight: .medium))
                .foregroundColor(.white.opacity(0.85))
                .multilineTextAlignment(.center)
                .padding(.horizontal, 18)
                .padding(.bottom, 14)

            VStack(spacing: 8) {
                ForEach(Array(question.choices.enumerated()), id: \.element.id) { idx, choice in
                    ChoiceButton(label: choice.label) {
                        onChoice(choice)
                    }
                    .transition(.asymmetric(
                        insertion: .opacity.combined(with: .move(edge: .top))
                            .animation(.spring(response: 0.4, dampingFraction: 0.7).delay(Double(idx) * 0.05)),
                        removal: .opacity
                    ))
                }
            }
            .padding(.horizontal, 14)
            .padding(.bottom, 16)
        }
        .frame(width: 400)
        .background(
            RoundedRectangle(cornerRadius: 22)
                .fill(Color.black)
        )
    }
}

private struct ChoiceButton: View {
    let label: String
    let action: () -> Void

    @State private var hovering = false
    @State private var clickScale: CGFloat = 1.0

    var body: some View {
        Button(action: triggerAction) {
            Text(label)
                .font(.system(size: 12, weight: .medium))
                .foregroundColor(.white)
                .frame(maxWidth: .infinity)
                .frame(height: 36)
                .background(
                    RoundedRectangle(cornerRadius: 10)
                        .fill(Color(white: 0.08))
                        .overlay(
                            RoundedRectangle(cornerRadius: 10)
                                .stroke(Color(red: 0.36, green: 0.78, blue: 1.00).opacity(hovering ? 0.85 : 0.45),
                                        lineWidth: 1)
                        )
                        .shadow(color: Color(red: 0.36, green: 0.78, blue: 1.00).opacity(hovering ? 0.5 : 0),
                                radius: hovering ? 8 : 0)
                )
        }
        .buttonStyle(.plain)
        .scaleEffect(clickScale != 1.0 ? clickScale : (hovering ? 1.02 : 1.0))
        .animation(.easeInOut(duration: 0.18), value: hovering)
        .animation(.easeInOut(duration: 0.1), value: clickScale)
        .onHover { hovering = $0 }
    }

    private func triggerAction() {
        clickScale = 0.95
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.08) { clickScale = 1.05 }
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.18) {
            clickScale = 1.0
            action()
        }
    }
}

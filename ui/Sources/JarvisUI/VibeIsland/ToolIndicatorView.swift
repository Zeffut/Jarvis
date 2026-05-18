import SwiftUI

struct ToolIndicatorView: View {
    let toolName: String
    @State private var spinnerRotation: Double = 0

    var body: some View {
        HStack(spacing: 6) {
            Text(toolName)
                .font(.system(size: 11, weight: .medium))
                .foregroundColor(.white.opacity(0.85))
                .lineLimit(1)
                .truncationMode(.tail)
            MiniSpinner()
        }
    }
}

private struct MiniSpinner: View {
    @State private var rotation: Double = 0

    var body: some View {
        Circle()
            .trim(from: 0.0, to: 0.7)
            .stroke(
                Color(red: 0.36, green: 0.78, blue: 1.00),
                style: StrokeStyle(lineWidth: 1.2, lineCap: .round)
            )
            .frame(width: 10, height: 10)
            .rotationEffect(.degrees(rotation))
            .onAppear {
                withAnimation(.linear(duration: 1.0).repeatForever(autoreverses: false)) {
                    rotation = 360
                }
            }
    }
}

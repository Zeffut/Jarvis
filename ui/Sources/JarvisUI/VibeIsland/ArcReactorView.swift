import SwiftUI

/// Rendu de l'Arc Reactor — anneaux, cœur, particules, scan lines, flicker.
struct ArcReactorView: View {
    let state: ArcReactorState
    let size: CGFloat

    @State private var ringRotation: Double = 0
    @State private var particleRotation: Double = 0
    @State private var breatheScale: CGFloat = 1.0
    @State private var flickerOpacity: Double = 1.0

    private var showFullDetails: Bool { size >= 40 }

    var body: some View {
        ZStack {
            // Anneau extérieur : dashed, rotation lente
            Circle()
                .strokeBorder(
                    state.color,
                    style: StrokeStyle(
                        lineWidth: max(1, size / 18),
                        lineCap: .round,
                        dash: [size * 0.25, size * 0.04, size * 0.05, size * 0.04]
                    )
                )
                .rotationEffect(.degrees(ringRotation))
                .shadow(color: state.color.opacity(0.8), radius: state.glowRadius / 2)

            // Anneau intérieur : dashed fin, statique
            if showFullDetails {
                Circle()
                    .strokeBorder(
                        state.color.opacity(0.4),
                        style: StrokeStyle(lineWidth: 0.8, dash: [2, 2])
                    )
                    .padding(size * 0.10)
            }

            // Particules orbitales (12h / 6h)
            if showFullDetails {
                ParticlesOrbit(color: state.color, size: size)
                    .rotationEffect(.degrees(particleRotation))
            }

            // Cœur : gradient radial
            Circle()
                .fill(
                    RadialGradient(
                        colors: [.white, state.color, Color(red: 0.07, green: 0.14, blue: 0.33)],
                        center: .center,
                        startRadius: 0,
                        endRadius: size * 0.18
                    )
                )
                .frame(width: size * 0.4, height: size * 0.4)
                .scaleEffect(breatheScale)
                .shadow(color: state.color, radius: state.glowRadius)

            // Scan lines holographiques
            if showFullDetails && state.hasHologramEffects {
                ScanLinesOverlay()
                    .clipShape(Circle())
                    .blendMode(.screen)
                    .opacity(0.5)
            }
        }
        .frame(width: size, height: size)
        .opacity(flickerOpacity)
        .onAppear { startAnimations() }
        .onChange(of: state) { _ in restartAnimations() }
    }

    private func startAnimations() {
        // Rotation continue anneau extérieur
        withAnimation(.linear(duration: state.rotationDuration).repeatForever(autoreverses: false)) {
            ringRotation = 360
        }
        // Rotation inverse particules
        withAnimation(.linear(duration: state.rotationDuration * 0.45).repeatForever(autoreverses: false)) {
            particleRotation = -360
        }
        // Breathe du cœur
        withAnimation(.easeInOut(duration: state.breatheDuration).repeatForever(autoreverses: true)) {
            breatheScale = 1.05
        }
        // Flicker holographique aléatoire
        if state.hasHologramEffects {
            scheduleNextFlicker()
        }
    }

    private func restartAnimations() {
        ringRotation = 0
        particleRotation = 0
        breatheScale = 1.0
        flickerOpacity = 1.0
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.05) {
            startAnimations()
        }
    }

    private func scheduleNextFlicker() {
        let delay = Double.random(in: 3.0...5.0)
        DispatchQueue.main.asyncAfter(deadline: .now() + delay) {
            guard state.hasHologramEffects else { return }
            withAnimation(.linear(duration: 0.05)) { flickerOpacity = 0.4 }
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.05) {
                withAnimation(.linear(duration: 0.05)) { flickerOpacity = 1.0 }
                scheduleNextFlicker()
            }
        }
    }
}

/// 2 points lumineux opposés sur l'anneau, à 12h et 6h.
private struct ParticlesOrbit: View {
    let color: Color
    let size: CGFloat

    var body: some View {
        ZStack {
            Circle()
                .fill(Color.white)
                .frame(width: size * 0.06, height: size * 0.06)
                .shadow(color: color, radius: 4)
                .offset(y: -size * 0.42)
            Circle()
                .fill(Color.white)
                .frame(width: size * 0.06, height: size * 0.06)
                .shadow(color: color, radius: 4)
                .offset(y: size * 0.42)
        }
    }
}

/// Scan lines horizontales (effet CRT/holographique).
private struct ScanLinesOverlay: View {
    var body: some View {
        Canvas { ctx, size in
            let lineSpacing: CGFloat = 3
            var y: CGFloat = 0
            while y < size.height {
                ctx.fill(
                    Path(CGRect(x: 0, y: y, width: size.width, height: 1)),
                    with: .color(Color(red: 0.36, green: 0.78, blue: 1.00).opacity(0.15))
                )
                y += lineSpacing
            }
        }
    }
}

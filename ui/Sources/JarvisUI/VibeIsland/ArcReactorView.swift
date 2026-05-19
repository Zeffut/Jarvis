import SwiftUI

/// Rendu de l'Arc Reactor — anneaux, cœur, pulse waves, particules, scan lines, flicker.
struct ArcReactorView: View {
    let state: ArcReactorState
    let size: CGFloat

    @State private var ringRotation: Double = 0
    @State private var particleRotation: Double = 0
    @State private var breatheScale: CGFloat = 1.0
    @State private var flickerOpacity: Double = 1.0

    // Deux pulse waves désynchronisées pour un effet continu (l'une émerge
    // pendant que l'autre se dissipe).
    @State private var pulse1Progress: CGFloat = 0
    @State private var pulse1Opacity: Double = 0
    @State private var pulse2Progress: CGFloat = 0
    @State private var pulse2Opacity: Double = 0

    private var showFullDetails: Bool { size >= 40 }

    var body: some View {
        ZStack {
            // ── Pulse waves : anneaux qui s'élargissent depuis le cœur ──────
            // Visibles à toutes les tailles → donne la vie en mode compact.
            pulseWave(progress: pulse1Progress, opacity: pulse1Opacity)
            pulseWave(progress: pulse2Progress, opacity: pulse2Opacity)

            // ── Anneau extérieur : dashed, rotation lente ──
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

            // ── Anneau intérieur dashed fin (uniquement en grand) ──
            if showFullDetails {
                Circle()
                    .strokeBorder(
                        state.color.opacity(0.4),
                        style: StrokeStyle(lineWidth: 0.8, dash: [2, 2])
                    )
                    .padding(size * 0.10)
            }

            // ── Particules orbitales (uniquement en grand) ──
            if showFullDetails {
                ParticlesOrbit(color: state.color, size: size)
                    .rotationEffect(.degrees(particleRotation))
            }

            // ── Cœur : gradient radial qui respire ──
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
                .shadow(color: state.color, radius: state.glowRadius * Double(breatheScale))

            // ── Scan lines holographiques (uniquement en grand) ──
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

    /// Onde concentrique unique — utilisée 2× désynchronisée.
    /// scaleEffect max 1.25x pour rester dans la hauteur du pill compact (32px).
    @ViewBuilder
    private func pulseWave(progress: CGFloat, opacity: Double) -> some View {
        Circle()
            .stroke(
                state.color,
                style: StrokeStyle(lineWidth: max(1.0, size / 18), lineCap: .round)
            )
            .scaleEffect(0.4 + progress * 0.85)   // grandit de 40% → 125% de size
            .opacity(opacity * (1.0 - Double(progress)))
            .frame(width: size, height: size)
    }

    // MARK: - Animations

    private func startAnimations() {
        // Rotation continue anneau extérieur
        withAnimation(.linear(duration: state.rotationDuration).repeatForever(autoreverses: false)) {
            ringRotation = 360
        }
        // Rotation inverse particules
        withAnimation(.linear(duration: state.rotationDuration * 0.45).repeatForever(autoreverses: false)) {
            particleRotation = -360
        }
        // Breathe du cœur — plus marqué : 1.0 ↔ 1.18
        withAnimation(.easeInOut(duration: state.breatheDuration).repeatForever(autoreverses: true)) {
            breatheScale = 1.18
        }
        // Pulse waves (2 en alternance, décalées d'un demi-cycle)
        schedulePulse1()
        DispatchQueue.main.asyncAfter(deadline: .now() + state.pulseInterval / 2) {
            schedulePulse2()
        }
        // Flicker holographique aléatoire — actif à TOUTES les tailles maintenant
        scheduleNextFlicker()
    }

    private func restartAnimations() {
        ringRotation = 0
        particleRotation = 0
        breatheScale = 1.0
        flickerOpacity = 1.0
        pulse1Progress = 0
        pulse1Opacity = 0
        pulse2Progress = 0
        pulse2Opacity = 0
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.05) {
            startAnimations()
        }
    }

    /// Pulse 1 : émet → fade, puis re-schedule.
    private func schedulePulse1() {
        pulse1Progress = 0
        pulse1Opacity = 0.85
        let expandDuration = 1.4
        withAnimation(.easeOut(duration: expandDuration)) {
            pulse1Progress = 1
            pulse1Opacity = 0
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + state.pulseInterval) {
            schedulePulse1()
        }
    }

    /// Pulse 2 : décalé d'un demi-cycle → onde quasi-continue.
    private func schedulePulse2() {
        pulse2Progress = 0
        pulse2Opacity = 0.85
        let expandDuration = 1.4
        withAnimation(.easeOut(duration: expandDuration)) {
            pulse2Progress = 1
            pulse2Opacity = 0
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + state.pulseInterval) {
            schedulePulse2()
        }
    }

    private func scheduleNextFlicker() {
        let baseDelay = state.flickerInterval
        let jitter = Double.random(in: -0.3...0.3) * baseDelay
        let delay = max(0.5, baseDelay + jitter)
        DispatchQueue.main.asyncAfter(deadline: .now() + delay) {
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

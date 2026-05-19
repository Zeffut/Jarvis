import SwiftUI

/// Orbe constituée de N points distribués uniformément sur une sphère 3D
/// (Fibonacci spiral). Rotation continue + déformations modulées par l'état
/// (breathing, ondulations, chaos, etc.).
///
/// Rendu via SwiftUI Canvas + TimelineView(.animation) — pas de Metal nécessaire
/// pour 300-500 points, et permet des déformations procédurales très simples.
struct OrbView: View {
    let state: ArcReactorState
    let size: CGFloat

    /// Distribution Fibonacci générée une fois à l'init.
    private let basePoints: [SIMD3<Double>]

    init(state: ArcReactorState, size: CGFloat) {
        self.state = state
        self.size = size
        // Plus de points quand l'orbe est grande, moins quand elle est petite.
        let n: Int
        if size >= 60 { n = 500 }
        else if size >= 30 { n = 300 }
        else { n = 180 }
        self.basePoints = OrbView.fibonacciSphere(n: n)
    }

    var body: some View {
        TimelineView(.animation) { context in
            let t = context.date.timeIntervalSinceReferenceDate
            Canvas { ctx, canvasSize in
                renderOrb(ctx: ctx, canvasSize: canvasSize, t: t)
            }
            .frame(width: size, height: size)
        }
    }

    // MARK: - Rendu

    private func renderOrb(ctx: GraphicsContext, canvasSize: CGSize, t: TimeInterval) {
        let center = CGPoint(x: canvasSize.width / 2, y: canvasSize.height / 2)
        let radius = min(canvasSize.width, canvasSize.height) * 0.45

        // Vitesse de rotation par état (rad/s)
        let rotSpeed: Double
        switch state {
        case .standby:   rotSpeed = 0.20
        case .listening: rotSpeed = 0.55
        case .thinking:  rotSpeed = 0.85
        case .speaking:  rotSpeed = 0.65
        }
        let angleY = t * rotSpeed
        let angleX = t * rotSpeed * 0.35   // léger tilt secondaire
        let cy = cos(angleY), sy = sin(angleY)
        let cx = cos(angleX), sx = sin(angleX)

        // Paramètres de déformation par état
        let breath: Double
        let wave: Double
        let chaos: Double
        switch state {
        case .standby:
            breath = 0.04 * sin(t * 1.3)           // respiration douce
            wave   = 0.01 * sin(t * 2.0)
            chaos  = 0
        case .listening:
            breath = 0.06 * sin(t * 3.0)           // pulse rapide
            wave   = 0.04 * sin(t * 5.0)
            chaos  = 0.01 * sin(t * 7.0)
        case .thinking:
            breath = 0.05 * sin(t * 2.5)
            wave   = 0.03 * sin(t * 4.0)
            chaos  = 0.04 * sin(t * 9.5)           // chaos prononcé
        case .speaking:
            breath = 0.08 * sin(t * 4.0)           // pulse marqué
            wave   = 0.05 * sin(t * 6.0)
            chaos  = 0.02 * sin(t * 8.0)
        }

        // Couleurs de l'état (séparées pour la modulation par profondeur)
        let baseColor = state.color
        let glowColor = state.color.opacity(0.4)

        // Projection 3D → 2D + tri par profondeur pour le rendu back-to-front
        var projected: [(point: CGPoint, depth: Double, sizeMul: Double)] = []
        projected.reserveCapacity(basePoints.count)

        for p in basePoints {
            // Rotation Y (autour de l'axe vertical)
            var x = p.x * cy + p.z * sy
            var y = p.y
            var z = -p.x * sy + p.z * cy
            // Légère rotation X (donne du dynamisme — l'orbe ne tourne pas que sur Y)
            let y2 = y * cx - z * sx
            let z2 = y * sx + z * cx
            y = y2
            z = z2

            // Déformation par latitude (ondulation onduleuse)
            let lat = asin(max(-1.0, min(1.0, y)))
            let r = 1.0 + breath
                       + wave * sin(lat * 3.0 + t * 2.0)
                       + chaos * sin(p.x * 8.0 + p.z * 6.0 + t * 4.0)

            let px = x * r * radius + center.x
            let py = y * r * radius + center.y
            // Profondeur normalisée 0..1 (z = -1 derrière, z = +1 devant)
            let depth = (z + 1.0) / 2.0
            projected.append((CGPoint(x: px, y: py), depth, r))
        }
        // Tri back-to-front
        projected.sort { $0.depth < $1.depth }

        // Rendu — taille et opacité augmentent avec la profondeur (effet 3D)
        for entry in projected {
            let d = entry.depth
            let pointRadius = (0.6 + d * 1.4) * max(0.6, size / 40)
            let alpha = 0.25 + d * 0.75
            let color = d > 0.7 ? baseColor.opacity(alpha) : glowColor.opacity(alpha)
            let rect = CGRect(
                x: entry.point.x - pointRadius,
                y: entry.point.y - pointRadius,
                width: pointRadius * 2,
                height: pointRadius * 2
            )
            ctx.fill(Path(ellipseIn: rect), with: .color(color))
        }
    }

    // MARK: - Distribution Fibonacci

    /// Génère N points distribués uniformément sur la sphère unité via spirale Fibonacci.
    private static func fibonacciSphere(n: Int) -> [SIMD3<Double>] {
        let goldenAngle = .pi * (3.0 - sqrt(5.0))
        var points: [SIMD3<Double>] = []
        points.reserveCapacity(n)
        for i in 0..<n {
            let y = 1.0 - (Double(i) / Double(max(1, n - 1))) * 2.0   // 1 → -1
            let radius = sqrt(max(0.0, 1.0 - y * y))
            let theta = goldenAngle * Double(i)
            let x = cos(theta) * radius
            let z = sin(theta) * radius
            points.append(SIMD3(x, y, z))
        }
        return points
    }
}

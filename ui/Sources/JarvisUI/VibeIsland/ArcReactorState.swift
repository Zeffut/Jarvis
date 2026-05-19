import SwiftUI

/// État courant de l'Arc Reactor. Source de vérité pour les couleurs,
/// vitesses d'animation et intensités du glow.
enum ArcReactorState: String, CaseIterable {
    case standby
    case listening
    case thinking
    case speaking

    /// Couleur dominante de l'anneau et du glow.
    /// Standby garde une saturation complète pour rester visible ;
    /// on calme la vie via les vitesses d'animation, pas la couleur.
    var color: Color {
        switch self {
        case .standby:   return Color(red: 0.36, green: 0.78, blue: 1.00).opacity(0.85)
        case .listening: return Color(red: 0.36, green: 0.78, blue: 1.00)
        case .thinking:  return Color(red: 1.00, green: 0.66, blue: 0.33)
        case .speaking:  return Color(red: 0.60, green: 0.93, blue: 1.00)
        }
    }

    /// Rayon du halo glow en pixels (à scaler avec la taille du reactor).
    var glowRadius: CGFloat {
        switch self {
        case .standby:   return 8
        case .listening: return 16
        case .thinking:  return 12
        case .speaking:  return 14
        }
    }

    /// Durée d'un cycle de "breathe" (scale 1 ↔ 1.05).
    var breatheDuration: Double {
        switch self {
        case .standby:   return 4.0
        case .listening: return 1.2
        case .thinking:  return 1.8
        case .speaking:  return 0.9
        }
    }

    /// Durée d'une rotation complète de l'anneau extérieur.
    var rotationDuration: Double {
        switch self {
        case .standby:   return 20.0
        case .listening: return 8.0
        case .thinking:  return 5.0
        case .speaking:  return 10.0
        }
    }

    /// Active scan lines (off en standby pour rester discret).
    var hasHologramEffects: Bool {
        self != .standby
    }

    /// Intervalle entre deux pulses (ondes concentriques émises depuis le cœur).
    /// Le pulse en standby donne le côté "vivant" même au repos.
    var pulseInterval: Double {
        switch self {
        case .standby:   return 3.5
        case .listening: return 1.4
        case .thinking:  return 1.8
        case .speaking:  return 0.9
        }
    }

    /// Intervalle moyen entre deux flickers holographiques.
    var flickerInterval: Double {
        switch self {
        case .standby:   return 6.0   // rare, presque dormant
        case .listening: return 2.5
        case .thinking:  return 1.8
        case .speaking:  return 3.0
        }
    }
}

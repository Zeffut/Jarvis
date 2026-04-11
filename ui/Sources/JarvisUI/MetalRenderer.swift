import MetalKit
import simd

// MARK: - Shader source (compilé à l'exécution — swift build ne compile pas les .metal)

private let shaderSource = """
#include <metal_stdlib>
using namespace metal;

struct Particle {
    float theta;
    float phi;
    float phase;
    float baseSize;
    float baseAlpha;
};

struct Uniforms {
    float time;
    float energy;
    float rotationSpeed;
    float viewWidth;
    float viewHeight;
    float colorR;
    float colorG;
    float colorB;
    float stateMode;   // 0=standby 1=listening 2=thinking 3=speaking
};

struct VertexOut {
    float4 position [[position]];
    float pointSize [[point_size]];
    float alpha;
    float3 color;
};

vertex VertexOut vertex_main(
    uint vid [[vertex_id]],
    constant Particle* particles [[buffer(0)]],
    constant Uniforms& u [[buffer(1)]]
) {
    Particle p = particles[vid];
    float rotY = u.time * u.rotationSpeed;

    // ── Breathing (toujours actif, même en standby) ──────────────────────
    float breathe = 0.045 * sin(u.time * 0.55 + p.phase * 0.2);

    // ── Listening : ripple rapide réactif à l'amplitude ──────────────────
    float isListening = step(0.5, u.stateMode) * (1.0 - step(1.5, u.stateMode));
    float ripple = isListening * u.energy * 0.35 * sin(u.time * 9.0 + p.phase * 2.5);

    // ── Speaking : burst asymétrique (grosses particules explosent plus) ──
    float isSpeaking = step(2.5, u.stateMode) * (1.0 - step(3.5, u.stateMode));
    float burst = isSpeaking * p.baseAlpha * u.energy * 18.0 * sin(u.time * 6.0 + p.phase);

    // ── Pulse total ───────────────────────────────────────────────────────
    float totalEnergy = u.energy + breathe;
    float pulse = totalEnergy * 22.0 * sin(u.time * 2.8 + p.phase) + ripple + burst;
    float r = 100.0 + pulse;

    float x3 = r * sin(p.phi) * cos(p.theta + rotY);
    float y3 = r * cos(p.phi);
    float z3 = r * sin(p.phi) * sin(p.theta + rotY);

    float fov = 200.0;
    float zd = z3 + 200.0;
    float px = (x3 * fov) / zd;
    float py = (y3 * fov) / zd;
    float2 ndc = float2(px / (u.viewWidth * 0.5), -py / (u.viewHeight * 0.5));

    float depth = clamp((z3 + 100.0) / 200.0, 0.0, 1.0);

    // ── Shimmer : scintillement par particule ─────────────────────────────
    float shimmer = 0.65 + 0.35 * sin(u.time * 4.5 + p.phase * 9.0);

    // ── Thinking : anneau lumineux qui balaie en latitude ────────────────
    float isThinking = step(1.5, u.stateMode) * (1.0 - step(2.5, u.stateMode));
    float sweepPhi = fmod(u.time * 0.75, 3.14159);
    float phiDist = abs(p.phi - sweepPhi);
    float scan = isThinking * 0.85 * exp(-phiDist * phiDist * 7.0);

    // ── Alpha final ───────────────────────────────────────────────────────
    float a = p.baseAlpha
            * (0.25 + depth * 0.75)
            * (0.45 + totalEnergy * 0.55)
            * shimmer;
    a = clamp(a + scan, 0.0, 1.0);

    // ── Taille des points ─────────────────────────────────────────────────
    float scale = fov / zd;
    float speakBoost = isSpeaking * p.baseAlpha * u.energy * 1.2;
    float sz = max(0.5, p.baseSize * scale * (1.0 + totalEnergy * 0.9 + speakBoost));

    VertexOut out;
    out.position = float4(ndc, 0.0, 1.0);
    out.pointSize = sz * 2.0;
    out.alpha = a;
    out.color = float3(u.colorR, u.colorG, u.colorB);
    return out;
}

fragment float4 fragment_main(VertexOut in [[stage_in]],
                               float2 coord [[point_coord]]) {
    float2 c = coord - 0.5;
    float d = length(c);
    if (d > 0.5) { discard_fragment(); }

    // Halo central lumineux + bord doux
    float glow   = exp(-d * d * 10.0);
    float edge   = 1.0 - smoothstep(0.25, 0.5, d);
    float alpha  = in.alpha * mix(edge, 1.0, glow * 0.6);
    float3 color = in.color + glow * float3(0.15, 0.08, 0.0);   // légère chaleur au cœur

    return float4(color, alpha);
}
"""

// MARK: - CPU-side structs (doivent correspondre byte-par-byte aux structs Metal)

private struct Particle {
    var theta: Float
    var phi: Float
    var phase: Float
    var baseSize: Float
    var baseAlpha: Float
}

private struct Uniforms {
    var time: Float
    var energy: Float
    var rotationSpeed: Float
    var viewWidth: Float
    var viewHeight: Float
    var colorR: Float = 0.0
    var colorG: Float = 0.831
    var colorB: Float = 1.0
    var stateMode: Float = 0.0
}

// MARK: - Renderer

final class MetalRenderer: NSObject, MTKViewDelegate {
    private let commandQueue: MTLCommandQueue
    private let pipelineState: MTLRenderPipelineState
    private let particleBuffer: MTLBuffer
    private let particleCount = 1500

    private var currentState: String = "standby"
    private var stateMode: Float = 0.0
    private var energy: Float = 0.05
    private var targetEnergy: Float = 0.05
    private var time: Float = 0

    init?(mtkView: MTKView) {
        guard
            let device = mtkView.device,
            let queue = device.makeCommandQueue()
        else { return nil }
        commandQueue = queue

        // Compile shaders at runtime
        guard
            let library = try? device.makeLibrary(source: shaderSource, options: nil),
            let vertFn = library.makeFunction(name: "vertex_main"),
            let fragFn = library.makeFunction(name: "fragment_main")
        else { return nil }

        let desc = MTLRenderPipelineDescriptor()
        desc.vertexFunction = vertFn
        desc.fragmentFunction = fragFn
        desc.colorAttachments[0].pixelFormat = mtkView.colorPixelFormat
        desc.colorAttachments[0].isBlendingEnabled = true
        desc.colorAttachments[0].sourceRGBBlendFactor = .sourceAlpha
        desc.colorAttachments[0].destinationRGBBlendFactor = .oneMinusSourceAlpha
        desc.colorAttachments[0].sourceAlphaBlendFactor = .one
        desc.colorAttachments[0].destinationAlphaBlendFactor = .oneMinusSourceAlpha

        guard let ps = try? device.makeRenderPipelineState(descriptor: desc) else { return nil }
        pipelineState = ps

        // Générer 1500 points répartis uniformément sur la sphère
        var particles = [Particle]()
        particles.reserveCapacity(particleCount)
        for _ in 0..<particleCount {
            particles.append(Particle(
                theta: Float.random(in: 0...(2 * .pi)),
                phi: acos(Float.random(in: -1...1)),
                phase: Float.random(in: 0...(2 * .pi)),
                baseSize: Float.random(in: 0.6...2.0),
                baseAlpha: Float.random(in: 0.3...1.0)
            ))
        }
        guard let buf = device.makeBuffer(
            bytes: particles,
            length: particles.count * MemoryLayout<Particle>.stride,
            options: .storageModeShared
        ) else { return nil }
        particleBuffer = buf

        super.init()
    }

    /// Appelé par AppDelegate quand un message socket arrive.
    func setState(_ state: String, amplitude: Float) {
        currentState = state
        switch state {
        case "listening":
            stateMode = 1.0
            targetEnergy = 0.25 + amplitude * 0.65
        case "thinking":
            stateMode = 2.0
            targetEnergy = 0.22
        case "speaking":
            stateMode = 3.0
            targetEnergy = 0.38 + amplitude * 0.55
        default:
            stateMode = 0.0
            targetEnergy = 0.04
        }
    }

    func mtkView(_ view: MTKView, drawableSizeWillChange size: CGSize) {}

    func draw(in view: MTKView) {
        time += 1.0 / 60.0

        // Interpolation plus réactive pendant listening/speaking
        let lerpSpeed: Float = (currentState == "listening" || currentState == "speaking") ? 0.07 : 0.04
        energy += (targetEnergy - energy) * lerpSpeed

        guard
            let drawable = view.currentDrawable,
            let passDesc = view.currentRenderPassDescriptor,
            let cmdBuf = commandQueue.makeCommandBuffer(),
            let encoder = cmdBuf.makeRenderCommandEncoder(descriptor: passDesc)
        else { return }

        let rotSpeed: Float = currentState == "speaking" ? 0.28
                            : currentState == "listening" ? 0.16
                            : currentState == "thinking"  ? 0.08
                            : 0.06

        var uniforms = Uniforms(
            time: time,
            energy: energy,
            rotationSpeed: rotSpeed,
            viewWidth: Float(view.drawableSize.width),
            viewHeight: Float(view.drawableSize.height),
            stateMode: stateMode
        )

        encoder.setRenderPipelineState(pipelineState)
        encoder.setVertexBuffer(particleBuffer, offset: 0, index: 0)
        encoder.setVertexBytes(&uniforms, length: MemoryLayout<Uniforms>.size, index: 1)
        encoder.drawPrimitives(type: .point, vertexStart: 0, vertexCount: particleCount)
        encoder.endEncoding()

        cmdBuf.present(drawable)
        cmdBuf.commit()
    }
}

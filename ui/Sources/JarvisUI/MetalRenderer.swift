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
    float pulse = u.energy * 28.0 * sin(u.time * 2.8 + p.phase);
    float r = 100.0 + pulse;

    float x3 = r * sin(p.phi) * cos(p.theta + rotY);
    float y3 = r * cos(p.phi);
    float z3 = r * sin(p.phi) * sin(p.theta + rotY);

    float fov = 380.0;
    float zd = z3 + 380.0;
    float px = (x3 * fov) / zd;
    float py = (y3 * fov) / zd;
    float2 ndc = float2(px / (u.viewWidth * 0.5), -py / (u.viewHeight * 0.5));

    float depth = (z3 + 120.0) / 240.0;
    float a = p.baseAlpha * (0.25 + depth * 0.75) * (0.5 + u.energy * 0.5);
    float scale = fov / zd;
    float sz = max(0.5, p.baseSize * scale * (1.0 + u.energy * 0.6));

    VertexOut out;
    out.position = float4(ndc, 0.0, 1.0);
    out.pointSize = sz * 2.0;
    out.alpha = clamp(a, 0.0, 1.0);
    out.color = float3(u.colorR, u.colorG, u.colorB);
    return out;
}

fragment float4 fragment_main(VertexOut in [[stage_in]],
                               float2 coord [[point_coord]]) {
    float2 c = coord - 0.5;
    float d = length(c);
    if (d > 0.5) { discard_fragment(); }
    float alpha = in.alpha * (1.0 - smoothstep(0.3, 0.5, d));
    return float4(in.color, alpha);
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
}

// MARK: - Renderer

final class MetalRenderer: NSObject, MTKViewDelegate {
    private let commandQueue: MTLCommandQueue
    private let pipelineState: MTLRenderPipelineState
    private let particleBuffer: MTLBuffer
    private let particleCount = 1500

    private var currentState: String = "standby"
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

        // Generate 1500 points on sphere surface
        var particles = [Particle]()
        particles.reserveCapacity(particleCount)
        for _ in 0..<particleCount {
            particles.append(Particle(
                theta: Float.random(in: 0...(2 * .pi)),
                phi: acos(Float.random(in: -1...1)),
                phase: Float.random(in: 0...(2 * .pi)),
                baseSize: Float.random(in: 0.7...2.2),
                baseAlpha: Float.random(in: 0.25...1.0)
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
        case "listening":  targetEnergy = 0.3 + amplitude * 0.6
        case "speaking":   targetEnergy = 0.4 + amplitude * 0.55
        case "thinking":   targetEnergy = 0.25
        default:           targetEnergy = 0.05
        }
    }

    func mtkView(_ view: MTKView, drawableSizeWillChange size: CGSize) {}

    func draw(in view: MTKView) {
        time += 1.0 / 60.0
        energy += (targetEnergy - energy) * 0.04

        guard
            let drawable = view.currentDrawable,
            let passDesc = view.currentRenderPassDescriptor,
            let cmdBuf = commandQueue.makeCommandBuffer(),
            let encoder = cmdBuf.makeRenderCommandEncoder(descriptor: passDesc)
        else { return }

        let rotSpeed: Float = currentState == "speaking" ? 0.25
                            : currentState == "listening" ? 0.15
                            : 0.10

        var uniforms = Uniforms(
            time: time,
            energy: energy,
            rotationSpeed: rotSpeed,
            viewWidth: Float(view.drawableSize.width),
            viewHeight: Float(view.drawableSize.height)
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

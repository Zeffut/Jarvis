// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "JarvisUI",
    platforms: [.macOS(.v13)],
    targets: [
        .executableTarget(
            name: "JarvisUI",
            path: "Sources/JarvisUI"
        )
    ]
)

// swift-tools-version: 6.0

import PackageDescription

let package = Package(
    name: "MacOSVoice",
    platforms: [
        .macOS("26.0")
    ],
    dependencies: [
        .package(name: "bithuman",
                 url: "https://gitlab.com/bithuman/sdk/bithuman-swift.git",
                 from: "2.20.4")
    ],
    targets: [
        .executableTarget(
            name: "MacOSVoice",
            dependencies: [
                .product(name: "bitHumanKit", package: "bithuman")
            ],
            path: "Sources"
        )
    ]
)

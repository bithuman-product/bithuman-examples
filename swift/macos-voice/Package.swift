// swift-tools-version: 6.0

import PackageDescription

let package = Package(
    name: "MacOSVoice",
    platforms: [
        .macOS("26.0")
    ],
    dependencies: [
        .package(name: "bithuman",
                 url: "https://github.com/bithuman-product/homebrew-bithuman.git",
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

// swift-tools-version: 6.0

import PackageDescription

let package = Package(
    name: "IOSAvatar",
    platforms: [
        .iOS("26.0")
    ],
    dependencies: [
        .package(url: "https://gitlab.com/bithuman/sdk/homebrew-bithuman",
                 from: "2.20.5")
    ],
    targets: [
        .executableTarget(
            name: "IOSAvatar",
            dependencies: [
                .product(name: "bitHumanKit", package: "homebrew-bithuman")
            ],
            path: "Sources"
        )
    ]
)

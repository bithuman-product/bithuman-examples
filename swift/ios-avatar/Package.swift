// swift-tools-version: 6.0

import PackageDescription

let package = Package(
    name: "IOSAvatar",
    platforms: [
        .iOS("26.0")
    ],
    dependencies: [
        .package(url: "https://gitlab.com/bithuman/sdk/bithuman-swift.git",
                 from: "2.20.4")
    ],
    targets: [
        .executableTarget(
            name: "IOSAvatar",
            dependencies: [
                .product(name: "bitHumanKit", package: "bithuman-swift")
            ],
            path: "Sources"
        )
    ]
)

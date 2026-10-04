// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "MacOSExpression2",
    // macOS 14: the Mac engine core the Expression2 product links is built for macOS 14,
    // so a macOS 13 target links with a "built for newer 'macOS' version" warning and
    // is not verified to run there.
    platforms: [.macOS(.v14)],
    dependencies: [
        .package(url: "https://github.com/bithuman-product/homebrew-bithuman.git", from: "2.20.2")
    ],
    targets: [
        .executableTarget(
            name: "MacOSExpression2",
            dependencies: [.product(name: "Expression2", package: "homebrew-bithuman")],
            path: "Sources"
        )
    ]
)

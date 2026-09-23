// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "MacOSExpression2",
    platforms: [.macOS(.v13)],
    dependencies: [
        .package(url: "https://github.com/bithuman-product/homebrew-bithuman.git", from: "2.14.1")
    ],
    targets: [
        .executableTarget(
            name: "MacOSExpression2",
            dependencies: [.product(name: "Expression2", package: "homebrew-bithuman")],
            path: "Sources"
        )
    ]
)

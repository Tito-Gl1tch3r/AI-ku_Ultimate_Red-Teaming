// swift-tools-version: 6.1
import PackageDescription

let package = Package(
  name: "event-store-adapter-sqlite",
  platforms: [.macOS(.v15)],
  products: [
    .library(
      name: "EventStoreAdapterSQLite",
      targets: ["EventStoreAdapterSQLite"],
    )
  ],
  dependencies: [
    .package(url: "https://github.com/lemo-nade-room/event-store-adapter-swift.git", from: "1.0.0"),
    .package(url: "https://github.com/lemo-nade-room/event-store-adapter-swift-support.git", from: "1.0.0"),
    .package(url: "https://github.com/pointfreeco/swift-dependencies.git", from: "1.0.0"),
    .package(url: "https://github.com/vapor/fluent.git", from: "4.0.0"),
    .package(url: "https://github.com/vapor/fluent-sqlite-driver.git", from: "4.0.0"),
    .package(url: "https://github.com/swiftlang/swift-docc-plugin.git", from: "1.0.0"),
  ],
  targets: [
    .target(
      name: "EventStoreAdapterSQLite",
      dependencies: [
        .product(name: "EventStoreAdapter", package: "event-store-adapter-swift"),
        .product(name: "Fluent", package: "fluent"),
        .product(name: "FluentSQLiteDriver", package: "fluent-sqlite-driver"),
      ],
      swiftSettings: swiftSettings,
    ),
    .testTarget(
      name: "EventStoreAdapterSQLiteTests",
      dependencies: [
        .product(name: "EventStoreAdapterSupport", package: "event-store-adapter-swift-support"),
        .product(name: "Dependencies", package: "swift-dependencies"),
        .target(name: "EventStoreAdapterSQLite"),
      ],
      swiftSettings: swiftSettings,
    ),
  ],
  swiftLanguageModes: [.v6],
)

var swiftSettings: [SwiftSetting] {
  [
    .enableUpcomingFeature("NonisolatedNonsendingByDefault"),
    .enableUpcomingFeature("NonescapableTypes"),
    .enableUpcomingFeature("ExistentialAny"),
    .enableUpcomingFeature("InternalImportsByDefault"),
  ]
}

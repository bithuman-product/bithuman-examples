// essence2-hello/settings.gradle.kts
pluginManagement {
    repositories { google(); mavenCentral(); gradlePluginPortal() }
}
dependencyResolutionManagement {
    repositories {
        google()         // AGP resolves its own aapt2 from here
        mavenCentral()   // ai.bithuman:essence2-android
    }
}
rootProject.name = "e2hello"
include(":app")

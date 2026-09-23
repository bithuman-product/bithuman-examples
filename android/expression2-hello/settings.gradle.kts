// expression2-hello/settings.gradle.kts
pluginManagement {
    repositories { google(); mavenCentral(); gradlePluginPortal() }
}
dependencyResolutionManagement {
    repositories {
        google()         // AGP resolves its own aapt2 from here — without it the build
                         // dies at :app:processDebugResources, nothing to do with bitHuman
        mavenCentral()   // ai.bithuman:expression2-android
    }
}
rootProject.name = "x2hello"
include(":app")

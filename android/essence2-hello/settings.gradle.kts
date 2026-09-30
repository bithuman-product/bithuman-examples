// essence2-hello/settings.gradle.kts
pluginManagement {
    repositories { google(); mavenCentral(); gradlePluginPortal() }
}
dependencyResolutionManagement {
    repositories {
        google()         // AGP resolves its own aapt2 from here
        mavenCentral()   // what the SDK itself depends on (kotlin-stdlib)
        exclusiveContent {   // ai.bithuman:essence2-android, from bitHuman's repository only
            forRepository { maven { url = uri("https://maven.bithuman.ai") } }
            filter { includeGroup("ai.bithuman") }
        }
    }
}
rootProject.name = "e2hello"
include(":app")

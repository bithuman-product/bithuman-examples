// expression2-hello/settings.gradle.kts
pluginManagement {
    repositories { google(); mavenCentral(); gradlePluginPortal() }
}
dependencyResolutionManagement {
    repositories {
        google()         // AGP resolves its own aapt2 from here — without it the build
                         // dies at :app:processDebugResources, nothing to do with bitHuman
        mavenCentral()   // what the SDK itself depends on (kotlin-stdlib, the Qualcomm runtime)
        exclusiveContent {   // ai.bithuman:expression2-android, from bitHuman's repository only
            forRepository { maven { url = uri("https://maven.bithuman.ai") } }
            filter { includeGroup("ai.bithuman") }
        }
    }
}
rootProject.name = "x2hello"
include(":app")

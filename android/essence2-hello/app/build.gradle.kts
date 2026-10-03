// essence2-hello/app/build.gradle.kts
import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

// Your bitHuman API secret, read the way docs.bithuman.ai/platforms/android#install
// reads it: `bithumanApiSecret=…` in ~/.gradle/gradle.properties, outside your source
// tree. Also accepted, in this order: BITHUMAN_API_SECRET in the environment (the name
// every bitHuman SDK and CLI reads), then `bithuman.apiSecret=…` in local.properties
// (what this project used before 2026-09-30).
// ★It becomes a BuildConfig string constant, so it is readable out of the APK —
// fine for this local hello-world, wrong for anything you ship: a real app fetches
// the secret from YOUR backend at startup.
val bithumanApiSecret: String =
    providers.gradleProperty("bithumanApiSecret").orNull?.takeIf { it.isNotBlank() }
        ?: providers.environmentVariable("BITHUMAN_API_SECRET").orNull?.takeIf { it.isNotBlank() }
        ?: run {
            val props = Properties()
            val f = rootProject.file("local.properties")
            if (f.isFile) f.inputStream().use { props.load(it) }
            props.getProperty("bithuman.apiSecret")
        }
        ?: ""

android {
    namespace  = "com.example.e2hello"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.example.e2hello"
        minSdk        = 29                      // essence2-android's own floor
        targetSdk     = 35
        versionCode   = 1
        versionName   = "1.0"
        ndk { abiFilters += "arm64-v8a" }       // the only ABI published

        // Read from ~/.gradle/gradle.properties or the environment (see the top of
        // this file) — never from a literal in a file you commit, never on a command line.
        buildConfigField("String", "BITHUMAN_API_SECRET", "\"$bithumanApiSecret\"")
    }

    // Required. AGP 8.x defaults buildConfig to OFF, so without this line the
    // BuildConfig class is never generated at all.
    buildFeatures { buildConfig = true }

    // Not optional: the SDK looks for its native libraries as real files on disk.
    packaging { jniLibs { useLegacyPackaging = true } }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
}

dependencies {
    implementation("ai.bithuman:essence2-android:0.9.3")
    testImplementation("junit:junit:4.13.2")   // app/src/test: the WAV reader, on the JVM
}

// expression2-hello/app/build.gradle.kts
import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

// Your bitHuman API secret: `bithuman.apiSecret=…` in local.properties (git-ignored,
// next to settings.gradle.kts), or BITHUMAN_API_SECRET in the environment.
// ★It becomes a BuildConfig string constant, so it is readable out of the APK —
// fine for this local hello-world, wrong for anything you ship: a real app fetches
// the secret from YOUR backend at startup.
val bithumanApiSecret: String = run {
    val props = Properties()
    val f = rootProject.file("local.properties")
    if (f.isFile) f.inputStream().use { props.load(it) }
    props.getProperty("bithuman.apiSecret") ?: System.getenv("BITHUMAN_API_SECRET") ?: ""
}

android {
    namespace  = "com.example.x2hello"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.example.x2hello"
        minSdk        = 26                      // the AAR's own floor
        targetSdk     = 35
        versionCode   = 1
        versionName   = "1.0"
        ndk { abiFilters += "arm64-v8a" }       // the only ABI published

        // Read from local.properties (git-ignored) or the environment — never
        // from a literal in a file you commit, and never on a command line.
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
    implementation("ai.bithuman:expression2-android:0.4.9")
}

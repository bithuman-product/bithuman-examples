plugins {
    id("com.android.application")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

// ONE source tree, TWO installable apps. The engine is a compile-time constant
// (the `BH_ENGINE` dart-define), so a single package id means installing one model
// REPLACES the other and the two can never be compared side by side on one handset.
// `bhModel` gives each model its own application id and its own home-screen label,
// so both live on the device at once and the person switches by tapping an icon.
//
// The default is `expression2` with the HISTORICAL id, so a bare `flutter build apk`
// — the command the README documents — still builds exactly what it always built and
// still upgrades an existing install in place. The second app is opt-in:
//
//     ORG_GRADLE_PROJECT_bhModel=essence2 flutter build apk --dart-define=BH_ENGINE=essence2
//
// A typo must not silently produce a third package id, so an unknown value fails the
// build rather than falling back to a default.
val bhModel = (project.findProperty("bhModel") as String? ?: "expression2").trim()
val bhAppId = when (bhModel) {
    "expression2" -> "ai.bithuman.example.avatar_chat"
    "essence2"    -> "ai.bithuman.example.avatar_chat.essence2"
    else -> throw org.gradle.api.GradleException(
        "bhModel must be 'expression2' or 'essence2', but was '$bhModel'")
}
// The two models are indistinguishable on a home screen — same icon, and the faces
// only differ once the app is open — so the label has to name the model.
val bhLabel = if (bhModel == "essence2") "bitHuman Essence-2" else "bitHuman Expression-2"

android {
    namespace = "ai.bithuman.example.avatar_chat"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    // The Hexagon (QNN) delegate opens its libraries by PATH from the native-library
    // directory: they must be extracted, or the SDK falls back to the CPU silently.
    packaging { jniLibs { useLegacyPackaging = true } }

    defaultConfig {
        // Set above from `bhModel`, so the two models install side by side. If you fork
        // this app, change both ids in `bhAppId` to your own.
        applicationId = bhAppId
        // The manifest reads the label from this placeholder, so the two apps are told
        // apart on the home screen without a second manifest or a second source tree.
        // A placeholder rather than a resValue: generated resource values are an opt-in
        // build feature in this AGP, and the manifest already uses ${applicationName}.
        manifestPlaceholders["appLabel"] = bhLabel
        // You can update the following values to match your application needs.
        // For more information, see: https://flutter.dev/to/review-gradle-config.
        minSdk = 29   // the plugin declares 29 since flutter-plugin-v2.6.0 (essence2-android declares 29; expression2-android 26)
        ndk { abiFilters += "arm64-v8a" }   // the only ABI the engine publishes
        targetSdk = flutter.targetSdkVersion
        versionCode = flutter.versionCode
        versionName = flutter.versionName
    }

    buildTypes {
        release {
            // TODO: Add your own signing config for the release build.
            // Signing with the debug keys for now, so `flutter run --release` works.
            signingConfig = signingConfigs.getByName("debug")
        }
    }
}

kotlin {
    compilerOptions {
        jvmTarget = org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17
    }
}

flutter {
    source = "../.."
}

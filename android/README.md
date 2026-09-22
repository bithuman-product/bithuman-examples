# Android — adding the bitHuman SDKs to a Gradle build

Three coordinates are published to **Maven Central**. All three ship `arm64-v8a`
only (no `armeabi-v7a`, no `x86_64`) and carry **no model weights** — models are
fetched at runtime.

| model | coordinate | latest |
|---|---|---|
| essence-2 | `ai.bithuman:essence2-android` | **0.5.12** |
| expression-2 | `ai.bithuman:expression2-android` | **0.4.8** |
| essence-1 | `ai.bithuman:sdk` | 2.3.6 |

`expression-1` is GPU-only and has no Android coordinate.

Verified against `repo1.maven.org` on 2026-09-22: each artifact's own
`maven-metadata.xml` names exactly these as `<release>`. That file is the
registry's own answer and is the thing to check — `search.maven.org` returns no
results for this group at all, so a web search saying "not found" is not evidence
the artifact is missing.

```bash
curl -s https://repo1.maven.org/maven2/ai/bithuman/essence2-android/maven-metadata.xml
```

## `mavenCentral()` is enough to resolve the SDKs

```kotlin
// settings.gradle.kts
dependencyResolutionManagement {
    repositories {
        google()         // AGP fetches its own aapt2 from here — not a bitHuman dependency
        mavenCentral()   // every ai.bithuman artifact, and everything they depend on
    }
}

// app/build.gradle.kts
android {
    defaultConfig {
        minSdk = 29                          // 29 covers both; expression-2 alone can go to 26
        ndk { abiFilters += "arm64-v8a" }
    }
    packaging { jniLibs { useLegacyPackaging = true } }   // required — see below
}
dependencies {
    implementation("ai.bithuman:essence2-android:0.5.12")
    // and/or
    implementation("ai.bithuman:expression2-android:0.4.8")
}
```

Keep `google()` in the list, but keep it for the right reason: the Android Gradle
Plugin resolves **its own** `aapt2` from Google's Maven, and without it the build
dies at `:app:processDebugResources`. No bitHuman artifact is served from there.

`useLegacyPackaging = true` is not optional. Both SDKs load their native libraries
as real files on disk; without it no `.so` is extracted and the engine cannot open
them.

### ★ Correction — expression-2 has not needed `google()` since 0.3.1

Earlier revisions of this page said `expression2-android` could not resolve from
Maven Central alone because it depended on `com.google.ai.edge.litert:litert`,
which is published only on Google's Maven. **That was true of 0.3.0 and of no
release since.** Reading every published POM for this artifact back from
`repo1.maven.org` on 2026-09-22, the `com.google.ai.edge.litert` edge appears in
0.3.0 alone and is absent from 0.3.1, 0.4.1, 0.4.6, 0.4.7 and 0.4.8. What 0.4.8
declares is exactly three dependencies:

| dependency | scope | where it is served |
|---|---|---|
| `org.jetbrains.kotlin:kotlin-stdlib:2.0.21` | compile | Maven Central |
| `com.qualcomm.qti:qnn-litert-delegate:2.49.0` | runtime | Maven Central |
| `com.qualcomm.qti:qnn-runtime:2.49.0` | runtime | Maven Central |

LiteRT is bundled **inside** the AAR as `jni/arm64-v8a/libLiteRt.so`, so there is
nothing left to resolve for it. Both Qualcomm coordinates — POM and AAR — answer
`200` on `repo1.maven.org`, checked the same day.

The two Qualcomm entries are the Snapdragon accelerator runtime, and 0.4.8 is the
first release that declares them for you; on 0.4.7 and older you had to add them
by hand or the engine rendered on the CPU.

`essence2-android:0.5.12` declares `kotlin-stdlib` and nothing else.

## Verify the graph, not the exit code

This still matters, and it is the reason this page exists. A resolution can return
**rc=0 with a dependency absent from the graph**: Gradle reports a missing
transitive edge as an `UnresolvedDependencyResult`, and code that walks only
`ResolvedDependencyResult` filters it out silently, so the build looks green.

Assert what you actually got, rather than trusting the exit code:

```bash
./gradlew :app:dependencies --configuration releaseRuntimeClasspath | grep ai.bithuman
# must print the coordinate and version you typed
```

That check is also how you catch an accidental downgrade. An older coordinate
still resolves, still compiles and still renders — it renders *differently*, and
almost none of the differences throws. The per-version table of what silently
changes is on
[Pin the version](https://docs.bithuman.ai/sdk/android#pin-the-version).

## Release builds — keep the default ProGuard file

Both SDKs reach their native code by **name** through JNI, so a shrinker that
renames or removes those entry points turns a working app into an
`UnsatisfiedLinkError` at the first frame.

The default Android file already covers this, so the template Android Studio
generates is correct as written. The part that matters is the first argument:

```kotlin
proguardFiles(
    getDefaultProguardFile("proguard-android-optimize.txt"),  // keeps native methods
    "proguard-rules.pro",
)
```

Measured 2026-09-22 with R8 9.5.17 against the published `essence2-android:0.5.12`
AAR: with the default file the engine's JNI bridge is kept and not renamed; with
`proguard-rules.pro` alone it is removed from the APK entirely. If you replace the
default file rather than adding to it, carry its rule across:

```proguard
-keepclasseswithmembernames,includedescriptorclasses class * {
    native <methods>;
}
```

Nothing else is needed. `expression2-android` ships its own rules inside the AAR,
which Gradle applies automatically; `essence2-android` ships none and needs none.
Full detail and the measurement are on
[Shrink the release build](https://docs.bithuman.ai/sdk/android#shrink-the-release-build).

## The worked example lives on the docs site, on purpose

There is no Gradle project checked in beside this file, and nothing is missing.
The complete Android project — seven files, printed in full, for **both** models —
is
[Kotlin / Android — Hello, avatar](https://docs.bithuman.ai/examples/kotlin-android-hello).
The Expression 2 half needs no account, no key and no credits.

That page is not a copy of a project; it **is** the project. A scheduled gate
fetches the published page, writes its code blocks out as the filenames on the
page say, and compiles them against a real Android SDK — so the page cannot drift
from something that builds. A project checked in here would have no such gate, and
this very file is the evidence for why that matters: until 2026-09-22 it
advertised `essence2-android` **0.2.0** and `expression2-android` **0.3.0** — 14
and 5 releases behind — because nothing graded it.

So when this page and the docs site disagree, **the docs site is right** — and
tell us, because this page should not have been allowed to disagree.

## See also

- [Android SDK](https://docs.bithuman.ai/sdk/android) — install, code, model, key
- [Android API reference](https://docs.bithuman.ai/sdk/android-api) — every public
  class, regenerated daily from the AARs Maven Central serves
- [`app/avatar_chat`](../app/avatar_chat/) — the one clonable app in this
  repository that runs on an Android handset

# Android — adding the bitHuman SDKs to a Gradle build

Three coordinates are published to **Maven Central**. All three ship
`arm64-v8a` only (no `armeabi-v7a`, no `x86_64`) and carry **no model
weights** — models are fetched at runtime.

| model | coordinate | latest |
|---|---|---|
| essence-2 | `ai.bithuman:essence2-android` | **0.5.12** |
| expression-2 | `ai.bithuman:expression2-android` | **0.4.7** |
| essence-1 | `ai.bithuman:sdk` | 2.3.6 — first generation; **cannot authenticate on a device** |

Read from Maven Central's own `maven-metadata.xml` on 2026-09-21.
`expression-1` is GPU-only and has no Android coordinate.

> **Type those versions, and nothing lower.** Older coordinates still resolve,
> still compile and render **differently**, and almost none of the differences
> throws — between `essence2-android` 0.5.11 and 0.5.12 the compiled Kotlin is
> byte-identical, so no compiler and no API reference can see it. What each
> older pin silently changes is tabulated on
> [docs.bithuman.ai/sdk/android](https://docs.bithuman.ai/sdk/android#type-these-versions-and-nothing-lower).

> **There is no Android project in this repository, and this file is notes, not
> a walkthrough.** Two complete Android apps — Expression 2 and Essence 2, every
> file printed in full — are at
> [docs.bithuman.ai/examples/kotlin-android-hello](https://docs.bithuman.ai/examples/kotlin-android-hello),
> and they are compiled from that published page on every release. Where this
> file and that page disagree, the page is right.

## Keep `google()` — but not for the reason this file used to give

Both repositories are still needed. The reason changed, and the old one is no
longer true of the artifacts published today:

```kotlin
// settings.gradle.kts
dependencyResolutionManagement {
    repositories {
        google()        // AGP fetches its own aapt2 from here
        mavenCentral()  // the bitHuman AARs
    }
}
```

**Why `google()`, now:** the Android Gradle Plugin resolves `aapt2` from
Google's Maven. Without it the build dies at `:app:processDebugResources`, which
has nothing to do with bitHuman.

**Why this file used to say it, and why that is stale:** at `0.3.0`,
`expression2-android` declared `com.google.ai.edge.litert:litert:2.2.0`, which
is served by Google's Maven and not by Central, so `mavenCentral()` alone
produced `Could not find com.google.ai.edge.litert:litert:2.2.0.` **That is no
longer the case.** Read from the published POMs on 2026-09-21,
`expression2-android:0.4.7` and `essence2-android:0.5.12` each declare exactly
one dependency — `org.jetbrains.kotlin:kotlin-stdlib:2.0.21` — and nothing else.
LiteRT now ships inside the AAR as a bundled `arm64-v8a` library rather than as
a Maven edge.

**`mavenCentral()` is not optional either, and searching will not find these.**
The `ai.bithuman` group is served by Central itself and is not mirrored on
Google's Maven, and it returns no results on `search.maven.org`. Browse
[repo1.maven.org/maven2/ai/bithuman/](https://repo1.maven.org/maven2/ai/bithuman/),
which lists every published version.

```kotlin
// app/build.gradle.kts
dependencies {
    implementation("ai.bithuman:essence2-android:0.5.12")     // essence-2, minSdk 29
    implementation("ai.bithuman:expression2-android:0.4.7")   // expression-2, minSdk 26
}
```

Both are `arm64-v8a` only and both need
`packaging { jniLibs { useLegacyPackaging = true } }`, or no `.so` is extracted
and neither engine finds its native library. They declare different `minSdk`, so
`minSdk 26` with `essence2-android` on the classpath fails the manifest merge —
give each model its own module, or raise the whole app to 29.

## ★ Verify the graph, not the exit code

A resolution can return **rc=0 with `litert` absent from the graph** — that
happened here on 2026-09-04 and is the reason this page exists. Gradle
reports a missing transitive edge as an `UnresolvedDependencyResult`; code
that walks only `ResolvedDependencyResult` filters it out silently and the
build looks green.

Assert the dependency is actually there:

```bash
./gradlew app:dependencies --configuration releaseRuntimeClasspath | grep litert
```

Measured 2026-09-04 from a clean consumer (empty `GRADLE_USER_HOME`,
Gradle 8.13, JDK 17). **This is a record of `0.3.0`, not of what ships
today** — 0.4.7 declares no `litert` edge, so its `mavenCentral()`-only row
would now read rc=0:

| coordinate | `mavenCentral()` only | `+ google()` |
|---|---|---|
| `ai.bithuman:sdk:2.3.6` | rc=0, 4 components, 0 unresolved | — |
| `ai.bithuman:essence2-android:0.2.0` | rc=0, 4 components, 0 unresolved | — |
| `ai.bithuman:expression2-android:0.3.0` | **rc=1, litert UNRESOLVED** | rc=0, 5 components |

## The essence-2 borrow is on the public API

★Teeth are BORROWED from the audio-driven teacher, never synthesized.
The Android surface exposes the borrow so you can assert it:
`attachTesseraBorrow`, `renderDriveBorrow`, `tesseraState`,
`getTesseraComposed` / `getTesseraPassthrough`.

Gate on the borrow state, not on the frame count — a render that
synthesized every mouth produces exactly as many frames as one that
borrowed them.

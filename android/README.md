# Android — adding the bitHuman SDKs to a Gradle build

Three coordinates are served by bitHuman's own Maven repository,
**`https://maven.bithuman.ai`**. New versions are published there only; the versions
published earlier stay on Maven Central as well. All three ship `arm64-v8a`
only (no `armeabi-v7a`, no `x86_64`) and carry **no model weights** — models are
fetched at runtime.

| model | coordinate | latest |
|---|---|---|
| essence-2 | `ai.bithuman:essence2-android` | **0.8.1** |
| expression-2 | `ai.bithuman:expression2-android` | **0.5.2** |
| essence-1 | `ai.bithuman:sdk` | 2.3.7 |

`expression-1` runs in the bitHuman cloud only and has no Android coordinate.

**Both second-generation SDKs need a bitHuman API secret.** They meter each session's
active time, talking or idle, and from `expression2-android` 0.4.9 Expression 2 does too:
`Expression2Avatar.create` throws `Expression2Exception` unless
an API secret is set: `Expression2Credential.set(secret)` (Essence 2: `Essence2Credential.set(secret)`).
Create one at [bithuman.ai/developer/api-keys](https://www.bithuman.ai/developer/api-keys); from 12 October 2026 API and SDK use requires the Creator plan or higher. For an app you distribute, read "What a shipped app holds" in the [top-level README](../README.md#your-api-secret).

## Two complete apps

| project | model | what it shows |
|---|---|---|
| [expression2-hello/](expression2-hello/) | expression-2 | Wise Pup (`A23WJF0199`) rendered on the phone from a WAV, played back on the audio clock |
| [essence2-hello/](essence2-hello/) | essence-2 | Sofia Ramirez (`A52DHS2219`), full-resolution 1080x1920, same shape |

Each is a whole Gradle project that resolves `ai.bithuman` from maven.bithuman.ai and
everything else from Maven Central, and each README carries the five commands that build,
install and run it.

**Start with a second-generation model.** `ai.bithuman:sdk` is the
first-generation artifact and is listed for completeness, not as a
recommendation: the published 2.3.6 installs and then throws before its first
frame with `be_auth_authenticate: status=11`, because its native library ships
with no CA trust store and there is no app-side workaround on that version. It is
also a different integration — a `.imx` you push to the device yourself plus an
API secret, rather than the model store the two rows above use. Details on
[Android SDK](https://docs.bithuman.ai/platforms/android#troubleshooting).

Each artifact's own `maven-metadata.xml` names its newest version as `<release>`.
That file is the registry's own answer and is the thing to check — a web search
saying "not found" is not evidence the artifact is missing.

```bash
curl -s https://maven.bithuman.ai/ai/bithuman/essence2-android/maven-metadata.xml
```

## Add maven.bithuman.ai for `ai.bithuman`

```kotlin
// settings.gradle.kts
dependencyResolutionManagement {
    repositories {
        google()         // AGP fetches its own aapt2 from here — not a bitHuman dependency
        mavenCentral()   // everything the SDKs depend on
        exclusiveContent {   // every ai.bithuman artifact, from bitHuman's repository only
            forRepository { maven { url = uri("https://maven.bithuman.ai") } }
            filter { includeGroup("ai.bithuman") }
        }
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
    implementation("ai.bithuman:essence2-android:0.8.1")
    // and/or
    implementation("ai.bithuman:expression2-android:0.5.2")
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
declares is exactly three dependencies (0.4.9 declares the same three, read back
from its POM on 2026-09-23):

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

`essence2-android:0.5.13` declares `kotlin-stdlib` and nothing else, and so does 0.5.14.

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
[Pin the version](https://docs.bithuman.ai/platforms/android#install).

## Release builds — nothing to add, from `essence2-android` 0.5.13

Both SDKs reach their native code by **name** through JNI, so a shrinker that
renames those entry points turns a working app into an `UnsatisfiedLinkError`
at the first frame. **Both AARs now carry their own keep rule** (`proguard.txt`
inside the AAR), and Gradle applies it to your R8 run whatever your
`proguardFiles(...)` line says — so `isMinifyEnabled = true` needs nothing from
you, with or without `getDefaultProguardFile(...)`.

Measured 2026-09-23 on a Galaxy S25+, the
[Essence 2 project](essence2-hello/)
resolved from Maven Central with `isMinifyEnabled = true` and
`proguardFiles("proguard-rules.pro")` **only**:

| `essence2-android` | R8 `mapping.txt` | on the phone |
|---|---|---|
| 0.5.12 | `ai.bithuman.elevate.NativeBridge -> a.P` | downloads the identity, then `UnsatisfiedLinkError: No implementation found for long a.P.l(...)` |
| 0.5.13 | `ai.bithuman.elevate.NativeBridge -> ai.bithuman.elevate.NativeBridge` | renders and plays |

`expression2-android` has shipped its rule since before 0.4.8 and came through
the same build unchanged.

**If you are pinned to `essence2-android` 0.5.12 or older** and your release
build replaces the default file instead of adding to it, carry the default
file's native-methods rule into your own:

```proguard
-keepclasseswithmembernames,includedescriptorclasses class * {
    native <methods>;
}
```

Full detail on
[Android SDK: platform notes](https://docs.bithuman.ai/platforms/android#platform-notes).

## Where the docs pages point

The docs pages [Android example: Expression 2](https://docs.bithuman.ai/examples/android-expression-2)
and [Android example: Essence 2](https://docs.bithuman.ai/examples/android-essence-2)
send readers to the two projects above, with the apps running on a Galaxy S25+.
Both projects are built before every merge by the `android-examples` step of
[`ci/run-local.sh`](../ci/run-local.sh),
and the docs site's scheduled gate builds `expression2-hello` from this
repository's `main` every day.

## See also

- [Android SDK](https://docs.bithuman.ai/platforms/android) — install, code, model, key
- [Android API reference](https://docs.bithuman.ai/platforms/android/reference) — every public
  class, regenerated daily from the AARs Maven Central serves
- [`app/avatar_chat`](../app/avatar_chat/) — the one clonable app in this
  repository that runs on an Android handset

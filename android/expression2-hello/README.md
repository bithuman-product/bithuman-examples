# expression2-hello — Expression 2 on an Android phone

A complete Android app that renders a talking Expression 2 avatar **on the phone**:
it downloads `A23WJF0199` (Wise Pup, a public showcase avatar) once through the SDK's model store, renders
every frame of a speech clip on the device, then plays the audio and shows each frame
on the audio clock. The clip is bundled in the app, so the first launch renders.

Its page on the docs site, with the app running on a Galaxy S25+, is
[Android example: Expression 2](https://docs.bithuman.ai/examples/android-expression-2). It resolves one coordinate, `ai.bithuman:expression2-android:0.6.1`, from bitHuman's Maven
repository (`https://maven.bithuman.ai`, declared in `settings.gradle.kts` for the
`ai.bithuman` group only), and nothing else from bitHuman; what the SDK depends on
comes from Maven Central.

## What you need

- A physical **arm64-v8a** Android phone with USB debugging on, unlocked. The AAR
  ships no x86_64 code, so an emulator installs and then fails.
- **JDK 17 to 23** (17 or 21 recommended; Android Studio's bundled JDK works), and an
  Android SDK with platform 35 (`minSdk` here is 26).
- `adb` on your `PATH` (it ships in `$ANDROID_HOME/platform-tools`).
- A **bitHuman API secret** from
  [bithuman.ai/developer/api-keys](https://www.bithuman.ai/developer/api-keys) (Creator plan or higher from 12 October 2026).
  `Expression2Avatar.create` throws `Expression2Exception` unless an API secret is set; the app sets it from `BuildConfig` with `Expression2Credential.set(secret)` before `create`.

## Run it

Put your API secret in `~/.gradle/gradle.properties`, outside your source tree, the
same name the [Android page](https://docs.bithuman.ai/platforms/android#install) uses:

```properties
bithumanApiSecret=<your API secret>
```

(Also read: `BITHUMAN_API_SECRET` in the environment, or `bithuman.apiSecret=` in
`local.properties` for checkouts set up before 2026-09-30.) Tell Gradle where your
Android SDK is with `ANDROID_HOME` or `sdk.dir=` in `local.properties` (git-ignored).
Then, from this directory:

```bash
./gradlew :app:assembleDebug
adb install -r app/build/outputs/apk/debug/app-debug.apk
adb shell am start -n com.example.x2hello/.MainActivity
```

The app renders the bundled 13.87 s clip (16 kHz mono) and plays it. Follow the run
with `adb logcat -s X2HELLO`. Tap the screen to replay.

**Your own audio:** push any 16-bit PCM WAV, mono or stereo, at any sample rate (the
docs' [24 kHz sample](https://docs.bithuman.ai/samples/speech.wav) works); the app
mixes it down and resamples it to the 16 kHz mono the engine takes, then restart:

```bash
adb push my.wav /storage/emulated/0/Android/data/com.example.x2hello/files/speech.wav
adb shell am start -S -n com.example.x2hello/.MainActivity
```

**Tests without a phone:** `./gradlew :app:testDebugUnitTest` runs the WAV reader's
tests (16 kHz pass-through, 24 kHz and 48 kHz stereo to 16 kHz mono) on the JVM.

★ **The API secret becomes a `BuildConfig` string constant, so anyone can read it
back out of the APK.** That is fine for a local hello-world and wrong for anything
you ship. A real app fetches the secret from **your** backend at startup and
passes it to the same call.

**Live microphone:** this app plays a file, so it needs only `INTERNET` (merged from
the AAR). To feed the avatar from `AudioRecord`, add `RECORD_AUDIO` to the manifest and
ask for it at run time; see [Live microphone input](../README.md#live-microphone-input).

## Troubleshooting

| You see | Do this |
|---|---|
| `./gradlew` says *this project needs JDK 17 to 23* (or, without that check, only `What went wrong: 25.0.4.1`) | Gradle 8.11.1 cannot run on JDK 24+: `export JAVA_HOME=` a JDK 17 or 21 and run again |
| The screen asks you to set an API secret | add `bithumanApiSecret=` to `~/.gradle/gradle.properties` (or export `BITHUMAN_API_SECRET`) and rebuild; the secret is baked in at build time |
| `need a 16-bit PCM WAV` | your pushed `speech.wav` is not 16-bit PCM (for example 32-bit float or MP3); convert it, e.g. `ffmpeg -i in.wav -ac 1 -ar 16000 -sample_fmt s16 speech.wav` |
| `Unable to strip the following libraries … libLiteRt.so, libQnn*.so` during the build | expected without an NDK installed; the libraries are packaged as they are |

## Measured

On a Galaxy S25+ (SM-S936U1, Android 16), 2026-09-23, with `expression2-android`
**0.4.9** and the 13.87 s clip the app now bundles, pushed as `speech.wav` (the app
then read only a pushed file). Not re-measured on 0.6.1 yet; the log lines are the
same apart from the new `speech:` line. `adb logcat -s X2HELLO`:

```text
audio: 221904 samples = 13.87 s fetching model A23WJF0199 — first run downloads ~158 MB…
model ready — starting the engine…
engine: acc=NPU routing=Routing(enc=CPU, tok14=CPU, step=CPU, dec=NPU) initMs=29629.193115234375 note=
FIRST_FRAME at 31878 ms
DONE_FRAMES 277 in 36600 ms
rendered 277 frames in 36 s — playing…
277 frames, 13.87 s — tap to replay
```

277 frames for 13.87 s is the contract: 20 fps x 13.87 s. Most of the 36.6 s is the
first `create()` compiling the decoder for the phone's NPU (`initMs`, about 30 s);
the frames themselves took under 5 s. The decoder ran on the Hexagon NPU with no
option set to ask for it.

## The files

Every file below is complete and is the one in this directory.

<details><summary><code>app/build.gradle.kts</code></summary>

```kotlin
// expression2-hello/app/build.gradle.kts
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
    namespace  = "com.example.x2hello"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.example.x2hello"
        minSdk        = 26                      // the AAR's own floor
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
    implementation("ai.bithuman:expression2-android:0.6.1")
    testImplementation("junit:junit:4.13.2")   // app/src/test: the WAV reader, on the JVM
}
```

</details>

<details><summary><code>app/src/main/java/com/example/x2hello/MainActivity.kt</code></summary>

```kotlin
// expression2-hello/app/src/main/java/com/example/x2hello/MainActivity.kt
package com.example.x2hello

import ai.bithuman.expression2.Expression2Avatar
import ai.bithuman.expression2.Expression2Credential
import ai.bithuman.expression2.Expression2ModelStore
import ai.bithuman.expression2.Expression2Options
import android.app.Activity
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.media.AudioAttributes
import android.media.AudioFormat
import android.media.AudioTrack
import android.os.Bundle
import android.util.Log
import android.view.Gravity
import android.view.WindowManager
import android.widget.FrameLayout
import android.widget.ImageView
import android.widget.TextView
import java.io.ByteArrayOutputStream
import java.io.File

/**
 * Hello, avatar — Expression 2 on Android.
 *
 * Renders the bundled speech clip (or a speech.wav you pushed) through the on-device
 * avatar, then plays the audio back with the rendered frames. Only the one-time model
 * download and the session's usage reports leave the phone.
 */
class MainActivity : Activity() {

    /** A PUBLIC showcase identity — the door serves it with no credential. Swap in your own agent code. */
    private val agentCode = "A23WJF0199"   // wise-pup

    /**
     * How the engine is built.
     *
     * A bare Expression2Options() is the right start on every arm64 device. On a
     * Snapdragon it runs the decoder on the Hexagon NPU — the SDK brings the Qualcomm
     * runtime with it, so there is nothing to add — and everywhere else it renders on
     * the CPU. The log line below prints which one you got, and why, in
     * avatar.acceleratorNote.
     *
     * Leaving `accelerator` at its AUTO default is what makes that safe: the SDK tries
     * the accelerator and falls back to the CPU by itself. Writing
     * accelerator = Accelerator.NPU turns a refusal into a thrown exception and no
     * frames.
     */
    private val options = Expression2Options()

    private lateinit var image: ImageView
    private lateinit var status: TextView

    @Volatile private var busy = false
    private var frames: List<ByteArray> = emptyList()
    private var pcm: FloatArray = FloatArray(0)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)

        image = ImageView(this).apply { scaleType = ImageView.ScaleType.FIT_CENTER }
        status = TextView(this).apply {
            setBackgroundColor(0xCC000000.toInt())
            setTextColor(0xFFFFFFFF.toInt())
            textSize = 13f
            setPadding(28, 28, 28, 28)
        }
        val root = FrameLayout(this).apply {
            setBackgroundColor(0xFF101014.toInt())
            addView(image, FrameLayout.LayoutParams(MATCH, MATCH))
            addView(status, FrameLayout.LayoutParams(MATCH, WRAP, Gravity.BOTTOM))
            setOnClickListener { start() }        // tap to run again
        }
        setContentView(root)
        start()
    }

    private fun start() {
        if (busy) return
        busy = true
        Thread {
            try {
                if (frames.isEmpty()) renderOnce() else say("replaying ${frames.size} frames")
                if (frames.isNotEmpty()) play()
            } catch (t: Throwable) {
                Log.e(TAG, "failed", t)
                say("FAILED: $t")
            } finally {
                busy = false
            }
        }.start()
    }

    // ---------------------------------------------------------------- render

    private fun renderOnce() {
        val secret = BuildConfig.BITHUMAN_API_SECRET
        if (secret.isBlank()) {
            say("No API secret. Put\n\nbithumanApiSecret=<your API secret>\n\nin ~/.gradle/gradle.properties (or export BITHUMAN_API_SECRET) and rebuild. The engine meters each session it renders and create() refuses without a key.")
            return
        }
        // The credential, before anything downloads or opens an engine: create()
        // throws Expression2Exception when no API secret is set.
        Expression2Credential.set(secret)

        val audio = loadSpeech()
        pcm = audio.toFloats()
        val seconds = audio.seconds
        val expected = Math.round(seconds * Expression2Avatar.FRAMES_PER_SECOND)
        say("audio: ${pcm.size} samples = %.2f s\nfetching model $agentCode — first run downloads ~158 MB…".format(seconds))

        // Blocks on the network the first time; that is why this is a worker thread.
        val model = Expression2ModelStore(this).fetch(agentCode)
        say("model ready — starting the engine…")

        val t0 = System.currentTimeMillis()
        val avatar = Expression2Avatar.create(this, model, options)
        Log.i(TAG, "engine: acc=${avatar.accelerator} routing=${avatar.routing} " +
            "initMs=${avatar.initMs} note=${avatar.acceleratorNote}")
        val out = ArrayList<ByteArray>(expected + 8)
        val jpeg = ByteArrayOutputStream(96 * 1024)

        avatar.use {
            val frame = avatar.newFrameBitmap()   // ARGB_8888, 416 x 720 — allocate once
            avatar.feed(pcm)                      // renders each complete 1.6 s chunk
            avatar.flushTail()                    // the padded tail is the last sentence
            while (true) {
                if (avatar.pull(frame) != null) {
                    if (out.isEmpty()) Log.i(TAG, "FIRST_FRAME at ${System.currentTimeMillis() - t0} ms")
                    jpeg.reset()
                    frame.compress(Bitmap.CompressFormat.JPEG, 85, jpeg)
                    out.add(jpeg.toByteArray())
                    if (out.size % 10 == 0) {
                        val preview = frame.copy(Bitmap.Config.ARGB_8888, false)
                        runOnUiThread { image.setImageBitmap(preview) }
                        say("rendering ${out.size} / $expected frames…")
                    }
                    continue
                }
                if (!avatar.hasPendingTail && avatar.queuedFrames == 0) break
                // A null is "not ready yet". pull() never renders, so asking again at
                // once just burns a core the engine needs — wait, then ask again.
                Thread.sleep(10)
            }
        }
        frames = out
        Log.i(TAG, "DONE_FRAMES ${out.size} in ${System.currentTimeMillis() - t0} ms")
        say("rendered ${out.size} frames in ${(System.currentTimeMillis() - t0) / 1000} s — playing…")
    }

    // -------------------------------------------------------------- playback

    /** Plays the PCM and shows each frame on the audio clock: 800 samples per frame at 20 fps. */
    private fun play() {
        val samples = ShortArray(pcm.size) { (pcm[it] * 32767f).toInt().toShort() }
        val track = AudioTrack.Builder()
            .setAudioAttributes(
                AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_MEDIA)
                    .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                    .build()
            )
            .setAudioFormat(
                AudioFormat.Builder()
                    .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                    .setSampleRate(Expression2Avatar.SAMPLE_RATE)
                    .setChannelMask(AudioFormat.CHANNEL_OUT_MONO)
                    .build()
            )
            .setTransferMode(AudioTrack.MODE_STATIC)
            .setBufferSizeInBytes(samples.size * 2)
            .build()
        try {
            track.write(samples, 0, samples.size)
            track.play()
            val perFrame = Expression2Avatar.SAMPLE_RATE / Expression2Avatar.FRAMES_PER_SECOND  // 800
            var shown = -1
            val deadline = System.currentTimeMillis() + (samples.size * 1000L / Expression2Avatar.SAMPLE_RATE) + 3000
            while (true) {
                val head = track.playbackHeadPosition           // samples the DAC has consumed
                val i = head / perFrame
                if (i < frames.size && i != shown) {
                    shown = i
                    val bmp = BitmapFactory.decodeByteArray(frames[i], 0, frames[i].size)
                    runOnUiThread { image.setImageBitmap(bmp) }
                }
                // The last frames are the padded tail, past the end of the audio.
                if (head >= samples.size || i >= frames.size) break
                if (System.currentTimeMillis() > deadline) break
                Thread.sleep(5)
            }
        } finally {
            track.stop()
            track.release()
        }
        say("${frames.size} frames, ${"%.2f".format(pcm.size.toFloat() / Expression2Avatar.SAMPLE_RATE)} s — tap to replay")
    }

    // ------------------------------------------------------------------ wav

    /**
     * Your own speech.wav if you pushed one (any 16-bit PCM WAV, any rate), else the
     * 16 kHz clip bundled in app/src/main/assets — so the first launch just works:
     *   adb push my.wav /storage/emulated/0/Android/data/com.example.x2hello/files/speech.wav
     */
    private fun loadSpeech(): Wav.Pcm16k {
        val pushed = File(getExternalFilesDir(null), "speech.wav")
        val audio = if (pushed.isFile) Wav.read16kMono(pushed.readBytes(), pushed.absolutePath)
                    else Wav.read16kMono(assets.open("speech.wav").use { it.readBytes() }, "assets/speech.wav")
        Log.i(TAG, "speech: ${if (pushed.isFile) pushed.absolutePath else "assets/speech.wav (bundled)"}, " +
            "${audio.sourceRate} Hz x ${audio.sourceChannels} ch -> 16 kHz mono, %.2f s".format(audio.seconds))
        return audio
    }

    private fun say(msg: String) {
        Log.i(TAG, msg.replace('\n', ' '))
        runOnUiThread { status.text = msg }
    }

    private companion object {
        const val TAG = "X2HELLO"
        val MATCH = FrameLayout.LayoutParams.MATCH_PARENT
        val WRAP = FrameLayout.LayoutParams.WRAP_CONTENT
    }
}
```

</details>

<details><summary><code>app/src/main/java/com/example/x2hello/Wav.kt</code></summary>

```kotlin
// expression2-hello/app/src/main/java/com/example/x2hello/Wav.kt
package com.example.x2hello

import java.nio.ByteBuffer
import java.nio.ByteOrder

/**
 * Any 16-bit PCM WAV -> 16 kHz mono 16-bit samples, the audio the engine takes.
 *
 * Walks the RIFF chunks — do not assume the data starts at byte 44, because real
 * encoders (macOS afconvert, for one) insert padding chunks before it. Stereo is
 * mixed down and any other sample rate (the docs' 24 kHz sample, OpenAI Realtime's
 * 24 kHz voice) is resampled to 16 kHz, so any 16-bit PCM WAV works.
 *
 * The resampler is linear interpolation: plenty for speech in an example. For
 * live audio in your app, resample where you capture it (AudioRecord at 16 kHz,
 * or your voice service's 16 kHz output) instead.
 */
object Wav {
    const val TARGET_RATE = 16_000

    class Pcm16k(val samples: ShortArray, val sourceRate: Int, val sourceChannels: Int) {
        val seconds: Float get() = samples.size.toFloat() / TARGET_RATE
        /** The FloatArray Expression2Avatar.feed() takes: [-1, 1). */
        fun toFloats(): FloatArray = FloatArray(samples.size) { samples[it] / 32768f }
        /** 16-bit little-endian bytes, as a 16 kHz mono WAV stores them. */
        fun toLittleEndianBytes(): ByteArray {
            val bb = ByteBuffer.allocate(samples.size * 2).order(ByteOrder.LITTLE_ENDIAN)
            bb.asShortBuffer().put(samples)
            return bb.array()
        }
    }

    fun read16kMono(b: ByteArray, name: String = "speech.wav"): Pcm16k {
        val bb = ByteBuffer.wrap(b).order(ByteOrder.LITTLE_ENDIAN)
        require(b.size > 12 && tag4(b, 0) == "RIFF" && tag4(b, 8) == "WAVE") { "$name is not a RIFF/WAVE file" }
        var pos = 12
        var format = 0; var channels = 0; var rate = 0; var bits = 0; var dataAt = -1; var dataLen = 0
        while (pos + 8 <= b.size) {
            val id = tag4(b, pos)
            var size = bb.getInt(pos + 4)
            if (size < 0 || pos + 8 + size > b.size) size = b.size - (pos + 8)
            when (id) {
                "fmt " -> {
                    format = bb.getShort(pos + 8).toInt() and 0xFFFF
                    channels = bb.getShort(pos + 10).toInt()
                    rate = bb.getInt(pos + 12)
                    bits = bb.getShort(pos + 22).toInt()
                }
                "data" -> { dataAt = pos + 8; dataLen = size }
            }
            pos += 8 + size + (size and 1)
        }
        require(dataAt >= 0) { "$name has no data chunk" }
        // 1 = PCM, 0xFFFE = WAVE_FORMAT_EXTENSIBLE (PCM in practice at 16 bits).
        require((format == 1 || format == 0xFFFE) && bits == 16 && channels >= 1 && rate > 0) {
            "need a 16-bit PCM WAV; $name is format $format, $rate Hz, $channels ch, $bits-bit"
        }
        val frames = dataLen / (2 * channels)
        val mono = ShortArray(frames) { f ->
            var sum = 0
            for (c in 0 until channels) sum += bb.getShort(dataAt + (f * channels + c) * 2)
            (sum / channels).toShort()
        }
        return Pcm16k(resample(mono, rate), rate, channels)
    }

    /** Linear-interpolation resampler, mono 16-bit. Returns [x] itself at 16 kHz. */
    fun resample(x: ShortArray, fromRate: Int, toRate: Int = TARGET_RATE): ShortArray {
        if (fromRate == toRate || x.isEmpty()) return x
        val n = (x.size.toLong() * toRate / fromRate).toInt()
        val step = fromRate.toDouble() / toRate
        return ShortArray(n) { i ->
            val t = i * step
            val k = t.toInt()
            val frac = t - k
            val a = x[minOf(k, x.size - 1)].toDouble()
            val b = x[minOf(k + 1, x.size - 1)].toDouble()
            (a + (b - a) * frac).toInt().coerceIn(-32768, 32767).toShort()
        }
    }

    private fun tag4(b: ByteArray, at: Int) = String(b, at, 4, Charsets.US_ASCII)
}
```

</details>

`settings.gradle.kts`, `build.gradle.kts`, `gradle.properties` and
`app/src/main/AndroidManifest.xml` are in this directory as they appear on the doc
page. `gradlew` and `gradle/wrapper/` are the Gradle 8.11.1 wrapper, with a JDK
version check added near the top of `gradlew`. `app/src/main/assets/speech.wav` is the
13.87 s, 16 kHz mono clip from [`python/quickstart`](../../python/quickstart).

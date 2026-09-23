# essence2-hello — Essence 2 on an Android phone

A complete Android app that renders a talking Essence 2 avatar **on the phone**:
it reads `speech.wav` from its own external files directory, downloads
`A52DHS2219` (Sofia Ramirez, a free showcase identity) once through the SDK's model store, renders every frame of the clip on
the device, then plays the audio and shows each frame on the audio clock.

Its page on the docs site, with the app running on a Galaxy S25+, is
[Android example: Essence 2](https://docs.bithuman.ai/examples/android-essence2). It resolves one coordinate, `ai.bithuman:essence2-android:0.5.14`, from
Maven Central, and nothing else from bitHuman.

## What you need

- A physical **arm64-v8a** Android phone with USB debugging on, unlocked. The AAR
  ships no x86_64 code, so an emulator installs and then fails.
- **JDK 17**, and an Android SDK with platform 35 (`minSdk` here is 29).
- `adb` on your `PATH` (it ships in `$ANDROID_HOME/platform-tools`).
- A **bitHuman API secret**. A free one:
  [bithuman.ai/developer/api-keys](https://www.bithuman.ai/developer/api-keys).
  The app sets it once from `BuildConfig` with `Essence2Credential.set(secret)`, which covers the model download and the meter.

## Run it

Write `local.properties` next to `settings.gradle.kts`. It is git-ignored; keep it
out of source control:

```properties
sdk.dir=/path/to/your/Android/sdk
bithuman.apiSecret=<your API secret>
```

(`BITHUMAN_API_SECRET` in the environment works instead of the second line.)
Then, from this directory:

```bash
./gradlew :app:assembleDebug
adb install -r app/build/outputs/apk/debug/app-debug.apk
adb shell am start -n com.example.e2hello/.MainActivity
adb push ../../python/quickstart/speech.wav /storage/emulated/0/Android/data/com.example.e2hello/files/speech.wav
adb shell am start -S -n com.example.e2hello/.MainActivity
```

The first launch creates the app's files directory and says on screen that
`speech.wav` is missing. The push fills it, and `am start -S` restarts the app so
it renders. Any 16 kHz mono 16-bit WAV works; the one above is the sample from
[`python/quickstart`](../../python/quickstart). Follow the run with
`adb logcat -s E2HELLO`. Tap the screen to replay.

★ **The API secret becomes a `BuildConfig` string constant, so anyone can read it
back out of the APK.** That is fine for a local hello-world and wrong for anything
you ship. A real app fetches the secret from **your** backend at startup and
passes it to the same call.

## Measured

On a Galaxy S25+ (SM-S936U1, Android 16), 2026-09-23, with `essence2-android`
0.5.14 resolved from Maven Central and the 13.87 s `speech.wav` above — `adb logcat -s E2HELLO`:

```text
audio: 221904 samples = 13.87 s fetching A52DHS2219 — first run downloads about 238 MB…
fetched manifest.json (237679631 B)
identity ready — starting the engine…
engine: 1080x1920 targetFrames=251
DONE_FRAMES 347 in 13595 ms
rendered 347 frames in 13 s — playing…
347 frames, 13.87 s — tap to replay
```

347 full-resolution 1080x1920 frames for 13.87 s of speech (25 fps), rendered in
13.6 s including `create()`: faster than the audio plays. The first run's download
(about 238 MB) is the slow part; later runs start at the engine.

## The files

Every file is complete: the Kotlin below is exactly what ran on the phone above.

<details><summary><code>app/build.gradle.kts</code></summary>

```kotlin
// essence2-hello/app/build.gradle.kts
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
    namespace  = "com.example.e2hello"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.example.e2hello"
        minSdk        = 29                      // essence2-android's own floor
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
    implementation("ai.bithuman:essence2-android:0.5.15")
}
```

</details>

<details><summary><code>app/src/main/java/com/example/e2hello/MainActivity.kt</code></summary>

```kotlin
// essence2-hello/app/src/main/java/com/example/e2hello/MainActivity.kt
package com.example.e2hello

import ai.bithuman.essence2.Essence2Avatar
import ai.bithuman.essence2.Essence2Credential
import ai.bithuman.essence2.Essence2ModelStore
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
import java.nio.ByteBuffer
import java.nio.ByteOrder

/**
 * Hello, avatar — essence-2 on Android.
 *
 * Reads speech.wav from the app's own external files dir, renders it through the
 * on-device avatar, then plays the audio back with the rendered frames.
 *
 * The ONE thing that differs from the expression-2 project on the same page: this
 * needs an API secret, and it needs it in two places. See the doc page.
 */
class MainActivity : Activity() {

    /** One of the published Essence 2 identities — the table on the doc page has the rest. */
    private val agentCode = "A52DHS2219"   // sofia-ramirez

    private lateinit var image: ImageView
    private lateinit var status: TextView

    @Volatile private var busy = false
    private var frames: List<ByteArray> = emptyList()
    private var pcm: ByteArray = ByteArray(0)     // 16-bit little-endian, 16 kHz mono

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
            say("No API secret. Put\n\nbithuman.apiSecret=<your API secret>\n\nin local.properties (or export BITHUMAN_API_SECRET) and rebuild. essence-2 needs one for the download AND for the meter.")
            return
        }

        // 1. The CREDENTIAL, once, before anything downloads or opens an engine.
        //    One setter covers the store's download and the engine's meter;
        //    create() refuses without it.
        Essence2Credential.set(secret)

        val wav = File(getExternalFilesDir(null), "speech.wav")
        if (!wav.isFile) {
            say("No speech.wav yet. On your machine:\n\nadb push speech.wav ${wav.absolutePath}\n\nthen tap the screen.")
            return
        }
        pcm = readWav16kMonoPcm16(wav)
        val seconds = pcm.size / 2f / SAMPLE_RATE
        val expected = Math.round(seconds * FPS)
        say("audio: ${pcm.size / 2} samples = %.2f s\nfetching $agentCode — first run downloads about 238 MB…".format(seconds))

        // 2. The STORE downloads with the credential set above.
        //    Blocks on the network the first time; that is why this is a worker thread.
        val store = Essence2ModelStore(this)
        val identity = store.fetch(agentCode, progress = { member, done, total ->
            if (done == total) Log.i(TAG, "fetched $member ($total B)")
        })
        say("identity ready — starting the engine…")

        val t0 = System.currentTimeMillis()
        // On Android the shared audio front end rides INSIDE the bundle, so
        // create() needs nothing but the directory the store just filled.
        Essence2Avatar.create(identity.dir).use { avatar ->
            Log.i(TAG, "engine: ${avatar.width}x${avatar.height} targetFrames=${avatar.targetFrames}")
            val frame = avatar.newFrameBuffer()   // direct, width * height * 4, RGBA
            val bmp = Bitmap.createBitmap(avatar.width, avatar.height, Bitmap.Config.ARGB_8888)
            val out = ArrayList<ByteArray>(expected + 16)
            val jpeg = ByteArrayOutputStream(512 * 1024)

            avatar.feed(pcm)                      // 16-bit little-endian PCM bytes, as read
            avatar.endOfAudio()                   // "that is the whole utterance"

            var quietMs = 0
            while (quietMs < 5_000) {             // 5 s with no frame at all = finished
                frame.clear()
                if (avatar.pull(frame)) {         // true = a frame was written
                    quietMs = 0
                    frame.rewind()
                    // Android's ARGB_8888 is R,G,B,A in memory, which is the
                    // order the engine delivers, so this copy is a memcpy.
                    bmp.copyPixelsFromBuffer(frame)
                    jpeg.reset()
                    bmp.compress(Bitmap.CompressFormat.JPEG, 88, jpeg)
                    out.add(jpeg.toByteArray())
                    if (out.size % 10 == 0) say("rendering ${out.size} / $expected frames…")
                    continue
                }
                if (out.size >= expected && avatar.available() == 0) break
                Thread.sleep(10)
                quietMs += 10
            }

            // A render that failed must not reach you as silence: checkRender()
            // turns a zero-frame render into a throw that names the reason.
            avatar.checkRender()
            frames = out
        }
        Log.i(TAG, "DONE_FRAMES ${frames.size} in ${System.currentTimeMillis() - t0} ms")
        say("rendered ${frames.size} frames in ${(System.currentTimeMillis() - t0) / 1000} s — playing…")
    }

    // -------------------------------------------------------------- playback

    /** Plays the PCM and shows each frame on the audio clock: 640 samples per frame at 25 fps. */
    private fun play() {
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
                    .setSampleRate(SAMPLE_RATE)
                    .setChannelMask(AudioFormat.CHANNEL_OUT_MONO)
                    .build()
            )
            .setTransferMode(AudioTrack.MODE_STATIC)
            .setBufferSizeInBytes(pcm.size)
            .build()
        // The stored frames are full resolution (1080x1920 here); the screen is not. Decoding at
        // half size keeps each step of the loop inside its 40 ms budget.
        val opts = BitmapFactory.Options().apply { inSampleSize = 2 }
        try {
            track.write(pcm, 0, pcm.size)
            track.play()
            val samples = pcm.size / 2
            val perFrame = SAMPLE_RATE / FPS                     // 640
            var shown = -1
            val deadline = System.currentTimeMillis() + (samples * 1000L / SAMPLE_RATE) + 3000
            while (true) {
                val head = track.playbackHeadPosition             // samples the DAC has consumed
                val i = head / perFrame
                if (i < frames.size && i != shown) {
                    shown = i
                    val b = BitmapFactory.decodeByteArray(frames[i], 0, frames[i].size, opts)
                    runOnUiThread { image.setImageBitmap(b) }
                }
                if (head >= samples || i >= frames.size) break
                if (System.currentTimeMillis() > deadline) break
                Thread.sleep(5)
            }
        } finally {
            track.stop()
            track.release()
        }
        say("${frames.size} frames, ${"%.2f".format(pcm.size / 2f / SAMPLE_RATE)} s — tap to replay")
    }

    // ------------------------------------------------------------------ wav

    /**
     * 16-bit PCM WAV -> the exact bytes feed(ByteArray) takes: 16 kHz mono,
     * 16-bit little-endian, no conversion. Walks the RIFF chunks — do not assume
     * the data starts at byte 44, because real encoders (macOS afconvert, for
     * one) insert padding chunks before it.
     */
    private fun readWav16kMonoPcm16(file: File): ByteArray {
        val b = file.readBytes()
        val bb = ByteBuffer.wrap(b).order(ByteOrder.LITTLE_ENDIAN)
        require(b.size > 44 && tag4(b, 0) == "RIFF" && tag4(b, 8) == "WAVE") { "${file.name} is not a RIFF/WAVE file" }
        var pos = 12
        var channels = 0; var rate = 0; var bits = 0; var dataAt = -1; var dataLen = 0
        while (pos + 8 <= b.size) {
            val id = tag4(b, pos)
            var size = bb.getInt(pos + 4)
            if (size < 0 || pos + 8 + size > b.size) size = b.size - (pos + 8)
            when (id) {
                "fmt " -> {
                    channels = bb.getShort(pos + 10).toInt()
                    rate = bb.getInt(pos + 12)
                    bits = bb.getShort(pos + 22).toInt()
                }
                "data" -> { dataAt = pos + 8; dataLen = size }
            }
            pos += 8 + size + (size and 1)
        }
        require(dataAt >= 0) { "${file.name} has no data chunk" }
        require(channels == 1 && rate == SAMPLE_RATE && bits == 16) {
            "need 16 kHz mono 16-bit PCM; ${file.name} is $rate Hz, $channels ch, $bits-bit"
        }
        return b.copyOfRange(dataAt, dataAt + (dataLen / 2) * 2)
    }

    private fun tag4(b: ByteArray, at: Int) = String(b, at, 4, Charsets.US_ASCII)

    private fun say(msg: String) {
        Log.i(TAG, msg.replace('\n', ' '))
        runOnUiThread { status.text = msg }
    }

    private companion object {
        const val TAG = "E2HELLO"
        const val SAMPLE_RATE = 16000
        const val FPS = 25
        val MATCH = FrameLayout.LayoutParams.MATCH_PARENT
        val WRAP = FrameLayout.LayoutParams.WRAP_CONTENT
    }
}
```

</details>

`settings.gradle.kts`, `build.gradle.kts`, `gradle.properties` and
`app/src/main/AndroidManifest.xml` are in this directory as they appear on the doc
page. `gradlew` and `gradle/wrapper/` are the Gradle 8.11.1 wrapper.

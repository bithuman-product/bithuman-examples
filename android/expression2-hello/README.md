# expression2-hello — Expression 2 on an Android phone

A complete Android app that renders a talking Expression 2 avatar **on the phone**:
it reads `speech.wav` from its own external files directory, downloads
`A23WJF0199` (Wise Pup, a free showcase identity) once through the SDK's model store, renders every frame of the clip on
the device, then plays the audio and shows each frame on the audio clock.

Its page on the docs site, with the app running on a Galaxy S25+, is
[Android example: Expression 2](https://docs.bithuman.ai/examples/android-expression2). It resolves one coordinate, `ai.bithuman:expression2-android:0.4.9`, from
Maven Central, and nothing else from bitHuman.

## What you need

- A physical **arm64-v8a** Android phone with USB debugging on, unlocked. The AAR
  ships no x86_64 code, so an emulator installs and then fails.
- **JDK 17**, and an Android SDK with platform 35 (`minSdk` here is 26).
- `adb` on your `PATH` (it ships in `$ANDROID_HOME/platform-tools`).
- A **bitHuman API secret**. A free one:
  [bithuman.ai/developer/api-keys](https://www.bithuman.ai/developer/api-keys).
  From `expression2-android` 0.4.9 the engine meters the talking time it renders, so `Expression2Avatar.create` throws `Expression2Exception` unless an API secret is set. The app sets it from `BuildConfig` with `Expression2Credential.set(secret)` before `create`. The model download itself stays anonymous.

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
adb shell am start -n com.example.x2hello/.MainActivity
adb push ../../python/quickstart/speech.wav /storage/emulated/0/Android/data/com.example.x2hello/files/speech.wav
adb shell am start -S -n com.example.x2hello/.MainActivity
```

The first launch creates the app's files directory and says on screen that
`speech.wav` is missing. The push fills it, and `am start -S` restarts the app so
it renders. Any 16 kHz mono 16-bit WAV works; the one above is the sample from
[`python/quickstart`](../../python/quickstart). Follow the run with
`adb logcat -s X2HELLO`. Tap the screen to replay.

★ **The API secret becomes a `BuildConfig` string constant, so anyone can read it
back out of the APK.** That is fine for a local hello-world and wrong for anything
you ship. A real app fetches the secret from **your** backend at startup and
passes it to the same call.

## Measured

On a Galaxy S25+ (SM-S936U1, Android 16), 2026-09-23, with `expression2-android`
0.4.9 resolved from Maven Central and the 13.87 s `speech.wav` above — `adb logcat -s X2HELLO`:

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

Every file is complete: the Kotlin below is exactly what ran on the phone above.

<details><summary><code>app/build.gradle.kts</code></summary>

```kotlin
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
    implementation("ai.bithuman:expression2-android:0.4.10")
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
import java.nio.ByteBuffer
import java.nio.ByteOrder

/**
 * Hello, avatar — Expression 2 on Android.
 *
 * Reads speech.wav from the app's own external files dir, renders it through the
 * on-device avatar, then plays the audio back with the rendered frames.
 * Nothing but the one-time model download leaves the phone.
 */
class MainActivity : Activity() {

    /** A PUBLIC showcase identity — the door serves it with no credential. Swap in your own agent code. */
    private val agentCode = "A23WJF0199"   // wise-pup

    /**
     * How the engine is built.
     *
     * A bare Expression2Options() is the right start on every arm64 device. On a
     * Snapdragon it runs the decoder on the Hexagon NPU — 0.4.8 brings the Qualcomm
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
            say("No API secret. Put\n\nbithuman.apiSecret=<your API secret>\n\nin local.properties (or export BITHUMAN_API_SECRET) and rebuild. From expression2-android 0.4.9 the engine meters the talking time it renders and create() refuses without a key.")
            return
        }
        // The METER, before anything opens an engine: from 0.4.9 create() throws
        // Expression2Exception when no API secret is set. The model download stays anonymous.
        Expression2Credential.set(secret)

        val wav = File(getExternalFilesDir(null), "speech.wav")
        if (!wav.isFile) {
            say("No speech.wav yet. On your machine:\n\nadb push speech.wav ${wav.absolutePath}\n\nthen tap the screen.")
            return
        }
        pcm = readWav16kMono(wav)
        val seconds = pcm.size.toFloat() / Expression2Avatar.SAMPLE_RATE
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
     * 16-bit PCM WAV -> the FloatArray feed() takes: 16 kHz mono float32 in [-1, 1].
     * Walks the RIFF chunks — do not assume the data starts at byte 44, because real
     * encoders (macOS afconvert, for one) insert padding chunks before it.
     */
    private fun readWav16kMono(file: File): FloatArray {
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
        require(channels == 1 && rate == Expression2Avatar.SAMPLE_RATE && bits == 16) {
            "need 16 kHz mono 16-bit PCM; ${file.name} is $rate Hz, $channels ch, $bits-bit"
        }
        val n = dataLen / 2
        return FloatArray(n) { bb.getShort(dataAt + it * 2) / 32768f }   // the normalisation feed() expects
    }

    private fun tag4(b: ByteArray, at: Int) = String(b, at, 4, Charsets.US_ASCII)

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

`settings.gradle.kts`, `build.gradle.kts`, `gradle.properties` and
`app/src/main/AndroidManifest.xml` are in this directory as they appear on the doc
page. `gradlew` and `gradle/wrapper/` are the Gradle 8.11.1 wrapper.

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

/**
 * Hello, avatar — essence-2 on Android.
 *
 * Renders the bundled speech clip (or a speech.wav you pushed) through the on-device
 * avatar, then plays the audio back with the rendered frames.
 *
 * It needs an API secret: one Essence2Credential.set call covers the download and the
 * session. See the doc page.
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
            say("No API secret. Put\n\nbithumanApiSecret=<your API secret>\n\nin ~/.gradle/gradle.properties (or export BITHUMAN_API_SECRET) and rebuild. Essence 2 needs it to download the avatar and run the session.")
            return
        }

        // 1. The CREDENTIAL, once, before anything downloads or opens an engine.
        //    One setter covers the store's download and the engine's meter;
        //    create() refuses without it.
        Essence2Credential.set(secret)

        val audio = loadSpeech()
        pcm = audio.toLittleEndianBytes()
        val seconds = audio.seconds
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
            Log.i(TAG, "engine: ${avatar.width}x${avatar.height}")
            val frame = avatar.newFrameBuffer()   // direct, width * height * 4, RGBA
            val bmp = Bitmap.createBitmap(avatar.width, avatar.height, Bitmap.Config.ARGB_8888)
            val out = ArrayList<ByteArray>(expected + 16)
            val jpeg = ByteArrayOutputStream(512 * 1024)

            avatar.feed(pcm)                      // 16-bit little-endian PCM bytes, as read
            avatar.endOfAudio()                   // "that is the whole utterance"

            // pull() returns false until frames are ready, so poll. Stop after 5 s
            // with no new frame — but give the FIRST frame longer (30 s): a cold
            // first render on a slower phone can take more than a few seconds, and
            // giving up before it arrives is a blank screen, not a result.
            var quietMs = 0
            while (quietMs < (if (out.isEmpty()) 30_000 else 5_000)) {
                frame.clear()
                if (avatar.pull(frame)) {         // true = a frame was written
                    if (out.isEmpty()) Log.i(TAG, "FIRST_FRAME at ${System.currentTimeMillis() - t0} ms")
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
     * Your own speech.wav if you pushed one (any 16-bit PCM WAV, any rate), else the
     * 16 kHz clip bundled in app/src/main/assets — so the first launch just works:
     *   adb push my.wav /storage/emulated/0/Android/data/com.example.e2hello/files/speech.wav
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
        const val TAG = "E2HELLO"
        const val SAMPLE_RATE = 16000
        const val FPS = 25
        val MATCH = FrameLayout.LayoutParams.MATCH_PARENT
        val WRAP = FrameLayout.LayoutParams.WRAP_CONTENT
    }
}

// essence2-hello/app/src/main/java/com/example/e2hello/MainActivity.kt
package com.example.e2hello

import ai.bithuman.essence2.Essence2Avatar
import ai.bithuman.essence2.Essence2Metering
import ai.bithuman.elevate.Essence2ModelStore.MeteredDoorResolver
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

        // 1. The METER, before anything opens an engine. create() arms the meter
        //    while it opens the bundle and refuses there if it has no credential.
        //    This is a DIFFERENT credential slot from the store's, and the engine
        //    says so in its own refusal: setting one does not arm the other.
        Essence2Metering.apiSecret = secret

        val wav = File(getExternalFilesDir(null), "speech.wav")
        if (!wav.isFile) {
            say("No speech.wav yet. On your machine:\n\nadb push speech.wav ${wav.absolutePath}\n\nthen tap the screen.")
            return
        }
        pcm = readWav16kMonoPcm16(wav)
        val seconds = pcm.size / 2f / SAMPLE_RATE
        val expected = Math.round(seconds * FPS)
        say("audio: ${pcm.size / 2} samples = %.2f s\nfetching $agentCode — first run downloads about 238 MB…".format(seconds))

        // 2. The STORE. Its default resolver carries an EMPTY credential and
        //    throws on the first fetch, so name the resolver explicitly.
        //    Blocks on the network the first time; that is why this is a worker thread.
        val store = Essence2ModelStore(
            this,
            urlResolver = MeteredDoorResolver(secret),
        )
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

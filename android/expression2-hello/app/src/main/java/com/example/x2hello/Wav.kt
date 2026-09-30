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

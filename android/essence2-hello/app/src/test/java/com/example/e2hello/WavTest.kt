package com.example.e2hello

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.ByteArrayOutputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder

/** Runs on the JVM: ./gradlew :app:testDebugUnitTest — no phone needed. */
class WavTest {
    private fun wav(rate: Int, channels: Int, frames: Int, padChunk: Boolean = false): ByteArray {
        val data = ByteBuffer.allocate(frames * channels * 2).order(ByteOrder.LITTLE_ENDIAN)
        for (f in 0 until frames) for (c in 0 until channels) {
            // a 440 Hz tone, the same on every channel
            data.putShort((Math.sin(2 * Math.PI * 440 * f / rate) * 10000).toInt().toShort())
        }
        val out = ByteArrayOutputStream()
        fun le32(v: Int) = ByteBuffer.allocate(4).order(ByteOrder.LITTLE_ENDIAN).putInt(v).array()
        fun le16(v: Int) = ByteBuffer.allocate(2).order(ByteOrder.LITTLE_ENDIAN).putShort(v.toShort()).array()
        val pad = if (padChunk) 8 + 12 else 0
        out.write("RIFF".toByteArray()); out.write(le32(36 + pad + data.capacity())); out.write("WAVE".toByteArray())
        out.write("fmt ".toByteArray()); out.write(le32(16)); out.write(le16(1)); out.write(le16(channels))
        out.write(le32(rate)); out.write(le32(rate * channels * 2)); out.write(le16(channels * 2)); out.write(le16(16))
        if (padChunk) { out.write("FLLR".toByteArray()); out.write(le32(12)); out.write(ByteArray(12)) }
        out.write("data".toByteArray()); out.write(le32(data.capacity())); out.write(data.array())
        return out.toByteArray()
    }

    @Test fun passesThrough16kMono() {
        val p = Wav.read16kMono(wav(16_000, 1, 16_000, padChunk = true))
        assertEquals(16_000, p.samples.size)
        assertEquals(16_000, p.sourceRate)
    }

    @Test fun resamples24kTo16k() {       // the docs' sample speech.wav is 24 kHz mono
        val p = Wav.read16kMono(wav(24_000, 1, 24_000 * 3))
        assertEquals(24_000, p.sourceRate)
        assertEquals(16_000 * 3, p.samples.size)
        assertEquals(3.0f, p.seconds, 0.001f)
        assertTrue(p.samples.any { it > 9000 })   // the tone survived
    }

    @Test fun mixesStereoDown() {
        val p = Wav.read16kMono(wav(48_000, 2, 48_000))
        assertEquals(1f, p.seconds, 0.001f)
        assertEquals(2, p.sourceChannels)
    }

    @Test fun byteAndFloatViews() {
        val p = Wav.read16kMono(wav(16_000, 1, 100))
        assertEquals(200, p.toLittleEndianBytes().size)
        assertEquals(100, p.toFloats().size)
    }
}

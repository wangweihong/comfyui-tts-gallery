"""Bounded audio decoding using PyAV, already supplied by ComfyUI."""
import io
import wave
from pathlib import Path

import numpy as np

MAX_BYTES = 25 * 1024 * 1024
MAX_SECONDS = 60
ALLOWED = {"wav", "flac", "mp3"}


def decode(path, *, max_seconds=MAX_SECONDS):
    """Return float32 [channels, samples] and the original sample rate."""
    import av
    try:
        with av.open(str(path), options={"protocol_whitelist": "file,pipe"}) as container:
            if not ALLOWED.intersection(container.format.name.split(",")):
                raise ValueError("仅支持 WAV、FLAC、MP3 / Only WAV, FLAC and MP3 are supported")
            if len(container.streams.audio) != 1:
                raise ValueError("音频必须包含一条音轨 / Exactly one audio stream is required")
            stream = container.streams.audio[0]
            rate = stream.codec_context.sample_rate
            channels = len(stream.codec_context.layout.channels)
            if not rate or not 8000 <= rate <= 192000 or not 1 <= channels <= 8:
                raise ValueError("不支持的采样率或声道数 / Unsupported audio configuration")
            resampler = av.AudioResampler(format="fltp", layout=stream.codec_context.layout, rate=rate)
            chunks, count = [], 0
            for frame in container.decode(stream):
                for out in resampler.resample(frame):
                    count += out.samples
                    if count > rate * max_seconds:
                        raise ValueError(f"音频最长 {max_seconds} 秒 / Audio exceeds {max_seconds} seconds")
                    chunks.append(out.to_ndarray())
            for out in resampler.resample(None):
                count += out.samples
                chunks.append(out.to_ndarray())
            if not chunks or count > rate * max_seconds:
                raise ValueError("音频为空或超过时长限制 / Empty or oversized audio")
            data = np.concatenate(chunks, axis=1)
            if not np.isfinite(data).all():
                raise ValueError("音频包含无效采样 / Invalid audio samples")
            return data, rate
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("音频损坏或无法解码 / Cannot decode audio") from exc


def preview_bytes(data, rate):
    """A mono PCM WAV preview; original audio is never overwritten."""
    mono = np.mean(data, axis=0)
    # Keep the original rate: WAV PCM plays without browser codec extensions.
    pcm = (np.clip(mono, -1, 1) * 32767).astype("<i2")
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes(pcm.tobytes())
    return buffer.getvalue()


def inspect(path):
    data, rate = decode(path)
    return {"sample_rate": rate, "channels": data.shape[0], "duration": round(data.shape[1] / rate, 5),
            "peak": round(float(np.abs(data).max()), 6)}, preview_bytes(data, rate)

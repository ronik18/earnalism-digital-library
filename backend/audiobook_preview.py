"""Bounded, read-only MP3 previews. Never expose a source object or its URL."""
MAX_DURATION_MS = 180_000
MAX_SOURCE_BYTES = 9 * 1024 * 1024


def preview_segments(package):
    remaining = MAX_DURATION_MS
    result = []
    for track in package["tracks"]:
        for chunk in track["chunks"]:
            if remaining <= 0:
                return result
            duration = int(chunk["duration_ms"])
            if duration <= 0 or len(result) >= 64:
                raise ValueError("Invalid preview duration/segment count")
            budget = min(duration, remaining)
            result.append((track, chunk, budget))
            remaining -= budget
    return result


def clip_mp3(source, budget_ms, *, complete_source=False):
    """Copy complete Layer III frames only, with a hard decoded-sample ceiling.

    Reject free-format, corrupt and mixed-codec streams. ID3/private metadata is
    omitted; Xing lengths are rewritten so seeking cannot refer to the source.
    This creates derived bytes; the immutable recording is never modified.
    """
    if not 0 < budget_ms <= MAX_DURATION_MS or len(source) > MAX_SOURCE_BYTES:
        raise ValueError("Preview bounds exceeded")
    pos = 0
    if source[:3] == b"ID3":
        if len(source) < 10 or source[3] not in (2, 3, 4) or any(v & 128 for v in source[6:10]):
            raise ValueError("Invalid ID3")
        size = sum(v << shift for v, shift in zip(source[6:10], (21, 14, 7, 0)))
        pos = 10 + size + (10 if source[3] == 4 and source[5] & 16 else 0)
        if pos > 1024 * 1024 or pos >= len(source):
            raise ValueError("Unbounded ID3")
    start = pos
    offsets = []
    codec = None
    samples = rate = channels = crc = 0
    reached_bound = False
    while pos + 4 <= len(source):
        header = int.from_bytes(source[pos:pos + 4], "big")
        version, layer = (header >> 19) & 3, (header >> 17) & 3
        bitrate, frequency = (header >> 12) & 15, (header >> 10) & 3
        if header >> 21 != 0x7ff or version == 1 or layer != 1 or bitrate in (0, 15) or frequency == 3:
            if complete_source and (source[pos:pos + 3] == b"TAG" or pos == len(source)):
                break
            raise ValueError("Invalid MPEG Layer III frame")
        current = (version, frequency, 1 if (header >> 6) & 3 == 3 else 2)
        if codec is not None and current != codec:
            raise ValueError("Mixed MPEG format")
        codec = current
        rate = (44100, 48000, 32000)[frequency] // (1 if version == 3 else 2 if version == 2 else 4)
        samples = 1152 if version == 3 else 576
        channels = current[2]
        crc = 0 if header & (1 << 16) else 2
        kbps = ((0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320) if version == 3
                else (0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160))[bitrate]
        size = (144 if version == 3 else 72) * kbps * 1000 // rate + ((header >> 9) & 1)
        if (len(offsets) + 1) * samples * 1000 > budget_ms * rate:
            reached_bound = True
            break
        if pos + size > len(source):
            raise ValueError("Incomplete source frame")
        offsets.append(pos - start)
        pos += size
    if not offsets or (not complete_source and not reached_bound):
        raise ValueError("Incomplete preview source")
    output = bytearray(source[start:pos])
    xing = 4 + crc + ((17 if channels == 1 else 32) if codec[0] == 3 else (9 if channels == 1 else 17))
    if output[xing:xing + 4] in (b"Xing", b"Info"):
        flags = int.from_bytes(output[xing + 4:xing + 8], "big")
        cursor = xing + 8
        for mask, value in ((1, len(offsets)), (2, len(output))):
            if flags & mask:
                output[cursor:cursor + 4] = value.to_bytes(4, "big")
                cursor += 4
        if flags & 4:
            output[cursor:cursor + 100] = bytes(min(255, offsets[min(len(offsets) - 1, i * len(offsets) // 100)] * 256 // len(output)) for i in range(100))
    if output[36:40] == b"VBRI":
        raise ValueError("Unsupported VBRI preview")
    return bytes(output), len(offsets) * samples * 1000 // rate

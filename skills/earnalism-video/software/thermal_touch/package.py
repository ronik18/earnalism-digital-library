"""Fresh-only local thermal-touch review kit; never upload or grant acceptance.

Reuse the shared tested player shell, actual-audio cues and hash-bound mux
evidence. Existing assembly, soundtracks, media and production records are read
only. The ordered-library/current-pointer integration remains the caller's task.
"""
from pathlib import Path
import argparse
import html
import json
import math
import re
import struct
import subprocess

from .assemble import QualificationError, load, require, sha, write_new

BASE = Path(__file__).resolve().parents[1]
TITLE = "Same Temperature. Why Does Metal Feel Colder?"
DISCLOSURE = "AI-generated narration. Illustrative diagrams; energy marks are schematic, not measurements."
CONTEXT = ("Illustrative starting temperature: 22°C, before contact. Ordinary unheated metal and wood "
           "are compared with a warmer hand. Initial contact depends on conduction, energy storage and "
           "contact conditions; these pictures are not measured skin-temperature curves. The warm-object "
           "reversal is animation only: do not test hot objects by touch.")
FORMATS = ("landscape", "shorts", "clean-shorts")
PACKAGE_FILES = (".thermal-package-lock.json", "watch.html", "shorts.html", "youtube-landscape.json",
                 "youtube-shorts.json", "instagram-caption.txt", "private-review.json",
                 "delivery-check.json", "delivery-manifest.json")
SOURCE_FILES = ("assembly-manifest.json", "voice-binding.json", "asr-review.json", "caption-quality.json",
                "timeline.json", "props.json", "shorts-props.json", "clean-shorts-props.json",
                "narration.wav", "captions.srt", "captions.vtt", "transcript.txt", "sources.json",
                "score-plan.json", "score.provenance.json", "mix-provenance.json",
                "soundtrack.m4a", "dry-soundtrack.m4a", "thumbnail-landscape.png", "thumbnail-shorts.png")
# A viewport-relative top becomes negative after scrolling. Convert it to its
# document coordinate before reserving header/control space, so scrolling cannot
# enlarge the player. Keep the exact emitted function separately executable in
# the focused layout regression; this is not a measured browser-playback claim.
PORTRAIT_FIT_JS = (
    "function portraitRoom(viewportHeight,documentVideoTop,controlsHeight,statusHeight){"
    "return Math.max(120,viewportHeight-Math.max(0,documentVideoTop)-controlsHeight-statusHeight-65);}"
    "function fitPortrait(){if(document.fullscreenElement){video.style.maxHeight='';video.style.width='';return;}"
    "const controls=document.querySelector('.player-controls'),note=document.querySelector('#preview-status');"
    "const documentTop=video.getBoundingClientRect().top+(window.scrollY||0);"
    "const room=portraitRoom(window.innerHeight,documentTop,controls.getBoundingClientRect().height,note.getBoundingClientRect().height);"
    "video.style.maxHeight=room+'px';video.style.width='min(100%,'+(room*9/16)+'px)';}"
)


def safe_relative(name):
    path = Path(name)
    require(not path.is_absolute() and ".." not in path.parts, "Unsafe evidence-relative path")
    return path


def check_bound_files(root, mapping, label):
    require(isinstance(mapping, dict) and mapping, f"Missing {label} bindings")
    for name, digest in mapping.items():
        require(sha(root / safe_relative(name)) == digest, f"Stale {label}: {name}")


def png_size(path):
    with Path(path).open("rb") as handle:
        header = handle.read(24)
    require(header[:8] == b"\x89PNG\r\n\x1a\n" and header[12:16] == b"IHDR", "Cover is not a PNG")
    width, height = struct.unpack(">II", header[16:24])
    require(width > 0 and height > 0, "Invalid cover dimensions")
    return width, height


def source_rows(value):
    rows = value if isinstance(value, list) else value.get("sources", [])
    require(rows and all(isinstance(r, dict) and r.get("title") and
                        str(r.get("url", "")).startswith("https://") for r in rows),
            "Source titles and exact HTTPS links required")
    return rows


def listening_targets(root):
    """Optional measurement-led questions, never listening verdicts or approvals."""
    path = Path(root) / "listening-targets.json"
    if not path.is_file():
        return []
    value = load(path)
    targets = value if isinstance(value, list) else value.get("targets") if isinstance(value, dict) else None
    require(isinstance(targets, list), "Listening targets must contain a target list")
    duration = load(Path(root) / "mix-provenance.json").get("final_duration")
    require(type(duration) in (int, float) and math.isfinite(duration) and duration > 0,
            "Missing actual finished duration for listening targets")
    selected = []
    for target in targets:
        require(isinstance(target, dict), "Invalid listening target")
        start, end, reason = target.get("start"), target.get("end"), target.get("reason")
        require(type(start) in (int, float) and type(end) in (int, float) and
                math.isfinite(start) and math.isfinite(end) and 0 <= start < end <= duration,
                "Listening target is outside actual finished duration")
        require(isinstance(reason, str) and reason.strip(), "Listening target requires a plain reason")
        selected.append({"start": start, "end": end, "reason": reason})
    return selected


def validate_inputs(root):
    root = Path(root)
    require(all((root / name).is_file() for name in SOURCE_FILES), "Incomplete actual private kit inputs")
    assembly, binding, mix = (load(root / name) for name in
                              ("assembly-manifest.json", "voice-binding.json", "mix-provenance.json"))
    require(assembly.get("state") == "ASSEMBLED_PRIVATE_REQUIRES_REVIEW", "Not a qualified assembly")
    required_assembly = {"timeline.json", "narration.wav", "voice-binding.json", "asr-review.json",
                         "caption-quality.json", "props.json", "shorts-props.json", "clean-shorts-props.json",
                         "captions.srt", "captions.vtt", "transcript.txt"}
    require(required_assembly <= set(assembly.get("output_files", {})), "Incomplete assembly bindings")
    check_bound_files(root, assembly.get("output_files"), "assembly output")
    source_root = Path(assembly["source_root"])
    check_bound_files(source_root, assembly.get("input_files"), "original narration source")
    require(binding.get("narration_sha256") == sha(root / "narration.wav") and
            binding.get("no_tempo_or_pitch_change") is True, "Narration binding changed")
    audits = load(root / "asr-review.json")
    require(isinstance(audits, list) and len(audits) == 6 and
            all(a.get("source_validation") == "PASS" and not a.get("differences") for a in audits),
            "Unresolved ASR finding")
    require(not load(root / "caption-quality.json").get("issues"), "Unresolved caption issue")
    require(mix.get("narration_sha256") == binding["narration_sha256"] and
            mix.get("narration_source_unchanged") is True and mix.get("pitch_or_tempo_changed") is False,
            "Finishing changed the protected narration")
    require({"assembly-manifest.json", "timeline.json", "voice-binding.json", "narration.wav"} <=
            set(mix.get("inputs", {})), "Incomplete finishing input bindings")
    check_bound_files(root, mix.get("inputs"), "finishing input")
    check_bound_files(root, mix.get("output_files"), "soundtrack output")
    timeline, props = load(root / "timeline.json"), load(root / "props.json")
    require(props.get("scenes") == timeline.get("scenes") and
            props.get("duration") == timeline.get("duration"), "Stale actual-audio scene timing")
    cues = props.get("captions", [])
    require(cues and all(isinstance(c.get("start"), (int, float)) and
                        isinstance(c.get("end"), (int, float)) and
                        math.isfinite(c["start"]) and math.isfinite(c["end"]) and
                        0 <= c["start"] < c["end"] <= timeline["duration"] and c.get("text")
                        for c in cues), "Invalid actual-audio caption cues")
    require(all(a["end"] <= b["start"] for a, b in zip(cues, cues[1:])), "Overlapping actual captions")
    for name, burned in (("shorts-props.json", True), ("clean-shorts-props.json", False)):
        candidate = load(root / name)
        require(candidate.get("scenes") == props["scenes"] and candidate.get("captions") == cues and
                candidate.get("burnCaptions") is burned, "Stale portrait caption/composition props")
    source_rows(load(root / "sources.json"))
    for name, ratio in (("thumbnail-landscape.png", 16 / 9), ("thumbnail-shorts.png", 9 / 16)):
        width, height = png_size(root / name)
        require(abs(width / height - ratio) < .01, "Cover aspect ratio does not match its format")
    common = {}
    for fmt in FORMATS:
        technical = load(root / fmt / "technical.json")
        require(technical.get("format") == fmt and technical.get("narration_source_unchanged") is True,
                "Wrong format or narrator delivery evidence")
        size = (1920, 1080) if fmt == "landscape" else (1080, 1920)
        require((technical.get("width"), technical.get("height")) == size, "Wrong final dimensions")
        require(abs(technical["duration"] - mix["final_duration"]) < .1, "Stale delivery duration")
        for name in ("video.mp4", "narration-only.mp4"):
            record = technical.get("outputs", {}).get(name, {})
            require(record.get("decode") == "PASS" and record.get("soundtrack_stream_copy") is True and
                    record.get("sha256") == sha(root / fmt / name), f"Stale mux/decode evidence: {fmt}/{name}")
            require(record.get("audio_video_duration_gap", 1) < .1, "Excessive A/V duration gap")
            packet_hash = record.get("common_audio_packet_hash")
            require(isinstance(packet_hash, str) and packet_hash, "Missing protected soundtrack packet hash")
            if name in common:
                require(common[name] == packet_hash, "Formats do not share the identical encoded soundtrack")
            common[name] = packet_hash
    names = list(SOURCE_FILES) + [f"{fmt}/{name}" for fmt in FORMATS
                                 for name in ("video.mp4", "narration-only.mp4", "technical.json")]
    if (root / "instagram-cover.png").is_file():
        png_size(root / "instagram-cover.png")
        names.append("instagram-cover.png")
    if (root / "listening-targets.json").is_file():
        listening_targets(root)
        names.append("listening-targets.json")
    return {name: sha(root / name) for name in names}, common


def preview_check(path, expected_size, duration):
    """Optional WebM is a compatibility derivative, never unchanged-AAC evidence."""
    probe = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_streams", "-show_format",
                                                "-of", "json", str(path)], text=True))
    video = [s for s in probe["streams"] if s["codec_type"] == "video"]
    audio = [s for s in probe["streams"] if s["codec_type"] == "audio"]
    require(len(video) == 1 and len(audio) == 1 and
            (video[0]["width"], video[0]["height"]) == expected_size and
            abs(float(probe["format"]["duration"]) - duration) < .12, "Invalid compatibility preview")
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "null", "-"], check=True)
    return {"sha256": sha(path), "decode": "PASS", "kind": "compatibility derivative; original AAC retained in MP4"}


def script_json(value):
    # Inline JSON remains data even when a source/transcript includes HTML syntax.
    return json.dumps(value, ensure_ascii=False).replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def page(root, portrait, webm=False):
    """Use the existing recovery/fullscreen/caption-safe player, not a new UI."""
    fmt = "shorts" if portrait else "landscape"
    sources = source_rows(load(root / "sources.json"))
    transcript = (root / "transcript.txt").read_text()
    cues = load(root / "props.json")["captions"]
    text = (BASE / "watch-template.html").read_text()
    substitutions = {
        "{{TOPIC}}": html.escape(TITLE), "{{VISUAL_DESCRIPTION}}": "",
        "{{DISCLOSURE}}": html.escape(DISCLOSURE), "{{DIAGRAM_CONTEXT}}": html.escape(CONTEXT),
        "{{ASR_REVIEW}}": '<p>Actual-audio ASR and caption checks passed their mechanical checks. '
                            'This is not listening or pronunciation acceptance. <a href="asr-review.json">ASR evidence</a></p>',
        "{{UNDERSTANDING_CHECKS}}": "<p>Why can matching starting temperatures feel different? What changes if the object is warmer than your hand?</p>",
        "{{TRANSCRIPT}}": html.escape(transcript).replace("\n\n", "</p><p>"),
        "{{SOURCES}}": "".join('<p><a href="' + html.escape(s["url"], quote=True) + '">' +
                                  html.escape(s["title"]) + "</a></p>" for s in sources),
        "{{LABEL_TIMELINE}}": "[]",
    }
    for before, after in substitutions.items():
        text = text.replace(before, after)
    targets = listening_targets(root)
    if targets:
        items = "".join("<li><strong>" + str(t["start"]) + "–" + str(t["end"]) +
                        " seconds</strong>: " + html.escape(t["reason"], quote=True) + "</li>" for t in targets)
        section = ('<section data-role="listening-targets"><h2>Listening targets</h2>'
                   '<p class="note">These diagnostic measurements identify listening targets, '
                   'not confirmed audible defects. Compare the scored and dry recordings.</p><ul>' + items + '</ul></section>')
        text = text.replace("</main>", section + "</main>", 1)
    text = text.replace("Animated explainer · Private review", "PRIVATE · New B recording · Final listening/AV and publication pending")
    text = text.replace('poster="landscape.png"', f'poster="thumbnail-{fmt}.png"')
    video_sources = f'<source src="{fmt}/video.mp4" type="video/mp4">'
    if webm:
        video_sources = f'<source src="{fmt}/preview.webm" type="video/webm">' + video_sources
    text = re.sub(r'<source src="landscape-preview\.mp4[^<]+<source src="landscape-preview\.webm[^>]+>', video_sources, text)
    text = text.replace('<a href="portrait-short.html">Portrait edition for Shorts</a>',
                        '<a href="watch.html">Landscape</a> · <a href="shorts.html">Captioned Shorts</a>')
    text = text.replace('<a href="landscape-narration-only.mp4">Narration-only listening comparison</a>',
                        '<span>Scored versus dry listening:</span></nav><audio controls controlslist="nodownload" '
                        'preload="none" src="dry-soundtrack.m4a" aria-label="Narration-only comparison"></audio><nav>')
    # Source cues, rather than activeCues alone, keep paused/seeked captions present
    # even when browser cue activation is delayed. The native track stays hidden
    # to avoid a second caption layer over the diagram.
    text = text.replace("const labelTimeline=[];", "const labelTimeline=[];\nconst reviewCues=" + script_json(cues) + ";")
    text = text.replace("captionText.textContent=captionsEnabled&&track?[...track.activeCues||[]].map(c=>c.text).join(' '):'';",
                        "captionText.textContent=captionsEnabled?reviewCues.filter(c=>video.currentTime>=c.start&&video.currentTime<c.end).map(c=>c.text).join(' '):'';")
    # Recover with a new decoder as in the shared player; a single source needs
    # no codec switch. With WebM available, retain its actually present ordering.
    text = text.replace("codec=switchCodec?1-codec:0;", "codec=switchCodec&&old.querySelectorAll('source').length>1?1-codec:0;")
    text = text.replace("status.textContent='Preview restored with '+(codec?'WebM':'MP4')+'. Press play to continue.';",
                        "status.textContent='Preview restored. Press Play to continue.';")
    if not webm:
        text = text.replace('<button id="switch-codec" type="button">',
                            '<button id="switch-codec" type="button" disabled title="No alternate codec generated">')
    if portrait:
        text = text.replace("<main>", '<main data-portrait="true">', 1)
        text = text.replace("<style>", '<style>body #sample{width:min(100%,calc((100dvh - 260px)*9/16));height:auto;max-height:calc(100dvh - 260px);aspect-ratio:9/16;object-fit:contain}body #caption-safe-area,body #diagram-key{display:none}', 1)
        text = text.replace('width="1920" height="1080"', 'width="1080" height="1920"')
        text = text.replace('<track kind="captions" src="captions.vtt" srclang="en" label="English" default>', "")
        text = text.replace('<button id="toggle-captions" type="button" aria-pressed="true">Captions: on</button>',
                            '<button id="toggle-captions" type="button" aria-pressed="true" disabled>Captions: burned in</button>')
        # Fit the actual title/status/wrapped controls, rather than guessing one
        # fixed desktop height. Refit a newly recovered decoder as well.
        text = text.replace("function bind(node,time=null,modes=[]){", "function bind(node,time=null,modes=[]){\nnode.addEventListener('loadedmetadata',fitPortrait);")
        text = text.replace("bind(video,Number.isFinite(initial)?initial:null);",
                            PORTRAIT_FIT_JS +
                            "window.addEventListener('resize',fitPortrait);document.addEventListener('fullscreenchange',fitPortrait);"
                            "bind(video,Number.isFinite(initial)?initial:null);fitPortrait();")
    text = text.replace("bind(video,Number.isFinite(initial)?initial:null);",
                        "bind(video,Number.isFinite(initial)?initial:null);\n"
                        "document.addEventListener('play',event=>{if(event.target.matches?.('video,audio'))"
                        "document.querySelectorAll('video,audio').forEach(other=>{if(other!==event.target)other.pause();});},true);")
    require(not re.search(r"\{\{[A-Z_]+\}\}", text), "Unfilled private-player placeholder")
    require("landscape-preview" not in text, "Stale shared-template media path")
    return text


def metadata(root, portrait):
    sources = source_rows(load(root / "sources.json"))
    description = ("Two objects. The same starting temperature. A different feeling. Follow the energy leaving "
                   "your hand to see why metal can feel colder than wood.\n\n"
                   "Explore books, audiobooks and visual learning at https://theearnalism.com\n\n" +
                   DISCLOSURE + "\nWarm-object reversal: animation only; do not test hot objects by touch.\n\nSources:\n" +
                   "\n".join(s["url"] for s in sources) + "\n\n#earnalism #learnalism #EverydayScience #HeatTransfer")
    return {"title": TITLE + " | Earnalism", "description": description,
            "privacyStatus": "private", "publishAt": None, "upload_automatically": False,
            "format": "shorts" if portrait else "landscape", "language": "en",
            "cover": "thumbnail-shorts.png" if portrait else "thumbnail-landscape.png",
            "video": "clean-shorts/video.mp4" if portrait else "landscape/video.mp4",
            "english_captions": "captions.srt", "caption_strategy": "Clean master plus reviewed native English captions; verify final player without duplicate layers",
            "audience_classification": "PENDING_OWNER_CHOICE_AT_AUTHORIZED_UPLOAD",
            "synthetic_narration": True, "platform_disclosure_setting": "Review current applicable rule at actual upload",
            "automatic_dubs": "Disable unreviewed automatic dubbing before upload where available",
            "platform_checks": "NOT_UPLOADED", "related_video": None, "sources": sources,
            "transcript": "transcript.txt", "publication_approved": False}


def package(root):
    root = Path(root).resolve()
    require(not any((root / name).exists() for name in PACKAGE_FILES),
            "Existing or partial private package preserved; use a fresh candidate")
    inputs, packets = validate_inputs(root)
    previews = {}
    duration = load(root / "mix-provenance.json")["final_duration"]
    for fmt in ("landscape", "shorts"):
        for filename in ("preview.webm", "narration-only.webm"):
            path = root / fmt / filename
            if path.is_file():
                previews[f"{fmt}/{filename}"] = preview_check(path, (1920, 1080) if fmt == "landscape" else (1080, 1920), duration)
                inputs[f"{fmt}/{filename}"] = sha(path)
    # Check all inputs before creating any package record, and bind them again
    # at completion so concurrent changes cannot yield a qualified manifest.
    write_new(root / PACKAGE_FILES[0], {"state": "EXCLUSIVE_PRIVATE_NEW_PACKAGE", "publication_approved": False})
    for portrait, name in ((False, "watch.html"), (True, "shorts.html")):
        fmt = "shorts" if portrait else "landscape"
        write_new(root / name, page(root, portrait, f"{fmt}/preview.webm" in previews), as_json=False)
        write_new(root / ("youtube-" + fmt + ".json"), metadata(root, portrait))
    caption = ("Same temperature. Different feeling.\n\n"
               "A metal surface can feel colder than wood even when both begin at the same room temperature. "
               "Follow the heat leaving your hand: the sensation depends on how the material and the contact "
               "transfer energy, not temperature alone.\n\n"
               "Earnalism brings books, audiobooks and visual explanations into everyday life. "
               "Explore the digital library through our profile link.\n\n" + DISCLOSURE +
               "\nUse only ordinary unheated objects for comparison; the warm-object reversal is animation only.\n\n"
               "#earnalism #learnalism #EverydayScience #HeatTransfer\n")
    write_new(root / "instagram-caption.txt", caption, as_json=False)
    review = {"state": "PRIVATE_REVIEW_CANDIDATE", "publication_approved": False, "uploads": False,
              "schedule": None, "factual": "PENDING_FINAL_REVIEW", "graphics_captions": "PENDING_FINAL_REVIEW",
              "rights": "PENDING_FINAL_REVIEW", "listening_av": "PENDING", "technical_delivery": "LOCAL_BOUND_MUX_EVIDENCE",
              "note": "Hash-bound decode/ASR checks are reused, not invented listening, graphical or publication acceptance.",
              "protected_narration_sha256": sha(root / "narration.wav"),
              "soundtrack_source_sha256": sha(root / "soundtrack.m4a"), "common_audio_packet_hashes": packets}
    write_new(root / "private-review.json", review)
    write_new(root / "delivery-check.json", {"state": "LOCAL_PRIVATE_PACKAGE", "bound_mp4_formats": list(FORMATS),
              "mux_decode_evidence": "Current technical.json hashes verified; no redundant full MP4 decode",
              "compatibility_previews": previews, "playback_in_browser": "PENDING",
              "listening_av": "PENDING", "platform_delivery": "NOT_UPLOADED", "publication_approved": False})
    require(all(sha(root / name) == digest for name, digest in inputs.items()), "Package input changed concurrently")
    files = {**inputs, **{name: sha(root / name) for name in PACKAGE_FILES if name != "delivery-manifest.json"}}
    write_new(root / "delivery-manifest.json", {"schema": "earnalism.thermal-private-kit.v1",
              "state": "PRIVATE_REVIEW_REQUIRES_ACCEPTANCE", "files": files,
              "listening_av": "PENDING", "publication_approved": False, "uploads": False, "schedule": None})
    return {"output": str(root), "manifest_sha256": sha(root / "delivery-manifest.json"),
            "landscape": str(root / "watch.html"), "shorts": str(root / "shorts.html"),
            "listening_av": "PENDING", "publication_approved": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="Actual fresh assembled/finished/muxed thermal-touch root")
    print(json.dumps(package(parser.parse_args().root), indent=2))

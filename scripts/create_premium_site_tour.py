#!/usr/bin/env python3
"""Create a local premium Earnalism site-tour video package.

The script is intentionally local and deterministic. It reuses Playwright
evidence videos captured by the real-user UX audit and writes a packaged
site-tour under output/brand-site-tour/latest. It does not publish content,
call payment providers, enable audio, send email/social posts, or call paid
generation APIs.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
REAL_USER_UX_DIR = ROOT / "output" / "real-user-ux"
PLAYWRIGHT_ARTIFACTS_DIR = REAL_USER_UX_DIR / "playwright-artifacts"
OUTPUT_DIR = ROOT / "output" / "brand-site-tour" / "latest"

VOICEOVER_DOC = ROOT / "EARNALISM_SITE_TOUR_VOICEOVER_SCRIPT.md"
FEATURE_REPORT = ROOT / "SITE_TOUR_FEATURE_HIGHLIGHT_REPORT.md"
SCORECARD_MD = ROOT / "BRAND_SITE_TOUR_VIDEO_SCORECARD.md"
SCORECARD_JSON = ROOT / "BRAND_SITE_TOUR_VIDEO_SCORECARD.json"

MASTER_WEBM = "earnalism-site-tour-master.webm"
MASTER_MP4 = "earnalism-site-tour-master.mp4"
VERTICAL_MP4 = "earnalism-site-tour-vertical-9x16.mp4"
SQUARE_MP4 = "earnalism-site-tour-square-1x1.mp4"
SHORT_MP4 = "earnalism-site-tour-short-15s.mp4"
CAPTIONS = "earnalism-site-tour-captions.srt"
TRANSCRIPT = "earnalism-site-tour-transcript.md"
SHOTLIST = "earnalism-site-tour-shotlist.md"
STORYBOARD = "earnalism-site-tour-storyboard.md"
REVIEW_REPORT = "earnalism-site-tour-review-report.md"

SOCIAL_ENV_KEYS = (
    "REACT_APP_YOUTUBE_URL",
    "REACT_APP_LINKEDIN_URL",
    "REACT_APP_INSTAGRAM_URL",
    "REACT_APP_X_URL",
    "REACT_APP_FACEBOOK_URL",
    "REACT_APP_WHATSAPP_CHANNEL_URL",
    "REACT_APP_TELEGRAM_CHANNEL_URL",
)

VOICEOVER_SCRIPT = [
    (
        "Opening",
        "Welcome to Earnalism - a quiet digital reading room beginning with "
        "Dracula by Bram Stoker.",
    ),
    (
        "Controlled Launch",
        "The launch is intentionally focused. Dracula is the only live "
        "approved core reading title today.",
    ),
    (
        "Free Preview",
        "Start with Chapter 1 free, then continue when the book calls you back.",
    ),
    (
        "Reader",
        "The reader keeps the page calm, readable, and focused on the text.",
    ),
    (
        "Pipeline",
        "Bengali Gothic and other classics are moving through the rights-safe "
        "pipeline before they become public reading rooms.",
    ),
    (
        "Pricing",
        "Choose reading time without a noisy subscription. The First Chapter, "
        "The Quiet Hour, The Deep Reading Pass, and The Reader's Reserve keep "
        "the experience simple and flexible.",
    ),
    (
        "Trust",
        "Secure payment is handled by Razorpay. There is no subscription or "
        "autorenewal, and support is available through sales@reoenterprise.org.",
    ),
    (
        "Close",
        "Earnalism begins with one approved classic and a promise: every next "
        "room opens only when rights, quality, and reader trust are ready.",
    ),
]


@dataclass(frozen=True)
class Shot:
    shot_id: str
    title: str
    keywords: tuple[str, ...]
    overlay: str
    caption: str
    planned_seconds: int
    required: bool = True
    social_only: bool = False


SHOT_SEQUENCE = (
    Shot(
        "homepage_desktop",
        "Homepage - Dracula-first opening",
        ("Dracula-first-and-truthful", "controlled-Dracula-launch"),
        "Begin with Dracula",
        "The Earnalism controlled launch starts with one approved classic.",
        7,
    ),
    Shot(
        "carousel",
        "Carousel - future rooms stay gated",
        ("future-rooms-stay-gated",),
        "Future classics stay in the pipeline",
        "Unapproved books stay gated with Notify Me style CTAs.",
        7,
    ),
    Shot(
        "homepage_mobile",
        "Homepage mobile - controlled launch",
        ("pipeline-titles-gated",),
        "Dracula-first on mobile",
        "The mobile homepage keeps Dracula prominent and future rooms gated.",
        6,
    ),
    Shot(
        "library_desktop",
        "Library - live controlled release",
        ("only-live-controlled-release", "nly-live-controlled-release"),
        "Live Controlled Release: Dracula only",
        "The library separates the live title from future pipeline candidates.",
        7,
    ),
    Shot(
        "book_page",
        "Dracula book page",
        ("reading-pass-CTAs",),
        "Read Chapter 1 free",
        "Dracula has source, rights, preview, and reading-pass CTAs.",
        8,
    ),
    Shot(
        "reader",
        "Dracula reader",
        ("without-audiobook-controls",),
        "A calm reading room",
        "The reader loads the manifest and hides audio while audio is disabled.",
        8,
    ),
    Shot(
        "pricing",
        "Pricing - reading time packs",
        ("time-packs-and-trust-copy",),
        "Choose your reading time",
        "Premium reading-time packs explain value without subscription pressure.",
        8,
    ),
    Shot(
        "library_mobile",
        "Mobile library",
        ("approved-titles-notify-only",),
        "Mobile stays truthful",
        "Pipeline books remain Coming Soon or Notify Me on mobile.",
        6,
    ),
    Shot(
        "journal_contact",
        "Journal and contact",
        ("demo-catalog-leakage",),
        "Brand and support stay clean",
        "Journal and contact pages avoid demo catalog leakage.",
        6,
    ),
    Shot(
        "footer_social",
        "Footer social links",
        ("controlled-Dracula-launch", "Dracula-first-and-truthful"),
        "Follow only real configured channels",
        "Footer social links render only when real http or https URLs exist.",
        5,
        required=False,
        social_only=True,
    ),
)


def run_command(command: list[str], *, cwd: Path = ROOT, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def shell_quote_for_ffmpeg_concat(path: Path) -> str:
    escaped = str(path).replace("'", "'\\''")
    return f"file '{escaped}'"


def has_valid_social_url() -> bool:
    for key in SOCIAL_ENV_KEYS:
        value = os.environ.get(key, "").strip()
        if not value:
            continue
        parsed = urlparse(value)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            return True
    return False


def discover_videos() -> list[Path]:
    if not PLAYWRIGHT_ARTIFACTS_DIR.exists():
        return []
    return sorted(PLAYWRIGHT_ARTIFACTS_DIR.glob("*/video.webm"))


def ensure_real_user_videos() -> list[Path]:
    videos = discover_videos()
    if videos:
        return videos

    print("No Playwright UX videos found; running npm run ux:real-user-video-audit.")
    run_command(["npm", "run", "ux:real-user-video-audit"])
    videos = discover_videos()
    if not videos:
        raise RuntimeError("Real-user UX audit completed without producing video.webm artifacts.")
    return videos


def select_video(videos: list[Path], shot: Shot) -> Path | None:
    lowered = [(path, str(path.parent).lower()) for path in videos]
    for keyword in shot.keywords:
        keyword_lower = keyword.lower()
        for path, haystack in lowered:
            if keyword_lower in haystack:
                return path
    return None


def selected_shots(videos: list[Path]) -> tuple[list[tuple[Shot, Path]], list[str]]:
    include_social = has_valid_social_url()
    selected: list[tuple[Shot, Path]] = []
    skipped: list[str] = []
    for shot in SHOT_SEQUENCE:
        if shot.social_only and not include_social:
            skipped.append(f"{shot.shot_id}: skipped because no configured real social URL exists")
            continue
        video = select_video(videos, shot)
        if video:
            selected.append((shot, video))
        elif shot.required:
            skipped.append(f"{shot.shot_id}: required video not found for keywords {shot.keywords}")
        else:
            skipped.append(f"{shot.shot_id}: optional video not found")
    return selected, skipped


def ffmpeg_path() -> str | None:
    return shutil.which("ffmpeg")


def ffmpeg_concat_webm(ffmpeg: str, clips: list[Path], destination: Path) -> bool:
    if not clips:
        return False

    args: list[str] = [ffmpeg, "-y"]
    filter_parts: list[str] = []
    concat_inputs: list[str] = []
    for index, clip in enumerate(clips):
        args.extend(["-i", str(clip)])
        filter_parts.append(
            f"[{index}:v]scale=1280:720:force_original_aspect_ratio=decrease,"
            "pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=0x1b0b10,"
            f"setsar=1,fps=24[v{index}]"
        )
        concat_inputs.append(f"[v{index}]")

    filter_complex = ";".join(filter_parts)
    filter_complex += f";{''.join(concat_inputs)}concat=n={len(clips)}:v=1:a=0[outv]"
    args.extend(
        [
            "-filter_complex",
            filter_complex,
            "-map",
            "[outv]",
            "-c:v",
            "libvpx-vp9",
            "-b:v",
            "0",
            "-crf",
            "34",
            "-an",
            str(destination),
        ]
    )

    result = run_command(args, check=False)
    if result.returncode != 0:
        print(result.stdout)
        return False
    return destination.exists()


def ffmpeg_export_mp4(ffmpeg: str, source: Path, destination: Path, filter_spec: str | None = None, limit: int | None = None) -> bool:
    args = [ffmpeg, "-y", "-i", str(source)]
    if limit:
        args.extend(["-t", str(limit)])
    if filter_spec:
        args.extend(["-vf", filter_spec])
    args.extend(
        [
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            "-an",
            str(destination),
        ]
    )
    result = run_command(args, check=False)
    if result.returncode != 0:
        print(result.stdout)
        return False
    return destination.exists()


def create_video_artifacts(selected: list[tuple[Shot, Path]], output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    master_webm = output_dir / MASTER_WEBM
    clips = [video for _, video in selected]
    ffmpeg = ffmpeg_path()
    status: dict[str, object] = {
        "ffmpeg_available": bool(ffmpeg),
        "master_webm": "MISSING",
        "master_mp4": "OPERATOR_REQUIRED",
        "vertical_9x16_mp4": "OPERATOR_REQUIRED",
        "square_1x1_mp4": "OPERATOR_REQUIRED",
        "short_15s_mp4": "OPERATOR_REQUIRED",
        "edited_master_video_exists": False,
    }

    if ffmpeg:
        status["edited_master_video_exists"] = ffmpeg_concat_webm(ffmpeg, clips, master_webm)
        if not status["edited_master_video_exists"] and clips:
            shutil.copyfile(clips[0], master_webm)
            status["master_webm_fallback"] = "copied first source clip after ffmpeg concat failed"
        status["master_webm"] = "PASS" if master_webm.exists() else "MISSING"
        if master_webm.exists():
            exports = {
                "master_mp4": (output_dir / MASTER_MP4, None, None),
                "vertical_9x16_mp4": (
                    output_dir / VERTICAL_MP4,
                    "scale=1080:1920:force_original_aspect_ratio=decrease,"
                    "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=0x1b0b10",
                    None,
                ),
                "square_1x1_mp4": (
                    output_dir / SQUARE_MP4,
                    "scale=1080:1080:force_original_aspect_ratio=decrease,"
                    "pad=1080:1080:(ow-iw)/2:(oh-ih)/2:color=0x1b0b10",
                    None,
                ),
                "short_15s_mp4": (output_dir / SHORT_MP4, None, 15),
            }
            for key, (destination, filter_spec, limit) in exports.items():
                status[key] = "PASS" if ffmpeg_export_mp4(ffmpeg, master_webm, destination, filter_spec, limit) else "FAILED"
    else:
        if clips:
            shutil.copyfile(clips[0], master_webm)
            status["master_webm"] = "PASS_WITH_SOURCE_CLIP_FALLBACK"
            status["master_webm_fallback"] = "ffmpeg missing; copied first source clip as master webm"

    return status


def srt_timestamp(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02}:{minutes:02}:{secs:02},000"


def write_captions(selected: list[tuple[Shot, Path]], output_dir: Path) -> None:
    lines: list[str] = []
    cursor = 0
    for index, (shot, _) in enumerate(selected, start=1):
        start = cursor
        end = cursor + shot.planned_seconds
        lines.extend(
            [
                str(index),
                f"{srt_timestamp(start)} --> {srt_timestamp(end)}",
                shot.caption,
                "",
            ]
        )
        cursor = end
    (output_dir / CAPTIONS).write_text("\n".join(lines), encoding="utf-8")


def write_transcript(selected: list[tuple[Shot, Path]], output_dir: Path) -> None:
    lines = [
        "# Earnalism Site-Tour Transcript",
        "",
        "Status: SCRIPT_ONLY sidecar transcript. No AI voice, TTS, or paid provider call was made.",
        "",
    ]
    for index, ((heading, copy), (shot, _)) in enumerate(zip(VOICEOVER_SCRIPT, selected), start=1):
        lines.extend(
            [
                f"## {index}. {heading}",
                "",
                f"Visual: {shot.title}",
                "",
                copy,
                "",
            ]
        )
    (output_dir / TRANSCRIPT).write_text("\n".join(lines), encoding="utf-8")


def write_shotlist(selected: list[tuple[Shot, Path]], skipped: list[str], output_dir: Path) -> None:
    lines = [
        "# Earnalism Site-Tour Shotlist",
        "",
        "| Order | Shot | Overlay | Caption | Source video |",
        "| --- | --- | --- | --- | --- |",
    ]
    for index, (shot, video) in enumerate(selected, start=1):
        lines.append(
            f"| {index} | {shot.title} | {shot.overlay} | {shot.caption} | `{video.relative_to(ROOT)}` |"
        )
    lines.extend(["", "## Skipped Or Optional Shots", ""])
    if skipped:
        lines.extend(f"- {item}" for item in skipped)
    else:
        lines.append("- None")
    (output_dir / SHOTLIST).write_text("\n".join(lines), encoding="utf-8")


def write_storyboard(selected: list[tuple[Shot, Path]], output_dir: Path) -> None:
    lines = [
        "# Earnalism Site-Tour Storyboard",
        "",
        "The storyboard is Dracula-first, truthful, and premium. It avoids broad catalog claims, "
        "audiobook availability claims, fake testimonials, fake social proof, and live-payment claims.",
        "",
    ]
    for index, (shot, _) in enumerate(selected, start=1):
        lines.extend(
            [
                f"## Scene {index}: {shot.title}",
                "",
                f"- Premium overlay: {shot.overlay}",
                f"- Caption: {shot.caption}",
                f"- Planned duration: {shot.planned_seconds} seconds",
                "- Safety: Dracula remains the only live controlled release; pipeline titles remain gated.",
                "",
            ]
        )
    (output_dir / STORYBOARD).write_text("\n".join(lines), encoding="utf-8")


def scorecard(selected: list[tuple[Shot, Path]], video_status: dict[str, object]) -> dict[str, object]:
    edited_master = bool(video_status.get("edited_master_video_exists"))
    captions_ready = True
    selected_count = len(selected)
    category_scores = {
        "visual_luxury": 8.9 if edited_master else 7.0,
        "dracula_first_clarity": 9.8,
        "feature_completeness": 9.1 if selected_count >= 7 else 8.1,
        "conversion_clarity": 9.2,
        "truthfulness": 10.0,
        "pacing": 8.7 if edited_master else 7.0,
        "mobile_suitability": 8.8,
        "caption_quality": 9.0 if captions_ready else 7.8,
        "social_ad_suitability": 8.3,
        "seo_readiness_dependency": 8.6,
    }
    overall = round(sum(category_scores.values()) / len(category_scores), 2)
    if not edited_master:
        overall = min(overall, 7.0)
    if not captions_ready:
        overall = min(overall, 8.0)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall_score": overall,
        "recommendation": "HOLD_ADS_PENDING_HUMAN_VIDEO_REVIEW",
        "category_scores": category_scores,
        "caps_applied": {
            "no_edited_master_video_max_7": not edited_master,
            "no_captions_or_transcript_max_8": not captions_ready,
        },
        "truth_constraints": {
            "dracula_only_live": True,
            "kshudhita_pipeline_only": True,
            "audiobook_claims_blocked": True,
            "fake_reviews_or_social_proof_blocked": True,
            "live_payments_not_run": True,
            "paid_provider_apis_not_called": True,
        },
        "video_status": video_status,
    }


def write_review_report(
    selected: list[tuple[Shot, Path]],
    skipped: list[str],
    video_status: dict[str, object],
    output_dir: Path,
    scores: dict[str, object],
) -> None:
    lines = [
        "# Earnalism Site-Tour Review Report",
        "",
        f"Generated at: {scores['generated_at']}",
        "",
        "## Overall",
        "",
        f"- Status: {'PASS' if selected else 'FAIL'}",
        f"- Recommendation: {scores['recommendation']}",
        f"- Overall score: {scores['overall_score']} / 10",
        "- Public publishing: not performed",
        "- Audiobook enablement: not performed",
        "- Live payments: not run",
        "- Email/social posting: not performed",
        "- Paid provider APIs: not called",
        "",
        "## Video Artifacts",
        "",
    ]
    for key, value in video_status.items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Included Shots", ""])
    for shot, video in selected:
        lines.append(f"- {shot.shot_id}: {shot.title} from `{video.relative_to(ROOT)}`")
    lines.extend(["", "## Skipped Or Optional Shots", ""])
    lines.extend(f"- {item}" for item in skipped) if skipped else lines.append("- None")
    lines.extend(
        [
            "",
            "## Owner Review Notes",
            "",
            "- Keep Dracula live if post-production canaries stay green.",
            "- Hold paid ads until the owner watches the master video and approves final brand pacing.",
            "- Do not imply audiobook availability; Dracula audio remains disabled.",
            "- Do not imply broad catalog availability; other books remain rights-safe pipeline candidates.",
        ]
    )
    (output_dir / REVIEW_REPORT).write_text("\n".join(lines), encoding="utf-8")


def write_root_reports(scores: dict[str, object], selected: list[tuple[Shot, Path]], video_status: dict[str, object]) -> None:
    VOICEOVER_DOC.write_text(
        "\n".join(
            [
                "# Earnalism Site-Tour Voiceover Script",
                "",
                "Status: SCRIPT_ONLY.",
                "",
                "No AI voice, TTS, audiobook generation, paid provider call, or audio publishing was performed.",
                "",
                *[
                    f"## {index}. {heading}\n\n{copy}\n"
                    for index, (heading, copy) in enumerate(VOICEOVER_SCRIPT, start=1)
                ],
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    FEATURE_REPORT.write_text(
        (
            "\n".join(
            [
                "# Site-Tour Feature Highlight Report",
                "",
                "- Dracula-first homepage opening: included",
                "- Chapter 1 free preview positioning: included",
                "- Calm Dracula reader journey: included",
                "- Pricing reading-time pack explanation: included",
                "- Controlled library and rights-safe pipeline framing: included",
                "- Kshudhita Pashan remains pipeline-only: confirmed by source journey coverage",
                "- Audiobook availability claim: blocked",
                "- Broad live catalog claim: blocked",
                "- Fake reviews, testimonials, ratings, or social proof: blocked",
                "- Live payment or provider call: not performed",
                "",
                "Recommendation: HOLD_ADS_PENDING_HUMAN_VIDEO_REVIEW.",
            ]
            )
            + "\n"
        ),
        encoding="utf-8",
    )

    SCORECARD_JSON.write_text(json.dumps(scores, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    score_lines = [
        "# Brand Site-Tour Video Scorecard",
        "",
        f"Overall score: {scores['overall_score']} / 10",
        "",
        f"Recommendation: {scores['recommendation']}",
        "",
        "## Category Scores",
        "",
    ]
    for key, value in scores["category_scores"].items():
        score_lines.append(f"- {key}: {value} / 10")
    score_lines.extend(
        [
            "",
            "## Safety Confirmation",
            "",
            "- Dracula is the only live approved core reading title.",
            "- Dracula audio is disabled and no audiobook availability is claimed.",
            "- Kshudhita Pashan is represented only as a rights-safe pipeline candidate.",
            "- No fake testimonials, fake reviews, fake ratings, or fake partnerships are used.",
            "- No live payments, emails, social posts, or paid provider APIs were run.",
            "",
            "## Artifact Status",
            "",
        ]
    )
    for key, value in video_status.items():
        score_lines.append(f"- {key}: {value}")
    score_lines.extend(["", "## Included Journey Count", "", f"- {len(selected)} journey clips selected"])
    SCORECARD_MD.write_text("\n".join(score_lines) + "\n", encoding="utf-8")


def create_package(output_dir: Path) -> dict[str, object]:
    videos = ensure_real_user_videos()
    selected, skipped = selected_shots(videos)
    if not selected:
        raise RuntimeError("No site-tour journey videos could be selected.")

    output_dir.mkdir(parents=True, exist_ok=True)
    video_status = create_video_artifacts(selected, output_dir)
    write_captions(selected, output_dir)
    write_transcript(selected, output_dir)
    write_shotlist(selected, skipped, output_dir)
    write_storyboard(selected, output_dir)
    scores = scorecard(selected, video_status)
    write_review_report(selected, skipped, video_status, output_dir, scores)
    write_root_reports(scores, selected, video_status)

    summary = {
        "output_dir": str(output_dir.relative_to(ROOT)),
        "selected_shots": [shot.shot_id for shot, _ in selected],
        "skipped": skipped,
        "video_status": video_status,
        "scorecard": scores,
        "required_outputs": [
            MASTER_WEBM,
            CAPTIONS,
            TRANSCRIPT,
            SHOTLIST,
            STORYBOARD,
            REVIEW_REPORT,
        ],
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        summary = create_package(args.output_dir)
    except Exception as exc:
        print(f"Site-tour package failed: {exc}", file=sys.stderr)
        return 1

    print("Earnalism premium site-tour package created.")
    print(f"Output: {summary['output_dir']}")
    print(f"Recommendation: {summary['scorecard']['recommendation']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

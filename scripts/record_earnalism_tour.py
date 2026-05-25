#!/usr/bin/env python3
"""Record and post-process a premium video tour of the Earnalism website."""

from __future__ import annotations

import random
import shutil
import sys
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://theearnalism.com"
OUTPUT_DIR = ROOT / "output"
VIDEO_DIR = OUTPUT_DIR / "playwright_video"
RAW_VIDEO = OUTPUT_DIR / "tour_raw.webm"
FINAL_VIDEO = OUTPUT_DIR / "earnalism_tour_final.mp4"
BACKGROUND_SCORE = ROOT / "assets" / "background_score.mp3"
VIEWPORT = {"width": 1920, "height": 1080}
SCROLL_STEP_PX = 80
SCROLL_SLEEP_MS = 30
NETWORKIDLE_TIMEOUT_MS = 15_000


def human_delay(page, min_seconds: float = 0.8, max_seconds: float = 1.8) -> None:
    page.wait_for_timeout(int(random.uniform(min_seconds, max_seconds) * 1000))


def wait_for_networkidle(page, label: str) -> None:
    try:
        page.wait_for_load_state("networkidle", timeout=NETWORKIDLE_TIMEOUT_MS)
    except PlaywrightTimeoutError:
        print(f"WARNING: {label} did not reach networkidle within 15s; proceeding.")


def goto(page, path: str, label: str) -> None:
    page.goto(f"{BASE_URL}{path}", wait_until="domcontentloaded", timeout=60_000)
    wait_for_networkidle(page, label)
    human_delay(page)


def wait_for_min_count(page, selector: str, minimum: int, label: str) -> None:
    try:
        page.wait_for_function(
            "([selector, minimum]) => document.querySelectorAll(selector).length >= minimum",
            arg=[selector, minimum],
            timeout=15_000,
        )
    except PlaywrightTimeoutError:
        print(f"WARNING: {label} did not fully load within 15s; proceeding.")


def wait_for_any(page, selectors: list[str], label: str) -> None:
    expression = " || ".join(f"document.querySelector({selector!r})" for selector in selectors)
    try:
        page.wait_for_function(f"() => Boolean({expression})", timeout=15_000)
    except PlaywrightTimeoutError:
        print(f"WARNING: {label} did not appear within 15s; proceeding.")


def smooth_scroll_by(page, pixels: float) -> None:
    remaining = int(round(pixels))
    if remaining == 0:
        return
    direction = 1 if remaining > 0 else -1
    while abs(remaining) > 0:
        delta = direction * min(SCROLL_STEP_PX, abs(remaining))
        page.evaluate("(dy) => window.scrollBy(0, dy)", delta)
        page.wait_for_timeout(SCROLL_SLEEP_MS)
        remaining -= delta


def smooth_scroll_to_top(page) -> None:
    current_y = page.evaluate("() => window.scrollY")
    smooth_scroll_by(page, -current_y)


def smooth_scroll_to_bottom(page) -> None:
    for _ in range(200):
        current_y, max_y = page.evaluate(
            "() => [window.scrollY, Math.max(0, document.documentElement.scrollHeight - window.innerHeight)]"
        )
        remaining = max_y - current_y
        if remaining <= 4:
            break
        smooth_scroll_by(page, min(560, remaining))
        page.wait_for_timeout(120)


def smooth_scroll_locator_into_view(page, locator, target_y: int = 300) -> None:
    try:
        locator.wait_for(state="visible", timeout=10_000)
    except PlaywrightTimeoutError:
        return

    for _ in range(30):
        box = locator.bounding_box()
        if not box:
            page.wait_for_timeout(100)
            continue
        bottom = box["y"] + box["height"]
        if 120 <= box["y"] <= 620 and bottom <= VIEWPORT["height"] - 80:
            return
        smooth_scroll_by(page, box["y"] - target_y)
        page.wait_for_timeout(80)


def hover_if_visible(page, locator, pause_ms: int = 1200) -> None:
    try:
        smooth_scroll_locator_into_view(page, locator)
        locator.hover(timeout=5_000)
        page.wait_for_timeout(pause_ms)
    except Exception as exc:
        print(f"WARNING: hover skipped: {exc}")


def tour_home_shelves(page, pause_ms: int = 2_000) -> None:
    goto(page, "/", "home")
    wait_for_min_count(page, '[data-testid^="category-card-"]', 9, "home shelf grid")
    shelves = page.locator('[data-testid^="category-card-"]')
    for index in range(min(9, shelves.count())):
        tile = shelves.nth(index)
        smooth_scroll_locator_into_view(page, tile)
        hover_if_visible(page, tile, pause_ms=pause_ms)
        human_delay(page, 0.8, 1.2)
    smooth_scroll_to_top(page)
    human_delay(page)


def choose_book_slug_with_chapters(page) -> str | None:
    try:
        return page.evaluate(
            """
            async () => {
              const api = "https://api.theearnalism.com/api";
              const books = await fetch(`${api}/books`).then((response) => response.json());
              for (const book of books.slice(0, 16)) {
                try {
                  const detail = await fetch(`${api}/books/${book.slug}`).then((response) => response.json());
                  if ((detail.chapters || []).length > 0) return book.slug;
                } catch (_) {}
              }
              return books[0]?.slug || null;
            }
            """
        )
    except Exception as exc:
        print(f"WARNING: could not choose a book with chapters: {exc}")
        return None


def tour_library(page) -> str | None:
    goto(page, "/library", "library")
    wait_for_any(
        page,
        ['[data-testid^="book-card-"]', '[data-testid="single-book-spotlight"]'],
        "library book cards",
    )

    cards = page.locator('[data-testid^="book-card-"]')
    hover_count = min(3, cards.count())
    for index in range(hover_count):
        hover_if_visible(page, cards.nth(index), pause_ms=1_500)
        human_delay(page)

    smooth_scroll_to_bottom(page)
    human_delay(page)

    chosen_slug = choose_book_slug_with_chapters(page)
    if chosen_slug:
        chosen = page.locator(f'[data-testid="book-card-{chosen_slug}"]').first
    else:
        chosen = cards.first

    hover_if_visible(page, chosen, pause_ms=2_000)
    return chosen_slug


def click_book_detail(page, preferred_slug: str | None) -> None:
    if preferred_slug:
        card = page.locator(f'[data-testid="book-card-{preferred_slug}"]').first
    else:
        card = page.locator('[data-testid^="book-card-"]').first

    smooth_scroll_locator_into_view(page, card)
    link = card.locator('a[href^="/book/"]').first
    try:
        if link.count() > 0:
            link.click(timeout=10_000)
        else:
            card.click(timeout=10_000)
    except Exception:
        page.locator('a[href^="/book/"]').first.click(timeout=10_000)
    wait_for_networkidle(page, "book detail")
    page.wait_for_selector('[data-testid="book-page"]', timeout=20_000)
    human_delay(page)


def tour_book_detail(page) -> None:
    top_cta = page.locator('[data-testid="start-reading"], [data-testid="read-preview"]').first
    hover_if_visible(page, top_cta, pause_ms=1_400)
    smooth_scroll_to_bottom(page)
    bottom_cta = page.locator(
        '[data-testid="bottom-buy-reading-time"], [data-testid="bottom-read-preview"], [data-testid="request-access"]'
    ).first
    hover_if_visible(page, bottom_cta, pause_ms=1_600)
    smooth_scroll_by(page, -420)
    human_delay(page)


def tour_journal(page) -> None:
    goto(page, "/journal", "journal")
    wait_for_any(page, ['[data-testid="journal-feature"]', '[data-testid^="journal-card-"]'], "journal cards")
    feature = page.locator('[data-testid="journal-feature"], [data-testid^="journal-card-"]').first
    hover_if_visible(page, feature, pause_ms=1_500)
    smooth_scroll_to_bottom(page)
    card = page.locator('[data-testid^="journal-card-"]').first
    hover_if_visible(page, card, pause_ms=1_600)
    human_delay(page)


def tour_about(page) -> None:
    goto(page, "/about", "about")
    page.wait_for_selector('[data-testid="about-page"]', timeout=15_000)
    smooth_scroll_to_bottom(page)
    human_delay(page)


def tour_sign_in(page) -> None:
    goto(page, "/signin", "sign in")
    wait_for_any(page, ['[data-testid="user-login-form"]', '[data-testid="user-login-page"]'], "sign in form")
    smooth_scroll_to_top(page)
    form = page.locator('[data-testid="user-login-form"], [data-testid="user-login-page"]').first
    hover_if_visible(page, form, pause_ms=1_800)


def final_home_return(page) -> None:
    goto(page, "/", "final home")
    wait_for_min_count(page, '[data-testid^="category-card-"]', 9, "final home shelf grid")
    shelves = page.locator('[data-testid^="category-card-"]')
    for index in range(min(9, shelves.count())):
        tile = shelves.nth(index)
        smooth_scroll_locator_into_view(page, tile)
        page.wait_for_timeout(700)
    smooth_scroll_to_top(page)
    logo = page.locator('[data-testid="brand-logo"]').first
    hover_if_visible(page, logo, pause_ms=2_000)


def move_saved_video(video_path: str | None) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if RAW_VIDEO.exists():
        RAW_VIDEO.unlink()

    source = Path(video_path) if video_path else None
    if not source or not source.exists():
        candidates = sorted(VIDEO_DIR.glob("*.webm"), key=lambda path: path.stat().st_mtime, reverse=True)
        source = candidates[0] if candidates else None
    if not source or not source.exists():
        raise FileNotFoundError("Playwright did not produce a .webm recording.")

    shutil.move(str(source), RAW_VIDEO)
    return RAW_VIDEO


def record_tour() -> Path:
    """Run the Playwright site tour and save ./output/tour_raw.webm."""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if VIDEO_DIR.exists():
        shutil.rmtree(VIDEO_DIR)
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)

    page = None
    context = None
    browser = None
    video_path: str | None = None
    tour_error: Exception | None = None

    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(headless=False)
            context = browser.new_context(
                viewport=VIEWPORT,
                record_video_dir=str(VIDEO_DIR),
                record_video_size=VIEWPORT,
                device_scale_factor=1,
            )
            page = context.new_page()
            page.set_default_timeout(20_000)

            tour_home_shelves(page, pause_ms=2_000)
            chosen_slug = tour_library(page)
            click_book_detail(page, chosen_slug)
            tour_book_detail(page)
            tour_journal(page)
            tour_about(page)
            tour_sign_in(page)
            final_home_return(page)
        except Exception as exc:
            tour_error = exc
            print(f"WARNING: Tour step failed; closing browser to preserve raw video: {exc}")
        finally:
            if page and page.video:
                try:
                    video_path = page.video.path()
                except Exception:
                    video_path = None
            if context:
                context.close()
            if browser:
                browser.close()

    raw_path = move_saved_video(video_path)
    print(f"Saved raw recording: {raw_path}")
    if tour_error:
        print("WARNING: Raw recording was saved after a tour interruption; post-processing will still run.")
    return raw_path


def _load_moviepy():
    try:
        from moviepy.editor import AudioFileClip, VideoFileClip, afx, vfx
    except ImportError as exc:
        raise RuntimeError(
            "MoviePy is required for post_process(). Install with: pip install 'moviepy>=1.0.3' mutagen"
        ) from exc
    return AudioFileClip, VideoFileClip, afx, vfx


def post_process() -> Path:
    """Convert the raw tour to a YouTube-ready MP4 with optional background score."""

    if not RAW_VIDEO.exists():
        raise FileNotFoundError(f"Raw recording missing: {RAW_VIDEO}")

    AudioFileClip, VideoFileClip, afx, vfx = _load_moviepy()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    video = VideoFileClip(str(RAW_VIDEO))
    audio = None
    processed = None
    try:
        processed = video.fx(vfx.fadein, 1.5).fx(vfx.fadeout, 1.5)

        if BACKGROUND_SCORE.exists():
            try:
                from mutagen.mp3 import MP3

                duration = MP3(str(BACKGROUND_SCORE)).info.length
                print(f"Background score detected: {BACKGROUND_SCORE} ({duration:.2f}s)")
            except Exception as exc:
                print(f"WARNING: Could not inspect MP3 duration with mutagen: {exc}")

            audio = AudioFileClip(str(BACKGROUND_SCORE))
            looped_audio = afx.audio_loop(audio, duration=processed.duration)
            looped_audio = looped_audio.volumex(0.4).audio_fadein(3).audio_fadeout(3)
            processed = processed.set_audio(looped_audio)
        else:
            print("Place your background score MP3 at ./assets/background_score.mp3 and re-run post_process()")

        if FINAL_VIDEO.exists():
            FINAL_VIDEO.unlink()
        processed.write_videofile(
            str(FINAL_VIDEO),
            fps=30,
            codec="libx264",
            audio_codec="aac",
            bitrate="8000k",
            preset="medium",
            threads=4,
        )
    finally:
        if processed:
            processed.close()
        if audio:
            audio.close()
        video.close()

    print(f"Saved final tour video: {FINAL_VIDEO}")
    return FINAL_VIDEO


if __name__ == "__main__":
    record_tour()
    post_process()

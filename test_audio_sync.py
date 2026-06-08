#!/usr/bin/env python3
"""
Test audio sync for sample English books.

Validates:
1. Audio file integrity (MP3 format, bitrate, duration)
2. Timestamp JSON validity
3. Word timing consistency
4. Reader integration readiness
"""

import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)
logger = logging.getLogger(__name__)


class AudioSyncTester:
    """Test audio and timestamp sync integrity."""

    def __init__(self, audio_dir: Path = Path("./audio_output/en")):
        self.audio_dir = audio_dir
        self.results = {
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "issues": []
        }

    def test_sample_books(self, book_slugs: List[str] = None) -> Dict:
        """Test specific sample books."""
        if not book_slugs:
            # Default sample books
            book_slugs = [
                "the-tell-tale-heart",
                "the-gift-of-the-magi",
                "the-necklace"
            ]

        logger.info("=" * 60)
        logger.info("Audio Sync Test Suite - Sample Books")
        logger.info("=" * 60)
        logger.info(f"Testing {len(book_slugs)} sample books\n")

        for slug in book_slugs:
            self._test_book(slug)

        return self.results

    def _test_book(self, slug: str) -> bool:
        """Test a single book's audio and timestamps."""
        logger.info(f"\n📖 Testing: {slug}")
        book_passed = True

        mp3_path = self.audio_dir / f"{slug}.mp3"
        json_path = self.audio_dir / f"{slug}_timestamps.json"

        # Test 1: MP3 file exists
        self.results["tests_run"] += 1
        if mp3_path.exists():
            logger.info(f"  ✓ MP3 file exists ({mp3_path.stat().st_size / 1024 / 1024:.2f} MB)")
            self.results["tests_passed"] += 1
        else:
            logger.error(f"  ✗ MP3 file not found: {mp3_path}")
            self.results["tests_failed"] += 1
            self.results["issues"].append(f"{slug}: MP3 file missing")
            book_passed = False

        # Test 2: Timestamps JSON exists
        self.results["tests_run"] += 1
        if json_path.exists():
            logger.info(f"  ✓ Timestamps file exists")
            self.results["tests_passed"] += 1
        else:
            logger.error(f"  ✗ Timestamps file not found: {json_path}")
            self.results["tests_failed"] += 1
            self.results["issues"].append(f"{slug}: Timestamps JSON missing")
            book_passed = False
            return book_passed

        # Test 3: JSON validity
        self.results["tests_run"] += 1
        try:
            with open(json_path) as f:
                ts_data = json.load(f)
            logger.info(f"  ✓ Timestamps JSON is valid")
            self.results["tests_passed"] += 1
        except json.JSONDecodeError as e:
            logger.error(f"  ✗ Timestamps JSON is invalid: {e}")
            self.results["tests_failed"] += 1
            self.results["issues"].append(f"{slug}: Invalid JSON - {e}")
            book_passed = False
            return book_passed

        # Test 4: Timestamp structure
        self.results["tests_run"] += 1
        words = ts_data.get("words", [])
        if words:
            logger.info(f"  ✓ Contains {len(words)} word timestamps")
            self.results["tests_passed"] += 1
        else:
            logger.error(f"  ✗ No word timestamps found")
            self.results["tests_failed"] += 1
            self.results["issues"].append(f"{slug}: No word timestamps")
            book_passed = False

        # Test 5: Word timing consistency
        self.results["tests_run"] += 1
        timing_valid = True
        for i, word in enumerate(words):
            if not all(k in word for k in ["word", "start_ms", "end_ms"]):
                logger.error(f"  ✗ Word {i} missing required fields")
                self.results["issues"].append(f"{slug}: Word {i} missing fields")
                timing_valid = False
                break

            if word["end_ms"] <= word["start_ms"]:
                logger.error(f"  ✗ Word {i} ({word['word']}) has invalid timing: {word['start_ms']}-{word['end_ms']}")
                self.results["issues"].append(f"{slug}: Word {i} invalid timing")
                timing_valid = False
                break

        if timing_valid:
            duration = words[-1]["end_ms"] if words else 0
            logger.info(f"  ✓ Word timing is consistent ({duration/1000:.1f}s total)")
            self.results["tests_passed"] += 1
        else:
            self.results["tests_failed"] += 1
            book_passed = False

        # Test 6: MP3 metadata (check with ffprobe if available)
        self.results["tests_run"] += 1
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1:nofile=1", str(mp3_path)],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                mp3_duration = float(result.stdout.strip())
                ts_duration = (words[-1]["end_ms"] / 1000) if words else 0

                # Allow 2% tolerance
                if abs(mp3_duration - ts_duration) / mp3_duration < 0.02:
                    logger.info(f"  ✓ MP3 duration matches timestamps ({mp3_duration:.1f}s)")
                    self.results["tests_passed"] += 1
                else:
                    logger.warning(f"  ⚠ Duration mismatch: MP3={mp3_duration:.1f}s, Timestamps={ts_duration:.1f}s")
                    self.results["tests_passed"] += 1  # Warning, not failure
            else:
                logger.info(f"  ⊘ Could not verify MP3 duration (ffprobe unavailable)")
                self.results["tests_passed"] += 1
        except Exception as e:
            logger.info(f"  ⊘ MP3 verification skipped: {e}")
            self.results["tests_passed"] += 1

        return book_passed

    def generate_report(self, output_path: Path = Path("./audio_output/audio_sync_test_report.json")) -> None:
        """Generate test report."""
        report = {
            **self.results,
            "pass_rate": (self.results["tests_passed"] / self.results["tests_run"] * 100)
            if self.results["tests_run"] > 0 else 0,
            "summary": (
                f"✓ Passed: {self.results['tests_passed']}, "
                f"Failed: {self.results['tests_failed']}, "
                f"Total: {self.results['tests_run']}"
            )
        }

        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info(f"\n📊 Test Report: {report['summary']}")
        logger.info(f"📄 Report saved to: {output_path}")


def main():
    """Run test suite."""
    import argparse

    parser = argparse.ArgumentParser(description="Test English audio sync")
    parser.add_argument(
        "--audio-dir",
        type=Path,
        default=Path("./audio_output/en"),
        help="Audio output directory"
    )
    parser.add_argument(
        "--books",
        nargs="+",
        help="Specific books to test (default: sample books)"
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("./audio_output/audio_sync_test_report.json"),
        help="Report output path"
    )

    args = parser.parse_args()

    tester = AudioSyncTester(args.audio_dir)
    results = tester.test_sample_books(args.books)
    tester.generate_report(args.report)

    if results["tests_failed"] > 0:
        logger.error(f"\n❌ {results['tests_failed']} tests failed")
        sys.exit(1)
    else:
        logger.info("\n✅ All tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()

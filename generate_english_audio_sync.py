#!/usr/bin/env python3
"""
Generate and sync English audiobooks with highlight timestamps.

This script:
1. Filters for English draft books from the manifest
2. Generates audio using Google Cloud TTS Neural2 voice (en-IN-Neural2-B)
   with emotional expression: rate -8%, pitch -1%
3. Captures word-level timestamps using SSML marks
4. Generates timestamps JSON for reader sync
5. Validates sync output
"""

import json
import logging
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)
logger = logging.getLogger(__name__)

def load_manifest(manifest_path):
    """Load the book import manifest."""
    with open(manifest_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_english_draft_books(manifest):
    """Filter for English books in draft state."""
    books = []
    for book in manifest['books']:
        if (book.get('language') == 'en' and
            book.get('availability') == 'draft' and
            book.get('audioallowed', True)):
            books.append(book)
    return books

def generate_english_audio(manifest_path, output_dir="./audio_output"):
    """Generate audio for English books using the main script with proper filtering."""

    # Load manifest
    manifest = load_manifest(manifest_path)
    en_books = get_english_draft_books(manifest)

    logger.info(f"Found {len(en_books)} English draft books to process")

    if not en_books:
        logger.warning("No English draft books found")
        return

    # Print first few books to verify
    logger.info("Processing English books:")
    for book in en_books[:5]:
        logger.info(f"  - {book['id']}: {book['title']} by {book['author']}")
    if len(en_books) > 5:
        logger.info(f"  ... and {len(en_books) - 5} more")

    # Prepare output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True, parents=True)

    # Setup environment for Google Cloud TTS
    google_creds = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    if not google_creds:
        logger.error("GOOGLE_APPLICATION_CREDENTIALS environment variable not set")
        return False

    # Run the main generate_audio.py script with English filter
    cmd = [
        "python3",
        "generate_audio.py",
        "--manifest", manifest_path,
        "--lang", "en",
        "--output-dir", output_dir,
        "--voice-tier", "neural2"
    ]

    logger.info(f"Running: {' '.join(cmd)}")
    logger.info("Voice settings: Google Neural2 (en-IN-Neural2-B), rate: -8%, pitch: -1%")
    logger.info("This will generate emotional, expressive English audiobooks with word-level sync")

    try:
        result = subprocess.run(cmd, check=True)
        logger.info("Audio generation completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Audio generation failed: {e}")
        return False

def verify_generated_files(output_dir, manifest_path):
    """Verify that audio and timestamp files were generated."""
    manifest = load_manifest(manifest_path)
    en_books = get_english_draft_books(manifest)

    audio_dir = Path(output_dir) / "en"
    generated = 0
    missing = []

    for book in en_books:
        slug = book['id'].lower()
        audio_file = audio_dir / f"{slug}.mp3"
        timestamps_file = audio_dir / f"{slug}_timestamps.json"

        if audio_file.exists() and timestamps_file.exists():
            generated += 1
        else:
            missing.append({
                'id': book['id'],
                'title': book['title'],
                'audio_exists': audio_file.exists(),
                'timestamps_exists': timestamps_file.exists()
            })

    logger.info(f"\n=== Generation Report ===")
    logger.info(f"Total English draft books: {len(en_books)}")
    logger.info(f"Successfully generated: {generated}")
    logger.info(f"Missing files: {len(missing)}")

    if missing:
        logger.warning("Missing files:")
        for item in missing[:10]:
            logger.warning(f"  - {item['id']}: {item['title']}")
            if not item['audio_exists']:
                logger.warning(f"    Missing audio file")
            if not item['timestamps_exists']:
                logger.warning(f"    Missing timestamps")
        if len(missing) > 10:
            logger.warning(f"  ... and {len(missing) - 10} more")

    return generated, len(en_books)

def create_sync_report(output_dir, manifest_path):
    """Create a report showing sync readiness for the reader."""
    manifest = load_manifest(manifest_path)
    en_books = get_english_draft_books(manifest)

    audio_dir = Path(output_dir) / "en"
    report = {
        "generated_at": datetime.now().isoformat(),
        "total_english_books": len(en_books),
        "books_with_audio": [],
        "voice_settings": {
            "provider": "Google Cloud TTS",
            "voice": "en-IN-Neural2-B",
            "rate": "-8%",
            "pitch": "-1%",
            "characteristics": ["emotional expression", "voice clarity", "intensity adjustment"]
        }
    }

    for book in en_books:
        slug = book['id'].lower()
        audio_file = audio_dir / f"{slug}.mp3"
        timestamps_file = audio_dir / f"{slug}_timestamps.json"

        if audio_file.exists() and timestamps_file.exists():
            report["books_with_audio"].append({
                "id": book['id'],
                "slug": slug,
                "title": book['title'],
                "author": book['author'],
                "audio_ready": True,
                "sync_ready": True,
                "audio_file": str(audio_file),
                "timestamps_file": str(timestamps_file)
            })

    report_path = Path(output_dir) / "english_audio_sync_report.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    logger.info(f"\nSync report saved to: {report_path}")
    logger.info(f"Books ready for sync: {len(report['books_with_audio'])}")

    return report

def main():
    """Main execution."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate and sync English audiobooks with highlights"
    )
    parser.add_argument(
        "--manifest",
        required=True,
        help="Path to book_import_manifest.json"
    )
    parser.add_argument(
        "--output-dir",
        default="./audio_output",
        help="Output directory for audio files"
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify existing files without generating"
    )

    args = parser.parse_args()

    if not os.path.exists(args.manifest):
        logger.error(f"Manifest not found: {args.manifest}")
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("Earnalism English Audio Generation & Sync Pipeline")
    logger.info("=" * 60)

    if args.verify_only:
        logger.info("Verification mode - checking existing files")
        generated, total = verify_generated_files(args.output_dir, args.manifest)
        create_sync_report(args.output_dir, args.manifest)
    else:
        # Generate audio
        success = generate_english_audio(args.manifest, args.output_dir)

        if success:
            # Verify and create sync report
            generated, total = verify_generated_files(args.output_dir, args.manifest)
            report = create_sync_report(args.output_dir, args.manifest)

            logger.info(f"\n✓ Pipeline complete: {generated}/{total} books ready for reader sync")
        else:
            logger.error("Audio generation failed")
            sys.exit(1)

if __name__ == "__main__":
    main()

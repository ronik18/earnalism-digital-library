#!/usr/bin/env python3
"""
Deploy English audiobooks to Cloudinary CDN with sync capability.

Uploads all generated MP3 and timestamp JSON files to Cloudinary,
generates public URLs for frontend integration, and creates a deployment manifest.
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)
logger = logging.getLogger(__name__)


def init_cloudinary() -> bool:
    """Initialize Cloudinary with environment credentials."""
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
    api_key = os.getenv("CLOUDINARY_API_KEY")
    api_secret = os.getenv("CLOUDINARY_API_SECRET")

    if not all([cloud_name, api_key, api_secret]):
        logger.error("Missing Cloudinary credentials in environment")
        return False

    cloudinary.config(
        cloud_name=cloud_name,
        api_key=api_key,
        api_secret=api_secret,
        secure=True,
    )
    logger.info(f"Cloudinary initialized: {cloud_name}")
    return True


def upload_audio_file(
    file_path: Path,
    folder: str = "earnalism/audio/en",
    public_id: Optional[str] = None
) -> Optional[Dict]:
    """Upload MP3 or JSON file to Cloudinary."""
    try:
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return None

        resource_type = "raw" if file_path.suffix == ".json" else "video"

        result = cloudinary.uploader.upload(
            str(file_path),
            folder=folder,
            public_id=public_id or file_path.stem,
            resource_type=resource_type,
            overwrite=True,
            tags=["english-audio", "earnalism-sync"],
        )

        return {
            "public_id": result.get("public_id"),
            "url": result.get("secure_url"),
            "file_size": result.get("bytes"),
            "format": result.get("format"),
        }
    except Exception as e:
        logger.error(f"Upload failed for {file_path}: {e}")
        return None


def deploy_english_audio(
    audio_dir: Path = Path("./audio_output/en"),
    manifest_path: Path = Path("./book_import_manifest.json")
) -> Dict:
    """Deploy all English audio files to Cloudinary."""

    if not init_cloudinary():
        sys.exit(1)

    # Load manifest to match book IDs with slugs
    with open(manifest_path) as f:
        manifest = json.load(f)

    en_books = {
        b['id'].lower(): b for b in manifest['books']
        if b.get('language') == 'en'
    }

    deployment = {
        "deployed_at": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat(),
        "cdn": "cloudinary",
        "total_files": 0,
        "successfully_deployed": 0,
        "failed": [],
        "books": []
    }

    # Deploy MP3 files
    mp3_files = sorted(audio_dir.glob("*.mp3"))
    logger.info(f"Found {len(mp3_files)} MP3 files to deploy")

    for mp3_path in mp3_files:
        slug = mp3_path.stem
        book_id = f"en-{slug.split('-')[0]}" if slug.startswith("en-") else f"en-{slug}"

        deployment["total_files"] += 1

        logger.info(f"Uploading: {slug}.mp3")
        result = upload_audio_file(
            mp3_path,
            public_id=f"audio/en/{slug}"
        )

        if result:
            deployment["successfully_deployed"] += 1

            # Also upload corresponding timestamps
            timestamps_path = audio_dir / f"{slug}_timestamps.json"
            if timestamps_path.exists():
                deployment["total_files"] += 1
                logger.info(f"Uploading: {slug}_timestamps.json")
                ts_result = upload_audio_file(
                    timestamps_path,
                    public_id=f"audio/en/{slug}_timestamps"
                )

                if ts_result:
                    deployment["successfully_deployed"] += 1

            # Get book info
            book_info = en_books.get(slug, {})
            deployment["books"].append({
                "slug": slug,
                "title": book_info.get("title", "Unknown"),
                "author": book_info.get("author", "Unknown"),
                "audio_url": result["url"],
                "timestamps_url": ts_result["url"] if ts_result else None,
                "file_size_bytes": result.get("file_size", 0),
            })
        else:
            deployment["failed"].append(slug)

    return deployment


def generate_deployment_manifest(
    deployment: Dict,
    output_path: Path = Path("./audio_output/cloudinary_deployment_manifest.json")
) -> None:
    """Save deployment manifest with CDN URLs."""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(deployment, f, indent=2, ensure_ascii=False)

    logger.info(f"Deployment manifest saved: {output_path}")
    logger.info(f"Successfully deployed: {deployment['successfully_deployed']}/{deployment['total_files']}")


def create_frontend_config(
    deployment: Dict,
    output_path: Path = Path("./frontend/src/config/audioSyncConfig.json")
) -> None:
    """Create frontend configuration for audio sync."""

    config = {
        "cdn": "cloudinary",
        "audioBase": "https://res.cloudinary.com/earnalism/video/upload",
        "timestampsBase": "https://res.cloudinary.com/earnalism/raw/upload",
        "books": {
            book["slug"]: {
                "title": book["title"],
                "author": book["author"],
                "audio": book["audio_url"],
                "timestamps": book["timestamps_url"],
            }
            for book in deployment.get("books", [])
        }
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    logger.info(f"Frontend config created: {output_path}")


def main():
    """Execute deployment pipeline."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Deploy English audio to Cloudinary CDN"
    )
    parser.add_argument(
        "--audio-dir",
        type=Path,
        default=Path("./audio_output/en"),
        help="Audio output directory"
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("./book_import_manifest.json"),
        help="Book manifest path"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deployed without uploading"
    )

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Earnalism English Audio CDN Deployment")
    logger.info("=" * 60)

    if args.dry_run:
        logger.info("DRY RUN MODE - No files will be uploaded")
        audio_files = list(args.audio_dir.glob("*.mp3"))
        logger.info(f"Would deploy {len(audio_files)} MP3 files")
        for f in audio_files[:5]:
            logger.info(f"  - {f.name}")
        if len(audio_files) > 5:
            logger.info(f"  ... and {len(audio_files) - 5} more")
    else:
        # Execute deployment
        deployment = deploy_english_audio(args.audio_dir, args.manifest)
        generate_deployment_manifest(deployment)
        create_frontend_config(deployment)

        logger.info("\n✓ Deployment complete")
        logger.info(f"Total files deployed: {deployment['successfully_deployed']}")
        if deployment['failed']:
            logger.warning(f"Failed deployments: {deployment['failed']}")


if __name__ == "__main__":
    main()

from __future__ import annotations

import json
from pathlib import Path

from backend import catalog_truth
from scripts import generate_social_brand_assets
from scripts.validate_social_links import validate_social_url


ROOT = Path(__file__).resolve().parents[2]


def read_json(relative_path: str):
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_social_brand_config_is_dracula_first():
    brand = read_json("data/social_brand/earnalism_social_brand.json")

    assert brand["brand_name"] == "The Earnalism"
    assert brand["display_name"] == "The Earnalism Digital Library"
    assert brand["primary_handle"] == "theearnalism"
    assert brand["live_title"]["slug"] == "dracula"
    assert brand["live_title"]["title"] == "Dracula"
    assert brand["live_title"]["audio_status"] == "DISABLED"
    assert "Chapter 1 is free" in brand["approved_claims"]
    assert "Bengali Gothic coming through rights-safe pipeline" in brand["approved_claims"]


def test_social_brand_config_does_not_imply_broad_live_catalog():
    brand = read_json("data/social_brand/earnalism_social_brand.json")
    profiles = read_json("data/social_brand/platform_profiles.json")
    rendered = json.dumps({"brand": brand, "profiles": profiles}, ensure_ascii=False).lower()

    assert "100+ live books" not in brand["short_bio"]
    assert "100+ live books" in brand["forbidden_claims"]
    assert "full audiobook available" in brand["forbidden_claims"]
    assert "human narrated unless proven" in brand["forbidden_claims"]
    assert "no ai touch unless proven" in rendered
    assert "full catalog live" in rendered
    assert "listen now" in rendered
    assert "broad live catalog" not in rendered


def test_platform_profiles_exist_for_all_supported_platforms():
    profiles = read_json("data/social_brand/platform_profiles.json")["platforms"]
    platforms = {profile["platform"] for profile in profiles}

    assert platforms == {
        "Instagram",
        "YouTube",
        "LinkedIn",
        "Facebook",
        "X",
        "WhatsApp Channel",
        "Telegram",
    }
    assert all(profile["website_link"] == "https://theearnalism.com/book/dracula" for profile in profiles)
    assert all(profile["manual_setup_checklist"] for profile in profiles)


def test_generated_asset_manifest_includes_required_social_assets():
    manifest = read_json("data/social_brand/asset_manifest.json")
    filenames = {asset["filename"] for asset in manifest["assets"]}

    assert "avatar-master.svg" in filenames
    assert "avatar-square.svg" in filenames
    assert "youtube-banner.svg" in filenames
    assert "linkedin-cover.svg" in filenames
    assert "facebook-cover.svg" in filenames
    assert "x-header.svg" in filenames
    assert "first-post-dracula.svg" in filenames
    assert "pinned-post-return-to-reading.svg" in filenames
    assert "dracula-launch-card.svg" in filenames
    assert "bengali-gothic-coming-card.svg" in filenames
    assert manifest["upload_policy"] == "OWNER_UPLOAD_REQUIRED"


def test_social_link_validator_rejects_empty_hash_and_javascript_urls():
    assert validate_social_url("REACT_APP_INSTAGRAM_URL", "")["status"] == "MISSING_OPERATOR_REQUIRED"
    assert validate_social_url("REACT_APP_INSTAGRAM_URL", "#")["status"] == "INVALID"
    assert validate_social_url("REACT_APP_INSTAGRAM_URL", "javascript:alert(1)")["status"] == "INVALID"


def test_social_link_validator_accepts_valid_https_platform_url():
    result = validate_social_url("REACT_APP_INSTAGRAM_URL", "https://www.instagram.com/theearnalism")

    assert result["status"] == "VALID"
    assert result["issues"] == []


def test_social_link_validator_rejects_placeholder_and_wrong_domain():
    placeholder = validate_social_url("REACT_APP_YOUTUBE_URL", "https://youtube.com/your-handle")
    wrong_domain = validate_social_url("REACT_APP_YOUTUBE_URL", "https://example.com/theearnalism")

    assert placeholder["status"] == "INVALID"
    assert wrong_domain["status"] == "INVALID"


def test_scorecard_caps_when_no_real_social_links_exist():
    scorecard = read_json("SOCIAL_PROFILE_REVAMP_SCORECARD.json")

    assert scorecard["status"] == "READY_FOR_MANUAL_SOCIAL_PROFILE_SETUP"
    assert scorecard["recommendation"] == "NOT_READY_FOR_PAID_SOCIAL_ADS"
    assert scorecard["score"] <= 8.5
    assert any(cap["rule"] == "no real social links configured" and cap["applies"] for cap in scorecard["caps"])


def test_scorecard_caps_fake_claims():
    brand = read_json("data/social_brand/earnalism_social_brand.json")
    brand["long_bio"] = brand["long_bio"] + " 100+ live books."
    card = generate_social_brand_assets.scorecard(brand, [{"filename": "avatar-master.svg"}])

    assert card["score"] <= 5.0
    assert "100+ live books" in card["forbidden_claims_detected_outside_policy"]


def test_no_auto_posting_command_or_social_api_credentials_exist():
    package_json = read_json("package.json")
    scripts = package_json["scripts"]
    joined_scripts = json.dumps(scripts).lower()
    new_script_sources = (
        read_text("scripts/generate_social_brand_assets.py")
        + read_text("scripts/validate_social_links.py")
        + read_text("data/social_brand/pinned_posts.json")
    ).lower()

    assert "social:post" not in scripts
    assert "social:publish" not in scripts
    assert "graph.facebook.com" not in joined_scripts
    assert "api.twitter.com" not in joined_scripts
    assert "instagram_basic" not in new_script_sources
    assert "access_token" not in new_script_sources
    assert "client_secret" not in new_script_sources
    assert "api_key" not in new_script_sources


def test_dracula_remains_only_live_approved_reading_title():
    assert catalog_truth.CONTROLLED_LIVE_BOOK_SLUGS == ("dracula",)
    assert catalog_truth.AUDIO_ENABLED_SLUGS == set()
    assert catalog_truth.PIPELINE_CANDIDATE_SLUGS == {"kshudhita-pashan"}

    artifact = catalog_truth.load_dracula_artifact_book(include_content=False)
    assert artifact is not None
    projected = catalog_truth.public_book_projection(artifact)
    assert projected["slug"] == "dracula"
    assert projected["reader_enabled"] is True
    assert projected["audio_enabled"] is False


def test_footer_social_links_render_only_configured_urls():
    social_links = read_text("frontend/src/config/socialLinks.js")
    footer_social = read_text("frontend/src/components/FooterSocialLinks.jsx")
    footer = read_text("frontend/src/components/Footer.jsx")

    assert "REACT_APP_INSTAGRAM_URL" in social_links
    assert "REACT_APP_WHATSAPP_CHANNEL_URL" in social_links
    assert "REACT_APP_TELEGRAM_CHANNEL_URL" in social_links
    assert "trimmed === \"#\"" in social_links
    assert "[\"http:\", \"https:\"]" in social_links
    assert "if (!enabledLinks.length) return null" in footer_social
    assert "target=\"_blank\"" in footer_social
    assert "rel=\"noopener noreferrer\"" in footer_social
    assert "aria-label={link.ariaLabel}" in footer_social
    assert "href=\"#\"" not in footer_social
    assert "href=\"\"" not in footer_social
    assert "mailto:${CONTACT_EMAIL}" in footer
    assert footer.index("<FooterSocialLinks />") > footer.index("mailto:${CONTACT_EMAIL}")

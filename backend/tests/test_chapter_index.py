import json
import hashlib
from copy import deepcopy
from pathlib import Path

import pytest

from backend.domain.chapter_index import (
    CHAPTER_INDEX_CONTRACT_VERSION,
    build_chapter_index_entries,
    chapter_index_entry,
    normalize_chapter_display_title,
)


ROOT = Path(__file__).resolve().parents[2]
CONTROLLED_ROOT = ROOT / "backend" / "data" / "controlled_publications"
INVENTORY_PATH = Path(__file__).parent / "fixtures" / "controlled-package-inventory.v1.json"


def assert_controlled_inventory(actual, inventory):
    """Check a frozen engineering baseline; this does not certify book contents."""
    packages = inventory["packages"]
    expected = {package["package_key"]: package for package in packages}
    assert len(expected) == len(packages) == inventory["expected_manifest_count"]
    assert sum(package["chapter_count"] for package in packages) == inventory["expected_chapter_count"]
    assert set(actual) == set(expected), {
        "missing": sorted(set(expected) - set(actual)),
        "unexpected": sorted(set(actual) - set(expected)),
    }
    for key, package in expected.items():
        expected_chapters = package["chapters"]
        assert len(expected_chapters) == package["chapter_count"], key
        assert len({chapter["id"] for chapter in expected_chapters}) == len(expected_chapters), key
        manifest = actual[key]
        assert manifest.get("slug") == package["manifest_slug"], key
        assert manifest.get("chapter_count") == package["chapter_count"], key
        actual_chapters = [
            {"id": chapter.get("id"), "order": chapter.get("order")}
            for chapter in manifest.get("chapters", [])
        ]
        assert actual_chapters == expected_chapters, key


def test_dracula_titles_have_one_normalized_structural_label():
    assert normalize_chapter_display_title(
        "CHAPTER II. JONATHAN HARKER’S JOURNAL-- continued"
    ) == "Chapter 2. Jonathan Harker’s Journal"
    entry = chapter_index_entry(
        {"id": "chapter-002", "title": "CHAPTER II. JONATHAN HARKER’S JOURNAL-- continued"},
        position=2,
        total=27,
    )
    assert entry["index_sequence_label"] == "02"
    assert entry["index_secondary_label"] == "Chapter 2"
    assert entry["index_title"] == "Jonathan Harker’s Journal"


def test_unsubtitled_and_non_english_units_remain_meaningful():
    assert chapter_index_entry(
        {"title": "CHAPTER V"}, position=5, total=27
    )["index_title"] == "Chapter 5"
    assert chapter_index_entry(
        {"title": "প্রথম পরিচ্ছেদ"}, position=1, total=4
    )["index_title"] == "প্রথম পরিচ্ছেদ"


def test_dracula_index_is_uniform_and_publisher_catalog_is_not_reader_content():
    artifact_roots = (
        ROOT / "backend" / "data" / "controlled_publications" / "dracula",
        ROOT / "data" / "controlled_publications" / "dracula",
    )
    expected_titles = [
        "CHAPTER I. JONATHAN HARKER’S JOURNAL",
        "CHAPTER II. JONATHAN HARKER’S JOURNAL-- continued",
        "CHAPTER III. JONATHAN HARKER’S JOURNAL-- continued",
        "CHAPTER IV. JONATHAN HARKER’S JOURNAL-- continued",
        "CHAPTER V. MINA MURRAY’S CORRESPONDENCE",
        "CHAPTER VI. MINA MURRAY’S JOURNAL",
        "CHAPTER VII. CUTTING FROM “THE DAILYGRAPH,” 8 AUGUST",
        "CHAPTER VIII. MINA MURRAY’S JOURNAL",
        "CHAPTER IX. MINA HARKER’S CORRESPONDENCE",
        "CHAPTER X. DR. SEWARD’S DIARY",
        "CHAPTER XI. LUCY WESTENRA’S DIARY",
        "CHAPTER XII. DR. SEWARD’S DIARY",
        "CHAPTER XIII. DR. SEWARD’S DIARY",
        "CHAPTER XIV. MINA HARKER’S JOURNAL",
        "CHAPTER XV. DR. SEWARD’S DIARY",
        "CHAPTER XVI. DR. SEWARD’S DIARY-- continued",
        "CHAPTER XVII. DR. SEWARD’S DIARY-- continued",
        "CHAPTER XVIII. DR. SEWARD’S DIARY",
        "CHAPTER XIX. JONATHAN HARKER’S JOURNAL",
        "CHAPTER XX. JONATHAN HARKER’S JOURNAL",
        "CHAPTER XXI. DR. SEWARD’S DIARY",
        "CHAPTER XXII. JONATHAN HARKER’S JOURNAL",
        "CHAPTER XXIII. DR. SEWARD’S DIARY",
        "CHAPTER XXIV. DR. SEWARD’S PHONOGRAPH DIARY, SPOKEN BY VAN HELSING",
        "CHAPTER XXV. DR. SEWARD’S DIARY",
        "CHAPTER XXVI. DR. SEWARD’S DIARY",
        "CHAPTER XXVII. MINA HARKER’S JOURNAL",
    ]

    for artifact_root in artifact_roots:
        manifest = json.loads((artifact_root / "reader_manifest.json").read_text(encoding="utf-8"))
        narrative = manifest["chapters"]
        # Both current mirrors restore Stoker's literary prefatory note;
        # the 27 historical narrative IDs/titles remain unchanged.
        assert narrative[0]["id"] == "chapter-000"
        assert narrative[0]["title"] == "Preface"
        assert len(narrative) == 28
        preface = json.loads((artifact_root / "chapters/chapter-000.json").read_text())
        assert "All needless matters have been eliminated" in preface["content"]
        assert hashlib.sha256((artifact_root / "chapters/chapter-000.json").read_bytes()).hexdigest() == "0379e9cb8ef91acbdad8ad7dc134b38940ffd9fead72d634b44623bec20ed39c"
        assert hashlib.sha256((artifact_root / "reader_manifest.json").read_bytes()).hexdigest() == "f51512441063fa5b19c8af4e6cb1130c9eda98897a242163416ec09fc321068d"
        source = json.loads((artifact_root / "source_evidence.json").read_text())
        assert source["source_hash"] == "96cd16eacdbfebae8fdda5591f66e0cc8ee76be18e0cd1aca02bc00615782d28"
        assert [chapter["id"] for chapter in narrative] == ["chapter-000"] + [f"chapter-{index:03d}" for index in range(1, 28)]
        assert [chapter["order"] for chapter in narrative] == list(range(1, 29))
        narrative = narrative[1:]
        assert [chapter["title"] for chapter in narrative] == expected_titles
        index_entries = build_chapter_index_entries(narrative)
        assert [index_entries[index - 1]["index_title"] for index in (5, 9, 10, 11, 13, 15)] == [
            "Mina Murray’s Correspondence",
            "Mina Harker’s Correspondence",
            "Dr. Seward’s Diary",
            "Lucy Westenra’s Diary",
            "Dr. Seward’s Diary",
            "Dr. Seward’s Diary",
        ]

        ending = json.loads(
            (artifact_root / "chapters" / "chapter-027.json").read_text(encoding="utf-8")
        )["content"]
        assert ending.rstrip().endswith("JONATHAN HARKER.\n\nTHE END")
        assert "Grosset & Dunlap" not in ending
        assert "DETECTIVE STORIES BY J. S. FLETCHER" not in ending


def test_catalog_wide_reader_indexes_are_complete_and_deterministic():
    manifests = sorted(CONTROLLED_ROOT.glob("*/reader_manifest.json"))
    inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    archived_hold_keys = {"yugalanguriya"}
    current_inventory = {
        **inventory,
        "packages": [
            package for package in inventory["packages"]
            if package["package_key"] not in archived_hold_keys
        ],
    }
    # Preserve the frozen historical fixture. This explicit addition is copied
    # unchanged from the approved root package at merged main 3f76c852, which
    # predated its backend mirror. Never regenerate expectations from candidate
    # manifests or remove archived membership from the frozen fixture.
    current_inventory["packages"].append({
        "package_key": "a-horseman-in-the-sky",
        "manifest_path": "backend/data/controlled_publications/a-horseman-in-the-sky/reader_manifest.json",
        "manifest_slug": "a-horseman-in-the-sky", "chapter_count": 1,
        "chapters": [{"id": "chapter-001", "order": 1}],
    })
    assert hashlib.sha256((CONTROLLED_ROOT / "a-horseman-in-the-sky/reader_manifest.json").read_bytes()).hexdigest() == "fcf6313edcaaac648fbc96dcb446bca87b5c5a79118606e3556905d681406748"
    # Current accepted exact-source overlay includes the author Preface. Keep
    # the frozen 27-chapter baseline untouched and bind this change to its
    # reviewed manifest digest instead of learning expectations from candidates.
    historical_dracula = next(package for package in inventory["packages"] if package["package_key"] == "dracula")
    assert historical_dracula["chapter_count"] == 27
    current_inventory["packages"] = [
        {**package, "chapter_count": 28,
         "chapters": [{"id": "chapter-000", "order": 1}] + [
             {"id": f"chapter-{index:03d}", "order": index + 1}
             for index in range(1, 28)
         ]} if package["package_key"] == "dracula" else package
        for package in current_inventory["packages"]
    ]
    assert hashlib.sha256((CONTROLLED_ROOT / "dracula/reader_manifest.json").read_bytes()).hexdigest() == "f51512441063fa5b19c8af4e6cb1130c9eda98897a242163416ec09fc321068d"
    # The reviewed bn-059 acceptance packet preserves its exact source
    # ordering rather than sorting chapter IDs. Keep the frozen historical
    # fixture unchanged and bind this explicit current overlay to the
    # accepted manifest digest.
    bn_059_ordered_ids = [
        "chapter-011", "chapter-008", "chapter-004", "chapter-003", "chapter-010",
        "chapter-012", "chapter-013", "chapter-001", "chapter-009", "chapter-006",
        "chapter-002", "chapter-007", "chapter-005",
    ]
    current_inventory["packages"] = [
        {
            **package,
            "chapters": [
                {"id": chapter_id, "order": index}
                for index, chapter_id in enumerate(bn_059_ordered_ids, start=1)
            ],
        } if package["package_key"] == "bn-059" else package
        for package in current_inventory["packages"]
    ]
    assert hashlib.sha256((CONTROLLED_ROOT / "bn-059/reader_manifest.json").read_bytes()).hexdigest() == "f6e6fb365561b7f796fa52ad190d6d16a4f7c409c1b5e6ebb648f833b768a2da"
    # Muchiram's accepted source replaces the historical two-chapter
    # placeholder with the reviewed fourteen-chapter edition. Preserve the
    # frozen fixture and bind this current overlay to that exact manifest.
    current_inventory["packages"] = [
        {
            **package,
            "chapter_count": 14,
            "chapters": [
                {"id": f"chapter-{index:03d}", "order": index}
                for index in range(1, 15)
            ],
        } if package["package_key"] == "muchiram-gurer-jibanchorit" else package
        for package in current_inventory["packages"]
    ]
    assert hashlib.sha256((CONTROLLED_ROOT / "muchiram-gurer-jibanchorit/reader_manifest.json").read_bytes()).hexdigest() == "ef7c6d21000b4f9d7fd56fc8bbb4768016682ee70466bc87e4f20d1ff6a4cd20"
    # New runtime mirrors use the unchanged, independently reviewed root sources
    # present at main 514c9ebc. Bind explicit overlays, preserving the old fixture.
    for package_key, chapter_count, manifest_sha256 in [
        ("the-student", 1, "8fe807a4936a240950d242a8084a8e4e0049b35e85087991e7567d5f10f16812"),
        ("bn-035", 10, "b1a64daa1c5bdd26b24544de0911bb687429cdab2cfd8382b5cc6dcd99ab81f3"),
    ]:
        assert hashlib.sha256((CONTROLLED_ROOT / package_key / "reader_manifest.json").read_bytes()).hexdigest() == manifest_sha256
        current_inventory["packages"].append({
            "package_key": package_key, "manifest_slug": package_key,
            "chapter_count": chapter_count,
            "chapters": [{"id": f"chapter-{index:03d}", "order": index}
                         for index in range(1, chapter_count + 1)],
        })
    # Source-complete next-cohort overlays are bound to independently reviewed
    # exact manifests. Preserve the historical fixture and never derive expected
    # identities, counts, or hashes from the runtime candidates being tested.
    next_cohort_overlays = {
        'acres-of-diamonds': [{'id': 'chapter-001', 'order': 1}, {'id': 'chapter-002', 'order': 2}, {'id': 'chapter-003', 'order': 3}, {'id': 'chapter-004', 'order': 4}, {'id': 'chapter-005', 'order': 5}, {'id': 'chapter-006', 'order': 6}, {'id': 'chapter-007', 'order': 7}, {'id': 'chapter-008', 'order': 8}, {'id': 'chapter-009', 'order': 9}, {'id': 'chapter-010', 'order': 10}, {'id': 'chapter-011', 'order': 11}, {'id': 'chapter-012', 'order': 12}],
        'my-life-and-work': [{'id': 'chapter-001', 'order': 1}, {'id': 'chapter-002', 'order': 2}, {'id': 'chapter-003', 'order': 3}, {'id': 'chapter-004', 'order': 4}, {'id': 'chapter-005', 'order': 5}, {'id': 'chapter-006', 'order': 6}, {'id': 'chapter-007', 'order': 7}, {'id': 'chapter-008', 'order': 8}, {'id': 'chapter-009', 'order': 9}, {'id': 'chapter-010', 'order': 10}, {'id': 'chapter-011', 'order': 11}, {'id': 'chapter-012', 'order': 12}, {'id': 'chapter-013', 'order': 13}, {'id': 'chapter-014', 'order': 14}, {'id': 'chapter-015', 'order': 15}, {'id': 'chapter-016', 'order': 16}, {'id': 'chapter-017', 'order': 17}, {'id': 'chapter-018', 'order': 18}, {'id': 'chapter-019', 'order': 19}, {'id': 'chapter-020', 'order': 20}],
        'the-principles-of-scientific-management': [{'id': 'chapter-001', 'order': 1}, {'id': 'chapter-002', 'order': 2}, {'id': 'chapter-003', 'order': 3}, {'id': 'chapter-004', 'order': 4}],
        'the-great-gatsby': [{'id': 'chapter-000', 'order': 1}, {'id': 'chapter-001', 'order': 2}, {'id': 'chapter-002', 'order': 3}, {'id': 'chapter-003', 'order': 4}, {'id': 'chapter-004', 'order': 5}, {'id': 'chapter-005', 'order': 6}, {'id': 'chapter-006', 'order': 7}, {'id': 'chapter-007', 'order': 8}, {'id': 'chapter-008', 'order': 9}, {'id': 'chapter-009', 'order': 10}],
        'the-time-machine': [{'id': 'chapter-001', 'order': 1}, {'id': 'chapter-002', 'order': 2}, {'id': 'chapter-003', 'order': 3}, {'id': 'chapter-004', 'order': 4}, {'id': 'chapter-005', 'order': 5}, {'id': 'chapter-006', 'order': 6}, {'id': 'chapter-007', 'order': 7}, {'id': 'chapter-008', 'order': 8}, {'id': 'chapter-009', 'order': 9}, {'id': 'chapter-010', 'order': 10}, {'id': 'chapter-011', 'order': 11}, {'id': 'chapter-012', 'order': 12}, {'id': 'chapter-013', 'order': 13}, {'id': 'chapter-014', 'order': 14}, {'id': 'chapter-015', 'order': 15}, {'id': 'chapter-016', 'order': 16}, {'id': 'chapter-017', 'order': 17}],
        'bn-066': [{'id': 'chapter-001', 'order': 1}, {'id': 'chapter-022', 'order': 2}, {'id': 'chapter-023', 'order': 3}, {'id': 'chapter-024', 'order': 4}, {'id': 'chapter-025', 'order': 5}, {'id': 'chapter-026', 'order': 6}, {'id': 'chapter-027', 'order': 7}, {'id': 'chapter-028', 'order': 8}, {'id': 'chapter-029', 'order': 9}, {'id': 'chapter-030', 'order': 10}, {'id': 'chapter-031', 'order': 11}, {'id': 'chapter-032', 'order': 12}, {'id': 'chapter-033', 'order': 13}, {'id': 'chapter-034', 'order': 14}, {'id': 'chapter-035', 'order': 15}, {'id': 'chapter-036', 'order': 16}, {'id': 'chapter-037', 'order': 17}, {'id': 'chapter-038', 'order': 18}, {'id': 'chapter-039', 'order': 19}, {'id': 'chapter-040', 'order': 20}, {'id': 'chapter-041', 'order': 21}, {'id': 'chapter-042', 'order': 22}, {'id': 'chapter-045', 'order': 23}, {'id': 'chapter-044', 'order': 24}, {'id': 'chapter-043', 'order': 25}, {'id': 'chapter-046', 'order': 26}, {'id': 'chapter-002', 'order': 27}, {'id': 'chapter-003', 'order': 28}, {'id': 'chapter-004', 'order': 29}, {'id': 'chapter-005', 'order': 30}, {'id': 'chapter-006', 'order': 31}, {'id': 'chapter-007', 'order': 32}, {'id': 'chapter-008', 'order': 33}, {'id': 'chapter-009', 'order': 34}, {'id': 'chapter-010', 'order': 35}, {'id': 'chapter-011', 'order': 36}, {'id': 'chapter-012', 'order': 37}, {'id': 'chapter-013', 'order': 38}, {'id': 'chapter-014', 'order': 39}, {'id': 'chapter-015', 'order': 40}, {'id': 'chapter-016', 'order': 41}, {'id': 'chapter-017', 'order': 42}, {'id': 'chapter-018', 'order': 43}, {'id': 'chapter-019', 'order': 44}, {'id': 'chapter-020', 'order': 45}, {'id': 'chapter-021', 'order': 46}],
        'lokrahasya': [{'id': 'chapter-006', 'order': 1}, {'id': 'chapter-008', 'order': 2}, {'id': 'chapter-001', 'order': 3}, {'id': 'chapter-002', 'order': 4}, {'id': 'chapter-007', 'order': 5}, {'id': 'chapter-011', 'order': 6}, {'id': 'chapter-004', 'order': 7}, {'id': 'chapter-009', 'order': 8}, {'id': 'chapter-010', 'order': 9}, {'id': 'chapter-012', 'order': 10}, {'id': 'chapter-015', 'order': 11}, {'id': 'chapter-013', 'order': 12}, {'id': 'chapter-005', 'order': 13}, {'id': 'chapter-003', 'order': 14}, {'id': 'chapter-014', 'order': 15}, {'id': 'chapter-016', 'order': 16}],
        'the-wonderful-wizard-of-oz': [{'id': 'chapter-000', 'order': 1}, {'id': 'chapter-001', 'order': 2}, {'id': 'chapter-002', 'order': 3}, {'id': 'chapter-003', 'order': 4}, {'id': 'chapter-004', 'order': 5}, {'id': 'chapter-005', 'order': 6}, {'id': 'chapter-006', 'order': 7}, {'id': 'chapter-007', 'order': 8}, {'id': 'chapter-008', 'order': 9}, {'id': 'chapter-009', 'order': 10}, {'id': 'chapter-010', 'order': 11}, {'id': 'chapter-011', 'order': 12}, {'id': 'chapter-012', 'order': 13}, {'id': 'chapter-013', 'order': 14}, {'id': 'chapter-014', 'order': 15}, {'id': 'chapter-015', 'order': 16}, {'id': 'chapter-016', 'order': 17}, {'id': 'chapter-017', 'order': 18}, {'id': 'chapter-018', 'order': 19}, {'id': 'chapter-019', 'order': 20}, {'id': 'chapter-020', 'order': 21}, {'id': 'chapter-021', 'order': 22}, {'id': 'chapter-022', 'order': 23}, {'id': 'chapter-023', 'order': 24}, {'id': 'chapter-024', 'order': 25}],
    }
    next_cohort_manifest_sha256 = {
        'dsires-baby': '83b0d5f8cc0bfbb540cb2bda14f5b974ebbf999c5c636a7f18bf6135a51737ee',
        'sredni-vashtar': '2c534a7cd97535a665942c1684181bf367394016bd12f83673405c123f2c73ad',
        'the-cop-and-the-anthem': 'a46c37d06a9623f73c0fe5598ece4d156d54ed0dfd526795105bfaa82a2ece22',
        'the-open-window': '8f5a8d563c587a28d30e1e001447cdb5328bdcd49df4b61d8d7838401aac6151',
        'the-selfish-giant': 'd5ce7da734364efdd9a2bd6eace1ee2df66bcfa0dcf7ea4e99d49502b330fc9c',
        'the-science-of-getting-rich': 'a42883b4eb214ae086998672472b0f86c9709e550da35c87789f95564cdefdb7',
        'bn-066': 'cf08811a9edf32051c6929e8eb5b29abd6a36df4232c50049e630575f43114d7',
        'lokrahasya': 'cd0d23d355b04e8a076dbc348a1364c3640fe7a149d8b7b2e78690c0ee22261c',
        'mrinalini': 'b2510b44fa9ec57a7a7cc48be2482787ee4fe6cba0021ddd8a6cff71ef5275f7',
        'frankenstein': '2d7d0f01dcbc35eebc51a178b4eb72a9d766cfe5ec56d618113455ba72c16434',
        'pride-and-prejudice': '81b6c23e716ea4d26fae26cc8e9e3e7e37637fd0c9fb1619dccb7a94d0ab7676',
        'the-great-gatsby': 'f544166427c91bb2b8546484bf0c811761345f2ec8f1c73c00afad88411fcb4c',
        'the-secret-garden': '75d9899ba4ecf348e9bc75da118a4b0ac3aa9cb1e595e8598e3541f9154dff4f',
        'the-time-machine': '1874f35f864ccffa65a9d7e38312c3f84df7fd8880120db0ac4ead237d1d913a',
        'acres-of-diamonds': 'c083501e4fd683fe9490a8d5b113ef524b57b3aecacc98fbf73caf44e3066d0c',
        'my-life-and-work': '8abb80566e377a38ba0730ffb69c7dc0fbb53358c6e0908492d968fea1313acd',
        'the-principles-of-scientific-management': '87a47f53b9dbcbae66a09bee4bcc5769f4b5f584ef9bdfc4ab31b65959c3318f',
        'the-wonderful-wizard-of-oz': '2323b65af075000645cd7ac0f3f841f4583ac1407ddefd849a1cbc7b06795d71',
        'book-5704b31005': '6c7daced7a35b9f20ba2f8828e5636d7c644e6ceb272f1707871adafb5a2b759',
    }
    for package_key, manifest_sha256 in next_cohort_manifest_sha256.items():
        assert hashlib.sha256((CONTROLLED_ROOT / package_key / "reader_manifest.json").read_bytes()).hexdigest() == manifest_sha256, package_key
    next_cohort_source_evidence_sha256 = {
        'dsires-baby': 'cbd008f6d99350ba22ccd90ebb8e75d3ce71cd279d632a7a4ecf7c1a9b2bf6fb',
        'sredni-vashtar': 'ee935954b41c2a5415222b6529137ec05cfbfa90d9beb9233e3fb62f1e891a9f',
        'the-cop-and-the-anthem': 'f40f277d758a03b9e05dd6ffa721b058766db6955ba4414d183a7f9bf45fb84f',
        'the-open-window': 'bec621140c44c17f56aaa3599d60cb3293be54a8287cf52fcb2a58e10ec9880d',
        'the-selfish-giant': '48732812096bd1158afd2bf90f9e1992796635c5917ab873d10da4e79f77d04d',
        'the-science-of-getting-rich': '6324de50de9db456175bcd2cbecec794641fa8bdd322d2de2b49eaacc713a117',
        'bn-066': '227c479e011f38150820a341bed084e5c184cda97bc12c034d7093ce660ab0e8',
        'lokrahasya': 'b91f203f5374ba789227c46411bf5d4c2a3721cd27c4ed5e58dcedffaa33fa7e',
        'mrinalini': 'd361d2a57e36d6cf70c84f1b5803a99306467116f44e200cfc16659e0145e94f',
        'frankenstein': 'dc06292e3e257f690c3017e88ded33d0b6baa8b778d1629f3074d1f76b5df449',
        'pride-and-prejudice': '9e4efacc3dbd251ea18aacd5805d781c1f64a450bea0225fae4ba6a394a97e99',
        'the-great-gatsby': '93a1e5eab7ce62def0ef60ba3a2ae6e56ed964c688c1f2a827f3e88664a30874',
        'the-secret-garden': 'd4fba2e016dc99ebbab2950c7f63186ec154e408da4d4acb09a82fa8ef959852',
        'the-time-machine': '010c2fd7d0fa5ae1370f081876448c94a9bad177df7fe0b621b0f91c39af0cf5',
        'acres-of-diamonds': '9371f2af833cbd9683e138e121b7c6ae77f17a18de6dd46cb4507a301a6eb29e',
        'my-life-and-work': '1d5f331b74b4ac24ba559209d4d1c8ca3543a1cdc274a71bdf14bb2022b7d4b7',
        'the-principles-of-scientific-management': 'e6b091fd0aebe2517dd1e2b6c8e8ef14d5ea6d6540daa66c33e0ba27a9ef2380',
        'the-wonderful-wizard-of-oz': '7ec444ed90caa41fb950757933ee7399ef94fceab855bdd8c3e52a6806358ec5',
        'book-5704b31005': 'f7d3ac1cbe169532038b008d48c0313290cedca638d23c7696d75d3a0c072f3b',
    }
    for package_key, source_sha256 in next_cohort_source_evidence_sha256.items():
        assert hashlib.sha256((CONTROLLED_ROOT / package_key / "source_evidence.json").read_bytes()).hexdigest() == source_sha256, package_key
    for package_key, expected_chapters in next_cohort_overlays.items():
        expected_package = {
            "package_key": package_key, "manifest_slug": package_key,
            "chapter_count": len(expected_chapters), "chapters": expected_chapters,
        }
        current_inventory["packages"] = [
            package for package in current_inventory["packages"]
            if package["package_key"] != package_key
        ] + [expected_package]
    current_inventory["expected_manifest_count"] = len(current_inventory["packages"])
    current_inventory["expected_chapter_count"] = sum(
        package["chapter_count"] for package in current_inventory["packages"]
    )
    assert current_inventory["expected_manifest_count"] == 102
    assert current_inventory["expected_chapter_count"] == 826
    actual = {
        path.parent.name: json.loads(path.read_text(encoding="utf-8"))
        for path in manifests
    }
    assert "yugalanguriya" not in actual
    assert any(
        package["package_key"] == "yugalanguriya"
        for package in inventory["packages"]
    ), "the frozen fixture must retain Yugalanguriya's historical snapshot"
    assert_controlled_inventory(actual, current_inventory)
    audited_chapters = 0
    for manifest_path in manifests:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        chapters = manifest.get("chapters") or []
        first = build_chapter_index_entries(chapters)
        second = build_chapter_index_entries(chapters)
        assert first == second, manifest.get("slug")
        assert len(first) == int(manifest.get("chapter_count") or 0), manifest.get("slug")
        assert len({entry.get("id") for entry in first}) == len(first), manifest.get("slug")
        assert [entry["index_sequence"] for entry in first] == list(range(1, len(first) + 1))
        assert all(entry["index_contract"] == CHAPTER_INDEX_CONTRACT_VERSION for entry in first)
        assert all(entry["index_title"].strip() for entry in first)
        audited_chapters += len(first)
    assert audited_chapters == current_inventory["expected_chapter_count"]


@pytest.mark.parametrize("mutation", [
    None,
    "missing_package",
    "missing_zero_chapter_alias",
    "unexpected_package",
    "same_count_substitution",
    "wrong_manifest_slug",
    "wrong_count",
    "renamed_chapter",
    "duplicate_chapter",
    "reordered_chapters",
    "changed_order",
])
def test_frozen_inventory_detects_catalog_drift(mutation):
    inventory = {
        "expected_manifest_count": 2,
        "expected_chapter_count": 2,
        "packages": [
            {"package_key": "story", "manifest_slug": "story", "chapter_count": 2,
             "chapters": [{"id": "opening", "order": 1}, {"id": "ending", "order": 2}]},
            {"package_key": "retired-alias", "manifest_slug": "retired-alias",
             "chapter_count": 0, "chapters": []},
        ],
    }
    actual = {
        "story": {"slug": "story", "chapter_count": 2,
                  "chapters": [{"id": "opening", "order": 1}, {"id": "ending", "order": 2}]},
        "retired-alias": {"slug": "retired-alias", "chapter_count": 0, "chapters": []},
    }
    if mutation is None:
        assert_controlled_inventory(actual, inventory)
        return
    if mutation == "missing_package":
        del actual["story"]
    elif mutation == "missing_zero_chapter_alias":
        del actual["retired-alias"]
    elif mutation == "unexpected_package":
        actual["unexpected"] = deepcopy(actual["story"])
    elif mutation == "same_count_substitution":
        actual["replacement"] = actual.pop("story")
    elif mutation == "wrong_manifest_slug":
        actual["story"]["slug"] = "different-story"
    elif mutation == "wrong_count":
        actual["story"]["chapter_count"] = 1
    elif mutation == "renamed_chapter":
        actual["story"]["chapters"][1]["id"] = "other-ending"
    elif mutation == "duplicate_chapter":
        actual["story"]["chapters"][1] = deepcopy(actual["story"]["chapters"][0])
    elif mutation == "reordered_chapters":
        actual["story"]["chapters"].reverse()
    elif mutation == "changed_order":
        actual["story"]["chapters"][0]["order"] = 3
    with pytest.raises(AssertionError):
        assert_controlled_inventory(actual, inventory)

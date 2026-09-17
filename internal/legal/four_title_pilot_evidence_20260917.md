# Four-title pilot evidence — 2026-09-17

This is an engineering and source-comparison checkpoint. It is not a legal
opinion, acceptance registry, publication approval, or deployment record.

## Reproducible current-byte check

The canonical checkout was clean and aligned at
`ca14c143af92450d2fcd8199e114f383c26ead31` before this controls-only change.
The reviewed pilot archive SHA-256 was
`119db1a448fa0aa963a627ea4e4a430e47aacd8bd15fe31fc5cdc974a2a0b2f8`.
Its `verify_package.py` reported 139 tracked files verified.

The following comparison was repeated in a temporary copy of the pilot using
the current canonical chapter bytes:

```sh
python3 english/compare_english_pilots.py
python3 bengali/compare_bengali.py
```

All 20 selected artifacts matched the worklist SHA-256 values: one chapter for
each English title, eight for Radharani, and ten for Yugalanguriya. The English
results retain independently selected source boundaries and report ordered
paragraph equality after documented NFC/line-ending/whitespace normalization:
30 paragraphs for *A Ghost Story* and 18 for *The Tell-Tale Heart*. This is
text-integrity evidence only, not a rights decision. The Bengali comparator
reports 17 normalized-body matches and one footnote presentation difference.

## Binding control status

`backend/data/rights_decision_registry.json` contains four named pilot HOLD
dispositions and **zero** accepted records. `backend/rights_decision_gate.py`
requires exact edition/operator identity, trusted country, explicit use,
validity, evidence, reviewer attribution, revocation status, and hashes for
every actual required component. The runtime-action table includes catalog CTA,
preview, reader/manifest/chapter, Reading Pass start/transfer/renewal, audio
manifest/HEAD/range/download, export, signed storage, and generation worker and
cache actions.

The control is intentionally not wired into production serving yet. Its strict
enforcement switch is off by default; turning it on before a trusted
country-assertion adapter and accepted records are reviewed would fail closed.
No existing reader, billing, cache, generation, storage, publication, or audio
behaviour was changed by this checkpoint.

## Remaining specific inputs

| Owner | Exact input | Affected scope |
|---|---|---|
| Authorized operator | Legal entity, operating locations, merchant-of-record relation, and authorised acceptance identity | all four titles and every target country/use |
| Rights reviewer | Hash-bound accepted/rejected decision records for each applicable act/country, with evidence and review/update trigger | reader first; audio separately |
| Asset reviewer | Exact cover/editorial component inventory and permitted use; an illustrated-cover provenance packet (not a typography-only substitute) | cover/CTA display |
| Provider/voice owner | Model revision and dated terms, processing locations, voice authority, master provenance and music-absence confirmation | generation and audio only |
| Bengali reviewer | Review the separate, source-bound reversible patch below against the recorded opening-image hashes; preserve the source footnote semantics | Yugalanguriya manuscript only |

## Yugalanguriya facsimile recovery (source evidence, not a clearance)

The earlier evidence did not preserve the exact URL, method, or timestamp of
the reported `404`, so that result is withdrawn from this record rather than
being described as source disappearance. It cannot support an absence claim.

On `2026-09-17T17:42:28Z`, a public `curl --get` request to the Wikimedia
Commons Action API returned HTTP `200` for the NFC-normalized title
`File:যুগলাঙ্গুরীয় - বঙ্কিমচন্দ্র চট্টোপাধ্যায়.djvu`. The request used
`action=query`, `prop=imageinfo`, `iiprop=url|sha1|size|mime|timestamp`, and
`format=json`; it identified a 58-page, 1,170,660-byte `image/vnd.djvu`:

```text
https://commons.wikimedia.org/w/api.php?action=query&titles=File%3A%E0%A6%AF%E0%A7%81%E0%A6%97%E0%A6%B2%E0%A6%BE%E0%A6%99%E0%A7%8D%E0%A6%97%E0%A7%81%E0%A6%B0%E0%A7%80%E0%A6%AF%E0%A6%BC%20-%20%E0%A6%AC%E0%A6%99%E0%A7%8D%E0%A6%95%E0%A6%BF%E0%A6%AE%E0%A6%9A%E0%A6%A8%E0%A7%8D%E0%A6%A6%E0%A7%8D%E0%A6%B0%20%E0%A6%9A%E0%A6%9F%E0%A7%8D%E0%A6%9F%E0%A7%8B%E0%A6%AA%E0%A6%BE%E0%A6%A7%E0%A7%8D%E0%A6%AF%E0%A6%BE%E0%A6%AF.djvu&prop=imageinfo&iiprop=url%7Csha1%7Csize%7Cmime%7Ctimestamp&format=json
```

Correction to the displayed historical record: that printed literal ends the
author name with `চট্টোপাধ্যায.djvu` (U+09AF before `.djvu`) and omits the
terminal U+09BC required by the NFC title
`চট্টোপাধ্যায়.djvu`. It is therefore not a reproducible copy of the
successful acquisition request and must not be treated as one. The retained
successful response identifies the NFC filename with U+09AF U+09BC and returns
the corresponding original-file URL; the original `curl --get` invocation
recorded parameters rather than this printed query literal. This documentation
correction neither revises nor erases the historical string.

Separately, at `2026-09-17T18:27:29Z`, a **new** query was constructed from
the NFC title using Python `urllib.parse.urlencode` and returned HTTP `200`.
Its raw JSON response is retained only in scratch as SHA-256
`11bb3e46974df3fd7aa0241345490d08ee98b1a415ff39e140b7ccb3b8d3b9e9`.
It returned `File:যুগলাঙ্গুরীয় - বঙ্কিমচন্দ্র চট্টোপাধ্যায়.djvu`, including
U+09AF U+09BC before `.djvu`, and the original URL used for byte retrieval.
This is a new reproducibility observation, not a retroactive description of
the earlier request.

Provider metadata gave SHA-1
`e27d4a6df52b13a9b3612fa21d662fa6578502c4` and source timestamp
`2014-04-24T05:12:49Z`. At `2026-09-17T17:43:12Z`, `curl --location --fail`
of the API-returned `upload.wikimedia.org` original URL returned HTTP `200`.
The locally retained scratch copy is 1,170,660 bytes, has the same SHA-1, and
has SHA-256 `03a6727006a314d4a8b9f804b0b75e531bd533a0c5293992935e55171fac46de`.
This is a byte verification, distinct from provider metadata. No source bytes
are added to the repository.

`ddjvu` rendered the ten queue positions (DjVu images 6, 13, 17, 23, 27, 30,
35, 38, 42, and 47) to scratch opening crops. Visual inspection, rather than
the already-truncated web extraction or OCR, establishes the displayed initials
and the corresponding proposed text joins below. The table records the crop
SHA-256 and an intentionally small, separate repair proposal; it does not
modify a manuscript, a checksum, pagination, metadata, or publication state.

| Chapter | Image / printed page | Source visual reading | Current opening | Proposed reversible opening | Crop SHA-256 |
|---|---:|---|---|---|---|
| 001 | 6 / 1 | `ই` + `জনে` | `ই জনে` | `ইজনে` | `8b21bb71ea8ca27328308361458a5cabcb914c13935bb2f1f153a0a4eada711c` |
| 002 | 13 / 8 | `কে` + `ন যে` | `ন যে` | `কেন যে` | `39145bf65132531a8c8521e43ee0d6a9fad1c612937cde844b0d13914f07383a` |
| 003 | 17 / 12 | `দু` + `ই বৎসরের` | `ই বৎসরের` | `দুই বৎসরের` | `1448045f9d5877ded335a0d4892d6a587ce676bb325fffdd2d4e5a1438fb2ae1` |
| 004 | 23 / 18 | `বি` + `বাহাস্তে` | `বাহাস্তে` | `বিবাহাস্তে` | `84066964d6e818a1a0326e16a711dd5e8e72c68783279eb65d233cda0f762ba1` |
| 005 | 27 / 22 | `হি` + `রণ্ময়ী` | `রণ্ময়ী` | `হিরণ্ময়ী` | `3d1d3efd1faaa03edd5b45ed455d826a94b2981cf6dd48035738570327488857` |
| 006 | 30 / 25 | `প` + `রে এক দিন` | `রে এক দিন` | `পরে এক দিন` | `48cfa81348c37cb6c094cef042df430e45bc7dcf58aaa8c86d499885155d0597` |
| 007 | 35 / 30 | `বি` + `বাহের পর` | `বাহের পর` | `বিবাহের পর` | `360248ab8101225446db66cac5a954679b786c52cc50bba76cc1c42303668f7f` |
| 008 | 38 / 33 | `হি` + `রণ্ময়ী` | `রণ্ময়ী` | `হিরণ্ময়ী` | `bfb5ccd94faf02bac22000a29672bc493fd1d03d1a4bc95dd869faec4d4a5862` |
| 009 | 42 / 37 | `হি` + `রণ্ময়ী` | `রণ্ময়ী` | `হিরণ্ময়ী` | `c28a058fcbfb66b130f2d053ed0e682ec70fd83307fbfce06d3ceef3e2ee0664` |
| 010 | 47 / 42 | `হি` + `রণ্ময়ী` | `রণ্ময়ী` | `হিরণ্ময়ী` | `763e821cdb2cee29fd75dd06025ae9490a7026af2f8042fa5453d853a5072827` |

All entries in this table are review proposals, not approved manuscript
repairs. In particular, Chapter 001's proposed `ইজনে` is withheld pending an
independent reading of uncropped image 6, including its left margin, beside the
hash-matching opening crop. Neither the crop hash, a damaged web transcription,
OCR, nor linguistic inference establishes the complete word or its boundary.

The first-page crop also shows the Tamralipta footnote with an asterisk. The
current chapter retains its words but substitutes an upward-arrow marker and
does not bind a semantic note reference. That is a separately localized
presentation/semantics repair, not evidence for rights or publication.

Before a future source-only patch: apply only independently confirmed opening
repairs plus the separately reviewed footnote-markup repair; regenerate dependent hashes using
the repository recipe; compare the full affected chapters and pagination/highlight
boundaries; and obtain independent Bengali review. It must be a new scoped PR
after this controls-only PR is resolved.

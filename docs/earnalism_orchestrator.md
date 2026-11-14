# The Earnalism production orchestrator

[Open the single notebook](../notebooks/Earnalism_Production_Orchestrator.ipynb).
It coordinates the existing book, audiobook, score and video implementations from
one instruction and one durable private project journal. It is the reusable entry
point; component notebooks and historical experiments remain preserved evidence.

Examples:

```text
Build the GO LIVE ready output for the audiovisual cinematic version for the book - The Selfish Giant
Build the next audiovisual for the EverydayScience topic for theearnalism social media platform
Build the GO LIVE ready output for the audiovisual cinematic version for the Bengali book - Bicharak
```

The bounded book grammar also accepts `Build the GO LIVE ready audiovisual for
Bengali book Bicharak using The Earnalism Voice`. The known terminal voice
direction stays separate from the exact title; multiple books/editions are not
silently combined, and other trailing clauses are not guessed away.

“GO LIVE ready” requests preparation and the existing readiness evaluation.
The notebook does not publish. Source/AV rights, actual content/voice quality,
measured timing, protected delivery and destination authority retain their
existing contracts. Existing owner holds remain effective.

## One-time private installation

The registry uses `earnalism.production_registry.v1` with a `projects` list.
Each project supplies `id`, `kind` (`book` or `science`), exact `title`, `language`
(`en` or `bn`) and typed `stages`. Optional explicit aliases resolve transliterated
titles. An EverydayScience queue entry additionally supplies `series`,
`queue_status: "ready"` and an unambiguous `queue_order`. Private history augments
canonical owner holds; an empty history cannot clear a known rejection.

The production agent registers exact content projects in the private Drive
workspace's `projects.json`: authoritative text, trained voice profile, measured
timing, cleared music/direction, source-specific visuals, independent delivery
compositions, exact brand/END assets and the existing release manifest. The agent
uses the four skills to prepare missing creative and editorial inputs. The
notebook executes their supported code; Markdown skills are not model weights or
an undocumented remote AI service.

Keep media, checkpoint parts, model caches, account evidence and project-specific
feedback on private Drive. The distributed notebook embeds only generic reviewed
software. It pins a Git source base and a complete checksum-verified code overlay,
so it does not silently execute whatever `main` contains later. A modified
runtime checkout is preserved and refused rather than overwritten on resume.

Connect the private Drive workspace through the ordinary Colab permission flow
when necessary. Preparation is the default. To execute model work, supply the
existing actual runtime envelope before setup; its original allocation start,
deadline, allowed operations and bounded compute remain fixed through transfer,
setup, inference and export. The outer envelope coordinates existing stage
authority and creates no new grant. No paid provider, purchase, training or
publication is enabled by a natural-language instruction.

After installation, the normal content input is `INSTRUCTION`; the same notebook
resolves the registered project and resumes its stage graph. “Next” selects an
explicit ready, ordered, unconsumed EverydayScience queue entry. Missing projects,
ambiguous editions or unsupported topics produce exact missing-input reports.
They do not cause another book, voice, mechanism or episode to be guessed.

## Real execution and reuse

The stage graph is source → narration → measured timing → score/visual production
→ composition → complete review → existing release-readiness evaluation. Fixed
typed adapters call the supported Python/Remotion/Wan implementations. Project
data cannot supply shell commands, Python module names or arbitrary callbacks.

Voice selection resolves **The Earnalism Voice** through actual base/model,
trained checkpoint, runtime and language acceptance. Genuine training and fresh
reload are useful lineage, while naturalness, accent, expression, endurance and
full-title fidelity retain their actual qualification. Authorized experimental
auditions can use an unqualified trained profile; full-book production cannot
silently promote that profile or substitute stock/base speech. Runtime ABI and
wheel availability are verified before installing or loading the model.

The retained trained voice currently needs Python 3.12, Torch 2.6.0,
Transformers 4.46.1, Parler 0.2.2 and DAC 1.0. A newer Colab image is not a
compatible substitute. Stage the exact interpreter, complete hash-locked wheels,
base files and trained checkpoint parts described by the voice profile before
runtime qualification. English and Bengali acceptance are independent; training
on one language does not qualify the other.

Scoring uses the complete source, real narration clock, contextual direction and
cleared finite stems through `audiobook_score`. Transitions, levels and deliberate
silence follow the actual content. Accepted KEEP passages remain candidate-bound.
Science body continuity does not override literary scoring preferences. Analysis
of loudness or signal coverage does not establish heard emotional fit.

Visual execution uses source-specific native motion or the registered science
adapter. Silent science body renders feed the same source-bound compositor as
books; the bound END is appended exactly once. The lunar studio cannot render
arbitrary subjects. Independent portrait/landscape layouts and actual body,
expression, identity/contact, caption and brand review remain necessary.

For supported science bodies, validated project inputs admit automatic setup of
the exact maintained Remotion package lock and its supported browser in an owned
private workspace cache. Setup uses the original allocation clock, fixed public
npm downloads and no account credentials. Resume verifies package versions,
manifest hashes and browser bytes; failed or unknown installations are retained
for reconciliation. Node/npm and required operating-system libraries must exist.
This setup is software preparation, not a successful render or visual review.
See the [supported browser API](https://www.remotion.dev/docs/renderer/ensure-browser).

Every stage fingerprints its exact inputs, relevant upstream outputs, software,
profile and scoped feedback. Reuse requires the recorded output bytes to match.
Changed narration invalidates dependent timing/music/anchors; a visual-only
finding preserves healthy narration and music. Intents are persisted before
consequential work. Interrupted or unknown attempts remain consumed until actual
reconciliation; changing an output filename does not create another allowance.

## Feedback and capability improvement

Candidate-bound feedback records the actual reviewer/source, content/time/frame
scope, finding, affected area, fix and preserve choices. The orchestrator retains
it privately and invalidates only the relevant stage/dependants. It never converts
a diagnostic, training log, source test or improvement in one attribute into
acceptance of another. Identity and expression defects stay visible even if torso
motion improves.

Reusable software/skill lessons are promoted through the Integration Lane with
focused regression evidence. Private corpus/media, checkpoints, account records
and unperformed quality scores are excluded from public commits. Feedback can
improve direction, scheduling, caching and tested defaults immediately. Model
fine-tuning remains a separate actual training operation requiring its dataset,
rights, checkpoint, evaluation and compute scope; feedback storage is not training.
Improved first-attempt results are the objective, not a promise of perfection.

## Build and validate the notebook

```sh
python3 scripts/build_earnalism_orchestrator_colab.py
python3 scripts/build_earnalism_orchestrator_colab.py --check
python3 -m unittest scripts.test_build_earnalism_orchestrator_colab
```

Source tests establish software behavior. Actual runtime/model qualification,
full listening/visual acceptance and supported destination verification remain
separate facts. Runtime cleanup requests are recorded; a timer or an unassign
request alone is not observed provider closure.

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

## Several contents in the same notebook

Set `BATCH_PATH` to a private `earnalism.production_batch.v1` JSON file instead
of entering one `INSTRUCTION`. Its data is an `id` and `items`, each with a safe
`id` and an explicit supported instruction. Name each exact book/topic; batches
reject `next` and duplicate selections before execution. The normal private
`projects.json` remains the one project registry.

`PREPARATION_WORKERS` (1–4) plans independent contents in parallel. Model work
then goes serially through the existing `run()` writer, lock and attempt journal;
this avoids several workers competing for one GPU. The controller makes no
Codex API calls. It returns compact status/file references while retaining full
plans/results privately. This removes repeated model-context/report overhead;
creative interpretation and narration/visual model work retain their actual costs.

```sh
python3 scripts/earnalism_orchestrator.py batch --input PRIVATE/batch.json \
  --workspace PRIVATE --workers 3
```

Preparation is the default. `--execute` may advance available local stages;
model stages still require their real project-bound scopes. An optional
`BATCH_AUTHORITIES_PATH` maps project IDs to exact authority file descriptors.
All supplied scopes are validated before dispatch and preserve one actual
allocation start/deadline, observed rate and compute cap. Per-title budgets are
not added together, and prior reservations stay consumed. Missing inputs hold
their own title. A source/registry change during preparation holds the batch and
preserves all observed plans, including a transient change later restored.

The existing candidate-bound feedback command remains the correction route.
Rerunning the same batch reuses valid stage outputs; it does not clear owner
holds, retrain weights, replay unknown attempts or start speculative retries.

## Whole-work and granular text context

`scripts/earnalism_content_context.py` builds hash-bound whole-work, serialized
block, sentence-candidate and phrase-candidate spans into bounded private pages.
UTF-8 bytes, Bengali marks, source order and parent/child coverage are preserved.
Unchanged context is verified before reuse. HTML/plain-text transformations and
true authorial paragraph boundaries must be documented separately: blank lines
in a wrapped source are not automatically literary paragraphs.

Genre notes and source-specific exceptions come from actual editorial reading,
with their source/hash and review scope. Context packets let a worker retrieve
the relevant passage, parent context and whole-work direction without repeatedly
sending a complete long book to Codex. Punctuation splitting does not establish
semantic understanding, emotion, measured audio timing or a performed caption.
The index records those as unassessed. Exact voice/score/scene jobs must still
incorporate the reviewed direction before generation; the index is not a model.

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

Check the [provider's current Python ABI](https://research.google.com/colaboratory/runtime-version-faq.html)
before allocation. The generated notebook requests `2026.07` (Python 3.12)
through its runtime metadata. This image pin does not
replace the actual Linux/Python preflight before storage or model work.

The pre-storage probe and actual native worker explicitly load the fixed,
hash-verified provider bootstrap before Torch. Automatic `sitecustomize` lookup
can select a different file even in an isolated venv; a successful metadata child
does not preload the later native process. Preserve the existing basename driver
lookup gate and stripped environment. Before shutdown, the pre-storage entry
prints bounded SHA/length-bound copies of its four primary receipts into notebook
output. Retrieve and verify the saved notebook to establish durable retention.
Missing child diagnostics leave an actual runtime failure's cause unknown; a
reproduction on another CPU host does not diagnose Colab or qualify CUDA.

The existing voice controller also registers the retained balanced128 checkpoint
for the single private Bengali qualification request `8d80e56eeb3b`, amendment
`bda98868de0d`. This is a separate Darwin arm64, Python 3.11, exact CPU100
environment; the historical male130/Linux contract is unchanged. The typed job
fixes the source, unspoken caption, seed, sampling controls and one native take.
Production remains held for this checkpoint, even if a profile claims acceptance.

A separate balanced128 English-female qualification registers two fixed dry
scenes on Linux x86_64, Python 3.12 and the retained 111-package closure. It uses
the same notebook and `trained-voice` adapter with a private qualification
registry. Its disabled control creates no allocation or model authority. The
native worker must use the exact owned interpreter and setup receipt bound to
the same original allocation and scope; it cannot fall back to the notebook's
interpreter. Setup, transfers and export stay inside the original clock. The
native cutoff leaves at least five seconds before that allocation's shutdown;
runtime binaries are checked by the native bridge, outside corpus/cache reads.
Neither distinction extends the allocation or weakens source/rights checks. The
prior Darwin CPU100 contract and all balanced128 production holds remain intact.

English restoration installs only the complete hash-locked local wheel set,
without pip resolving dependencies a second time. The retained Parler metadata
names a Git dependency that hash-checking mode cannot resolve; its matching
distribution already exists in the exact closure. Keep `pip check` and installed
version verification after installation: missing/incompatible dependencies and
changed hashes still block acceptance. Check the frozen dependency metadata and
exercise the actual offline installer when this path changes, before another GPU
allocation. CPU/package checks do not establish model or narration quality.

Verify saved cell literals for the actual scope, Connect timestamp and observed
rate before running them. A numeric form widget can display a value without
committing it to the cell source. Correct only pre-admission input within the
same original clock; never renew a grant or replay an admitted model stage.

This comparison fixes two takes, 180 seconds of total native audio and 32 MiB of
native output, with no optimizer, new weights or automatic retry. Source audio
guides the unspoken performance brief and later listening comparison; Parler
does not receive it as waveform conditioning. Keep an owner's selected window
separate from the complete publisher-paired recording and disclose any original
test-set exposure. New dry auditions do not replace a retained film soundtrack,
score or selected visual style. Software checks do not establish accent,
naturalness, reference similarity or complete scene fit on the future runtime.

Local CPU authority uses a real execution start, rather than an invented cloud
allocation or extended GPU deadline. It binds the controller, runtime and Darwin
helper, the existing journal prefix and both the venv launcher and resolved
interpreter. The controller journals the entire case before loading; renaming a
job or output does not permit replay after a failure or unknown result. A separate
pre-model guardian follows parent liveness and the existing shared-memory floor
while native calls run. Resource observations do not prove model memory fit.
Fake tests prove these source contracts only. This implementation grants no
activation, training, synthesis, allocation or publication; Bicharak stays held.

For the CPython 3.12 Linux Colab worker, `QUALIFY_PRE_STORAGE_DRIVER` is an
optional, execution-disabled prerequisite check before Drive authentication.
Supply its actual approved scope in the runtime envelope; the notebook binds
that scope to its existing original allocation clock and live shutdown guard.
The embedded source runs without a package download or Drive mount. A failed
lookup stops before private storage access, model setup or narration.

`scripts/earnalism_voice_runtime/provider_driver_bootstrap.py` resolves the
already loaded provider library through `/proc/self/maps` and binds its exact
path, size and hash. It installs a single owned-venv preload without passing
`LD_LIBRARY_PATH` or account credentials into the worker. Changed library bytes
terminate startup. `pre_drive_loader_entry.py` checks a fresh, stripped-environment
interpreter and emits a small retainable receipt. These checks do not import
Torch, load a model, train, allocate a GPU or qualify CUDA compute. Their CPU and
mock tests do not establish successful execution on a Colab GPU.

The separate opt-in `position_table.py` utility prepares sufficient sinusoidal
position capacity before snapshots and training/inference, retaining the original
prefix and frozen state. It is not wired into the existing inference adapter or
its qualified profiles. Preserve the original frozen experiment source and
private evidence when promoting reusable helpers; no source refactor renews an
expired execution scope or qualifies a rejected voice.

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

`metal-rust` now has its own maintained silent-body adapter. It binds the exact
reviewed script, actual words/scenes/captions, native audio clock and genuine
trained English profile. The finite topic contract cannot relabel another
explanation or use an illustrative study clock. Landscape and portrait have
independent pictorial layouts; the common compositor owns the selected score and
exact END once. See `skills/earnalism-video/software/metal_rust/README.md`.
Source fixtures/stills qualify software and visible geometry only. Actual
narration, measured timing, scoring, complete AV review and release remain separate.

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

# Foundation diagnostic: environment qualification

The foundation diagnostic consumes an existing qualified environment; it does
not install packages. The separate `foundation-qualification` operation prepares
that environment under an actual bounded scope and records its observations.
A recipe, implementation or software test is not actual runtime evidence,
compute authority or voice acceptance. Distributed execution remains disabled.

After editing an admission cell, fetch the final saved notebook before running
that cell. Check its observation literals locally without executing notebook code:

```bash
python3 scripts/check_colab_scope.py \
  --notebook /PRIVATE/saved-notebook.ipynb \
  --cell-id SAVED_CELL_ID --expected-json /PRIVATE/observed-controls.json
```

The expected JSON is an independently observed name-to-literal map. The checker
requires one simple top-level binding per name and rejects duplicates, nested or
nonliteral assignments, prior syntactic reads and type mismatches. A later correct assignment cannot
hide an earlier placeholder. Any subsequent edit invalidates the saved-byte check.
This verifies source bindings only, with no compute grant or runtime acceptance.

Use the existing notebook's empty `FOUNDATION_QUALIFICATION_PATH` control, or
inspect the private request without execution:

```bash
python3 -m scripts.earnalism_orchestrator foundation-qualification \
  --request /PRIVATE/QUALIFICATION-REQUEST.json --workspace /PRIVATE
```

This route is outside production stages and never dispatches the two scenes.
The new request binds the unchanged frozen proposal, original data-only recipe,
complete wheel manifest and current runner sources. A separate
`foundation_qualification` capability records one package attempt, one provider
lookup and one minimal CUDA call, with zero model loads/generation/training.
The existing runtime envelope still checks the original clock/rate/allowance and
armed shutdown guard. A qualification capability cannot reserve model work;
diagnostic/production capabilities cannot substitute for it.

For an authorized future notebook run, reviewed public software and provider
lookup precede interactive Drive access or large inputs. Its bounded primary
receipt is printed before mounting Drive and bound to the original scope/clock.
The durable workspace then retains the qualification intent, raw setup/probe
logs and exact results. Final packages and preload belong to the owned local
runtime venv, while private journals survive on Drive. The canonical experiment
blocks package/probe replay across renamed requests or scopes; verified completed
results are status-only and do not qualify a new runtime.

A successful setup or CUDA command can produce an empty log. Completed-result
verification retains and checks its exact zero-byte log and checksum; missing,
changed or redirected logs still fail. Other qualification inputs remain nonempty.
Test the producer-to-result-verifier path before spending on a runtime; a passing
producer alone does not prove that its retained result can pass the later handoff.

Qualification returns actual interpreter/preload/package/CUDA descriptors as
evidence, without synthesizing another authority. A later selected diagnostic
independently validates its genuine complete-operation scope and actual files.
It retains its own one-load/two-call counter. No route automatically accepts a
voice, changes the soundtrack/style or publishes a candidate.

Plan the runtime lifecycle before allocation. Standalone qualification keeps the
notebook's default final disconnect. If the actual approved complete operation
also includes a later selected diagnostic in the same allocation, configure
`AUTO_DISCONNECT_OWN_RUNTIME=False` before starting and retain the independent
original-deadline guard. Populate only observed diagnostic descriptors under that
existing genuine scope, finish its bounded operation and close the runtime.
Qualification does not restart the clock, grant another allocation or justify
reconstructing an expired environment from old receipts.

Do not reuse an English restoration request, allocation-specific setup result,
expired clock or disposable lookup venv as foundation qualification. The English
setup controller remains bound to its own request and job. Its pure three-command
package recipe can be reused as reviewed data without dispatching that controller.

Prepare one private packet for the existing single orchestrator containing:

- The frozen experiment, full reference, exact software bindings and disabled
  envelope. Preserve both rejected recordings and selected soundtrack/style.
- A requirements lock derived from the complete retained wheel manifest, plus
  per-object expected byte counts and hashes. Cached names/sizes are metadata;
  verify bytes when consumed. Exclude adapted checkpoint parts from a
  foundation-only comparison.
- Data-only command arrays for a fresh owned CPython venv, local-only wheel
  installation and `pip check`. Retain `--no-index`, `--only-binary=:all:`,
  `--require-hashes`, `--no-deps`, `--no-cache-dir` and `--no-compile`.
  Check the actual provider pip supports `--python`; do not fetch another
  installer or resolve the retained Parler wheel's VCS dependency.
- Actual-evidence slots for the provider, interpreter, packages, paths, driver,
  bootstrap, minimal CUDA probe, resource observations and export/accounting.
  Leave unobserved facts null and every preparation/authority switch disabled.
- Complete-operation resource scope covering qualification, storage/transfers,
  setup, the one foundation load/two fixed calls, native/trace export and closure.
  Old allowances do not renew. Proposed topology and output limits are not time,
  credit, disk, RAM or VRAM grants.

Under a future authorized and reviewed runner, the qualification order is:

1. Observe the genuine same-allocation identity, original clock/deadline, rate,
   allowance and independent shutdown guard before software/storage/model work.
   Reconcile cumulative journals and consumed attempts first. No stage restarts
   the clock or budget.
2. Check actual Linux/x86_64/CPython 3.12, hash the provider interpreter and
   confirm provider pip capability. Hash all retained input bytes at consumption.
   Observe free space on each actual filesystem; archive and installed expansion,
   model memory and scratch requirements are additional to logical input bytes.
3. Create a new owned venv using `venv --without-pip`. Use existing provider pip
   with `--python` for the exact local wheel lock, then `pip check` and independent
   distribution-metadata comparison. Capture command intent, raw logs, exit and
   timing; package readiness alone does not qualify CUDA or a model.
4. Resolve/hash the actual provider driver using the pinned provider helper.
   Install its fixed bootstrap in the **final** owned venv at
   `lib/python3.12/site-packages/sitecustomize.py`. Record launcher and resolved
   interpreter descriptors, library identity and exact bootstrap source/hash.
5. Start a fresh `-I -B` child with the diagnostic's credential-stripped
   environment. Explicitly load the exact bootstrap before importing Torch.
   Compare all pinned package versions and observe CUDA0. A proposed single
   FP32 tensor sum `[2, 3] -> 5`, synchronized on CUDA0, checks only that tiny
   operation. Record stdout/stderr, exit, device/capability/memory and elapsed
   time. It proves neither full-model fit nor narration quality. No model/TTS
   import, fallback, retry, training or generation belongs in qualification.
6. Stop on failure/unknown, retain partial evidence and reconcile actual charges
   or explicit unknown accounting. A passing preparation checker or CUDA smoke
   cannot authorize dispatch. Only genuine complete-operation authority and
   actual prerequisite evidence can populate the existing diagnostic envelope.

Use the reviewed runner's current source binding; preserve historical packets
and their original states. A data-only recipe still reports
`RECIPE_PREPARED_RUNNER_UNBOUND_RUNTIME_UNQUALIFIED`; implemented dry planning
does not populate actual observations or admit a runtime. Native WAV bytes are
bounded across both scenes; trace limits are per scene. The cumulative audio
duration threshold is checked after native persistence, so it is an acceptance
and stop threshold rather than a hard pre-write ceiling. None of these bounds
limits logs, archives, full-model memory or total compute.

Keep private evidence out of public source: account and Drive identifiers,
absolute media paths, paired reference text and actual provider receipts belong
only in the private packet. Preserve owner quality holds and the canonical
experiment key across renamed packets and fresh scopes.

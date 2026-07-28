# Sprint 1 audiobook 8.9 cutoff impact report

Generated: 2026-07-28
Policy: `sprint1_audiobook_acceptance_v3_89`

## Owner decision

The active overall listening floor is `8.9` for new Sprint 1 Bengali and
English evaluations. Confidence remains `>= 0.90`; ordinary listening
dimensions remain `>= 8.9`; anti-robotic and anti-choppy dimensions remain
`>= 9.2`; fatal flags remain disqualifying.

ASR/manuscript remains `>= 9.7`, coverage remains `>= 0.98`, and exact
opening, ending, order, measured sync, rights, covers, checksum-bound upload,
metadata, ranged endpoint, browser playback, and an empty blocker list remain
mandatory.

## Immediate release audit

No additional Sprint 1 title has an exact full-title package that passes every
gate after lowering only overall listening to `8.9`.

- **The Tell-Tale Heart** has a full listening result of `9.0` and full ASR
  `9.8529`, but ordered-content integrity and downstream delivery are
  incomplete.
- **The Gift of the Magi** has representative listening above `8.9`, but its
  prior full candidate has content/order failures. Its later VoxCPM2 sample
  scored only `8.5` with fatal robotic and choppy flags, while the terminal
  Qwen sample clipped.
- **The Time Machine** has representative listening `9.0`, but emotional
  expression is `8.0` and there is no complete full-title package.
- **Radharani**, **Nishkriti**, **Devdas**, and **Kshudhita Pashan** have
  attractive isolated samples but fail full/representative source fidelity,
  generalization, or downstream gates.
- **The Call of the Wild** generated four OpenAI representative clips, but raw
  ASR scores were `9.6032`, `9.5000`, `9.7041`, and `9.5849`; every passage
  failed exact ordered-content integrity and coverage remained below `0.98`.
  Listening QA was therefore not run.
- **The Secret Garden** passed its four-passage objective screen at exact
  `10.0/1.0` and passed v3.89 representative listening with a minimum overall
  `9.0` at `0.92` confidence and no fatal flags. Its chapter-one checkpoint
  nevertheless failed exact content and measured sync (`9.6262`) after the
  single allowed retained-audio repair because unexpected speech persisted.
  The remaining 26 chapters were not generated and the title remains hidden.

## Net production effect

- Production readers: `32/32`
- Production audiobooks: `4/32`
- Newly eligible on overall listening alone: some incomplete candidates
- Newly full-title release-ready: `0`
- Newly published: `0`
- Hidden audio exposed: `0`

The policy change is active, but it cannot convert a pilot, incomplete
recording, content-mismatched recording, or missing delivery package into a
production audiobook.

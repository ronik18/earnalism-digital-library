# Earnalism original motion model

This is an in-house, scratch-trained **2D skeletal motion research model**. It
predicts joint angles and pelvis height for nine declared actions: idle, walk,
run, point, reach, react, sit, wave and look. NumPy inference drives an original
illustrated character rig. Root travel is an explicit path control; bone lengths
come from forward kinematics. Neither is learned human acting.

The trainer creates original procedural trajectories, splits complete characters
and trajectories before fitting, and saves actual initial/trained numerical
weights, data, source, history, baselines and checksums. No captured person,
copyrighted film, voice recording, pretrained checkpoint, generation service or
membership is required. PyTorch is needed for training; NumPy, Pillow and FFmpeg
support local inference and review. Existing dependencies are reused. Do not
automatically buy, subscribe, allocate paid compute or download a larger model.

## Run and review

Use a new private output folder for every run. Existing outputs are preserved.
The maintained implementation supports explicit data/objective versions; the
exact first GPU implementation remains in `motion_model_v1.py` for reproduction.

```bash
python3 -m scripts.original_motion.motion_model train --device cpu --teacher-version v2 --objective geometry-v2 --characters 48 --variants 2 --frames 64 --hidden 96 --max-steps 4000 --max-seconds 180 --output /PRIVATE/new-motion-run
python3 -m scripts.original_motion.motion_model infer --model-dir /PRIVATE/new-motion-run --action walk --output /PRIVATE/new-walk-prediction
python3 -m scripts.original_motion.learned_rig_render --prediction /PRIVATE/new-walk-prediction/prediction.json --output-dir /PRIVATE/new-walk-review
python3 -m scripts.original_motion.diagnose_motion --model-dir /PRIVATE/new-motion-run --output /PRIVATE/new-motion-diagnostics.json
```

Source paths and report paths must resolve to the exact retained files. A renderer must consume
the actual model prediction, not replace it with the teacher, a pose fixture or
camera movement on a still image. Preserve raw predictions separately from fixed
anatomical clipping and any presentation treatment.

The self-contained Colab notebook embeds the frozen first trainer, verifies its
hash, requires an actual CUDA/autograd probe and exports weights/data/predictions
with an artifact index. It uses preinstalled Torch and mounts no Drive tree.
Its original allocation guard releases only that notebook after 720 seconds;
training is capped at 4,000 steps/420 seconds and worker work at 540 seconds.
Do not reset the allocation clock on export/reconnect. Verify the local archive
and every indexed hash, then release the runtime and verify that it stopped.
Prepared code, a selected GPU dropdown and a successful training log do not prove
that the checkpoint was durably downloaded or the allocation was released.

Colab access/credits remain a separate runtime choice. The 14 November probe used
the owner's existing Pro account and reported 1.15 compute units/hour. No product
was purchased; that session must not be represented as a verified free-tier run.
The local trainer/inference path does not depend on that subscription. Future
GPU runs still need their own actual allocation and applicable usage authority.

Current probe disposition: actual T4 training, the executed notebook, the exact
exported ZIP and all 26 indexed files are durably retained and hash-verified.
After the Mac was unlocked, ordinary Colab controls showed **no active sessions**.
The saved notebook was retrieved through the official Drive HTTPS connector and
its attachment decoded locally; the blocked browser data-URL download was not
repeated. Historical unverified-export/shutdown observations remain in the
earlier receipt, followed by the actual import/release observation. No retraining
or additional allocation was needed. Keep the GPU v1 weights distinct from the
separately retained CPU v2 refinement.

## Improve from evidence

Keep held-out characters, trajectories and inputs fixed during a controlled
comparison. Record changed data/objective/settings, actual new weights and both
successful and regressed metrics. Compare with random weights and the static
action baseline; report per-action joint/target errors, contact drift, raw
velocity/acceleration/jerk, conditioning response and NumPy/Torch parity.
Never optimize repeatedly against the held-out test set and call it independent
acceptance. A future promotion needs a new forward test and actual visual review.

The first real CPU and T4 models learned the synthetic reference. Visual review
still found crouched standing/gait and unsupported sitting. Those are data and
interaction defects: more steps against the same reference do not establish
naturalness. The bounded second experiment changes the original teacher's
standing/support geometry and declares a seat target before inference. Any seat
prop must match that fixed target and the actual predicted hips/feet; moving a
chair to conceal a failed pose is not an accepted repair.

Use the existing book AV feedback record for content-specific findings, binding
the exact candidate/model, source, scope, concrete defect, repair and preserved
attributes. Update title history, decision ledger and sprint learning by reference
to the same result. Only licensed, actually reviewed examples may become future
training data. A feedback entry alone does not train weights. No background
training, standing GPU job or autonomous public publishing is created here.

## Production applicability

These checkpoints and demos remain private research assets. Synthetic reference
accuracy is not human-motion accuracy, premium acting, book comprehension, facial
performance, lip synchronization or full cinematic acceptance. Never silently
insert them into the accepted Open Window film or change its exact narration,
score, timing, illustrations or prior evidence. An eventual motion replacement
requires a separate source-bound candidate and the affected full visual review.
The existing release controller remains the sole GO LIVE authority.

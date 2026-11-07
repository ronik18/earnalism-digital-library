"""Build a self-contained video-only notebook without executing the supplied notebook."""
import hashlib,json,pathlib
BASE=pathlib.Path(__file__).resolve().parent
files={str(p.relative_to(BASE)):p.read_text() for p in [BASE/'viewer_study.py',BASE/'audience_plan.py',BASE/'production_journal.py',BASE/'strict_quality.py',BASE/'caption_preview.py',BASE/'learning_acceptance.py',BASE/'frozen_edition.py',BASE/'participant_preview.py',BASE/'studio.py',BASE/'caption_layout.py',BASE/'audio_derivation.py',BASE/'narration_edit.py',BASE/'music_automation.py',BASE/'audio_balance.py',BASE/'delivery_conform.py',BASE/'pace_review.py',BASE/'score.py',BASE/'chamber_score_v10.py',BASE/'chamber_score_v9.py',BASE/'final_chamber_score.py',BASE/'balanced_score.py',BASE/'chamber_score.py',BASE/'chamber_arrangement.py',BASE/'acoustic_score.py',BASE/'intro.py',BASE/'asr_review.py',BASE/'colab_runner.py',*sorted((BASE/'vendor').glob('*.py')),*sorted((BASE/'config').glob('*.json')),*sorted((BASE/'episodes').glob('*.json'))]}
cells=[]
def md(s):cells.append({'cell_type':'markdown','metadata':{},'source':s.splitlines(True)})
def code(s):cells.append({'cell_type':'code','execution_count':None,'outputs':[],'metadata':{},'source':s.splitlines(True)})
md('''# Earnalism Video Narration Pipeline
**Earnalism — See differently.** Private Qwen Ryan narration, independent timed ASR, verified transfer.

Isolated from the supplied audiobook notebook and every production record. Local original SHA256: `62647ee05557a6eab9fbee3d7c76334da3d9e6b99064b8acb90a80971d408aa4`.

1. Run setup first (CPU; embeds reviewed software, no synthesis).
2. Select a **free CUDA GPU runtime**. If unavailable, stop. No paid compute is authorized. Do not connect a runtime that consumes prepaid units.
3. Set `FREE_RUNTIME_CONFIRMED=True` only after checking the runtime allocation; set `RUN_NARRATION=True` for the private 34-word test. Set `USE_VIDEO_DRIVE=True` to preserve attempts across runtime resets in a new video-only Drive folder; approve Drive access yourself. Without Drive, download outputs before disconnecting and never reset the run to bypass exhausted attempts.
4. Listen to the complete test. No publication approval is granted by generation or ASR.
5. Run alignment and export, then download the ZIP. Local import verifies every transfer hash. Captions use actual recognized word times; discrepancies stop the run.

The current selected voice direction is original B (`original_warm_baritone_v2`); resolve the actual private candidate locally through `evidence/current-private-review.json`. Earlier mature-teacher editions are archives, not generation defaults. Non-fixture episodes require a complete audience plan before model setup: the creator fills the learning promise, distinct format purposes, title/cover hypotheses and scene-bound opening/application plan. Audition selection is not full-recording or publication approval. The refined edition scores an original composition locally using pinned, licensed acoustic instrument notes; no voice cloning or new speech service. Stock Ryan performance: warm, clear, measured and original.
''')
code('''# Video-only configuration; safe Run All defaults
RUN_NARRATION = False
FREE_RUNTIME_CONFIRMED = False
AUTHORIZED_COMPUTE_UNITS = 0.0
OBSERVED_UNITS_PER_HOUR = 0.0
USE_VIDEO_DRIVE = False
RUN_ALIGNMENT_EXPORT = False
EPISODE = 'private-test.json'
RUN_ID = 'private-test-v1'
WALL_BUDGET_SECONDS = 1200
''')
code('''import hashlib, json, pathlib, sys, os
SOFTWARE = pathlib.Path('/content/earnalism-video/software')
SOFTWARE.mkdir(parents=True, exist_ok=True)
FILES = '''+repr(files)+'''
for name, text in FILES.items():
    p = SOFTWARE/name
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists() and p.read_text() != text:
        raise RuntimeError('Existing video software differs: preserve it and inspect before replacement')
    if not p.exists(): p.write_text(text)
if str(SOFTWARE) not in sys.path: sys.path.insert(0, str(SOFTWARE))
print('Video-only software ready:', SOFTWARE)
print('No audiobook notebook or production data was executed or changed.')
''')
code('''if RUN_NARRATION:
    if USE_VIDEO_DRIVE:
        from google.colab import drive
        drive.mount('/content/drive')
        persistent = pathlib.Path('/content/drive/MyDrive/Earnalism_Video_Studio/outputs')
        persistent.mkdir(parents=True, exist_ok=True)
        outputs = SOFTWARE/'outputs'
        if outputs.exists() and not outputs.is_symlink():
            raise RuntimeError('Existing local output folder: preserve it before switching persistence')
        if not outputs.exists(): outputs.symlink_to(persistent, target_is_directory=True)
    if not FREE_RUNTIME_CONFIRMED and AUTHORIZED_COMPUTE_UNITS > 0:
        import threading
        from google.colab import runtime as colab_runtime
        if 'video_runtime_deadline' not in globals():
            video_runtime_deadline = threading.Timer(1800, colab_runtime.unassign)
            video_runtime_deadline.daemon = True
            video_runtime_deadline.start()
    from colab_runner import execute
    folder = execute(SOFTWARE/'episodes'/EPISODE, FREE_RUNTIME_CONFIRMED, WALL_BUDGET_SECONDS, RUN_ID, approved_compute_units=AUTHORIZED_COMPUTE_UNITS, observed_units_per_hour=OBSERVED_UNITS_PER_HOUR)
    from IPython.display import Audio, display
    for wav in sorted((folder/'raw').glob('*.wav')): display(Audio(filename=str(wav)))
    print('PRIVATE narration generated. Listen fully. No approval inferred.', folder)
else:
    print('Safe setup only. Narration disabled; no model installation or GPU generation.')
''')
code('''if RUN_ALIGNMENT_EXPORT:
    import notebook_runtime as runtime
    from colab_runner import align
    from studio import sha
    # Same pinned large-v3 ASR recipe as source notebook, CPU execution.
    asr_python, asr_env = runtime.pip_env('video-asr', [['faster-whisper==1.2.1','av==15.1.0','rapidfuzz==3.14.1','huggingface-hub>=0.34,<1']])
    # Resolve once and retain exact ASR commit for subsequent runs.
    lock = folder/'config/asr-model.json'
    if lock.exists(): revision=json.loads(lock.read_text())['model_revision']
    else:
        output = __import__('subprocess').check_output([asr_python,'-c',"from huggingface_hub import HfApi;print(HfApi().model_info('Systran/faster-whisper-large-v3').sha)"],text=True)
        revision=output.strip()
    model=runtime.snapshot(asr_python,'Systran/faster-whisper-large-v3',revision,lock)
    align(folder,asr_python,model['model_path'],revision)
    import zipfile
    archive = pathlib.Path('/content')/(RUN_ID+'-narration.zip')
    if archive.exists(): raise RuntimeError('Transfer ZIP already exists; preserve before exporting again')
    paths=[p for p in folder.rglob('*') if p.is_file() and p.name not in ('asr-model.json','qwen-job.json')]
    manifest={str(p.relative_to(folder)):sha(p) for p in paths}
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
        for p in paths: z.write(p,str(p.relative_to(folder)))
        z.writestr('transfer-manifest.json',json.dumps(manifest,indent=2))
    print('Transfer ZIP:',archive, 'SHA256:',sha(archive))
    from google.colab import files
    files.download(str(archive))
''')
md('''## Local continuation
Codex imports the downloaded ZIP with `studio.import_narration`, then runs `studio.py render <imported-folder>` from this project. This produces portrait and landscape H.264/AAC MP4, a captioned portrait, SRT/VTT, transcript, references, thumbnails, YouTube metadata, technical report, delivery manifest, and a private local watch page. Full decode and audible-soundtrack checks are mandatory. Local download delivery must pass byte hash and decode checks before reporting delivery success.

Publication remains draft until factual, rights, voice, audiovisual, technical and delivery review bind the final manifest. Private test fixtures cannot publish. The existing Earnalism website/storage adapter must be inspected and integrated separately after local verification; this notebook has no production write capability.
''')
notebook={'nbformat':4,'nbformat_minor':5,'metadata':{'colab':{'name':'Earnalism_Video_Narration_Pipeline.ipynb'},'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'}},'cells':cells}
for i,c in enumerate(cells):c['id']=f'video-{i:02}'
(BASE.parent/'Earnalism_Video_Narration_Pipeline.ipynb').write_text(json.dumps(notebook,indent=1,ensure_ascii=False)+'\n')

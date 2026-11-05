"""Append the pinned visual ident with FFmpeg; never read/change episode audio."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess

BASE = Path(__file__).resolve().parents[1]
IDENT = BASE / 'assets/standard-intro/v1/portrait.mp4'
IDENT_SHA = '8ffd07e69bd4715dc06e26eccaf7b884f01793ea411f736b04486ebc1ab7470e'
IDENT_FILTER = ('crop=960:1800:60:60,scale=902:1692:flags=lanczos,'
                'pad=1080:1920:30:114:color=0xfff9ed,'
                'fillborders=left=30:right=148:top=114:bottom=114:mode=smear,'
                'setsar=1,fps=30,format=yuv420p')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def probe(path, count=False):
    command = ['ffprobe', '-v', 'error'] + (['-count_frames'] if count else [])
    result = subprocess.run(command + ['-show_streams', '-show_format', '-of', 'json', str(path)],
                            capture_output=True, text=True, check=True)
    if result.stderr.strip():
        raise ValueError('Video probe/decode reported errors: ' + result.stderr)
    return json.loads(result.stdout)


def append(folder, expected_body_frames):
    folder = Path(folder).resolve()
    if type(expected_body_frames) is not int or expected_body_frames <= 0:
        raise ValueError('Positive actual body-frame count required')
    body = folder / 'body-animation.mp4'
    output = folder / 'animation.mp4'
    ident = folder / 'ident-animation.mp4'
    listing = folder / 'visual-concat.txt'
    record = folder / 'visual-append.json'
    if any(p.exists() for p in (output, ident, listing, record)):
        raise ValueError('Existing visual append preserved; use a fresh folder')
    if sha(IDENT) != IDENT_SHA:
        raise ValueError('Approved portrait ident changed')
    info = probe(body)
    streams = info['streams']
    if len(streams) != 1 or streams[0]['codec_type'] != 'video':
        raise ValueError('Body must contain only one silent video stream')
    video = streams[0]
    expected = (1080, 1920, 'h264', 'yuv420p', '30/1', '1/90000')
    actual = tuple(video[k] for k in ('width', 'height', 'codec_name', 'pix_fmt', 'r_frame_rate', 'time_base'))
    if actual != expected or int(video.get('nb_frames', -1)) != expected_body_frames:
        raise ValueError('Body dimensions, codec, timebase or frame count differ from the render plan')
    if abs(float(video['duration']) - expected_body_frames / 30) > .002:
        raise ValueError('Body duration does not match actual padded frames')
    before = sha(body)
    subprocess.run(['ffmpeg', '-v', 'error', '-n', '-i', str(IDENT), '-map', '0:v:0',
        '-vf', IDENT_FILTER,
        '-frames:v', '90', '-an', '-c:v', 'libx264', '-crf', '20', '-profile:v', 'high',
        '-colorspace', 'bt709', '-color_trc', 'bt709', '-color_primaries', 'bt709',
        '-video_track_timescale', '90000', '-movflags', '+faststart', str(ident)], check=True)
    quote = lambda p: str(p).replace("'", "'\\''")
    listing.write_text("file '" + quote(body) + "'\nfile '" + quote(ident) + "'\n")
    subprocess.run(['ffmpeg', '-v', 'error', '-n', '-f', 'concat', '-safe', '0', '-i', str(listing),
        '-map', '0:v:0', '-c:v', 'copy', '-an', '-video_track_timescale', '90000',
        '-movflags', '+faststart', str(output)], check=True)
    completed = probe(output, count=True)
    final = completed['streams'][0]
    if len(completed['streams']) != 1 or int(final['nb_read_frames']) != expected_body_frames + 90:
        raise ValueError('Final animation lost/added frames or acquired an audio stream')
    if abs(float(final['duration']) - (expected_body_frames + 90) / 30) > .002:
        raise ValueError('Final visual duration differs from padded narration plus three-second ident')
    if sha(body) != before:
        raise ValueError('Body changed during append')
    result = {'method': 'FFmpeg H264 concat demuxer; body packets copied, only ident reframed',
              'body_sha256': before, 'approved_ident_sha256': IDENT_SHA,
              'ident_derivative_sha256': sha(ident), 'animation_sha256': sha(output),
              'body_frames': expected_body_frames, 'ident_frames': 90,
              'decoded_final_frames': int(final['nb_read_frames']),
              'portrait_ident_filter': IDENT_FILTER,
              'portrait_ident_essential_review_rect': {'x': 77, 'y': 650, 'width': 818, 'height': 550},
              'ident_graphics_scope': 'Pinned lockup reframed; only empty outer border cropped, background edges extended. Essential review box is a scoped aid; final pixels still require inspection.',
              'audio_processed': False, 'publication_approved': False}
    record.write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    parser.add_argument('body_frames', type=int)
    args = parser.parse_args()
    print(json.dumps(append(args.folder, args.body_frames), indent=2))

# Video Square-Crop & Cleanup Pipeline

Batch-processes `.mp4`/`.mov` training videos for motion-capture/pose work:
detects the most central person in each clip, crops to a stable 1:1 square
around them, trims long clips down to a fixed duration, and flags any video
where more than one person ever appears in frame.

Built for prepping hand-shot training footage before feeding it into a
pose-estimation pipeline (MediaPipe Pose, GVHMR, etc.) — square aspect ratio
and single-subject framing are common input requirements for that kind of
model.

## What it does

For every video in `--input_dir`:

1. **Samples 8 frames** spread across the middle 80% of the clip (skips the
   first/last 10% to avoid intros/outros).
2. **Runs pose detection** (MediaPipe `PoseLandmarker`, multi-person) on each
   sampled frame.
3. **Multi-person check:** if any single sampled frame shows 2 or more
   people, the original video is **copied** (never deleted, never moved) into
   a `flagged/` subfolder for manual review, and skipped entirely — no crop,
   no encode.
4. **Picks the most central person** in every frame where exactly the
   detection step succeeded — if multiple people are present, whichever
   detected person's bounding box center is closest to the frame's
   geometric center is selected.
5. **Computes one stable square crop window** for the whole video, using the
   median center position and the largest bounding box seen across all
   sampled frames — this avoids a jittery crop that moves frame-to-frame.
6. **Crops and scales** the full video to that square window via `ffmpeg`,
   output at `--output_size` (default `720x720`).
7. **Trims to `--max_duration` seconds** (default `10`) if the source is
   longer. Videos already at or under that length are left at their
   original length, untouched.
8. If no person is detected at all in any sampled frame, falls back to a
   plain geometric center-crop (configurable via `--fallback`).

Every run produces a `_processing_log.txt` in the output folder listing the
per-video outcome, crop coordinates, detection count, and any trim/flag
notes — check this after every run, don't just trust a clean exit.

## Requirements

- Python 3.9+
- [ffmpeg](https://ffmpeg.org/) and `ffprobe` available on your system `PATH`
- Python packages:

  ```bash
  pip install mediapipe opencv-python numpy
  ```

  On Linux, if you hit an externally-managed-environment error:

  ```bash
  pip install mediapipe opencv-python numpy --break-system-packages
  ```

**First run only:** the script auto-downloads the MediaPipe pose model
(`pose_landmarker_lite.task`, ~5–10MB) into the same folder as the script.
This needs a normal internet connection and only happens once.

## Usage

```bash
python3 crop_to_square.py --input_dir /path/to/videos --output_dir /path/to/output
```

### Options

| Flag | Default | Description |
|---|---|---|
| `--input_dir` | *(required)* | Folder containing source `.mp4`/`.mov` files |
| `--output_dir` | *(required)* | Folder for cropped output + logs (created if it doesn't exist) |
| `--output_size` | `720` | Final square resolution in pixels (e.g. `512`, `1080`) |
| `--samples` | `8` | Number of frames sampled per video for person detection |
| `--margin` | `1.4` | Padding around the detected person's bounding box (`1.0` = tight crop, `1.4` = 40% extra room — raise this if subjects' arms/legs extend past the detected box, e.g. mid-strike) |
| `--fallback` | `center` | What to do if no person is detected in any sampled frame: `center` (plain geometric center-crop) or `skip` (don't process the video at all) |
| `--max_duration` | `10` | Trim output to this many seconds if the source is longer. Set to `0` to disable trimming. |
| `--flag_multi_person` | *(on by default)* | Copy any video with 2+ people detected in one frame to a `flagged/` subfolder instead of cropping it |
| `--no_flag_multi_person` | — | Disable multi-person flagging; process every video regardless of person count |

### Example: smaller output, looser margin, no trimming

```bash
python3 crop_to_square.py \
  --input_dir ./raw_clips \
  --output_dir ./processed \
  --output_size 512 \
  --margin 1.6 \
  --max_duration 0
```

## Output structure

```
output_dir/
├── clip1.mp4              # cropped + trimmed
├── clip2.mp4
├── flagged/
│   └── clip7.mp4           # copy of original — 2+ people detected, not processed
└── _processing_log.txt     # per-video outcome, crop box, detection counts
```

Your original source files are **never modified, moved, or deleted** —
everything in `output_dir` is a new copy.

## After running

Don't trust a clean exit blindly. Open `_processing_log.txt` and check for:

- **`FAILED`** entries — real errors (bad codec, corrupted file, etc.); the
  logged ffmpeg/ffprobe error text usually tells you exactly what went wrong.
- **`FLAGGED`** entries — review these manually in the `flagged/` folder.
  Detection runs on only 8 sampled frames, so a flag can occasionally be a
  false positive (a shadow, reflection, or momentary noisy detection) rather
  than a real second person — that's why originals are copied, not deleted.
- **Low detection counts** (e.g. `1/8` or `2/8`) on videos marked `OK` — the
  crop for that video was computed from very little data and may be
  unreliable even though the script didn't error out. Worth a manual look
  before trusting it as clean training data.

## Known limitations

- Detection is **sampled**, not per-frame — a person who appears only
  briefly outside the 8 sampled timestamps won't be caught by the
  multi-person flag.
- One **fixed crop window per video** — if the subject moves dramatically
  across the frame over the clip's duration, a single static crop may not
  keep them centered throughout. This is a deliberate tradeoff to avoid a
  jittery, frame-by-frame-tracked crop.
- Requires a clear, internet-reachable model download on first run.

#!/usr/bin/env python3
"""
Batch-crops MP4s to a 1:1 square centered on whichever person is most
central in the frame. One stable crop window is computed per video
(sampled across several frames) so the output doesn't jitter.

Usage:
    python3 crop_to_square.py --input_dir /path/to/videos --output_dir /path/to/output

Optional:
    --output_size 720        # final square resolution (default 720x720)
    --samples 8               # how many frames to sample per video for detection
    --margin 1.4              # how much padding around the detected person (1.0 = tight, 1.4 = 40% padding)
    --fallback center         # what to do if no person is detected: 'center' (geometric center crop) or 'skip'
    --max_duration 10         # trim output to this many seconds if source is longer;
                              # videos already <= this length are left untouched.
                              # Set to 0 to disable trimming entirely. Default 10.
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import os
import urllib.request

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import PoseLandmarker, PoseLandmarkerOptions, RunningMode

MODEL_URL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"
MODEL_PATH = Path(__file__).parent / "pose_landmarker_lite.task"


def ensure_model():
    """Download the PoseLandmarker model file once, if not already present."""
    if MODEL_PATH.exists():
        return
    print(f"Downloading pose model to {MODEL_PATH} (one-time, ~5-10MB)...")
    urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
    print("Model downloaded.")


def make_landmarker():
    options = PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(MODEL_PATH)),
        running_mode=RunningMode.IMAGE,
        num_poses=5,  # detect up to 5 people per frame so we can pick the most central
        min_pose_detection_confidence=0.5,
    )
    return PoseLandmarker.create_from_options(options)


def get_video_info(path: Path):
    """Get width, height, duration, frame count via ffprobe."""
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,nb_frames,duration,r_frame_rate",
        "-of", "json", str(path),
    ]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(out.stdout)
    stream = data["streams"][0]
    width = int(stream["width"])
    height = int(stream["height"])
    duration = float(stream.get("duration", 0) or 0)
    return width, height, duration


def sample_frame_indices(duration: float, fps_guess: float, n_samples: int):
    """Pick n_samples timestamps spread across the video (skip the very start/end)."""
    if duration <= 0:
        return [0.5] * n_samples  # fallback: just grab frame 0 repeatedly
    # spread samples between 10% and 90% of the video to avoid intros/outros
    start, end = duration * 0.1, duration * 0.9
    if n_samples == 1:
        return [duration * 0.5]
    return list(np.linspace(start, end, n_samples))


def detect_person_centers(path: Path, timestamps, width, height, landmarker):
    """
    For each timestamp, grab the frame and run PoseLandmarker (multi-person).
    For frames with multiple detected people, picks whichever pose's bounding
    box center is closest to the frame's geometric center -- this is the
    "person in the middle" selection logic.

    Returns:
        results_list: list of (cx, cy, bbox_w, bbox_h) for the chosen
                       (most-central) person, one entry per timestamp where
                       at least one person was found.
        max_people_in_one_frame: the highest number of people detected
                       simultaneously in any single sampled frame. Used to
                       flag videos that ever show more than one person.
    """
    cap = cv2.VideoCapture(str(path))
    results_list = []
    max_people_in_one_frame = 0
    frame_center = np.array([width / 2, height / 2])

    for t in timestamps:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, frame = cap.read()
        if not ok:
            continue
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = landmarker.detect(mp_image)

        if not result.pose_landmarks:
            continue

        max_people_in_one_frame = max(max_people_in_one_frame, len(result.pose_landmarks))

        # result.pose_landmarks is a list of per-person landmark lists
        best_dist = None
        best_box = None
        for person_landmarks in result.pose_landmarks:
            xs = [lm.x for lm in person_landmarks]
            ys = [lm.y for lm in person_landmarks]
            x_min, x_max = min(xs) * width, max(xs) * width
            y_min, y_max = min(ys) * height, max(ys) * height
            cx = (x_min + x_max) / 2
            cy = (y_min + y_max) / 2
            dist = np.linalg.norm(np.array([cx, cy]) - frame_center)
            if best_dist is None or dist < best_dist:
                best_dist = dist
                best_box = (cx, cy, x_max - x_min, y_max - y_min)

        if best_box is not None:
            results_list.append(best_box)

    cap.release()
    return results_list, max_people_in_one_frame


def compute_crop_box(detections, width, height, margin):
    """
    Given per-frame (cx, cy, bbox_w, bbox_h) detections, compute one stable
    square crop box (x, y, side_length) in pixel coords, clamped to the frame.
    If no detections, returns None (caller decides fallback).
    """
    if not detections:
        return None

    cxs = [d[0] for d in detections]
    cys = [d[1] for d in detections]
    bws = [d[2] for d in detections]
    bhs = [d[3] for d in detections]

    # use the median center across sampled frames -> robust to one bad detection
    cx = float(np.median(cxs))
    cy = float(np.median(cys))
    # use the max bbox extent seen -> crop wide enough to cover the person
    # even in their most spread-out (e.g., mid-punch, arms out) pose
    bbox_extent = max(np.max(bws), np.max(bhs))

    side = bbox_extent * margin
    side = min(side, min(width, height))  # never exceed frame bounds
    side = max(side, min(width, height) * 0.3)  # don't crop absurdly tight

    x = cx - side / 2
    y = cy - side / 2

    # clamp so the crop box stays inside the frame
    x = max(0, min(x, width - side))
    y = max(0, min(y, height - side))

    return int(round(x)), int(round(y)), int(round(side))


def fallback_center_box(width, height):
    """Geometric center square crop, used when no person is detected."""
    side = min(width, height)
    x = (width - side) // 2
    y = (height - side) // 2
    return x, y, side


def crop_video_ffmpeg(input_path: Path, output_path: Path, x, y, side, output_size,
                       duration: float, max_duration: float):
    """
    Run ffmpeg to crop to (x, y, side, side) then scale to output_size x output_size.
    If duration > max_duration, trims output to the first max_duration seconds.
    If duration <= max_duration (or max_duration is None/0), no trimming is applied.
    """
    cmd = ["ffmpeg", "-y", "-i", str(input_path)]

    will_trim = max_duration and duration > max_duration
    if will_trim:
        cmd += ["-t", str(max_duration)]

    cmd += [
        "-vf", f"crop={side}:{side}:{x}:{y},scale={output_size}:{output_size}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0, result.stderr, will_trim


def process_one_video(input_path: Path, output_path: Path, n_samples, margin,
                       output_size, fallback_mode, max_duration, flagged_dir,
                       landmarker, log):
    try:
        width, height, duration = get_video_info(input_path)
    except Exception as e:
        log.append((input_path.name, "FAILED", f"ffprobe error: {e}"))
        return False

    timestamps = sample_frame_indices(duration, 30.0, n_samples)
    detections, max_people = detect_person_centers(input_path, timestamps, width, height, landmarker)

    # Flag and set aside any video where 2+ people were ever seen in the same
    # sampled frame -- moved to flagged_dir for manual review, never deleted,
    # and never cropped/encoded (no point spending ffmpeg time on it).
    if flagged_dir is not None and max_people >= 2:
        flagged_path = flagged_dir / input_path.name
        shutil.copy2(input_path, flagged_path)
        log.append((input_path.name, "FLAGGED",
                    f"{max_people} people detected in at least one sampled frame -> moved to {flagged_dir.name}/"))
        return False

    box = compute_crop_box(detections, width, height, margin)

    used_fallback = False
    if box is None:
        if fallback_mode == "skip":
            log.append((input_path.name, "SKIPPED", "no person detected"))
            return False
        box = fallback_center_box(width, height)
        used_fallback = True

    x, y, side = box
    ok, err, trimmed = crop_video_ffmpeg(input_path, output_path, x, y, side,
                                          output_size, duration, max_duration)
    if not ok:
        log.append((input_path.name, "FAILED", f"ffmpeg error: {err[-500:]}"))
        return False

    status = "OK (fallback center crop, no person found)" if used_fallback else "OK"
    trim_note = f", trimmed {duration:.1f}s->{max_duration:.1f}s" if trimmed else ""
    log.append((input_path.name, status,
                f"crop=({x},{y},{side}) detections={len(detections)}/{n_samples}{trim_note}"))
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input_dir", required=True)
    ap.add_argument("--output_dir", required=True)
    ap.add_argument("--output_size", type=int, default=720)
    ap.add_argument("--samples", type=int, default=8)
    ap.add_argument("--margin", type=float, default=1.4)
    ap.add_argument("--fallback", choices=["center", "skip"], default="center")
    ap.add_argument("--max_duration", type=float, default=10.0,
                     help="Trim output to this many seconds if the source is longer. "
                          "Videos already at or under this length are left full-length. "
                          "Set to 0 to disable trimming entirely.")
    ap.add_argument("--flag_multi_person", action="store_true", default=True,
                     help="If set (default), videos where any sampled frame shows 2+ "
                          "people are copied to a 'flagged' subfolder of output_dir for "
                          "manual review, and are NOT cropped/encoded. Originals are "
                          "never deleted or modified.")
    ap.add_argument("--no_flag_multi_person", dest="flag_multi_person", action="store_false",
                     help="Disable multi-person flagging; process every video normally "
                          "regardless of how many people are detected.")
    args = ap.parse_args()

    in_dir = Path(args.input_dir)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    flagged_dir = out_dir / "flagged"
    if args.flag_multi_person:
        flagged_dir.mkdir(parents=True, exist_ok=True)

    videos = sorted(in_dir.glob("*.mp4")) + sorted(in_dir.glob("*.MP4")) + \
             sorted(in_dir.glob("*.mov")) + sorted(in_dir.glob("*.MOV"))
    if not videos:
        print(f"No .mp4 or .mov files found in {in_dir}")
        sys.exit(1)

    ensure_model()
    landmarker = make_landmarker()

    print(f"Found {len(videos)} videos. Processing...\n")
    log = []
    for i, vid in enumerate(videos, 1):
        out_path = out_dir / (vid.stem + ".mp4")
        print(f"[{i}/{len(videos)}] {vid.name} ...", end=" ", flush=True)
        process_one_video(vid, out_path, args.samples, args.margin,
                           args.output_size, args.fallback, args.max_duration,
                           flagged_dir if args.flag_multi_person else None,
                           landmarker, log)
        print(log[-1][1])

    landmarker.close()

    print("\n--- Summary ---")
    ok_count = sum(1 for _, status, _ in log if status.startswith("OK"))
    fallback_count = sum(1 for _, status, _ in log if "fallback" in status)
    flagged_count = sum(1 for _, status, _ in log if status == "FLAGGED")
    failed_count = sum(1 for _, status, _ in log if status in ("FAILED", "SKIPPED"))
    print(f"Succeeded: {ok_count} (of which {fallback_count} used center fallback)")
    print(f"Flagged (2+ people detected, copied to flagged/ folder): {flagged_count}")
    print(f"Failed/Skipped: {failed_count}")

    log_path = out_dir / "_processing_log.txt"
    with open(log_path, "w") as f:
        for name, status, detail in log:
            f.write(f"{name}\t{status}\t{detail}\n")
    print(f"\nFull log written to {log_path}")


if __name__ == "__main__":
    main()

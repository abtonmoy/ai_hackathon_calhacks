# AprilTag Jab Capture (the path we chose)

Capture a human jab with AprilTags and turn it into a G1 reference motion —
**without GMR or SMPL**. Tag-pair relative rotations *are* the joint angles, so we
write the G1 CSV directly and feed the existing `../scripts/12_to_npz.sh` onward.

```
phone video
  -> 02_track.py        AprilTag 6-DoF per frame      -> tag_poses.npz
     -> 03_tags_to_g1_csv.py  relative-rotation solve -> jab.csv   (TESTED)
        -> ../scripts/20_validate_motion.py   (GATE)
           -> ../scripts/12_to_npz.sh -> 30_train.sh -> 31_play.sh -> real G1
```
> The GMR scripts (`10_retarget.sh`, `11_pkl_to_csv.py`) are NOT used on this
> path; they remain as a markerless fallback.

## Why AprilTag, not QR
QR encodes data → needs high res, dies under motion blur/rotation. AprilTag is a
fiducial built for real-time 6-DoF pose: fast, blur-tolerant, unique IDs, native
in OpenCV/pupil-apriltags. Since we use **relative** rotations between tags, the
joint angles are robust to rough camera calibration.

## Physical setup
- Print `tag36h11` tags, each **rigidly** mounted on a flat backing (foamcore).
  Measure the black-square size and put it in `AT_TAG_SIZE_M`.
- Strap one tag per segment on bony/flat spots. Start minimal (jabbing arm):
  | Tag ID | Segment (`body_map.BODY`) | Place on |
  |--------|---------------------------|----------|
  | 0 | torso | sternum / chest |
  | 1 | r_upperarm | mid right upper arm |
  | 2 | r_forearm | mid right forearm |
  | 3 | r_hand (optional) | back of glove |
- Tags must stay **flat and not rotate on the limb**. Face them toward the camera.
- Good even lighting, plain background, full upper body in frame, 60 fps if possible.
- **Calibration frame:** hold a still guard pose for ~1 s at the start. All joint
  angles are measured relative to it (`--calib-frame 0`).

## Run it
```bash
source config.env                       # ../scripts/config.env also sources WORK
# 1) detect tags
uv run --with opencv-python,pupil-apriltags,numpy python 02_track.py \
    --video "$AT_VIDEO" --out "$AT_POSES" \
    --family "$AT_FAMILY" --tag-size "$AT_TAG_SIZE_M" --hfov-deg "$AT_HFOV_DEG"
#    -> check per-tag detection rate is high (>80%)

# 2) solve to a G1 reference CSV (uses LAFAN1 header for exact joint order)
uv run --with numpy,scipy python 03_tags_to_g1_csv.py \
    --poses "$AT_POSES" --out "$AT_CSV" \
    --template-csv "$AT_TEMPLATE_CSV" --calib-frame "$AT_CALIB_FRAME"

# 3) gate, then hand off to the shared G1 pipeline
python ../scripts/20_validate_motion.py "$AT_CSV" --fps "$AT_FPS" --dof 29
bash ../scripts/12_to_npz.sh "$AT_CSV"
bash ../scripts/30_train.sh
bash ../scripts/31_play.sh               # eyeball the reference + trained policy
```

## Tuning (expect one pass of this)
Edit `body_map.py`:
- **Wrong-direction joint** → flip its entry in `signs`.
- **Axes swapped** (pitch acts like roll) → change the group's Euler `seq`
  (`YXZ`, `ZXY`, …) or the per-joint axis letter.
- **Add joints** → add a JOINT_GROUP (e.g. left arm, waist) once the right arm is clean.
- **Joint name mismatch** → 03 errors and prints the template's joint columns;
  rename `body_map` joints to match exactly.
Watch `31_play.sh` in sim — the reference overlay tells you immediately if an
axis/sign is off. The motion validator catches degrees-vs-radians and base drift.

## Status
`03_tags_to_g1_csv.py` is **tested**: synthetic shoulder(0.5 rad)+elbow(1.2 rad)
sweeps recover to machine precision and the output passes the validator.
`02_track.py` needs real video to exercise (no synthetic camera here).

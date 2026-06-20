# Jab Capture Guide — Markerless (GVHMR)

For the person filming. No special gear, no markers — a phone, a tripod, and 20
minutes. Follow this and the footage will reconstruct cleanly into a G1 motion.

---

## 0. What we're capturing & why the angle matters
We film one person throwing a **boxing jab**, standing in place. A vision model
(GVHMR) turns the video into a 3D body motion → retargeted to the Unitree G1 →
the robot learns to throw it.

**The one thing that makes or breaks this:** GVHMR is a *single-camera* model and
its weak spot is **depth** (motion straight toward or away from the lens). A jab
is a forward punch. So we film from the **side**, where the punch travels *across*
the frame instead of *into* it. Get this right and everything else is forgiving.

---

## 1. Equipment checklist
- [ ] Phone with a decent camera (any modern phone is fine)
- [ ] **Tripod** or a stable surface (the camera must NOT move during a take)
- [ ] ~4 × 3 m of clear floor space
- [ ] Good lighting (bright, even — daylight or overhead room lights)
- [ ] The person throwing the jab, in **fitted clothing**
- [ ] (Optional) a second phone for a backup angle

---

## 2. Space & environment
- [ ] **Plain, uncluttered background** (a wall is ideal). Avoid mirrors,
      busy patterns, other people walking behind.
- [ ] **Even lighting, no harsh shadows.** Don't stand right in front of a bright
      window (backlight wrecks the silhouette).
- [ ] Floor clear of clutter so the **feet are clearly visible**.
- [ ] Subject has room to fully extend the arm without hitting anything.

---

## 3. Camera placement (the critical part)

```
            (plain wall)
   ┌─────────────────────────────┐
   │                             │
   │        P  ──►  (jab goes    │      P = person, facing this way ─►
   │       /|\      forward,     │      Jab extends LEFT→RIGHT across frame
   │       / \      across frame)│
   │                             │
   └─────────────────────────────┘
                 ▲
                 │  ~3–4 m, perpendicular to the punch
                 │
              [ CAMERA ]   ← on tripod, chest height, LEVEL (no tilt)
```

- [ ] **Side view (90°):** the camera looks at the person's **profile**. The jab
      travels **left→right across the frame**, never toward the lens.
- [ ] **Distance ~3–4 m:** the **entire body, head to feet, stays in frame for the
      whole motion**, with ~0.5 m margin above the head and below the feet, plus
      horizontal room for the arm to fully extend.
- [ ] **Height ≈ chest level (1.2–1.4 m), camera perfectly level** — no tilting up
      or down. Prop the tripod to the right height rather than angling it.
- [ ] **Camera locked down — zero movement** during a take (we run GVHMR with SLAM
      off, which assumes a static camera).
- [ ] **Orientation:** landscape if the whole body + arm extension fits; switch to
      portrait only if the room is too tight to get head-to-feet otherwise.

**Optional second camera:** a **45° front-side (¾) angle** as a backup take. We
process each clip separately and keep whichever reconstructs best — GVHMR does NOT
merge two views, so this is just insurance, not a stereo rig.

### Do NOT film from:
- ✗ Head-on / front (punch goes straight at the lens = worst case)
- ✗ Directly behind
- ✗ High or low angles, any tilt, fisheye/ultra-wide distortion
- ✗ Handheld / moving camera

---

## 4. Camera settings
- [ ] **60 fps** (a jab is fast; more frames = smoother motion). 30 fps works if 60
      isn't available.
- [ ] **1080p** is plenty (4K just makes huge files; not needed).
- [ ] Lock focus/exposure if your camera app allows (prevents mid-take refocus).
- [ ] Turn OFF any "beauty"/face-smoothing filters.

---

## 5. Subject prep
- [ ] **Fitted clothing** — t-shirt + shorts/leggings is ideal. **Avoid baggy
      clothes, skirts, long coats** (they hide the body shape the model needs).
- [ ] Hair tied back if it covers the face/shoulders.
- [ ] Shoes on, feet clearly distinct from the floor.
- [ ] Whole body visible — nothing cropped at the top of the head or the feet.

---

## 6. How to throw the jab (motion protocol)
Each take is ONE short sequence, ~4–6 seconds:

1. **Hold a still guard stance for ~1 full second** at the start. ← important: this
   is the calibration/neutral pose. Hands up, side-on to the camera.
2. **Throw the jab** — lead arm extends straight forward to full reach.
3. **Snap it back** to guard.
4. Hold guard briefly, then relax.

Rules that keep it trainable + safe on the robot:
- [ ] **Feet planted — do NOT step, shuffle, or pivot off the ground.** Standing
      jab only. (This is what makes it safe to run on the real G1.)
- [ ] Keep it **clean and deliberate** — a crisp jab beats a flurry.
- [ ] **Stay fully in frame** the entire take, including the arm at full extension.
- [ ] Same person, same stance, same spot across takes.

---

## 7. Take protocol
- [ ] Shoot **5–10 takes.** They're cheap; we keep the best 1–2.
- [ ] Before each take, say the take number out loud or hold up fingers (a "slate")
      so clips are easy to sort later.
- [ ] A little variation across takes is fine (speed, height) but keep the **same
      basic jab** — we want one clean motion, not ten different ones.
- [ ] If using two cameras, **start both before** the guard pose so the take is
      captured from both angles.

---

## 8. On-set QC — check BEFORE you tear down
Play back 2–3 takes on the phone and confirm:
- [ ] Whole body (head to feet) in frame the **entire** take, including full punch
- [ ] Camera was **side-on**, level, and **didn't move**
- [ ] Subject is **sharp**, not motion-blurred into a smear at full extension
- [ ] Lighting even; face and limbs clearly visible; no heavy backlight
- [ ] At least **2 clean takes** you're happy with

If anything's off, reshoot now — it's far cheaper than discovering it later.

---

## 9. Files & handoff
- [ ] Transfer the **original video files** (no compression, no screen-recording,
      no social-media re-encode — those destroy quality).
- [ ] Name them clearly: `jab_side_take03.mp4`, `jab_34_take02.mp4`, etc.
- [ ] Hand the best clip to the pipeline as `JAB_VIDEO` in `g1/config.env`.

---

## 10. Common failure modes → fix
| Symptom in the footage | Fix |
|---|---|
| Punch looks foreshortened / arm vanishes | You filmed too front-on → go more **side-on** |
| Feet or head cut off at full extension | Move camera **back**, re-frame for full body |
| Blurry at the fastest part of the punch | Raise to **60 fps**, add light, lock exposure |
| Body blends into background | Plainer background / better contrast in clothing |
| Reconstruction drifts across the floor | Camera **moved** mid-take, or subject **stepped** — redo, keep both static |
| Baggy clothing → wrong body shape | Re-shoot in **fitted** clothes |

---

## What happens next (not your job, just context)
The clip feeds `g1/scripts/09_gvhmr.sh` → `hmr4d_results.pt` → GMR retarget →
validated → trained into a G1 jab policy. A clean side-on take with the whole body
in frame is 90% of the battle. Thanks for nailing it.

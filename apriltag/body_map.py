"""Tag → G1 joint mapping for the AprilTag jab capture.

Edit this to match (a) where you physically stick each tag, and (b) the joint
names in your LAFAN1 template CSV header. The solver computes each JOINT_GROUP's
child-vs-parent relative rotation, subtracts the calibration (guard) pose, and
decomposes the leftover rotation into Euler angles assigned to the listed joints.

Standing jab = feet planted. We drive the upper body from tags and hold legs +
the non-driven joints at DEFAULT_STANCE. Start with ONE arm (the jabbing arm) —
it's the whole skill — then add the other arm / waist if markerless-grade detail
is wanted.
"""

# Physical tag placement: AprilTag ID -> body segment it's strapped to.
# Put tags on rigid spots (bony, flat): sternum, mid-upper-arm, mid-forearm, glove.
BODY = {
    0: "torso",          # sternum / chest plate
    1: "r_upperarm",     # right upper arm
    2: "r_forearm",      # right forearm
    3: "r_hand",         # back of glove (optional; sharpens wrist)
}

# Each group: relative rotation of `child` tag w.r.t. `parent` tag, decomposed
# with scipy Euler `seq`, assigned in order to `joints` (with optional sign flip).
# `seq` letters are intrinsic axes of the PARENT tag frame — you WILL tune these
# by watching play.py and flipping a sign/axis when a joint moves the wrong way.
JOINT_GROUPS = [
    {   # shoulder: torso -> upper arm, 3-DoF
        "parent": "torso", "child": "r_upperarm",
        "seq": "YXZ",
        "joints": ["right_shoulder_pitch_joint",
                   "right_shoulder_roll_joint",
                   "right_shoulder_yaw_joint"],
        "signs": [1, 1, 1],
    },
    {   # elbow: upper arm -> forearm, 1-DoF hinge
        "parent": "r_upperarm", "child": "r_forearm",
        "seq": "Y",
        "joints": ["right_elbow_joint"],
        "signs": [1],
    },
]

# Held fixed (radians) unless driven above. Names must match the template header.
# 0.0 everywhere = neutral standing default; tweak the guard stance if wanted.
DEFAULT_STANCE = {}     # empty -> every non-driven joint defaults to 0.0

# Fixed floating-base for a planted standing jab.
ROOT_HEIGHT_M = 0.74

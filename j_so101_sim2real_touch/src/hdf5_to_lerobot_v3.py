#!/usr/bin/env python
"""Lightweight converter: IsaacLab HDF5 (leisaac format) → LeRobot v3.0

Reads HDF5 files produced by our IsaacLab data collection,
outputs LeRobot v3.0 parquet + videos + meta format.

Does NOT require Isaac AppLauncher or leisaac modules.

Usage:
    python hdf5_to_lerobot_v3.py \
        --hdf5_file /path/to/dataset.hdf5 \
        --output_dir /path/to/output \
        --repo_id local/sim_act_test \
        --fps 30 \
        --task pick_and_place \
        --cameras camera1 camera2
"""

import argparse
import os
import sys
from pathlib import Path

import h5py
import numpy as np
import torch

from lerobot.datasets.lerobot_dataset import LeRobotDataset


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--hdf5_file", type=str, required=True)
    parser.add_argument("--output_dir", type=str, required=True)
    parser.add_argument("--repo_id", type=str, default="local/sim_act_test")
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--task", type=str, default="pick_and_place")
    parser.add_argument("--cameras", type=str, nargs="*", default=["camera1", "camera2"])
    parser.add_argument("--state_dim", type=int, default=6)
    parser.add_argument("--vcodec", type=str, default="libsvtav1")
    return parser.parse_args()


def main():
    args = parse_args()
    hdf5_file = Path(args.hdf5_file)
    output_dir = Path(args.output_dir)

    if not hdf5_file.exists():
        print(f"ERROR: HDF5 file not found: {hdf5_file}")
        sys.exit(1)

    # Read first episode to get image dimensions
    with h5py.File(str(hdf5_file), "r") as f:
        data_group = f["data"]
        demo_names = list(data_group.keys())
        if not demo_names:
            print("ERROR: No episodes found in HDF5")
            sys.exit(1)

        first_demo = data_group[demo_names[0]]
        img_h, img_w = first_demo[f"obs/{args.cameras[0]}"].shape[1], first_demo[f"obs/{args.cameras[0]}"].shape[2]

    joint_names = [
        "shoulder_pan.pos",
        "shoulder_lift.pos",
        "elbow_flex.pos",
        "wrist_flex.pos",
        "wrist_roll.pos",
        "gripper.pos",
    ]

    features = {
        "observation.state": {"dtype": "float32", "shape": (args.state_dim,), "names": joint_names},
        "action": {"dtype": "float32", "shape": (args.state_dim,), "names": joint_names},
    }
    for cam in args.cameras:
        features[f"observation.images.{cam}"] = {
            "dtype": "video",
            "shape": (img_h, img_w, 3),
            "names": ["height", "width", "channels"],
        }

    ds = LeRobotDataset.create(
        repo_id=args.repo_id,
        fps=args.fps,
        features=features,
        robot_type="so_follower",
        root=output_dir,
        use_videos=True,
        vcodec=args.vcodec,
    )

    print(f"Dataset created at {output_dir}")

    # Read all episodes
    with h5py.File(str(hdf5_file), "r") as f:
        data_group = f["data"]
        demo_names = list(data_group.keys())
        print(f"Found {len(demo_names)} episodes: {demo_names}")

        total_frames = 0
        for ep_idx, demo_name in enumerate(demo_names):
            demo = data_group[demo_name]
            actions = demo["actions"][:]
            states = demo["states/articulation/robot/joint_position"][:]
            initial_state = demo["initial_state/articulation/robot/joint_position"][0]

            cam_images = {}
            for cam in args.cameras:
                cam_images[cam] = demo[f"obs/{cam}"][:]

            n_steps = len(actions)
            if n_steps < 10:
                print(f"  Skipping {demo_name}: {n_steps} frames < 10")
                continue

            print(f"  Processing {demo_name}: {n_steps} frames")

            for t in range(n_steps):
                current_state = initial_state.astype(np.float32) if t == 0 else states[t - 1].astype(np.float32)
                current_action = actions[t].astype(np.float32)

                frame = {
                    "observation.state": current_state,
                    "action": current_action,
                    "task": args.task,
                }
                for cam in args.cameras:
                    frame[f"observation.images.{cam}"] = cam_images[cam][t]

                ds.add_frame(frame)

            ds.save_episode()
            total_frames += n_steps
            print(f"  Saved episode {ep_idx}")

    print(f"\nConversion complete!")
    print(f"  Episodes: {len(demo_names)}, Total frames: {total_frames}")
    print(f"  Output: {output_dir}")


if __name__ == "__main__":
    main()

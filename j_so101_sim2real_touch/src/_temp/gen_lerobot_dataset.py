#!/usr/bin/env python
"""Generate LeRobot v3.0 dataset from HDF5 files using LeRobot's official API."""

import argparse
import os
import sys
from pathlib import Path

import h5py
import numpy as np
import torch

from lerobot.datasets.lerobot_dataset import LeRobotDataset


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--h5_dir", type=str, required=True)
    parser.add_argument("--output_dir", type=str, required=True)
    parser.add_argument("--repo_id", type=str, default="local/sim_act_test")
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--task", type=str, default="pick_and_place")
    parser.add_argument("--cameras", type=str, nargs="*", default=["camera1", "camera2"])
    parser.add_argument("--state_dim", type=int, default=6)
    parser.add_argument("--vcodec", type=str, default="libsvtav1")
    args = parser.parse_args()

    h5_dir = Path(args.h5_dir)
    output_dir = Path(args.output_dir)
    h5_files = sorted(h5_dir.glob("*.hdf5"))

    if not h5_files:
        print(f"No HDF5 files found in {h5_dir}")
        sys.exit(1)

    print(f"Found {len(h5_files)} episodes")

    # Read first HDF5 to get image dimensions
    with h5py.File(str(h5_files[0]), "r") as f:
        demo = f["data/demo_0"]
        first_cam = demo[f"obs/{args.cameras[0]}"][:]
        img_h, img_w = first_cam.shape[1], first_cam.shape[2]

    joint_names = [
        "shoulder_pan.pos",
        "shoulder_lift.pos",
        "elbow_flex.pos",
        "wrist_flex.pos",
        "wrist_roll.pos",
        "gripper.pos",
    ]

    # Build features dict
    features = {
        "observation.state": {"dtype": "float32", "shape": [args.state_dim], "names": joint_names},
        "action": {"dtype": "float32", "shape": [args.state_dim], "names": joint_names},
    }
    for cam in args.cameras:
        features[f"observation.images.{cam}"] = {
            "dtype": "video",
            "shape": [img_h, img_w, 3],
            "names": ["height", "width", "channels"],
        }

    # Create dataset using official API
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

    # Add episodes
    total_frames = 0
    for ep_idx, h5_file in enumerate(h5_files):
        print(f"\nProcessing {h5_file.name} -> episode {ep_idx}")
        with h5py.File(str(h5_file), "r") as f:
            demo = f["data/demo_0"]
            actions = demo["actions"][:]
            states = demo["states/articulation/robot/joint_position"][:]
            initial_state = demo["initial_state/articulation/robot/joint_position"][0]

            cam_images = {}
            for cam in args.cameras:
                cam_images[cam] = demo[f"obs/{cam}"][:]

            n_steps = len(actions)
            if n_steps < 1:
                print(f"  Skipping: no frames")
                continue

            # Add frames
            for t in range(n_steps):
                if t == 0:
                    current_state = initial_state.astype(np.float32)
                else:
                    current_state = states[t - 1].astype(np.float32)

                current_action = actions[t].astype(np.float32)

                # Only include data features, metadata is auto-generated
                frame = {
                    "observation.state": current_state,
                    "action": current_action,
                    "task": args.task,
                }

                for cam in args.cameras:
                    img = cam_images[cam][t]
                    frame[f"observation.images.{cam}"] = img

                ds.add_frame(frame)

            ds.save_episode()
            total_frames += n_steps
            print(f"  Added {n_steps} frames")

    # Finalize
    ds.consolidate()
    print(f"\nDataset saved to {output_dir}")
    print(f"Episodes: {len(h5_files)}, Total frames: {total_frames}")


if __name__ == "__main__":
    main()

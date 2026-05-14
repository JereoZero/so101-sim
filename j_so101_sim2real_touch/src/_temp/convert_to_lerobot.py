#!/usr/bin/env python
"""SO101 HDF5 to LeRobot v3.0 Converter

将 Isaac Lab 采集的 HDF5 数据转换为 LeRobot v3.0 格式 (parquet + videos + meta)
用于 ACT 训练。

使用方法：
    cd /home/jer/ws_issac/ws/j_so101_sim2real_touch/src
    python convert_to_lerobot.py /path/to/output_dir \
        --h5_dir /path/to/hdf5_sim_block_act_test \
        --fps 30 \
        --task pick_and_place
"""

import argparse
import json
import os
import sys
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
import imageio.v3 as imageio


def parse_args():
    parser = argparse.ArgumentParser(description="Convert SO101 HDF5 data to LeRobot v3.0 format")
    parser.add_argument("output_dir", type=str, help="Output directory for LeRobot dataset")
    parser.add_argument("--h5_dir", type=str, required=True, help="Directory containing HDF5 episode files")
    parser.add_argument("--fps", type=int, default=30, help="Frames per second (default: 30)")
    parser.add_argument("--task", type=str, default="pick_and_place", help="Task name (default: pick_and_place)")
    parser.add_argument("--cameras", type=str, nargs="*", default=["camera1", "camera2"], help="Camera names")
    parser.add_argument("--state_dim", type=int, default=6, help="State/action dimension (default: 6)")
    return parser.parse_args()


def save_video(frames, output_path, fps):
    """保存图像帧为 mp4 视频"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    imageio.imwrite(output_path, frames, fps=fps, codec="libx264", quality=10)


def convert_episode(h5_path, output_dir, task_name, task_index, episode_idx, fps, cameras, state_dim):
    """Convert a single HDF5 episode to LeRobot v3.0 format."""
    print(f"  -> Processing {os.path.basename(h5_path)} -> Episode {episode_idx}...")

    with h5py.File(h5_path, "r") as f:
        demo_keys = [k for k in f["data"].keys() if k.startswith("demo_")]
        if not demo_keys:
            print(f"     Skipped: no demo_ group found")
            return None

        demo = f[f"data/{demo_keys[0]}"]

        # Read data
        actions = demo["actions"][:]  # (N, state_dim)
        states = demo["states/articulation/robot/joint_position"][:]  # (N, state_dim)
        initial_state = demo["initial_state/articulation/robot/joint_position"][0]  # (state_dim,)

        # Read camera images
        cam_images = {}
        for cam in cameras:
            cam_images[cam] = demo[f"obs/{cam}"][:]  # (N, H, W, 3)

        n_steps = len(actions)
        if n_steps < 1:
            print(f"     Skipped: no frames")
            return None

        # Save video files: videos/chunk-000/CAMERA/episode_000000.mp4
        video_paths = {}
        for cam in cameras:
            video_dir = output_dir / "videos" / "chunk-000" / f"observation.images.{cam}"
            video_path = video_dir / f"episode_{episode_idx:06d}.mp4"
            save_video(cam_images[cam], str(video_path), fps)
            video_paths[cam] = str(video_path)
            print(f"     Video saved: {video_path.relative_to(output_dir)} ({n_steps} frames)")

        # Build parquet data with data_file_index
        rows = []
        for t in range(n_steps):
            # state: use initial_state at t=0, otherwise previous state
            if t == 0:
                current_state = initial_state.astype(np.float32)
            else:
                current_state = states[t - 1].astype(np.float32)

            current_action = actions[t].astype(np.float32)

            row = {
                "episode_index": episode_idx,
                "frame_index": t,
                "task_index": task_index,
                "index": t,
                "timestamp": float(t / fps),
                "observation.state": current_state,
                "action": current_action,
                "data_file_index": 0,  # v3.0 requires this column
            }
            rows.append(row)

        # Save parquet: data/chunk-000/episode_000000.parquet
        data_dir = output_dir / "data" / "chunk-000"
        data_dir.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame(rows)
        episode_file = data_dir / f"episode_{episode_idx:06d}.parquet"
        df.to_parquet(episode_file, index=False)

        # Calculate stats
        stats = {}
        for key in ["observation.state", "action"]:
            data = np.array([row[key] for row in rows], dtype=np.float32)
            stats[key] = {
                "min": [float(x) for x in data.min(axis=0).tolist()],
                "max": [float(x) for x in data.max(axis=0).tolist()],
                "mean": [float(x) for x in data.mean(axis=0).tolist()],
                "std": [float(x) for x in data.std(axis=0).tolist()],
                "count": [len(rows)],
            }

        # Stats for images (normalized to [0,1])
        for cam in cameras:
            imgs = np.array(cam_images[cam], dtype=np.float32) / 255.0
            stats[f"observation.images.{cam}"] = {
                "min": [float(x) for x in np.min(imgs, axis=(0, 1, 2)).tolist()],
                "max": [float(x) for x in np.max(imgs, axis=(0, 1, 2)).tolist()],
                "mean": [float(x) for x in np.mean(imgs, axis=(0, 1, 2)).tolist()],
                "std": [float(x) for x in np.std(imgs, axis=(0, 1, 2)).tolist()],
                "count": [n_steps],
            }

        # Stats for scalar fields
        for key in ["timestamp", "frame_index", "episode_index", "index", "task_index", "data_file_index"]:
            data = np.array([row[key] for row in rows], dtype=np.float32)
            stats[key] = {
                "min": [float(data.min())],
                "max": [float(data.max())],
                "mean": [float(data.mean())],
                "std": [float(data.std())],
                "count": [len(rows)],
            }

        # Get image shape and video file size
        img_h, img_w = cam_images[cameras[0]].shape[1], cam_images[cameras[0]].shape[2]
        total_video_size = sum(os.path.getsize(p) for p in video_paths.values())

        print(f"     Done: {n_steps} steps")
        return {
            "episode_index": episode_idx,
            "length": n_steps,
            "tasks": [task_name],
            "stats": stats,
            "filepath": str(episode_file),
            "img_shape": (img_h, img_w),
            "total_video_size": total_video_size,
        }


def main():
    args = parse_args()
    output_path = Path(args.output_dir)
    data_path = output_path / "data" / "chunk-000"
    data_path.mkdir(parents=True, exist_ok=True)
    video_path = output_path / "videos" / "chunk-000"
    video_path.mkdir(parents=True, exist_ok=True)
    meta_path = output_path / "meta"
    meta_path.mkdir(parents=True, exist_ok=True)

    # Find all HDF5 files
    h5_files = sorted(Path(args.h5_dir).glob("*.hdf5"))
    if not h5_files:
        print(f"ERROR: No HDF5 files found in {args.h5_dir}")
        sys.exit(1)

    print(f"Found {len(h5_files)} HDF5 files")
    print(f"Task: {args.task}, FPS: {args.fps}, Cameras: {args.cameras}, State dim: {args.state_dim}")

    # Convert episodes
    episode_metadata = []
    img_shape = None
    for i, h5_file in enumerate(h5_files):
        result = convert_episode(
            str(h5_file),
            output_path,
            args.task,
            0,  # task_index
            i,  # episode_idx
            args.fps,
            args.cameras,
            args.state_dim,
        )
        if result:
            episode_metadata.append(result)
            img_shape = result["img_shape"]

    if not episode_metadata:
        print("ERROR: No valid episodes were processed")
        sys.exit(1)

    # Save metadata
    total_episodes = len(episode_metadata)
    total_frames = sum(ep["length"] for ep in episode_metadata)
    total_video_size = sum(ep["total_video_size"] for ep in episode_metadata)

    # Build features dict
    features = {
        "observation.state": {"dtype": "float32", "shape": [args.state_dim], "names": None, "fps": args.fps},
        "action": {"dtype": "float32", "shape": [args.state_dim], "names": None, "fps": args.fps},
        "timestamp": {"dtype": "float32", "shape": [1], "names": None, "fps": args.fps},
        "frame_index": {"dtype": "int64", "shape": [1], "names": None, "fps": args.fps},
        "episode_index": {"dtype": "int64", "shape": [1], "names": None, "fps": args.fps},
        "index": {"dtype": "int64", "shape": [1], "names": None, "fps": args.fps},
        "task_index": {"dtype": "int64", "shape": [1], "names": None, "fps": args.fps},
        "data_file_index": {"dtype": "int64", "shape": [1], "names": None, "fps": args.fps},
    }
    for cam in args.cameras:
        features[f"observation.images.{cam}"] = {
            "dtype": "video",
            "shape": [img_shape[0], img_shape[1], 3],
            "names": ["height", "width", "channel"],
        }

    # Build video_codecs dict (v3.0 requirement)
    video_codecs = {
        f"observation.images.{cam}": "h264" for cam in args.cameras
    }

    # info.json (v3.0 format)
    info = {
        "codebase_version": "v3.0",
        "robot_type": "so101",
        "total_episodes": total_episodes,
        "total_frames": total_frames,
        "total_tasks": 1,
        "total_videos": total_episodes * len(args.cameras),
        "total_size": total_video_size,
        "total_keys": 1,
        "chunks_size": total_episodes,
        "fps": args.fps,
        "splits": {"train": f"0:{total_episodes}"},
        "data_path": "data/chunk-000/episode_{episode_index:06d}.parquet",
        "video_path": "videos/chunk-000/{camera_key}/episode_{episode_index:06d}.mp4",
        "video_codecs": video_codecs,
        "features": features,
    }
    with open(meta_path / "info.json", "w") as f:
        json.dump(info, f, indent=2)

    # episodes.jsonl (v3.0 format)
    with open(meta_path / "episodes.jsonl", "w") as f:
        for ep in episode_metadata:
            ep_size = os.path.getsize(ep["filepath"])
            json.dump({
                "episode_index": ep["episode_index"],
                "tasks": ep["tasks"],
                "length": ep["length"],
                "total_frames": ep["length"],
                "total_size": ep_size + ep["total_video_size"],
                "data_path": f"data/chunk-000/episode_{ep['episode_index']:06d}.parquet",
                "video_path": f"videos/chunk-000/{{camera_key}}/episode_{ep['episode_index']:06d}.mp4",
                "video_codecs": video_codecs,
            }, f)
            f.write("\n")

    # episodes_stats.jsonl
    with open(meta_path / "episodes_stats.jsonl", "w") as f:
        for ep in episode_metadata:
            json.dump({"episode_index": ep["episode_index"], "stats": ep["stats"]}, f)
            f.write("\n")

    # tasks.parquet (v3.0 requirement)
    tasks_df = pd.DataFrame([{"task_index": 0, "task": args.task}])
    tasks_df.to_parquet(meta_path / "tasks.parquet", index=False)

    print(f"\nConversion complete!")
    print(f"  Episodes: {total_episodes}")
    print(f"  Total frames: {total_frames}")
    print(f"  Output: {output_path}")


if __name__ == "__main__":
    main()

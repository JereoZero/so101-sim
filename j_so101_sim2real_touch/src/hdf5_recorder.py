"""HDF5 数据录制器 - 兼容 IsaacLab 官方格式，可用 isaaclab2lerobotv3.py 转换"""
import os
import h5py
import numpy as np
import torch


class HDF5Recorder:
    def __init__(self, record_dir, hdf5_filename="dataset.hdf5"):
        self.record_dir = record_dir
        self.hdf5_path = os.path.join(record_dir, hdf5_filename)
        self.current_demo_index = 0
        self.is_recording = False
        self.recording_paused = False
        self._file = None
        self._data_group = None

        # 缓冲区
        self.camera_names = ["camera1", "camera2"]
        self.buffer = {
            "camera1": [],
            "camera2": [],
            "actions": [],
            "states": [],
        }
        self.initial_state = None

    def _open_file(self):
        if self._file is None:
            os.makedirs(self.record_dir, exist_ok=True)
            self._file = h5py.File(self.hdf5_path, "a")
            if "data" not in self._file:
                self._data_group = self._file.create_group("data")
                self._data_group.attrs["env_args"] = "{}"
                self._data_group.attrs["total"] = 0
            else:
                self._data_group = self._file["data"]
                # 找到最大的 demo_id
                existing = [k for k in self._data_group.keys() if k.startswith("demo_")]
                if existing:
                    ids = [int(k.split("_")[1]) for k in existing]
                    self.current_demo_index = max(ids) + 1

    def _close_file(self):
        if self._file is not None:
            self._file.flush()
            self._file.close()
            self._file = None
            self._data_group = None

    def __del__(self):
        self._close_file()

    def reset_buffer(self):
        self.buffer = {
            "camera1": [],
            "camera2": [],
            "actions": [],
            "states": [],
        }
        self.initial_state = None

    def start(self):
        self.reset_buffer()
        self.is_recording = True
        self.recording_paused = False

    def stop(self):
        self.is_recording = False
        self.recording_paused = True

    def add_frame(self, cam1_img, cam2_img, action, state):
        self.buffer["camera1"].append(cam1_img)
        self.buffer["camera2"].append(cam2_img)
        self.buffer["actions"].append(action)
        self.buffer["states"].append(state)

        if self.initial_state is None:
            self.initial_state = np.array(state, dtype=np.float32)

    def save_episode(self):
        if not self.buffer["camera1"]:
            print("[录制] 没有数据可保存")
            return None

        n_frames = len(self.buffer["camera1"])
        self._open_file()

        demo_name = f"demo_{self.current_demo_index}"
        demo_grp = self._data_group.create_group(demo_name)
        demo_grp.attrs["num_samples"] = n_frames
        demo_grp.attrs["success"] = True
        demo_grp.attrs["seed"] = 0

        # Actions (N, 6)
        demo_grp.create_dataset("actions", data=np.array(self.buffer["actions"], dtype=np.float32), compression="gzip")

        # States (N, 6)
        states_grp = demo_grp.create_group("states")
        states_grp.create_dataset(
            "articulation/robot/joint_position",
            data=np.array(self.buffer["states"], dtype=np.float32),
            compression="gzip",
        )

        # Initial state (6,)
        init_grp = demo_grp.create_group("initial_state")
        init_grp.create_dataset(
            "articulation/robot/joint_position",
            data=self.initial_state.reshape(1, -1),
            dtype=np.float32,
        )

        # Camera images (N, H, W, 3)
        obs_grp = demo_grp.create_group("obs")
        obs_grp.create_dataset("camera1", data=np.array(self.buffer["camera1"], dtype=np.uint8), compression="gzip")
        obs_grp.create_dataset("camera2", data=np.array(self.buffer["camera2"], dtype=np.uint8), compression="gzip")

        # Update total
        self._data_group.attrs["total"] = self._data_group.attrs.get("total", 0) + n_frames
        self._file.flush()

        print(f"[录制] 保存到: {self.hdf5_path}/{demo_name} ({n_frames} 帧)")
        self.current_demo_index += 1
        return self.hdf5_path

    def discard_and_clear(self):
        self.is_recording = False
        self.recording_paused = False
        self.reset_buffer()

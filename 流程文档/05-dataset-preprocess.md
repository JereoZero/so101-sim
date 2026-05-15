# 05 — 数据集预处理

## 概述

数据预处理分为两步：
1. **HDF5 → LeRobot 格式**：将仿真录制的 HDF5 文件转换为 LeRobot v3.0 格式（Parquet + Videos）
2. **LeRobot → SmolVLA 格式**：通过 `modify_tasks()` 添加语言任务描述

## 完整转换流程

```
仿真录制 HDF5
     ↓ hdf5_to_lerobot_v3.py
LeRobot v3.0 数据集 (sim_lerobot_act)
     ↓ convert_act_to_smolvla.py
SmolVLA 数据集 (sim_lerobot_smolvla)
     ↓ lerobot-train
SmolVLA 模型
```

---

## 步骤 1：HDF5 → LeRobot 格式

### 脚本

`hdf5_to_lerobot_v3.py` 是一个轻量转换器，不需要 Isaac AppLauncher 或 leisaac 模块。

```bash
conda activate lerobot
python /home/jer/ws_issac/ws/j_so101_sim2real_touch/src/hdf5_to_lerobot_v3.py \
    --hdf5_file /path/to/dataset.hdf5 \
    --output_dir /path/to/sim_lerobot_act \
    --repo_id local/sim_act_test \
    --fps 30 \
    --task pick_and_place \
    --cameras camera1 camera2
```

### 核心逻辑

脚本读取 HDF5 中的数据，构建 LeRobot 数据集：

```python
with h5py.File(hdf5_file, "r") as f:
    for demo_name in f["data"]:
        actions = demo["actions"][:]
        states = demo["states/articulation/robot/joint_position"][:]
        initial_state = demo["initial_state/articulation/robot/joint_position"][0]
        cam_images = {cam: demo[f"obs/{cam}"][:] for cam in cameras}

        for t in range(n_steps):
            # t=0 用 initial_state，其余用 t-1 帧的 state
            cur_state = initial_state if t == 0 else states[t - 1]
            frame = {
                "observation.state": cur_state,
                "action": actions[t],
                "task": "pick_and_place",
            }
            ds.add_frame(frame)
        ds.save_episode()
```

### 关键：State 帧的时序关系

第 t 帧的 `observation.state` = 执行 action 之前的关节位置（即第 t-1 步的 state），因为 LeRobot 的数据格式是 `(obs_t, action_t)` 对。第一帧的 state 使用 episode 的 `initial_state`。

---

## 步骤 2：LeRobot → SmolVLA 格式

### 转换脚本

使用 LeRobot 官方的 `modify_tasks()` API 进行转换：

```bash
conda activate lerobot
python /home/jer/ws_issac/ws/j_so101_sim2real_touch/docs/convert_act_to_smolvla.py
```

脚本核心逻辑：
1. 加载 ACT 数据集
2. 调用 `modify_tasks(act_dataset, new_task="put small orange block in plate")` 添加任务描述
3. 复制数据集到 SmolVLA 目录
4. 验证新数据集

## 数据集结构对比

| 特性 | sim_lerobot_act | sim_lerobot_smolvla |
|---|---|---|
| 任务描述 | 无 | "put small orange block in plate" |
| episodes | 100 | 100 |
| 帧数 | ~35913 | ~35913 |
| 图像 | 640×480 RGB | 640×480 RGB |
| 动作 | 6 关节 | 6 关节 |
| 格式 | Parquet + Videos | Parquet + Videos + tasks.jsonl |

## SmolVLA 数据集目录结构

```
sim_lerobot_smolvla/
├── data/
│   └── chunk-000/
│       ├── episode_000000.parquet
│       ├── ...
│       └── episode_000099.parquet
├── meta/
│   ├── info.json           ← 数据集信息
│   ├── stats.pth            ← 统计信息
│   ├── episodes.jsonl       ← episode 列表
│   ├── tasks.jsonl          ← 任务描述（新增）
│   └── features.json        ← 特征定义
└── videos/                   ← 视频文件
```

## 训练命令格式

转换后，使用以下参数引用数据集：

```bash
--dataset.repo_id=local/sim_smolvla
--dataset.root=/home/jer/ws_issac/ws/j_so101_sim2real_touch/datasets/sim_lerobot_smolvla
--dataset.streaming=false
```

## 关键参数说明

| 参数 | 值 | 说明 |
|---|---|---|
| `repo_id` | `local/sim_smolvla` | 本地数据集标识 |
| `streaming` | `false` | 不使用流式加载 |
| `image_transforms.enable` | `false`（v4+） | v4 起关闭数据增强 |
| `n_obs_steps` | 4 | 使用 4 帧历史作为输入 |

## 验证数据集

```python
from lerobot.datasets.lerobot_dataset import LeRobotDataset

ds = LeRobotDataset(
    repo_id="local/sim_smolvla",
    root="/home/jer/ws_issac/ws/j_so101_sim2real_touch/datasets/sim_lerobot_smolvla"
)
print(f"Episodes: {ds.meta.total_episodes}")
print(f"Frames: {ds.meta.total_frames}")
print(f"Tasks: {ds.meta.tasks}")
```
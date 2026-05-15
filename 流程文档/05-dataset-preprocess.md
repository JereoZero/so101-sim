# 05 — 数据集预处理

## 概述

录制好的 ACT 格式数据集需要转换为 SmolVLA 格式，主要是添加**语言任务描述**，使模型能够理解自然语言指令。

## 转换流程

```
ACT 数据集 (sim_lerobot_act)
         ↓ convert_act_to_smolvla.py
SmolVLA 数据集 (sim_lerobot_smolvla)
         ↓ lerobot-train
SmolVLA 模型
```

## 转换脚本

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

| 特性 | ACT 格式 | SmolVLA 格式 |
|---|---|---|
| 任务描述 | 无 | "put small orange block in plate" |
| episodes | 100 | 100 |
| 帧数 | ~35913 | ~35913 |
| 图像 | 640×480 RGB | 640×480 RGB |
| 动作 | 6 关节 | 6 关节 |
| 格式 | HDF5 + Parquet | HDF5 + Parquet + tasks.jsonl |

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
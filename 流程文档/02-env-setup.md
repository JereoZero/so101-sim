# 02 — 环境搭建

## Conda 环境

项目使用三个 Conda 环境：

| 环境名 | 用途 |
|---|---|
| `isaaclab` | Isaac Sim + Isaac Lab 仿真 |
| `lerobot` | SmolVLA 模型训练 |
| `lerobot_issac` | 仿真 + LeRobot 联合开发 |

激活环境示例：
```bash
conda activate isaaclab   # 仿真
conda activate lerobot    # 训练
```

## Isaac Lab 安装

**主目录**：`/home/jer/ws_issac/thirdparty/IsaacLab`

**启动方式**：
```bash
cd /home/jer/ws_issac/thirdparty/IsaacLab
export DISPLAY=:0
export ISAACSIM_ASSETS_PATH=~/isaacsim/Assets/Assets/Isaac/5.1
./isaaclab.sh -p <script_path> --enable_cameras
```

**环境变量**：
```bash
export ISAACSIM_ASSETS_PATH=~/isaacsim/Assets/Assets/Isaac/5.1
export IsaacSim_ROOT=~/isaacsim/Assets/Assets/Isaac/5.1
# 建议添加到 ~/.bashrc
```

**Isaac Sim 资源**：
```
~/isaacsim/Assets/Assets/Isaac/5.1/
├── Isaac/    (54GB)
└── NVIDIA/   (124GB)
```

## LeRobot 框架

项目使用 LeRobot v0.5.0。

| 路径 | 说明 |
|---|---|
| `/home/jer/ws_issac/thirdparty/lerobot-0.5.0` | 官方源码 |
| `~/miniconda3/envs/lerobot/lib/python3.12/site-packages/lerobot` | lerobot 环境 |

安装完 LeRobot 后，需要应用 5 处源代码修改，详见 [03-仿真场景搭建](03-sim-scene.md) 的「LeRobot 源码修改」章节。

## SO101 URDF

```
/home/jer/ws_issac/thirdparty/SO-ARM100/Simulation/SO101/so101_new_calib.urdf
```

仿真中的 SO101 模型来自 `isaac_so_arm101` 包：
```
/home/jer/ws_issac/thirdparty/isaac_so_arm101/src/isaac_so_arm101/robots/trs_so101/
├── so_arm101.py          ← 机器人配置（含物理材质修改）
└── so_arm101.urdf        ← URDF 模型
```

## 关键路径汇总

| 资源 | 路径 |
|---|---|
| IsaacLab | `/home/jer/ws_issac/thirdparty/IsaacLab` |
| LeRobot 源码 | `/home/jer/ws_issac/thirdparty/lerobot-0.5.0` |
| SO101 URDF | `/home/jer/ws_issac/thirdparty/SO-ARM100/Simulation/SO101/so101_new_calib.urdf` |
| Isaac Sim 资源 | `~/isaacsim/Assets/Assets/Isaac/5.1/` |
| isaac_so_arm101 | `/home/jer/ws_issac/thirdparty/isaac_so_arm101` |

## 串口设备（真机遥操作）

| 设备 | 串口 | 用途 |
|---|---|---|
| 主臂 | `/dev/ttySO101_LEADER` | 真机主臂（遥操作控制） |
| 从臂 | `/dev/ttySO101_FOLLOWER` | 真机从臂 |

## GPU

NVIDIA RTX 5070 12GB，用于模型训练和推理。

## 常见环境问题

1. **DISPLAY 未设置**：Isaac Sim 需要 GUI 才能接收键盘事件，必须 `export DISPLAY=:0`
2. **USD 缓存**：修改 URDF 后需清理缓存 `rm -rf /tmp/IsaacLab/`
3. **GPU 显存不足**：确认之前 Isaac Sim 进程已完全退出
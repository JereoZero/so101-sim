# 环境配置详情

本文档记录所有环境路径、依赖和配置信息。

---

## 1. Conda 环境

### 1.1 环境列表

```bash
# 查看所有环境
conda env list

# 预期输出:
# isaaclab                /home/jer/miniconda3/envs/isaaclab
# lerobot                 /home/jer/miniconda3/envs/lerobot
# lerobot_issac          /home/jer/miniconda3/envs/lerobot_issac
```

### 1.2 lerobot_issac 环境

```bash
conda activate lerobot_issac
```

**关键依赖**:
- Python: 3.12
- isaaclab: ✅
- torch: ✅
- lerobot: ✅ (从 /home/jer/ws_issac/lerobot_so101/workspace/projects/lerobot/src)

---

## 2. 关键路径

### 2.1 IsaacLab

| 路径 | 说明 |
|------|------|
| `/home/jer/ws_issac/thirdparty/IsaacLab` | IsaacLab 主目录 |
| `/home/jer/ws_issac/thirdparty/IsaacLab/source/isaaclab` | isaaclab 源码 |
| `/home/jer/ws_issac/thirdparty/IsaacLab/apps` | IsaacLab 启动脚本 |

**IsaacLab 启动方式**:
```bash
cd /home/jer/ws_issac/thirdparty/IsaacLab
./isaaclab.sh -p <script_path>
```

### 2.2 LeRobot

| 路径 | 说明 |
|------|------|
| `/home/jer/ws_issac/thirdparty/lerobot-0.5.0` | LeRobot 官方源码 (需应用修改) |
| `/home/jer/ws_issac/lerobot_so101/workspace/projects/lerobot/src` | LeRobot 修改版 (已调试完成) |
| `~/miniconda3/envs/lerobot_issac/lib/python3.12/site-packages/lerobot` | lerobot_issac 环境中的 LeRobot |

### 2.3 SO101 URDF

```
/home/jer/ws_issac/thirdparty/SO-ARM100/Simulation/SO101/so101_new_calib.urdf
```

### 2.4 Isaac Sim 资源

```
~/isaacsim/Assets/Assets/Isaac/5.1/
├── Isaac/    (54GB)
└── NVIDIA/   (124GB)
```

---

## 3. 串口设备

### 3.1 SO101 设备

| 设备 | 串口 | 用途 |
|------|------|------|
| 主臂 | `/dev/ttySO101_LEADER` | 真实主臂 (遥操作控制) |
| 从臂 | `/dev/ttySO101_FOLLOWER` | 真实从臂 (跟随主臂) |

### 3.2 检查设备

```bash
# 列出所有 tty 设备
ls -la /dev/ttySO101*

# 检查权限
ls -la /dev/ttyUSB* 2>/dev/null || echo "No USB devices found"
```

---

## 4. 环境变量

### 4.1 Isaac Sim 资源路径

```bash
export ISAACSIM_ASSETS_PATH=~/isaacsim/Assets/Assets/Isaac/5.1
export IsaacSim_ROOT=~/isaacsim/Assets/Assets/Isaac/5.1
```

### 4.2 永久配置

```bash
# 添加到 ~/.bashrc
echo 'export ISAACSIM_ASSETS_PATH=~/isaacsim/Assets/Assets/Isaac/5.1' >> ~/.bashrc
echo 'export IsaacSim_ROOT=~/isaacsim/Assets/Assets/Isaac/5.1' >> ~/.bashrc
source ~/.bashrc
```

---

## 5. LeRobot 命令

### 5.1 遥操作

```bash
lerobot-teleoperate \
    --teleop.type=so101_leader \
    --teleop.port=/dev/ttySO101_LEADER \
    --teleop.id=j_leader
```

### 5.2 校准

```bash
lerobot-calibrate \
    --robot.type=so101_follower \
    --robot.port=/dev/ttySO101_FOLLOWER \
    --robot.id=j_follower
```

### 5.3 录制数据

```bash
lerobot-record \
    --robot.type=so101_follower \
    --robot.port=/dev/ttySO101_FOLLOWER \
    --robot.id=j_follower \
    --teleop.type=so101_leader \
    --teleop.port=/dev/ttySO101_LEADER \
    --teleop.id=j_leader
```

---

## 6. 校准文件位置

LeRobot 校准文件存放在:

```
~/.lerobot/teleoperators/so_leader/<id>.json
~/.lerobot/robots/so_follower/<id>.json
```

例如:
- 主臂: `~/.lerobot/teleoperators/so_leader/j_leader.json`
- 从臂: `~/.lerobot/robots/so_follower/j_follower.json`

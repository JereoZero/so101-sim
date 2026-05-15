# 07 — 模型推理

## 推理架构

SmolVLA 推理采用 **TCP 客户端-服务器** 架构：

```
┌──────────────────────────┐      ┌──────────────────────────┐
│  终端1: lerobot 环境     │      │  终端2: isaaclab 环境    │
│  smolvla_inference_      │      │  smolvla_inference_      │
│  server.py               │      │  client.py               │
│                          │      │                          │
│  - SmolVLA 模型          │ TCP  │  - Isaac Sim 仿真场景    │
│  - 接收图像+关节状态     │◀────▶│  - 双摄像头捕获          │
│  - 语言指令→预测chunk    │ 9877 │  - chunk队列管理         │
│  - 返回动作chunk         │      │  - 30Hz机器人控制        │
└──────────────────────────┘      └──────────────────────────┘
```

## 运行命令

### 终端1 — 推理服务器（lerobot 环境）

```bash
conda activate lerobot
python /home/jer/ws_issac/ws/j_so101_sim2real_touch/src/smolvla_inference_server.py
```

### 终端2 — 仿真客户端（isaaclab 环境）

```bash
export DISPLAY=:0
cd /home/jer/ws_issac/thirdparty/IsaacLab
conda activate isaaclab
export ISAACSIM_ASSETS_PATH=~/isaacsim/Assets/Assets/Isaac/5.1
./isaaclab.sh -p /home/jer/ws_issac/ws/j_so101_sim2real_touch/src/smolvla_inference_client.py --enable_cameras
```

## 键盘快捷键

| 按键 | 功能 |
|---|---|
| **M** | 切换手动/自动推理模式 |
| **R** | 重置环境（方块位置随机化） |
| **ESC** | 退出 |

## 推理流程

### Chunk 队列管理

模型预测 50 步的 action chunk，客户端通过队列管理逐步执行：

```
模型预测 [50, 6] chunk
    → 服务器返回完整列表
    → 客户端取前 50 步加入队列
    → 每步 pop 队列头并执行
    → 新推理到达后直接替换整个队列（receding horizon）
    → 仿真以 30Hz 频率执行
```

### Receding Horizon 控制

当前设置为每帧推理（30Hz），可通过修改 `INFERENCE_INTERVAL` 调整：
- `INFERENCE_INTERVAL = 1`：30Hz 推理，动作最灵敏（当前）
- `INFERENCE_INTERVAL = 3`：10Hz 推理，减小服务器负载
- 新推理到达后**直接替换旧队列**
- 动作连续不间断
- 仿真始终以 30Hz 频率执行

## 模型切换

推理服务器通过修改 `CHECKPOINT_PATH` 切换不同模型版本：

```python
# smolvla_inference_server.py

# v6 20000步（推荐）
CHECKPOINT_PATH = "/home/jer/ws_issac/ws/j_so101_sim2real_touch/models/smolvla_sim_v6/checkpoints/020000"

# 其他可选版本：
# smolvla_sim_v6/checkpoints/016000  ← 16000步
# smolvla_sim_v6/checkpoints/012000  ← 12000步
# smolvla_sim_v7/checkpoints/008000  ← v7 8000步
```

## 核心问题与修复

### ⚠️ Chunk Size 问题（最关键的坑）

**问题**：推理服务器原来只返回 chunk 的**第一步动作**，而不是完整的 50 步 chunk。

```python
# ❌ 错误代码
action = action_tensor.squeeze(0)[0].cpu().numpy()  # 只取 [0]

# ✅ 正确代码
action_chunk = action_tensor.squeeze(0).cpu().numpy()
action_list = action_chunk.flatten().tolist()  # 返回完整 chunk
```

**影响**：
- 客户端每帧都触发推理
- 推理请求过多导致卡顿
- 浪费了 chunk 预测的优势

**修复后**：服务器返回完整 50 步 chunk，客户端队列管理，10Hz 推理 + 30Hz 执行。

## 推理参数

| 参数 | 值 | 说明 |
|---|---|---|
| 模型 | smolvla_sim_v6/020000 | 推荐版本 |
| 任务描述 | "put small orange block in plate" | 语言指令 |
| chunk_size | 50 | 模型预测 50 步 |
| 推理频率 | 30Hz（当前），可调至 10Hz | receding horizon |
| 执行频率 | 30Hz | 仿真帧率 |
| 分辨率 | 640×480 | 与录制时对齐 |
| 端口 | 9877 | 与 ACT(9876) 区分 |
| max_steps | 1800 | 每 episode 上限 |

## 常见问题

1. **机械臂不动**：清理 USD 缓存 `rm -rf /tmp/IsaacLab/`
2. **动作卡顿**：检查推理频率和 chunk_size 配置
3. **模型加载失败**：确认 `HF_HUB_OFFLINE=1` 和 `pretrained_model` 目录存在
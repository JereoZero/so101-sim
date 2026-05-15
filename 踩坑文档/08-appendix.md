# 08 — 附录

## 常用命令速查

### 仿真启动
```bash
export DISPLAY=:0
cd /home/jer/ws_issac/thirdparty/IsaacLab
conda activate isaaclab
export ISAACSIM_ASSETS_PATH=~/isaacsim/Assets/Assets/Isaac/5.1
./isaaclab.sh -p <script.py> --enable_cameras
```

### 训练命令模板
```bash
cd /home/jer/ws_issac/thirdparty/IsaacLab
conda activate lerobot
HF_HUB_OFFLINE=1 lerobot-train \
    --policy.path=<base_model> \
    --policy.use_amp=true \
    --policy.n_obs_steps=4 \
    --policy.optimizer_lr=1e-5 \
    --policy.device=cuda \
    --dataset.repo_id=local/sim_smolvla \
    --dataset.root=/home/jer/ws_issac/ws/j_so101_sim2real_touch/datasets/sim_lerobot_smolvla \
    --dataset.streaming=false \
    --dataset.image_transforms.enable=false \
    --output_dir=<output_dir> \
    --steps=20000 --batch_size=36 --save_freq=2000
```

### 推理服务器
```bash
conda activate lerobot
python /home/jer/ws_issac/ws/j_so101_sim2real_touch/src/smolvla_inference_server.py
```

### 进程管理
```bash
# 查看 Isaac 进程
ps aux | grep -i isaac | grep -v grep
# 强制终止
kill -9 <PID>
# 查看端口占用
lsof -i:9877
# 清理 USD 缓存
rm -rf /tmp/IsaacLab/
```

---

## 关键路径速查

| 路径 | 说明 |
|---|---|
| `/home/jer/ws_issac/thirdparty/IsaacLab` | Isaac Lab 主目录 |
| `/home/jer/ws_issac/thirdparty/lerobot-0.5.0` | LeRobot 源码 |
| `/home/jer/ws_issac/thirdparty/isaac_so_arm101` | SO101 仿真模型 |
| `/home/jer/ws_issac/thirdparty/SO-ARM100/Simulation/SO101` | SO101 URDF |
| `~/isaacsim/Assets/Assets/Isaac/5.1/` | Isaac Sim 资源 |
| `/home/jer/ws_issac/ws/j_so101_sim2real_touch/src/` | 项目源码 |
| `/home/jer/ws_issac/ws/j_so101_sim2real_touch/models/` | 训练模型 |
| `/home/jer/ws_issac/ws/j_so101_sim2real_touch/datasets/` | 数据集 |

---

## 训练参数速查

| 参数 | 推荐值 | 说明 |
|---|---|---|
| `steps` | 20000 | 训练步数 |
| `batch_size` | 36 | 批次大小 |
| `optimizer_lr` | 1e-5 | **低学习率** |
| `n_obs_steps` | 4 | 历史帧数 |
| `use_amp` | true | 混合精度 |
| `image_transforms` | **false** | 关闭增强 |
| `save_freq` | 2000 | 保存间隔 |

---

## 推理参数速查

| 参数 | 推荐值 |
|---|---|
| 模型 | smolvla_sim_v6/020000 |
| chunk_size | 50 |
| 推理频率 | 10Hz (receding) |
| 执行频率 | 30Hz |
| 摄像头分辨率 | 640×480 |
| 服务器端口 | 9877 |
| 任务描述 | "put small orange block in plate" |

---

## 模型版本对照

| 版本 | 步数 | Loss | 状态 |
|---|---|---|---|
| v6/020000 | 20000 | 0.038 | ★ 推荐基线 |
| v6/016000 | 16000 | — | 较稳定 |
| v6/012000 | 12000 | — | 中等 |
| v6/006000 | 6000 | — | 可能欠拟合 |
| v7/008000 | 8000 | — | 待评估 |
| v7/002000 | 2000 | — | 待评估 |
| v4/020000 | 20000 | 0.033 | 较稳定 |

---

## Conda 环境速查

| 环境 | 用途 |
|---|---|
| `isaaclab` | 仿真 |
| `lerobot` | 训练 + 推理服务器 |

---

## 硬件信息

| 组件 | 型号 |
|---|---|
| GPU | NVIDIA RTX 5070 12GB |
| CPU | AMD Ryzen 7 3700X |
| 主板 | B450M |
| RAM | 96GB DDR4 |
| OS | Ubuntu 22.04 |

*最后更新: 2026-05-14*
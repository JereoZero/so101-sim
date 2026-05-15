# 07 — SmolVLA 模型推理

## 坑 1：Chunk Size = 1（最关键！浪费了大量时间）

### 现象
推理时机械臂运动**一顿一顿**，执行不流畅。日志中推理请求没有报错，但动作感觉是离散的。

### 原因
推理服务器只返回 chunk 的**第一步动作**而非完整 chunk！

```python
# ❌ 错误代码（只取了 [0]）
action = action_tensor.squeeze(0)[0].cpu().numpy()
action_list = [action]  # 只有 1 步
```

模型 `predict_action_chunk()` 返回 `[50, 6]` 的张量（chunk_size=50），但只取了第一步。

### 影响
- 客户端每帧都触发推理（30Hz），而不是 10Hz
- Socket 通信延迟导致动作卡顿
- 完全浪费了 chunk 预测的优势

### 解决
```python
# ✅ 正确代码 — 返回完整 50 步 chunk
action_chunk = action_tensor.squeeze(0).cpu().numpy()
action_list = action_chunk.flatten().tolist()  # [50*6] 扁平列表
```

修复后实现 10Hz 推理 + 30Hz 执行 + Receding Horizon 队列管理。

---

## 坑 2：wrist_roll 锁定问题

### 现象
推理时腕关节旋转角度不对，方块被甩飞或抓不住。

### 原因
仿真环境中 wrist_roll 需要保持固定角度（末端执行器不旋转），但模型输出了变化的 wrist_roll 值。

### 解决
在客户端强制覆盖：
```python
joint_names_list = list(robot.data.joint_names)
wr_idx = joint_names_list.index("wrist_roll")
action_clipped[wr_idx] = -1.57  # 固定 -90 度
```

---

## 坑 3：HF_HUB_OFFLINE 加载失败

### 现象
```
HFValidationError: Repo id must be in the form 'repo_name' or 'namespace/repo_name'
```

### 原因
`SmolVLAPolicy.from_pretrained()` 把本地路径当成 HuggingFace repo_id。

### 解决
在 `smolvla_inference_server.py` 的 `__init__` 中：
```python
import os
os.environ["HF_HUB_OFFLINE"] = "1"
self.policy = SmolVLAPolicy.from_pretrained(str(pretrained_dir))
```

---

## 坑 4：推理频率的选择

### 测试过的配置：

| 推理频率 | chunk_size | 效果 |
|---|---|---|
| 30Hz | 10 | 推理请求过多，仿真卡顿 |
| 3Hz | 10→50 | 队列空等待时间长，动作停顿 |
| 10Hz | 50 (receding) | 流畅 + 及时更新 |
| 30Hz | 50 (receding) | ✅ 当前配置，最灵敏 |

### 当前最佳配置
- **执行**：30Hz（仿真帧率）
- **推理**：每 INFERENCE_INTERVAL 帧一次，新推理替换旧队列
- **chunk_size**：50（模型完整输出）

```python
CHUNK_SIZE = 50
INFERENCE_INTERVAL = 1  # 可设为 3（10Hz）或 1（30Hz）
```

---

## 坑 5：端口冲突

### 现象
```
Address already in use
```

### 解决
SmolVLA 使用端口 **9877**（ACT 使用 9876）：
```bash
# 检查端口占用
lsof -i:9877
# 释放端口
kill -9 <PID>
```

---

## 坑 6：摄像头图像方向

### 说明
推理时摄像头方向应与录制时一致。客户端从摄像头获取的图像是 `[C, H, W]` 格式的 tensor，通过 `.cpu().numpy()` 转为 numpy 后发送。如果需要添加 batch 维度或 resize，在服务器端做。

---

## 坑 7：数据集路径不一致

### 现象
推理时服务器加载 `DATASET_DIR` 相关的 stats，找不到路径。

### 原因
DATASET_DIR 仍指向 ACT 数据集路径，而非 SmolVLA 数据集。

### 解决
```python
DATASET_DIR = "/home/jer/ws_issac/ws/j_so101_sim2real_touch/datasets/sim_lerobot_smolvla"
```
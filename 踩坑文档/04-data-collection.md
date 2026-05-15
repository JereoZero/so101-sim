# 04 — 仿真数据录制

## 坑 1：录制数据中夹爪角度不正确

### 现象
录制完成后回放发现夹爪始终处于某个固定状态（张开/闭合）。

### 原因
真机夹爪的角度范围（-0.94~0.94 rad）与仿真 URDF 范围（-0.17~1.75 rad）不一致，映射关系需要正确处理。

### 解决
在数据录制时做好角度映射：
```python
# 真机 → 仿真映射
gripper_real = joint_pos_from_leader[5]   # -0.94 ~ 0.94
gripper_sim = map_range(gripper_real, -0.94, 0.94, -0.17, 1.75)
```

具体校准值参考 `/home/jer/ws_issac/ws/j_so101_sim2real_touch/docs/calibration/CALIBRATION_DATA.md`。

---

## 坑 2：摄像头分辨率不一致

### 现象
训练时报错图像尺寸不匹配。

### 原因
录制时摄像头设为 640×480，某些脚本可能默认设为 160×120。

### 解决
统一设定 640×480：
```python
camera_cfg = CameraCfg(
    resolution=(640, 480),
    fps=30,
)
```

640×480 与 SmolVLA 模型预处理流程兼容（会自动 resize 到 512×512）。

---

## 坑 3：录制帧率不稳定

### 现象
回放时帧间隔不均匀，有时 30fps 有时掉帧。

### 说明
仿真渲染 + 数据录制（HDF5 I/O）同时进行会有性能波动。这在一定程度上是正常的。降低录制分辨率可以缓解（如果确实需要严格 30fps）。

当前 640×480@30fps 在 RTX 5070 上可行。

---

## 坑 4：录制文件太大

### 现象
每个 episode 的 HDF5 文件几百 MB，100 个 episodes 就几十 GB。

### 说明
640×480 RGB × 2 摄像头，每个 episode 几百帧。这是正常的数据量。

转换后的 LeRobot Parquet 格式会更紧凑。

---

## 坑 5：TCP 粘包

### 现象
接收到的遥操作指令包含多个 JSON 对象连在一起。

### 解决
在 `tcp_server.py` 中按换行符分割：
```python
data = self.sock.recv(4096).decode()
messages = data.strip().split('\n')
for msg in messages:
    cmd = json.loads(msg)
    self.joint_pos_target = cmd["joint_pos"]
```

---

## 坑 6：物体随机化失效

### 现象
方块/盘子总是出现在同一个位置，没有随机化。

### 原因
随机化逻辑中 `np.random.seed()` 被固定了，或随机范围写错。

### 正确的随机化
```python
# 盘子：基准位置 ± 5cm 随机
plate_offset = np.random.uniform(-0.05, 0.05, 2)
plate_pos = base_plate_pos + plate_offset

# 方块：盘子边缘外 2-10cm
angle = np.random.uniform(0, 2*np.pi)
distance = np.random.uniform(0.02, 0.10) + plate_radius
block_pos = plate_pos + [distance * cos(angle), distance * sin(angle)]
```
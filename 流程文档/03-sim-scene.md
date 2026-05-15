# 03 — 仿真场景搭建

## 场景概览

仿真场景由 `so101_sim_data_collection.py`（后拆分为 `so101_sim_with_comm.py`）构建，包含以下元素：

```
场景层级：
  World/
  ├── 地面（哑光灰色地砖）
  ├── 灯光（DomeLight + 聚光灯）
  ├── 桌子（100cm × 50cm，高 75cm，浅橡木色）
  ├── SO101 机器人（URDF 导入）
  ├── 小方块（3.5cm 边长，随机位置）
  ├── 小盘子（8.5cm 直径，随机位置）
  ├── 腕部摄像头（GC0308，640×480，30fps）
  └── 第三视角摄像头（GC2083，640×480，30fps）
```

## 场景参数

### 桌子

| 参数 | 值 |
|---|---|
| 尺寸 | 100cm × 50cm × 2cm |
| 高度 | 75cm |
| 颜色 | 浅橡木色 (0.82, 0.71, 0.57) |
| 物理材质 | 木质（静摩擦 0.8，动摩擦 0.6） |

### 机器人

- **URDF 路径**：`/home/jer/ws_issac/thirdparty/SO-ARM100/Simulation/SO101/so101_new_calib.urdf`
- **位置**：桌子长边中间，底座固定
- **关节驱动**：stiffness=1000, damping=100, effort_limit=50
- **关节配置**：6 个 STS3215 舵机

| 关节 | 正常范围（度） |
|---|---|
| shoulder_pan | -165 ~ 165 |
| shoulder_lift | -100 ~ 100 |
| elbow_flex | -165 ~ 165 |
| wrist_flex | -165 ~ 165 |
| wrist_roll | -180 ~ 180（360°旋转） |
| gripper | 0 ~ 100 |

### 摄像头

| 摄像头 | 型号 | 分辨率 | 帧率 | 数据类型 | 位置 |
|---|---|---|---|---|---|
| 腕部 | GC0308 格科微 | 640×480 | 30fps | RGB | 夹爪侧 |
| 第三视角 | GC2083 | 640×480 | 30fps | RGB + 深度 | 桌面斜上方 |

**第三视角摄像头详细参数**：
- 焦距：3.42mm
- 视场角：160°（水平 125°）
- 位置：`(0.9, -0.05, 1.12)`，离桌面约 39cm
- 朝向（Isaac Sim UI 显示）：欧拉角 XYZ `(16°, 38°, 76°)`
- USD 文件四元数：`(w=0.7099, x=0.3022, y=0.1730, z=0.6122)`

> ⚠️ **摄像头朝向设置注意**：不能在 Python API 中直接用 USD 的四元数设置朝向（坐标系转换不一致），应该让 USD 文件的 transform 自然生效。详见踩坑文档 [坑 6: 摄像头朝向设置不生效](../踩坑文档/03-robot-control.md#坑-6摄像头朝向设置不生效isaaclab-坐标系陷阱)。

### 物体随机化

- **盘子**：基准位置 ± 5cm 半径内随机
- **方块**：距离盘子外边缘 2-10cm 随机

## 物理材质优化

为了提升抓取稳定性，修改了多种物体的物理材质：

| 物体 | 静摩擦 | 动摩擦 | 弹性 |
|---|---|---|---|
| **夹爪** | 1.2 | 1.0 | 0.1 |
| **方块** | 1.5 | 1.2 | 0.1 |
| **桌面** | 0.8 | 0.6 | 0.2 |
| **盘子** | 0.4 | 0.3 | 0.1 |

同时优化了求解器参数：
- `solver_position_iteration_count`: 8 → 16
- `solver_velocity_iteration_count`: 0 → 1
- `max_depenetration_velocity`: 10.0

## 源码文件

场景构建的核心源码：

| 文件 | 职责 |
|---|---|
| `so101_sim_with_comm.py` | 主入口，场景构建 + 仿真循环 |
| `tcp_server.py` | TCP 通信，接收遥操作指令 |
| `hdf5_recorder.py` | HDF5 数据录制 |
| `robot_config.py` | 关节限位 + 角度裁剪 |
| `physics_config.py` | 物理材质配置 |

## LeRobot 源码修改

为适配 SO101 机械臂，对 LeRobot 0.5.0 做了 5 处修改：

| 修改 | 文件 | 说明 |
|---|---|---|
| wrist_roll 可校准 | so_leader.py | 校准时包含全部 6 关节 |
| wrist_roll 可校准 | so_follower.py | 校准时包含全部 6 关节 |
| 夹爪扭矩 100% | so_follower.py | Max_Torque_从 500 → 1000 |
| 复位阶段 teleop | lerobot_record.py | 简化判断逻辑 |
| fixed_joints 锁定 | config_so_follower.py<br>so_follower.py | 新增固定关节功能 |

## 常见问题

1. **关节不响应**：检查 USD 缓存，清理 `/tmp/IsaacLab/` 和 `~/.local/share/isaaclab/usd_cache/`
2. **夹爪抓不住**：检查摩擦系数设置和扭矩限制（详见踩坑文档 [坑 3](../踩坑文档/03-robot-control.md#坑-3夹爪扭矩不足)、[坑 8](../踩坑文档/03-robot-control.md#坑-8夹爪空气碰撞还没碰到物体就被弹开)）
3. **方块穿透桌面**：增加 `max_depenetration_velocity` 和求解器迭代次数（详见踩坑文档 [坑 9](../踩坑文档/03-robot-control.md#坑-9夹爪穿透物体)）
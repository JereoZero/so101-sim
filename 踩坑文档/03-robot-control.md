# 03 — 仿真中 SO101 运动控制

## 坑 1：关节 stiffness=0 导致机械臂不动（最重要）

### 现象
仿真启动后，机械臂收到关节目标指令但完全不响应，保持初始姿态不动。

### 原因
Isaac Sim 中关节的 `stiffness` 参数默认值为 0，意味着 PD 控制器不生效，目标位置被忽略。

### 解决
在 `so_arm101.py` 中**强制设置**关节驱动参数（发现 stiffness 未被正确从 URDF 读取）：

```python
joint_drive_params = {
    "stiffness": 1000.0,
    "damping": 100.0,
    "effort_limit": 50.0,
}
```

**路径**：`/home/jer/ws_issac/thirdparty/isaac_so_arm101/src/isaac_so_arm101/robots/trs_so101/so_arm101.py`

---

## 坑 2：关节角度超出限位

### 现象
机械臂运动到极限位置后抖动、反弹或穿透。

### 原因
真机主臂发送的角度在仿真 URDF 关节限位之外。

### 解决
使用 `robot_config.py` 中的 `clip_joint_angles()` 裁剪：

```python
def clip_joint_angles(joint_angles):
    for i, angle in enumerate(joint_angles):
        joint_angles[i] = max(JOINT_LIMITS[i][0], min(JOINT_LIMITS[i][1], angle))
    return joint_angles
```

关节限位配置（弧度，来自真机校准数据 `j_leader.json`）：

| 关节 | 下限 | 上限 |
|---|---|---|
| shoulder_pan | -1.99 | 1.96 |
| shoulder_lift | -1.82 | 1.83 |
| elbow_flex | -1.69 | 1.69 |
| wrist_flex | -1.79 | 1.79 |
| wrist_roll | -1.46 | 2.92 |
| gripper | -0.94 | 0.94 |

---

## 坑 3：夹爪扭矩不足

### 现象
夹爪无法完全张开或闭合无力。

### 原因
LeRobot 默认 Max_Torque_Limit 为 500（50%扭矩）。

### 解决
修改 `so_follower.py`（LeRobot 源码）：

```python
if motor == "gripper":
    self.bus.write("Max_Torque_Limit", motor, 1000)  # 100%
```

---

## 坑 4：仿真运动一顿一顿

### 现象
真机主臂操作流畅，但仿真从臂运动卡顿、不连续。

### 可能原因
1. **TCP 延迟**：网络通信延迟
2. **求解器迭代不足**：物理计算跟不上
3. **渲染帧率低**：GUI 窗口渲染占用资源

### 解决
```python
# 增加求解器参数
articulation_props=ArticulationRootPropertiesCfg(
    solver_position_iteration_count=16,  # 8 → 16
    solver_velocity_iteration_count=1,   # 0 → 1
)

# 增加速度限制
rigid_props=RigidBodyPropertiesCfg(
    max_angular_velocity=1000.0,
    max_linear_velocity=1000.0,
)
```

---

## 坑 5：单帧控制 vs 连续轨迹

### 说明
仿真中 `robot.set_joint_position_target()` 设置的是**目标位置**而非直接位置。PD 控制器会逐步移动到目标。如果目标是跳跃式的（真机→仿真的离散映射），运动看起来不够平滑。

这是正常的，因为使用的是位置控制而非轨迹控制。在数据录制阶段可以接受。

---

## 坑 6：摄像头朝向设置不生效（IsaacLab 坐标系陷阱）

### 现象
在 Isaac Sim UI 中手动调整好摄像头视角后导出 USD 文件，USD 中的 `quatd xformOp:orient` 参数是正确的。但在 Python 脚本中使用相同的四元数设置 `CameraOffsetCfg(rot=...)` 或 `set_world_poses()`，摄像头朝向完全不对。

### 原因
**IsaacLab 的 Python API 与 USD 的坐标系约定不一致。** USD 中的四元数不能直接在 Python API 中使用，即使使用 `convention="ros"/"world"/"opengl"` 等参数也无法修正。

### 目标参数
从 Isaac Sim UI 手动调整后得到的正确参数：
- **位置**: `(0.9, -0.05, 1.12)`
- **UI 显示的欧拉角**: `(16°, 38°, 76°)` XYZ 顺序
- **USD 文件中的四元数**: `(w=0.7099, 0.3022, 0.1730, 0.6122)`

### 尝试过的方法（全部失败）

| 方法 | 结果 |
|---|---|
| `CameraOffsetCfg(rot=四元数)` | 朝向错误 |
| `set_world_poses(convention="ros")` | 朝向错误 |
| `set_world_poses(convention="world")` | 朝向错误 |
| `set_world_poses(convention="opengl")` | 朝向错误 |
| 用 scipy 从欧拉角反算四元数 | 得到的四元数与 USD 不匹配 |

### 最终解决
**不要在 Python 代码中设置朝向。** 正确做法是：

1. 在 Isaac Sim GUI 中手动调整好摄像头位置和角度
2. 导出为 USD 文件
3. 仿真启动时直接加载 USD 文件，让 USD 的 transform 自动生效
4. Python 代码中只设置摄像头参数（分辨率、帧率、数据类型），不覆盖 transform

在 IsaacLab 中创建摄像头时，用空的 `offset` 或干脆不设 `rot`，让 USD 文件中的朝向自然生效：

```python
overhead_camera_cfg = CameraCfg(
    prim_path="/World/CameraTripod/camera_third_person",
    update_period=0.033,
    height=480,
    width=640,
    data_types=["rgb"],
    spawn=sim_utils.PinholeCameraCfg(
        focal_length=3.42,
        horizontal_aperture=13.1,
        focus_distance=0.37,
        clipping_range=(0.01, 2.0),
    ),
    offset=CameraOffsetCfg(
        pos=(0.0, 0.0, 0.0),
        # 不要设置 rot！让 USD 自身的 transform 生效
    ),
)
```

**教训**：在 IsaacLab 中，USD 文件可以通过 Python API 加载和修改，但 **transform（位置+朝向）层面的数据在两者之间的传递存在坐标系转换问题**。如果 USD 中已经设置了正确的 transform，就不要在 Python 中覆盖它。

---

## 坑 7：方块弹性过高（碰撞后弹飞）

### 现象
方块与桌面碰撞时像橡胶球一样弹跳，完全不像泡沫垫的物理表现。

### 原因
- `restitution`（弹性系数）默认值导致过弹
- `solver_position_iteration_count` 太少（默认 8），物理计算精度不够
- 质量太轻（1.9g），轻微碰撞就飞

### 解决
```python
cube_physics = sim_utils.RigidBodyMaterialCfg(
    static_friction=0.8,
    dynamic_friction=0.6,
    restitution=0.05,       # 极低弹性（原来是 0.1）
)

rigid_props = sim_utils.RigidBodyPropertiesCfg(
    max_depenetration_velocity=0.1,       # 大幅降低（原来是 10.0）
    solver_position_iteration_count=64,   # 大幅提高精度
    solver_velocity_iteration_count=8,
)

mass_props = sim_utils.MassPropertiesCfg(mass=0.01)  # 增加到 10g
```

**教训**：抓取任务中方块需要硬且重，低弹性 + 高求解器迭代 + 10g 以上质量。

---

## 坑 8：夹爪空气碰撞（还没碰到物体就被弹开）

### 现象
夹爪还没实际碰到方块，方块就被弹飞了。感觉像"隔空取物"。

### 原因
URDF 导入时默认使用 `convexHull`（凸包）近似碰撞体。凸包比实际网格大，产生"空气碰撞"。

### 解决

**推荐**：修改 URDF 导入配置，使用更精确的碰撞体：
```python
SO_ARM101_CFG = ArticulationCfg(
    spawn=sim_utils.UrdfFileCfg(
        collider_type="convex_decomposition",  # 默认是 "convex_hull"
    ),
)
```
修改后需删除 USD 缓存（`~/.local/share/isaaclab/usd_cache/`）。

**运行时缓解**（无法重新导入时）：
```python
from pxr import UsdPhysics

mesh_collision_api = UsdPhysics.MeshCollisionAPI.Apply(prim)
mesh_collision_api.CreateApproximationAttr().Set(
    UsdPhysics.Tokens.none  # 使用原始网格，不用凸包
)
```

碰撞近似方式精度排序：`none`（原始网格）> `convexDecomposition` > `sdf` > `convexHull`（默认，最大）

---

## 坑 9：夹爪穿透物体

### 现象
夹爪能穿透方块内部，看起来像是碰撞检测失效。

### 解决
```python
# 全局物理设置
sim_cfg = sim_utils.SimulationCfg(
    physx=sim_utils.PhysxCfg(
        solver_type="TGS",         # TGS solver 更稳定
        enable_ccd=True,           # 启用连续碰撞检测（CCD）
        enable_stabilization=True,
    )
)

# 碰撞属性
collision_props = sim_utils.CollisionPropertiesCfg(
    contact_offset=0.005,  # 接触偏移
    rest_offset=0.001,     # 静止偏移
)
```

**关键参数说明**：
- `enable_ccd=True`：连续碰撞检测，防止高速穿透
- `solver_type="TGS"`：相比默认的 PGS 更稳定，但稍慢
- `contact_offset` 越小越精确，但太小可能导致穿透

---

## 坑 10：机械臂自动复位抖动

### 现象
没有遥操作信号时，机械臂周期性地自动复位抖动。

### 原因
代码中每 N 步自动重置机器人状态（`if count % 500 == 0`），导致机械臂突然跳回默认姿态。

### 解决
```python
# ❌ 错误：周期性重置
if count % 500 == 0:
    root_state = robot.data.default_root_state.clone()
    robot.write_root_state_to_sim(root_state)

# ✅ 正确：只在初始时重置一次
if count == 0:
    root_state = robot.data.default_root_state.clone()
    robot.write_root_state_to_sim(root_state)
```

---

## 附录：LeRobot 源码修改详解

以下 5 处修改是让 LeRobot 0.5.0 适配 SO101 机械臂所必需的，修改文件位于 `/home/jer/ws_issac/thirdparty/lerobot-0.5.0/src/lerobot/`。

### 修改 1 & 2：wrist_roll 关节可校准

**文件**：`teleoperators/so_leader/so_leader.py` + `robots/so_follower/so_follower.py`

原代码将 `wrist_roll` 排除在校准流程之外（因为它是 360° 旋转关节），直接设为固定范围 0-4095。但由于机械结构限制，SO101 的 wrist_roll 并非无限旋转，需要实际校准。

```python
# ❌ 原代码
full_turn_motor = "wrist_roll"
unknown_range_motors = [motor for motor in self.bus.motors if motor != full_turn_motor]
range_mins, range_maxes = self.bus.record_ranges_of_motion(unknown_range_motors)
range_mins[full_turn_motor] = 0
range_maxes[full_turn_motor] = 4095

# ✅ 修改后
range_mins, range_maxes = self.bus.record_ranges_of_motion(self.bus.motors)
```

### 修改 3：夹爪扭矩 100%

**文件**：`robots/so_follower/so_follower.py`

```python
# ❌ 原代码：50% 扭矩
self.bus.write("Max_Torque_Limit", motor, 500)
self.bus.write("Protection_Current", motor, 250)
self.bus.write("Overload_Torque", motor, 25)

# ✅ 修改后：100% 扭矩
self.bus.write("Max_Torque_Limit", motor, 1000)
self.bus.write("Protection_Current", motor, 500)
self.bus.write("Overload_Torque", motor, 50)
```

### 修改 4：复位阶段遥操作判断简化

**文件**：`scripts/lerobot_record.py`

原代码使用 `isinstance(teleop, Teleoperator)` 判断类型，在复位阶段（dataset=None）时可能无法正确识别。改为直接检查 `teleop is not None`。

```python
# ❌ 原代码
elif policy is None and isinstance(teleop, Teleoperator):

# ✅ 修改后
elif policy is None and teleop is not None:
```

### 修改 5：fixed_joints 锁定关节

**文件**：`robots/so_follower/config_so_follower.py` + `so_follower.py`

新增功能：允许在配置中指定固定关节角度，在 `send_action` 时被强制覆盖。常用于锁定 wrist_roll。

```python
# 配置文件新增
fixed_joints: dict[str, float] | None = None

# so_follower.py send_action 中新增
if self.config.fixed_joints is not None:
    for joint_name, fixed_angle in self.config.fixed_joints.items():
        if joint_name in goal_pos:
            goal_pos[joint_name] = fixed_angle
```

使用示例：
```bash
lerobot-teleoperate \
    --robot.fixed_joints='{"wrist_roll": -67.74}'
```
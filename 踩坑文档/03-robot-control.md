# 03 — 仿真中 SO101 运动控制

## 坑 1：关节 stiffness=0 导致机械臂不动（最重要）

### 现象
仿真启动后，机械臂收到关节目标指令但完全不响应，保持初始姿态不动。

### 原因
Isaac Sim 中关节的 `stiffness` 参数默认值为 0，意味着 PD 控制器不生效，目标位置被忽略。

### 解决
在 `so_arm101.py` 中**强制设置**关节驱动参数：

```python
# 发现 stiffness 未被正确从 URDF 读取后被解决
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

关节限位配置（弧度）：

| 关节 | 下限 | 上限 |
|---|---|---|
| shoulder_pan | -2.88 | 2.88 |
| shoulder_lift | -1.75 | 1.75 |
| elbow_flex | -2.88 | 2.88 |
| wrist_flex | -2.88 | 2.88 |
| wrist_roll | -3.14 | 3.14 |
| gripper | -0.17 | 1.75 |

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
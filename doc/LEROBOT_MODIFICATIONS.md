# LeRobot 0.5.0 源代码修改记录

本文档记录对 LeRobot 0.5.0 官方源码的修改。

---

## 修改概述

| 修改 | 文件 | 说明 |
|------|------|------|
| 1. wrist_roll 可校准 | so_leader.py | 校准时包含 wrist_roll 关节 |
| 2. wrist_roll 可校准 | so_follower.py | 校准时包含 wrist_roll 关节 |
| 3. 夹爪扭矩 100% | so_follower.py | Max_Torque_Limit=1000 |
| 4. 复位阶段 teleop | lerobot_record.py | 改为 `teleop is not None` |
| 5. fixed_joints 锁定关节 | config_so_follower.py, so_follower.py | 新增功能 |

---

## 修改 1: wrist_roll 可校准 (so_leader.py)

### 文件位置
`/home/jer/ws_issac/thirdparty/lerobot-0.5.0/src/lerobot/teleoperators/so_leader/so_leader.py`

### 修改内容 (第 105-109 行)

**修改前:**
```python
full_turn_motor = "wrist_roll"
unknown_range_motors = [motor for motor in self.bus.motors if motor != full_turn_motor]
print(
    f"Move all joints except '{full_turn_motor}' sequentially through their "
    "entire ranges of motion.\nRecording positions. Press ENTER to stop..."
)
range_mins, range_maxes = self.bus.record_ranges_of_motion(unknown_range_motors)
range_mins[full_turn_motor] = 0
range_maxes[full_turn_motor] = 4095
```

**修改后:**
```python
print(
    "Move all joints sequentially through their "
    "entire ranges of motion.\nRecording positions. Press ENTER to stop..."
)
range_mins, range_maxes = self.bus.record_ranges_of_motion(self.bus.motors)
```

### 原理说明
- 原代码将 `wrist_roll` 排除在校准流程之外，直接设置固定范围（0-4095）
- 修改后，所有 6 个关节都会进行校准，包括 `wrist_roll`

---

## 修改 2: wrist_roll 可校准 (so_follower.py)

### 文件位置
`/home/jer/ws_issac/thirdparty/lerobot-0.5.0/src/lerobot/robots/so_follower/so_follower.py`

### 修改内容 (第 130-139 行)

**修改前:**
```python
# Attempt to call record_ranges_of_motion with a reduced motor set when appropriate.
full_turn_motor = "wrist_roll"
unknown_range_motors = [motor for motor in self.bus.motors if motor != full_turn_motor]
print(
    f"Move all joints except '{full_turn_motor}' sequentially through their "
    "entire ranges of motion.\nRecording positions. Press ENTER to stop..."
)
range_mins, range_maxes = self.bus.record_ranges_of_motion(unknown_range_motors)
range_mins[full_turn_motor] = 0
range_maxes[full_turn_motor] = 4095
```

**修改后:**
```python
print(
    "Move all joints sequentially through their "
    "entire ranges of motion.\nRecording positions. Press ENTER to stop..."
)
range_mins, range_maxes = self.bus.record_ranges_of_motion(self.bus.motors)
```

### 原理说明
- 同修改 1，让 `wrist_roll` 可以被校准而不是使用固定值

---

## 修改 3: 夹爪扭矩 100%

### 文件位置
`/home/jer/ws_issac/thirdparty/lerobot-0.5.0/src/lerobot/robots/so_follower/so_follower.py`

### 修改内容 (第 161-164 行)

**修改前:**
```python
if motor == "gripper":
    self.bus.write("Max_Torque_Limit", motor, 500)  # 50% of max torque to avoid burnout
    self.bus.write("Protection_Current", motor, 250)  # 50% of max current to avoid burnout
    self.bus.write("Overload_Torque", motor, 25)  # 25% torque when overloaded
```

**修改后:**
```python
if motor == "gripper":
    self.bus.write("Max_Torque_Limit", motor, 1000)  # 100% max torque for gripper
    self.bus.write("Protection_Current", motor, 500)  # 100% max current for gripper
    self.bus.write("Overload_Torque", motor, 50)  # 50% torque when overloaded
```

### 原理说明
- Feetech 电机 Max_Torque_Limit 范围是 0-1000
- 原代码设置为 500（50%），扭矩不足以驱动夹爪完全张开
- 修改为 1000（100%）后，夹爪可以正常张开

---

## 修改 4: 复位阶段 teleop 控制

### 文件位置
`/home/jer/ws_issac/thirdparty/lerobot-0.5.0/src/lerobot/scripts/lerobot_record.py`

### 修改内容 (第 371 行)

**修改前:**
```python
elif policy is None and isinstance(teleop, Teleoperator):
    if robot.name == "unitree_g1":
        teleop.send_feedback(obs)
    act = teleop.get_action()
```

**修改后:**
```python
elif policy is None and teleop is not None:
    if robot.name == "unitree_g1":
        teleop.send_feedback(obs)
    act = teleop.get_action()
```

### 原理说明
- 原代码使用 `isinstance(teleop, Teleoperator)` 检查类型
- 修改为直接检查 `teleop is not None`，更简单直接
- 这样在复位阶段（dataset 为 None 时）也能正确识别 teleop 并发送控制指令

---

## 修改 5: fixed_joints 锁定关节功能

### 5.1 config_so_follower.py

### 文件位置
`/home/jer/ws_issac/thirdparty/lerobot-0.5.0/src/lerobot/robots/so_follower/config_so_follower.py`

### 修改内容 (第 38-41 行)

**新增配置项:**
```python
# Fixed joints: specify joint angles that will remain constant during teleoperation/recording.
# Format: {"joint_name": angle_in_degrees}
# Example: {"wrist_roll": -67.74}
fixed_joints: dict[str, float] | None = None
```

### 5.2 so_follower.py

### 文件位置
`/home/jer/ws_issac/thirdparty/lerobot-0.5.0/src/lerobot/robots/so_follower/so_follower.py`

### 修改内容 (第 207-211 行)

**在 send_action 方法中添加:**
```python
goal_pos = {key.removesuffix(".pos"): val for key, val in action.items() if key.endswith(".pos")}

# Apply fixed joints - override the goal position for specified joints
if self.config.fixed_joints is not None:
    for joint_name, fixed_angle in self.config.fixed_joints.items():
        if joint_name in goal_pos:
            goal_pos[joint_name] = fixed_angle
```

### 原理说明
- 允许在配置中指定固定关节角度
- 在 send_action 时，被指定的关节会被强制设置为固定角度
- 常用于锁定不需要控制的关节（如第5关节 wrist_roll）

### 使用示例
```bash
lerobot-teleoperate \
    --robot.type=so101_follower \
    --robot.port=/dev/ttySO101_FOLLOWER \
    --robot.id=j_follower \
    --robot.fixed_joints='{"wrist_roll": -67.74}'
```

---

## 关节配置参考

| 关节 | ID | 类型 | 正常范围 (度) |
|------|-----|------|---------------|
| shoulder_pan | 1 | STS3215 | -165 ~ 165 |
| shoulder_lift | 2 | STS3215 | -100 ~ 100 |
| elbow_flex | 3 | STS3215 | -165 ~ 165 |
| wrist_flex | 4 | STS3215 | -165 ~ 165 |
| wrist_roll | 5 | STS3215 | -180 ~ 180 (360旋转) |
| gripper | 6 | STS3215 | 0 ~ 100 |

---

## 更新日志

### 2026-04-16
- 添加 fixed_joints 锁定关节功能
- 完成所有 5 项修改
- 测试通过真机遥操作

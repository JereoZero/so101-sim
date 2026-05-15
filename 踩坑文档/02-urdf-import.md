# 02 — SO101 URDF 导入与适配

## 坑 1：URDF 路径不存在或格式不对

### 现象
```
Error: Could not find URDF file at ...
```

### 原因
SO101 的 URDF 文件位于第三方目录，不是 IsaacLab 默认路径。

### 解决
确认 URDF 正确路径：
```
/home/jer/ws_issac/thirdparty/SO-ARM100/Simulation/SO101/so101_new_calib.urdf
```

仿真中通过 `isaac_so_arm101` 包导入：
```python
from isaac_so_arm101 import SO_ARM101_CFG
```

---

## 坑 2：坐标系对齐问题

### 现象
机器人导入后方向不对，或夹爪朝向错误。

### 说明
URDF 中的坐标系可能与 Isaac Sim 世界坐标系不一致。项目中 `isaac_so_arm101` 已经处理好了坐标系对齐，一般不需要手动调整。

如有需要，在 `so_arm101.py` 的 `init_state` 中调整：
```python
init_state = ArticulationCfg.InitialStateCfg(
    pos=(x, y, z),
    rot=(w, x, y, z),
    joint_pos={...}
)
```

---

## 坑 3：关节名称不匹配

### 现象
仿真中某些关节不响应控制指令。

### 原因
URDF 关节名称与代码中使用的名称不匹配。

### S0-101 6 个关节名称：
```
shoulder_pan
shoulder_lift
elbow_flex
wrist_flex
wrist_roll
gripper
```

务必使用这些确切名称，不要用 `Joint1`/`Joint2` 等别名。

---

## 坑 4：self_collision 导致的运动限制

### 现象
机械臂在某些角度下运动异常、卡顿甚至崩溃。

### 原因
`enabled_self_collisions=True` 时，机械臂的连杆之间会相互碰撞检测。复现真机的碰撞限制。

### 解决
在 `so_arm101.py` 配置中：
```python
articulation_props=sim_utils.ArticulationRootPropertiesCfg(
    enabled_self_collisions=True,
    solver_position_iteration_count=16,
    solver_velocity_iteration_count=1,
)
```

增加求解器迭代次数（8→16）可以减少碰撞检测误差。
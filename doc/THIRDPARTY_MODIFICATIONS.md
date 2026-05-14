# 第三方库修改记录

本文档记录对第三方依赖库（thirdparty）的修改。

---

## 修改概述

| 修改 | 库 | 文件 | 说明 |
|------|-----|------|------|
| 1. 夹爪物理材质 | isaac_so_arm101 | so_arm101.py | ~~增加夹爪摩擦系数~~ (UrdfFileCfg不支持) |
| 2. 方块物理材质 | so101_sim_with_comm.py | 仿真服务器 | 增加硬度和摩擦 |
| 3. 桌面物理材质 | so101_sim_with_comm.py | 仿真服务器 | 木质桌面摩擦 |
| 4. 盘子物理材质 | so101_sim_with_comm.py | 仿真服务器 | 光滑陶瓷摩擦 |
| 5. URDF夹爪摩擦 | isaac_so_arm101 | so_arm101.urdf | 夹爪表面摩擦系数 |

---

## 修改 1: 夹爪物理材质 + 机械臂刚体属性优化 (isaac_so_arm101)

### 文件位置
`/home/jer/ws_issac/thirdparty/isaac_so_arm101/src/isaac_so_arm101/robots/trs_so101/so_arm101.py`

### 修改内容

**新增导入:**
```python
from isaaclab.sim.spawners.materials import RigidBodyMaterialCfg
```

**新增物理材质定义 (在 SO_ARM101_CFG 之前):**
```python
# 夹爪物理材质 - 高摩擦力，便于抓取
GRIPPER_PHYSICS_MATERIAL = RigidBodyMaterialCfg(
    static_friction=1.2,   # 高静摩擦
    dynamic_friction=1.0,  # 高动摩擦
    restitution=0.1,       # 低弹性
)
```

**修改 UrdfFileCfg 配置:**
```python
spawn=sim_utils.UrdfFileCfg(
    ...
    rigid_props=sim_utils.RigidBodyPropertiesCfg(
        disable_gravity=False,
        max_depenetration_velocity=5.0,
        max_angular_velocity=1000.0,  # 增加角速度限制
        max_linear_velocity=1000.0,   # 增加线速度限制
    ),
    articulation_props=sim_utils.ArticulationRootPropertiesCfg(
        enabled_self_collisions=True,
        solver_position_iteration_count=16,  # 从8增加到16
        solver_velocity_iteration_count=1,   # 从0增加到1
    ),
    physics_material=GRIPPER_PHYSICS_MATERIAL,
)
```

### 参数说明
| 参数 | 值 | 说明 |
|------|-----|------|
| static_friction | 1.2 | 静摩擦系数，默认0.5 |
| dynamic_friction | 1.0 | 动摩擦系数，默认0.5 |
| restitution | 0.1 | 弹性系数，默认0.0 |
| solver_position_iteration_count | 16 | 位置求解器迭代次数（原8）|
| solver_velocity_iteration_count | 1 | 速度求解器迭代次数（原0）|
| max_angular_velocity | 1000.0 | 最大角速度 |
| max_linear_velocity | 1000.0 | 最大线速度 |

---

## 修改 2: 方块物理材质 (仿真服务器)

### 文件位置
`/home/jer/ws_issac/ws/j_so101_sim2real_touch/src/so101_sim_with_comm.py`

### 修改内容

**新增导入:**
```python
from isaaclab.sim.spawners.materials import RigidBodyMaterialCfg
```

**方块配置修改:**
```python
# 方块材质：高密度泡沫垫 - 硬且高摩擦
cube_physics_material = RigidBodyMaterialCfg(
    static_friction=1.5,  # 高静摩擦
    dynamic_friction=1.2,  # 高动摩擦
    restitution=0.1,  # 低弹性（不Q弹）
)

cube_cfg = RigidObjectCfg(
    prim_path="/World/Cube",
    spawn=sim_utils.CuboidCfg(
        size=(0.035, 0.035, 0.035),
        rigid_props=sim_utils.RigidBodyPropertiesCfg(
            max_depenetration_velocity=10.0,  # 减少形变
            solver_position_iteration_count=8,  # 增加求解器迭代次数，更硬
        ),
        mass_props=sim_utils.MassPropertiesCfg(mass=0.0019),
        collision_props=sim_utils.CollisionPropertiesCfg(),
        visual_material=sim_utils.PreviewSurfaceCfg(
            diffuse_color=(1.0, 0.4, 0.2),
            roughness=0.95,  # 非常粗糙的表面（沙沙感）
            metallic=0.0,
        ),
        physics_material=cube_physics_material,
    ),
    ...
)
```

### 参数说明
| 参数 | 值 | 说明 |
|------|-----|------|
| static_friction | 1.5 | 静摩擦系数 |
| dynamic_friction | 1.2 | 动摩擦系数 |
| restitution | 0.1 | 弹性系数（低弹性不Q弹） |
| roughness | 0.95 | 视觉粗糙度（沙沙感表面） |
| max_depenetration_velocity | 10.0 | 最大穿透恢复速度 |
| solver_position_iteration_count | 8 | 求解器位置迭代次数 |

---

## 物理材质参考

### 摩擦系数对比
| 物体 | 静摩擦 | 动摩擦 | 说明 |
|------|--------|--------|------|
| 方块 | 1.5 | 1.2 | 泡沫垫材质，高摩擦 |
| 夹爪 | 1.2 | 1.0 | 便于抓取 |
| 默认值 | 0.5 | 0.5 | IsaacLab默认 |

### 弹性系数 (restitution)
| 物体 | 值 | 说明 |
|------|-----|------|
| 方块 | 0.1 | 低弹性，不Q弹 |
| 夹爪 | 0.1 | 低弹性 |
| 桌面 | 0.2 | 木质中等弹性 |
| 盘子 | 0.1 | 陶瓷低弹性 |
| 默认值 | 0.0 | 无弹性 |

---

## 修改 3: 桌面物理材质

### 文件位置
`/home/jer/ws_issac/ws/j_so101_sim2real_touch/src/so101_sim_with_comm.py`

### 修改内容

```python
# 桌面物理材质 - 木质桌面，中等摩擦
wood_physics_material = RigidBodyMaterialCfg(
    static_friction=0.8,   # 木质桌面摩擦
    dynamic_friction=0.6,
    restitution=0.2,
)
```

### 参数说明
| 参数 | 值 | 说明 |
|------|-----|------|
| static_friction | 0.8 | 木质桌面静摩擦 |
| dynamic_friction | 0.6 | 木质桌面动摩擦 |
| restitution | 0.2 | 中等弹性 |

---

## 修改 4: 盘子物理材质

### 文件位置
`/home/jer/ws_issac/ws/j_so101_sim2real_touch/src/so101_sim_with_comm.py`

### 修改内容

```python
# 盘子物理材质 - 光滑陶瓷/塑料材质
plate_physics_material = RigidBodyMaterialCfg(
    static_friction=0.4,   # 光滑表面
    dynamic_friction=0.3,
    restitution=0.1,
)
```

### 参数说明
| 参数 | 值 | 说明 |
|------|-----|------|
| static_friction | 0.4 | 光滑表面静摩擦 |
| dynamic_friction | 0.3 | 光滑表面动摩擦 |
| restitution | 0.1 | 低弹性 |

---

## 更新日志

### 2026-04-16
- 添加夹爪物理材质配置
- 添加方块物理材质配置
- 添加桌面物理材质配置
- 添加盘子物理材质配置
- 增加摩擦系数便于抓取

# 项目框架文档

本文档记录整体项目框架、环境配置和项目进度。

---

## 1. 项目概览

### 1.1 项目结构

```
/home/jer/ws_issac/
├── ws/                          # 工作空间
│   ├── doc/                     # 项目框架文档 (本文档)
│   │   ├── README.md           # 项目概览
│   │   ├── ENVIRONMENT.md       # 环境配置详情
│   │   └── LEROBOT_MODIFICATIONS.md  # LeRobot 源码修改记录
│   ├── j_so101_sim2real_touch/  # SO101 Sim2Real 项目
│   │   ├── src/                # 源代码
│   │   ├── docs/               # 项目文档
│   │   └── data/               # 录制数据
│   └── lerobot_so101/           # LeRobot 修改版 (已调试完成)
├── thirdparty/                  # 第三方库
│   ├── IsaacLab/                # IsaacLab 仿真框架
│   ├── SO-ARM100/              # SO101 官方 URDF
│   ├── lerobot-0.5.0/          # LeRobot 官方源码 (已应用修改)
│   └── isaac_so_arm101/         # IsaacLab SO101 配置参考
└── doc/                         # 公共文档
```

### 1.2 主要项目

| 项目 | 路径 | 说明 |
|------|------|------|
| SO101 Sim2Real | `/home/jer/ws_issac/ws/j_so101_sim2real_touch/` | 主力项目：IsaacLab + LeRobot 遥操作 |
| LeRobot 修改版 | `/home/jer/ws_issac/ws/lerobot_so101/` | 已调试完成，有校准数据 |

---

## 2. 环境配置

### 2.1 Conda 环境

| 环境名 | Python | 用途 | 关键依赖 |
|--------|--------|------|----------|
| `lerobot_issac` | 3.12 | IsaacLab + LeRobot 遥操作 | isaaclab, lerobot, torch |
| `lerobot` | 3.12 | LeRobot 开发 | lerobot, torch |
| `isaaclab` | 3.11 | IsaacLab 仿真 | isaaclab, torch |

### 2.2 关键路径

| 路径 | 说明 |
|------|------|
| `/home/jer/ws_issac/thirdparty/IsaacLab` | IsaacLab 主目录 |
| `/home/jer/ws_issac/thirdparty/SO-ARM100/Simulation/SO101/so101_new_calib.urdf` | SO101 URDF |
| `/home/jer/ws_issac/thirdparty/lerobot-0.5.0` | LeRobot 官方源码 (已应用修改) |
| `/home/jer/ws_issac/lerobot_so101/workspace/projects/lerobot/src` | LeRobot 修改版源码 |
| `~/isaacsim/Assets/Assets/Isaac/5.1` | Isaac Sim 资源路径 |

### 2.3 Isaac Sim 资源

```
~/isaacsim/Assets/Assets/Isaac/5.1/
├── Isaac/    (54GB) ✅
└── NVIDIA/   (124GB) ✅
```

---

## 3. 项目进度

### 3.1 已完成

- [x] 真机遥操作测试（主臂 + 从臂）
- [x] fixed_joints 锁定第5关节功能
- [x] LeRobot 0.5.0 源码修改

### 3.2 进行中

- [ ] 仿真环境测试
- [ ] 仿真遥操作测试
- [ ] 仿真 + 真机集成测试

### 3.3 待完成

- [ ] 录制数据测试
- [ ] 数据集管理
- [ ] 训练流程集成

---

## 4. LeRobot 源码修改

### 4.1 已应用的修改

参考文档：[LEROBOT_MODIFICATIONS.md](./LEROBOT_MODIFICATIONS.md)

| 修改 | 文件 | 说明 |
|------|------|------|
| 1. wrist_roll 可校准 | so_leader.py | 校准时包含 wrist_roll |
| 2. wrist_roll 可校准 | so_follower.py | 校准时包含 wrist_roll |
| 3. 夹爪扭矩 100% | so_follower.py | Max_Torque_Limit=1000 |
| 4. 复位阶段 teleop | lerobot_record.py | 改为 `teleop is not None` |
| 5. fixed_joints | config + so_follower.py | 锁定关节功能 |

### 4.2 修改位置

- `/home/jer/ws_issac/thirdparty/lerobot-0.5.0/src/lerobot/teleoperators/so_leader/so_leader.py`
- `/home/jer/ws_issac/thirdparty/lerobot-0.5.0/src/lerobot/robots/so_follower/so_follower.py`
- `/home/jer/ws_issac/thirdparty/lerobot-0.5.0/src/lerobot/robots/so_follower/config_so_follower.py`
- `/home/jer/ws_issac/thirdparty/lerobot-0.5.0/src/lerobot/scripts/lerobot_record.py`

---

## 5. 测试结果

### 5.1 真机遥操作测试

| 测试项 | 结果 |
|--------|------|
| 主臂连接 | ✅ 通过 |
| 从臂连接 | ✅ 通过 |
| 遥操作频率 | ✅ 60Hz (~16.7ms 延迟) |
| fixed_joints | ✅ wrist_roll 锁定在 -67.74° |

---

## 6. 下一步计划

### 6.1 仿真环境测试

1. 测试 IsaacLab 基本场景加载
2. 测试 SO101 URDF 导入
3. 验证场景配置（桌子、地面、摄像头）

### 6.2 仿真遥操作测试

1. 测试真机主臂 + 仿真从臂
2. 测试 fixed_joints 在仿真中生效
3. 验证遥操作延迟和稳定性

### 6.3 仿真 + 真机集成测试

1. 录制仿真数据
2. 对比真机录制数据
3. 验证 Sim2Real 一致性

---

## 7. 硬件配置

### 7.1 SO101 机械臂

| 组件 | 型号 | 串口 | 状态 |
|------|------|------|------|
| 主臂 | SO101 Leader | `/dev/ttySO101_LEADER` | ✅ 已连接 |
| 从臂 | SO101 Follower | `/dev/ttySO101_FOLLOWER` | ✅ 已连接 |

### 7.2 关节配置

| 关节 | ID | 类型 | 锁定角度 |
|------|-----|------|----------|
| shoulder_pan | 1 | STS3215 | - |
| shoulder_lift | 2 | STS3215 | - |
| elbow_flex | 3 | STS3215 | - |
| wrist_flex | 4 | STS3215 | - |
| wrist_roll | 5 | STS3215 | **-67.74°** |
| gripper | 6 | STS3215 | - |

---

## 8. 文档目录

### 8.1 项目框架文档
- `/home/jer/ws_issac/ws/doc/README.md` - 项目概览
- `/home/jer/ws_issac/ws/doc/ENVIRONMENT.md` - 环境配置详情
- `/home/jer/ws_issac/ws/doc/LEROBOT_MODIFICATIONS.md` - LeRobot 源码修改记录

### 8.2 项目文档
- `/home/jer/ws_issac/ws/j_so101_sim2real_touch/docs/` - SO101 Sim2Real 项目文档

### 8.3 公共文档
- `/home/jer/ws_issac/doc/COMMANDS.md` - 常用命令

---

## 9. 更新日志

### 2026-04-16
- 完成真机遥操作测试
- 完成 fixed_joints 功能添加和测试
- 创建 LeRobot 源码修改记录文档
- 规划仿真环境测试和仿真遥操作测试

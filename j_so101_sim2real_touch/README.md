# SO101 Sim2Real Touch - 定点归位项目

## 项目概述

- **机器人**：幻尔 SO101 机械臂
- **任务**：定点归位（Home Position）
- **方法**：Isaac Lab RL 训练 + Sim2Real 迁移
- **目标**：完成仿真到真机的完整闭环

## 技术栈

- **Isaac Lab**：仿真训练框架
- **LeRobot**：真机控制与模仿学习
- **URDF**：SO101 模型（已获取）

## 硬件配置

- **机械臂**：幻尔 SO101
- **GPU**：RTX 5070 (12GB)
- **操作系统**：Ubuntu 22.04
- **ROS**：ROS 2 Humble

## 软件环境

- **仿真平台**：NVIDIA Isaac Lab（thirdparty）
- **真机框架**：LeRobot
- **URDF 模型**：`/home/jer/ws_issac/thirdparty/SO-ARM100/Simulation/SO101/so101_new_calib.urdf`

## 目录结构

```
j_so101_sim2real_touch/
├── src/                 # 源代码
├── configs/             # 配置文件
├── scripts/             # 脚本
├── data/                # 数据集
├── models/              # 模型 checkpoint
├── outputs/             # 训练输出
├── docs/                # 文档
│   ├── EXECUTION_PLAN.md
│   └── EXECUTION_LOG.md
└── tests/               # 测试代码
```

## Sim2Real 流程

1. **仿真阶段**（Isaac Lab）
   - 创建 SO101 仿真环境
   - 设计 Reward 函数
   - RL 训练定点归位策略
   - 域随机化配置

2. **迁移阶段**
   - 观测/动作空间对齐
   - 真机参数校准
   - 开环测试
   - 闭环测试

3. **验证阶段**
   - 成功率统计
   - 性能优化
   - 演示录制

## 项目阶段

### Phase 1: 环境配置 ✅
- [x] Isaac Lab 环境
- [x] LeRobot 环境
- [x] SO101 URDF

### Phase 2: 仿真环境搭建
- [ ] 创建 SO101 Isaac Lab 环境
- [ ] 配置观测/动作空间
- [ ] 设计 Reward 函数
- [ ] 域随机化配置

### Phase 3: RL 训练
- [ ] 配置训练参数
- [ ] 训练监控
- [ ] 模型导出

### Phase 4: Sim2Real 迁移
- [ ] 真机参数校准
- [ ] 开环测试
- [ ] 闭环测试

### Phase 5: 优化与验证
- [ ] 成功率测试
- [ ] 性能优化
- [ ] 演示视频录制
- [ ] GitHub 整理

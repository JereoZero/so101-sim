# 踩坑记录 — 索引

本文档汇总 SO101 仿真项目中遇到的关键问题和解决方案，按章节划分。

---

## [01 — Isaac Lab 环境搭建](01-isaaclab-env.md)
- Isaac Sim 安装与配置
- Isaac Lab 依赖安装
- Conda 环境管理
- Display 显示问题

## [02 — SO101 URDF 导入与适配](02-urdf-import.md)
- URDF 路径与格式问题
- 关节名称映射
- 坐标系对齐

## [03 — 仿真中 SO101 运动控制](03-robot-control.md)
- 关节驱动参数配置 (stiffness/damping/max_force)
- 关节角度限制与裁剪
- PD 控制器调参
- 关节默认位置与初始化

## [04 — 仿真数据录制](04-data-collection.md)
- 摄像头配置 (分辨率和帧率)
- 遥操作数据录制流程
- 数据质量检查

## [05 — ACT → SmolVLA 数据集转换](05-dataset-convert.md)
- ACT 数据集结构
- LeRobot modify_tasks() 使用
- SmolVLA 格式转换脚本

## [06 — SmolVLA 模型训练](06-model-training.md)
- 训练参数配置
- 学习率选择
- 数据增强开关
- 训练中断与续训
- 基础模型选择

## [07 — SmolVLA 模型推理](07-inference.md)
- **Chunk Size 问题（关键）**：服务器只返回第一步动作导致推理卡顿
- TCP 通信架构
- receding horizon 推理策略
- 推理频率调优

## [08 — 附录](08-appendix.md)
- 常用命令速查
- 路径速查
- 参数速查
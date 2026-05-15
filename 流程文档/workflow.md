# 流程文档索引

完整项目流程记录，按阶段拆分：

1. [项目概述](01-project-overview.md) — 项目背景、技术栈、训练版本表
2. [环境搭建](02-env-setup.md) — Conda 环境、Isaac Lab 路径、LeRobot 框架、SO101 URDF、硬件
3. [仿真场景搭建](03-sim-scene.md) — 场景层级、物理材质、LeRobot 修改、摄像头、物体随机化
4. [遥操作与数据录制](04-teleop-data.md) — TCP 遥操作架构、运行命令、键盘快捷键、HDF5 录制
5. [数据集预处理](05-dataset-preprocess.md) — HDF5→LeRobot 转换、LeRobot→SmolVLA 转换、modify_tasks()
6. [模型训练](06-training.md) — 全部训练版本、v6 基线命令、训练结果、经验教训
7. [模型推理](07-inference.md) — TCP 推理架构、chunk 队列管理、receding horizon、Chunk Size 陷阱
8. [项目总结](08-summary.md) — 训练结果汇总、checkpoint 对比、关键经验
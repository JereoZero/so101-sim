# 踩坑文档索引

仿真项目全过程踩坑记录，按章节拆分：

1. [Isaac Lab 环境搭建](01-isaaclab-env.md) — DISPLAY、USD 缓存、HF_HUB_OFFLINE、conda 环境、资源路径、GPU 问题
2. [SO101 URDF 导入与适配](02-urdf-import.md) — URDF 路径、坐标系对齐、关节命名、self_collision
3. [仿真中 SO101 运动控制](03-robot-control.md) — stiffness=0、关节限位、夹爪扭矩、stuttering、单帧控制、摄像头朝向、物理材质调优、空气碰撞、穿透、LeRobot 源码修改
4. [仿真数据录制](04-data-collection.md) — 夹爪映射、摄像头分辨率、帧率、文件大小、TCP 粘包、随机化失败、校准数据
5. [数据集格式转换](05-dataset-convert.md) — modify_tasks、路径冲突、streaming、错用数据集、tasks.jsonl 格式
6. [SmolVLA 模型训练](06-model-training.md) — 高 LR、数据增强、错用 base model、续训 LR、optimizer config、HF_HUB_OFFLINE、pretrained_model 子目录、wandb
7. [SmolVLA 模型推理](07-inference.md) — Chunk Size=1、wrist_roll 锁定、HF 加载、频率选择、端口冲突、摄像头朝向、DATASET_DIR
8. [附录](08-appendix.md) — 命令、路径、参数、模型版本、conda 环境、硬件速查
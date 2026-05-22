# SO101 Sim 项目

**一句话概括**：在 Isaac Sim 仿真环境中，使用 LeRobot + SmolVLA 框架，完成 SO101 机械臂从遥操作数据录制到模型训练再到仿真推理的完整闭环。

本项目是 [so101-real](https://github.com/JereoZero/so101-real) 的姊妹项目，专注于**仿真端**（Isaac Lab / Isaac Sim）的工作。真机端相关内容在 so101-real 仓库。

## 目录结构

```
├── README.md                    ← 本文件
├── .gitignore
├── 踩坑文档/                    ← 仿真项目全过程踩坑记录（按章节拆分）
│   ├── pitfalls.md              ← 索引
│   ├── 01-isaaclab-env.md       ← 1. Isaac Lab 环境搭建
│   ├── 02-urdf-import.md        ← 2. SO101 URDF 导入与适配
│   ├── 03-robot-control.md      ← 3. 仿真中 SO101 运动控制
│   ├── 04-data-collection.md    ← 4. 仿真数据录制
│   ├── 05-dataset-convert.md    ← 5. 数据集格式转换
│   ├── 06-model-training.md     ← 6. SmolVLA 模型训练
│   ├── 07-inference.md          ← 7. SmolVLA 模型推理
│   └── 08-appendix.md           ← 附录（命令、路径、参数速查）
├── 流程文档/                    ← 完整项目流程记录（按阶段拆分）
│   ├── workflow.md              ← 索引
│   ├── 01-project-overview.md   ← 1. 项目概述
│   ├── 02-env-setup.md          ← 2. 环境搭建
│   ├── 03-sim-scene.md          ← 3. 仿真场景搭建
│   ├── 04-teleop-data.md        ← 4. 遥操作与数据录制
│   ├── 05-dataset-preprocess.md ← 5. 数据集预处理
│   ├── 06-training.md           ← 6. 模型训练
│   ├── 07-inference.md          ← 7. 模型推理
│   └── 08-summary.md            ← 8. 项目总结
└── j_so101_sim2real_touch/      ← 源码（模型/数据集不上传）
    └── src/                     ← 核心源码
```

## 项目概述

### 任务目标

在 Isaac Sim 仿真环境中，使用 SmolVLA 模型让 SO101 机械臂学会在随机位置抓取小方块并放入小盘子中。

### 工作流程

```
仿真场景搭建 → 遥操作录制数据 → 数据集转换 → 模型训练 → 仿真推理闭环
```

### 技术栈

| 层 | 技术 |
|---|---|
| 仿真 | Isaac Sim + Isaac Lab |
| 算法 | SmolVLA（Vision-Language-Action） |
| 框架 | LeRobot v0.5.0 |
| 机器人 | SO101 六轴机械臂（仿真 URDF） |
| 感知 | 双摄像头（腕部 + 第三视角，采集160×120 / 推理640×480 RGB） |
| GPU | NVIDIA RTX 5070 12GB |

### 项目亮点

- **全仿真闭环**：场景搭建 → 遥操作 → 数据录制 → 训练 → 推理全在仿真中完成
- **跨范式数据复用**：遥操作录制一次数据，可同时用于 ACT 和 SmolVLA 训练
- **多版本迭代**：v0 → v1 → v4 → v5 → v6 → v7，持续优化训练策略
- **推理优化**：30Hz receding horizon 推理 + chunk 队列管理
- **仿真特有坑**：关节驱动配置、摄像头参数、物理引擎调优

## 快速导航

- 遇到了问题 → [踩坑文档/](踩坑文档/pitfalls.md)
- 想了解项目流程 → [流程文档/workflow.md](流程文档/workflow.md)
- 想看源码 → [j_so101_sim2real_touch/src/](j_so101_sim2real_touch/src/)

## 参考项目

- [so101-real](https://github.com/JereoZero/so101-real) — 真机端姊妹项目
- LeRobot 教程：[子豪兄SO101教程](https://zihao-ai.feishu.cn/wiki/TS6swApHbinx01kHDi5cf5n5n8c)
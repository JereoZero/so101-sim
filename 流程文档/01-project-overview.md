# 01 — 项目概述

## 项目背景

SO101 Sim 项目致力于在 Isaac Sim 仿真环境中，使用 LeRobot + SmolVLA 框架，完成 SO101 单臂六轴机械臂从遥操作数据录制到模型训练再到仿真推理的完整闭环。

本项目是 [so101-real](https://github.com/JereoZero/so101-real) 真机项目的姊妹项目，专注于**仿真端**工作。

## 任务描述

**核心任务**：让 SO101 机械臂学会在随机位置抓取小方块（3.5cm 边长）并放入小盘子（8.5cm 直径）中。

| 物品 | 尺寸 | 说明 |
|---|---|---|
| 小方块 | 3.5cm 边长 | 橙色，泡沫垫材质 |
| 盘子 | 8.5cm 直径 | 小盘子，放置精度要求高 |

## 技术栈

| 层 | 技术 |
|---|---|
| 仿真 | Isaac Sim + Isaac Lab |
| 算法 | SmolVLA（Vision-Language-Action） |
| 框架 | LeRobot v0.5.0 |
| 深度学习 | PyTorch 2.x + CUDA |
| 机器人 | 幻尔 SO101 机械臂（仿真 URDF） |
| 感知 | 双摄像头（腕部 + 第三视角，640x480 RGB） |
| 硬件 | NVIDIA RTX 5070 12GB |
| 遥操作 | 真机主臂 → TCP → 仿真从臂 |

## 工作流程

```
仿真场景搭建 → 遥操作录制数据 → 数据集转换 → 模型训练 → 仿真推理闭环
```

具体步骤：

1. **仿真场景搭建**：桌子、灯光、SO101 URDF、方块、盘子、双摄像头
2. **遥操作数据录制**：真机主臂通过 TCP 控制仿真从臂，录制 100 个 episodes
3. **数据集预处理**：ACT 格式 → SmolVLA 格式转换，添加语言任务描述
4. **模型训练**：多个版本迭代（v0 → v1 → v4 → v5 → v6 → v7），持续优化参数
5. **仿真推理闭环**：TCP 客户端-服务器架构，30Hz receding horizon 推理

## 项目目录

```
ws/
├── j_so101_sim2real_touch/
│   ├── src/           ← 核心源码（45+ 文件）
│   ├── configs/       ← 配置文件
│   ├── scripts/       ← 脚本
│   └── tests/         ← 测试代码
├── 流程文档/          ← 项目完整流程
└── 踩坑文档/          ← 踩坑记录
```

## 训练版本迭代

| 版本 | 基础模型 | 步数 | 学习率 | 数据增强 | 说明 |
|---|---|---|---|---|---|
| v0  | smolvla_v3_infer_18k | 40000 | 1e-4 | ✅ | 初始版本，不稳定 |
| v1  | smolvla_sim_v0/008000 | 10000 | 1e-5 | ❌ | **路线错误**，用了错误基础模型 |
| v4  | smolvla_v3_infer_18k | 20000 | 1e-5 | ❌ | 修正路线，关闭增强 |
| v5  | smolvla_sim_v4/020000 | 4000 | 1e-5 | ❌ | v4 继续微调 |
| v6  | smolvla_base_migrated | 20000 | 1e-5 | ❌ | 换迁移基础模型 |
| v7  | smolvla_sim_v6/020000 | 8000 | 2.5e-6 | ❌ | v6 继续微调，超低 LR |

## 参考项目

- [so101-real](https://github.com/JereoZero/so101-real) — 真机端姊妹项目
- [子豪兄SO101教程](https://zihao-ai.feishu.cn/wiki/TS6swApHbinx01kHDi5cf5n5n8c)
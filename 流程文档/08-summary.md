# 08 — 项目总结

## 训练结果汇总

| 版本 | 基础模型 | 步数 | Loss | 评估 |
|---|---|---|---|---|
| v0 | smolvla_v3_infer_18k | 18000 | — | 不稳定 |
| v1 | smolvla_sim_v0/008000 | 2000 | — | 路线错误 |
| v4 | smolvla_v3_infer_18k | 20000 | 0.033 | 较稳定 |
| v5 | smolvla_sim_v4/020000 | 4000 | — | 小幅提升 |
| **v6** | **smolvla_base_migrated** | **20000** | **0.038** | **最佳** ★ |
| v7 | smolvla_sim_v6/020000 | 8000 | — | 待评估 |

> **说明**：v4 训练 Loss (0.033) 最低，但 v6 的迁移基础模型泛化能力更好，推理实测表现最佳。

## 最优 Checkpoint 对比

| Checkpoint | Loss | 备注 |
|---|---|---|
| v6/006000 | — | 早期checkpoint，可能欠拟合 |
| v6/012000 | — | 中期checkpoint |
| v6/016000 | — | 中后期checkpoint |
| v6/020000 | 0.038 | 最终版本，推荐基线 |
| v7/002000 | — | v7 早期 |
| v7/008000 | — | v7 最终 |

## 技术路线总结

```
1. Isaac Sim 场景搭建     ← 物理材质优化，关节驱动配置
2. 遥操作数据录制          ← TCP 真机→仿真，100 episodes
3. HDF5→LeRobot→SmolVLA 转换 ← modify_tasks() 添加语言描述
4. 多版本迭代训练          ← LR 从 1e-4 到 1e-5，关闭增强
5. TCP 推理闭环            ← Chunk 队列 + Receding Horizon
6. 持续优化                ← 换基础模型，超低 LR 续训
```

## 关键经验教训

### 1. 学习率选择
- 1e-4 对仿真数据偏高，导致训练震荡
- 1e-5 是合适的折中
- 续训使用衰减后的超低 LR（2.5e-6）

### 2. 数据增强
- **仿真数据建议关闭增强**
- 增强引入的色偏和随机裁剪干扰了仿真中已有的固定视觉特征

### 3. 基础模型选择
- `smolvla_base_migrated`（迁移版）效果优于 `smolvla_v3_infer_18k`
- 原因可能是迁移版经过了更好的基础训练

### 4. Chunk Size 对齐
- 训练时 `chunk_size=50`，推理时务必使用完整 chunk
- 只取第一步动作是重大错误（导致卡顿）

### 5. 物理参数
- 仿真中的摩擦系数、碰撞参数对抓取成功率影响很大
- hardness + friction + solver iterations 三管齐下

### 6. 推理架构
- TCP 双终端分离模型加载和仿真渲染
- Receding Horizon 保证动作连续性
- 30Hz 推理 + 30Hz 执行（可通过 INFERENCE_INTERVAL 调节）

## 下一步计划

1. **继续优化 v7**：评估 8000 步的效果
2. **尝试更大数据量**：增加 episodes 数量和多样性
3. **多任务扩展**：添加其他颜色的方块，不同形状的干扰物
4. **真机迁移**：将仿真训练模型应用于真机 so101-real

## 参考

- [so101-real](https://github.com/JereoZero/so101-real) — 真机端姊妹项目
- [SmolVLA](https://huggingface.co/huggingface/SmolVLA) — 使用的 VLA 模型
- [子豪兄SO101教程](https://zihao-ai.feishu.cn/wiki/TS6swApHbinx01kHDi5cf5n5n8c)
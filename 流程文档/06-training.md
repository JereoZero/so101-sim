# 06 — 模型训练

## 训练概览

SmolVLA 采用**部分微调**策略：
- `train_expert_only=true`：只训练 action expert 层（约 100M 参数 / 总共 450M）
- `freeze_vision_encoder=true`：冻结视觉编码器
- `use_amp=true`：bfloat16 混合精度训练

## 训练版本迭代

| 版本 | 基础模型 | 步数 | LR | 增强 | Loss | 说明 |
|---|---|---|---|---|---|---|
| v0 | smolvla_v3_infer_18k | 18000 | 1e-4 | ✅ | — | 初始版，LR 高+增强导致不稳定 |
| v1 | smolvla_sim_v0/008000 | 2000 | 1e-5 | ❌ | — | **路线错误**，用错基础模型 |
| v4 | smolvla_v3_infer_18k | 20000 | 1e-5 | ❌ | 0.033 | 修正路线 |
| v5 | smolvla_sim_v4/020000 | 4000 | 1e-5 | ❌ | — | v4 继续微调 |
| v6 | smolvla_base_migrated | 20000 | 1e-5 | ❌ | 0.038 | 换迁移基础模型，整体最稳定 |
| v7 | smolvla_sim_v6/020000 | 8000 | 2.5e-6 | ❌ | — | v6 继续微调，超低 LR |

## v6 版本（推荐基线）

v6 是目前表现最好的版本，以下是训练详情。

> **为什么 v6 Loss (0.038) 高于 v4 (0.033) 但效果更好？**  
> v6 使用了 `smolvla_base_migrated`（迁移版基础模型），该模型经过更大规模预训练，泛化能力更强。虽然训练 Loss 略高，但推理时动作更准确、场景适应更好。v4 虽然拟合 Loss 更低，但推理实测中泛化不足。

### 训练命令

```bash
conda activate lerobot

HF_HUB_OFFLINE=1 lerobot-train \
    --policy.path=/home/jer/ws_issac/ws/j_so101_sim2real_touch/models/smolvla_base_migrated \
    --policy.load_vlm_weights=false \
    --policy.use_amp=true \
    --policy.n_obs_steps=4 \
    --policy.optimizer_lr=1e-5 \
    --policy.optimizer_betas=[0.9,0.95] \
    --policy.optimizer_eps=1e-8 \
    --policy.optimizer_weight_decay=1e-10 \
    --policy.optimizer_grad_clip_norm=10.0 \
    --policy.device=cuda \
    --dataset.repo_id=local/sim_smolvla \
    --dataset.root=/home/jer/ws_issac/ws/j_so101_sim2real_touch/datasets/sim_lerobot_smolvla \
    --dataset.streaming=false \
    --dataset.image_transforms.enable=false \
    --output_dir=/home/jer/ws_issac/ws/j_so101_sim2real_touch/models/smolvla_sim_v6 \
    --job_name=so101_smolvla_sim_v6 \
    --wandb.enable=false \
    --policy.push_to_hub=false \
    --steps=20000 \
    --batch_size=36 \
    --save_freq=2000 \
    --log_freq=100 \
    --num_workers=4 \
    --seed=1000
```

### v6 训练结果

```
step:20K smpl:720K ep:2K epch:20.05 loss:0.038 grdn:0.439 lr:2.5e-06 updt_s:1.045 data_s:0.038
```

- **最终 Loss**：0.038
- **梯度范数**：0.439
- **总耗时**：约 6 小时（20000 步 × 1.07s/步）

## 训练参数对比

| 参数 | v0 | v4+ | 说明 |
|---|---|---|---|
| `steps` | 18000 | 20000 | v0 实际只到 18000 |
| `optimizer_lr` | 1e-4 | 1e-5 | 降低 10 倍，避免震荡 |
| `image_transforms` | true | **false** | **关闭数据增强** |
| `batch_size` | 36 | 36 | 不变 |
| `save_freq` | 2000 | 2000 | 每 2000 步保存 |
| `use_amp` | true | true | 混合精度 |

## 训练策略演变

### v0 阶段：高 LR + 数据增强
- 学习率 1e-4，开启数据增强
- 结果：训练不稳定，Loss 震荡
- 结论：仿真数据增强引入过多噪声

### v1 阶段：低 LR + 关闭增强
- 学习率降至 1e-5，关闭增强
- **路线错误**：从 v0/008000 开始（而非 smolvla_v3_infer_18k）
- 结论：需纠正基础模型

### v4-v7 阶段：持续优化
- v4：修正基础模型为 smolvla_v3_infer_18k
- v5：v4 继续微调 4000 步
- v6：换用 smolvla_base_migrated（迁移版基础模型），效果最佳
- v7：v6 继续微调 8000 步，学习率降至 2.5e-6

## Checkpoint 管理

```
models/
├── smolvla_sim_v0/    ← v0（18000步）
├── smolvla_sim_v1/    ← v1（2000步）
├── smolvla_sim_v4/    ← v4（20000步）
├── smolvla_sim_v5/    ← v5（4000步）
├── smolvla_sim_v6/    ← v6（20000步）★ 推荐
└── smolvla_sim_v7/    ← v7（8000步）
```

每个版本下的 `checkpoints/` 目录包含检查点（`save_freq=2000`，v5 例外使用 1000）：

## 关键教训

1. **学习率很重要**：1e-4 太高导致震荡，1e-5 更稳定
2. **数据增强要谨慎**：仿真数据增强引入噪声，关闭后训练更稳定
3. **基础模型选择**：smolvla_base_migrated（迁移版）优于 smolvla_v3_infer_18k
4. **续训学习率**：v7 从 v6 续训时使用 v6 最终 LR（2.5e-6），不重设
5. **chunk_size=50**：训练和推理 chunk 大小务必一致
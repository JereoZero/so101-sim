# 06 — SmolVLA 模型训练

## 坑 1：学习率太高导致训练震荡（核心）

### 现象
训练 Loss 不收敛，忽高忽低，checkpoint 推理效果不稳定。

### 原因
v0 使用默认学习率 1e-4，对于仿真数据（100 episodes）偏高。

### 解决
将学习率降低 10 倍：
```bash
--policy.optimizer_lr=1e-5  # 从 1e-4 降到 1e-5
```

这是整个项目最重要的超参数调整。

---

## 坑 2：数据增强干扰仿真数据

### 现象
开启数据增强后，推理时模型对场景不敏感，动作偏离很大。

### 原因
仿真场景的光照和背景相对固定，颜色抖动和随机裁剪反而引入了不必要的干扰。

### 解决
v4 起关闭数据增强：
```bash
--dataset.image_transforms.enable=false
```

---

## 坑 3：基础模型选错（v1 路线错误）

### 现象
v1 训练用了 `smolvla_sim_v0/checkpoints/008000` 作为基础模型，该模型本身就有问题（高 LR + 数据增强导致的震荡）。

### 解决
v4 起修正为从 `smolvla_v3_infer_18k`（官方预训练）开始。v6 进一步换用 `smolvla_base_migrated`（迁移版基础模型），效果更好。

---

## 坑 4：续训时的学习率问题

### 现象
从 checkpoint 续训时，adams 重设为 1e-5 再训练不稳定。

### 解决
v7 续训 v6 时，使用 v6 训练最终的衰减学习率（2.5e-6），不重设：
```bash
--policy.optimizer_lr=2.5e-06  # 从 v6 最终 lr 继续
```

---

## 坑 5：resume=true 需要 optimizer 配置

### 现象
```bash
ValueError: Optimizer config is required but not provided
```

### 原因
使用 `--resume=true` 时需要从 checkpoint 恢复 optimizer 状态，但 checkpoint 中缺失 optimizer 配置。

### 解决
不用 `--resume=true`，改用 `--policy.path` 加载权重：
```bash
--policy.path=/path/to/checkpoint/pretrained_model
--policy.load_vlm_weights=false
```

---

## 坑 6：HF_HUB_OFFLINE 未设置导致训练启动失败

### 现象
训练命令卡在加载模型阶段，报 HuggingFace 连接错误。

### 解决
```bash
HF_HUB_OFFLINE=1 lerobot-train ...
```

---

## 坑 7：pretrained_model 子目录问题

### 现象
指定 `--policy.path=checkpoints/020000` 失败。

### 原因
checkpoint 目录下真正能加载的是 `pretrained_model` 子目录。

### 解决
```bash
--policy.path=/path/to/checkpoints/020000/pretrained_model
```

或者在推理服务器的代码中自动检测：
```python
pretrained_dir = Path(checkpoint_path) / "pretrained_model" if (Path(checkpoint_path) / "pretrained_model").exists() else Path(checkpoint_path)
```

---

## 坑 8：wandb 未禁用

### 现象
训练时尝试连接 wandb 服务器失败。

### 解决
```bash
--wandb.enable=false
--policy.push_to_hub=false
```
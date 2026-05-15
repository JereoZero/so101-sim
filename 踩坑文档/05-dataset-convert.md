# 05 — ACT → SmolVLA 数据集转换

## 坑 1：modify_tasks() 不生效

### 现象
执行转换脚本后，SmolVLA 数据集中没有 `tasks.jsonl`。

### 原因
`modify_tasks()` 返回的是修改后的数据集对象，需要检查是否成功写入了新的任务描述。

### 解决
验证脚本执行输出：
```python
smolvla_ds = LeRobotDataset(repo_id="local/sim_smolvla", root=SMOLVLA_PATH)
print(f"Tasks: {smolvla_ds.meta.tasks}")
# 输出应包含 "put small orange block in plate"
```

---

## 坑 2：数据集路径重复

### 现象
训练时提示 "Dataset already exists" 或加载了旧数据集。

### 原因
多次执行转换脚本时，新数据集目录与旧目录冲突。

### 解决
转换前清理：
```python
if smolvla_path.exists():
    shutil.rmtree(smolvla_path)
```

---

## 坑 3：数据集 streaming 参数

### 现象
训练时数据加载非常慢或报错。

### 原因
`streaming=true` 时从远程加载，本地数据应设为 `false`。

### 解决
```bash
--dataset.streaming=false
```

---

## 坑 4：数据转换的源数据集选错了

### 现象
在 ACT 数据上训练 SmolVLA，模型输出异常。

### 说明
必须使用转换后的 SmolVLA 数据集（含 tasks.jsonl），不能用原始 ACT 数据集。SmolVLA 需要语言任务描述才能正常工作。

---

## 坑 5：tasks.jsonl 格式不对

### 现象
训练的 SmolVLA 读不到任务描述。

### 原因
`tasks.jsonl` 格式被手动修改后结构错误。

### 正确格式
```json
{"task": "put small orange block in plate", "task_index": 0}
```

每行一个 JSON 对象，使用 `modify_tasks()` API 自动生成，不要手动编辑。
# 01 — Isaac Lab 环境搭建

## 坑 1：DISPLAY 未设置导致键盘快捷键失效

### 现象
启动 Isaac Sim 后，按键（M/R/ESC/Z/Y/C）完全无响应。

### 原因
Isaac Sim 需要一个 X11 display 才能接收键盘事件。如果不设置 `DISPLAY` 环境变量，GUI 窗口不会正常渲染，键盘回调不触发。

### 解决
```bash
export DISPLAY=:0
```

每次启动仿真前必须设置。建议写入 `~/.bashrc`。

---

## 坑 2：Isaac Sim 启动后 GUI 无响应/闪退

### 现象
`./isaaclab.sh` 执行后窗口一闪而过或卡在加载界面。

### 可能原因
1. **残留进程**：之前的 Isaac Sim 进程未完全退出
2. **GPU 显存不足**：残留进程占用显存
3. **ASSETS_PATH 未设置**：找不到 Isaac Sim 资源文件

### 解决
```bash
# 清理残留进程
ps aux | grep -i isaac | grep -v grep
kill -9 <PID>

# 确认资源路径
export ISAACSIM_ASSETS_PATH=~/isaacsim/Assets/Assets/Isaac/5.1

# 确认 GPU 空闲
nvidia-smi
```

---

## 坑 3：Conda 环境混乱

### 现象
在 `lerobot_issac` 环境中 `import lerobot` 报错，或在 `isaaclab` 环境中执行 `lerobot-train` 找不到命令。

### 原因
项目需要多个 Conda 环境，混用会导致依赖冲突。

### 解决
严格遵守环境分工：

| 环境 | 用途 | 关键操作 |
|---|---|---|
| `isaaclab` | Isaac Sim + Isaac Lab | — |
| `lerobot_issac` | 仿真运行（含 LeRobot） | `./isaaclab.sh` 启动仿真 |
| `lerobot` | SmolVLA 训练/推理 | `lerobot-train`、模型服务器 |

仿真（遥操作、推理客户端）从 `lerobot_issac` 环境启动，训练和推理服务器从 `lerobot` 环境启动。

---

## 坑 4：Isaac Sim 资源路径错误

### 现象
```
Error: Could not find Isaac Sim assets
```

### 原因
`ISAACSIM_ASSETS_PATH` 未正确设置或路径不对。

### 解决
```bash
# 确认资源目录存在
ls ~/isaacsim/Assets/Assets/Isaac/5.1/

# 正确设置
export ISAACSIM_ASSETS_PATH=~/isaacsim/Assets/Assets/Isaac/5.1
export IsaacSim_ROOT=~/isaacsim/Assets/Assets/Isaac/5.1
```

---

## 坑 5：USD 缓存导致修改不生效

### 现象
修改了 URDF 或机器人配置，重启仿真后修改不生效。

### 原因
Isaac Lab 会缓存 USD 文件到 `/tmp/IsaacLab/`。

### 解决
```bash
rm -rf /tmp/IsaacLab/
rm -rf ~/.local/share/isaaclab/usd_cache/isaac_so_arm101/
```

每次修改 URDF 或机器人配置后都需清理。后面在 `so_arm101.py` 中解决得比较好了。

---

## 坑 6：HF_HUB_OFFLINE 未设置

### 现象
训练/推理时尝试连接 HuggingFace Hub 超时或报错。

### 解决
```bash
export HF_HUB_OFFLINE=1
```

在所有 lerobot 相关命令前加上此环境变量。训练命令示例：
```bash
HF_HUB_OFFLINE=1 lerobot-train ...
```

推理服务器中也需要：
```python
os.environ["HF_HUB_OFFLINE"] = "1"
```
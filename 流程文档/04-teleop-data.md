# 04 — 遥操作与数据录制

## 遥操作架构

真机主臂通过 TCP 协议控制仿真从臂：

```
真机主臂 (SO101 Leader)
    ↓ USB 串口
LeRobot teleoperate
    ↓ 读取关节角度
so101_real_teleop_client.py
    ↓ TCP :8765
so101_sim_camera_server.py (Isaac Sim 内)
    ↓ clip_joint_angles → robot.set_joint_position_target()
```

## 运行命令

### 终端1 — 仿真数据采集环境

```bash
export DISPLAY=:0
cd /home/jer/ws_issac/thirdparty/IsaacLab
conda activate lerobot_issac
export ISAACSIM_ASSETS_PATH=~/isaacsim/Assets/Assets/Isaac/5.1
./isaaclab.sh -p /home/jer/ws_issac/ws/j_so101_sim2real_touch/src/so101_sim_camera_server.py --enable_cameras
```

### 终端2 — 真机遥操作客户端（lerobot_issac 环境）

```bash
export PYTHONPATH=/home/jer/ws_issac/thirdparty/lerobot-0.5.0/src:$PYTHONPATH
cd /home/jer/ws_issac/thirdparty/IsaacLab
conda activate lerobot_issac
python /home/jer/ws_issac/ws/j_so101_sim2real_touch/src/so101_real_teleop_client.py
```

## 键盘快捷键（Isaac Sim 窗口）

| 按键 | 功能 |
|---|---|
| **Z** | 开始/结束录制 |
| **Y** | 保存当前 episode |
| **C** | 放弃当前 episode + 刷新场景 |

## 录制流程

1. 按 **Z** → 开始录制
2. 操作真机主臂，仿真从臂跟随运动
3. 完成任务（抓取方块 → 放入盘子）
4. 按 **Z** → 结束录制
5. 按 **Y** → 确认保存（episode 编号 +1）
6. 重复以上步骤

## 数据格式

数据以 HDF5 格式保存，所有 episode 存储在同一个文件中：

```
/home/jer/ws_issac/ws/j_so101_sim2real_touch/datasets/hdf5_sim_block_act_test/
└── dataset.hdf5
    ├── data/
    │   ├── demo_0/   (actions, states, initial_state, obs/camera1, obs/camera2)
    │   ├── demo_1/
    │   └── ...
```

每帧包含：
- **腕部摄像头图像**（160×120 RGB）
- **第三视角摄像头图像**（160×120 RGB）
- **关节动作**（6 个关节目标角度，弧度）
- **关节状态**（6 个关节当前位置，弧度）

## 数据集规格

最终录制了 **100 个 episodes**，用于 ACT 和 SmolVLA 模型训练：

| 指标 | 数值 |
|---|---|
| 总 episodes | 100 |
| 总帧数 | ~35913 |
| 图像分辨率 | 160×120（采集）/ 640×480（推理） |
| 帧率 | 30fps |
| 任务 | 抓取方块放入盘子 |

## 关节映射

真机角度范围映射到仿真 URDF 范围：

| 转换方向 | 公式 |
|---|---|
| 真机 → 仿真 | 根据校准数据做线性映射 |
| 夹爪 | 真机 (-0.94~0.94) → 仿真 (-0.17~1.75) |

关节角度通过 `robot_config.py` 中的 `clip_joint_angles()` 进行裁剪，确保不超出限位。

## 关键问题与解决

### 关节驱动失效
- **现象**：机械臂不响应目标位置
- **原因**：Isaac Sim 中关节 stiffness 默认为 0
- **解决**：在 `so_arm101.py` 中强制设置 stiffness=1000, damping=100

### 夹爪扭矩不足
- **现象**：夹爪无法完全张开
- **原因**：默认 Max_Torque_Limit 为 500（50%）
- **解决**：修改为 1000（100%）
"""
SO101 真机遥操作客户端 - LeRobot 环境

运行命令：
conda activate lerobot_issac
export PYTHONPATH=/home/jer/ws_issac/thirdparty/lerobot-0.5.0/src:$PYTHONPATH
python /home/jer/ws_issac/ws/j_so101_sim2real_touch/src/so101_real_teleop_client.py

通信协议：
- TCP 客户端，连接到 127.0.0.1:8765
- 发送 JSON 格式的关节命令：{"joint_pos": [6个角度值]}
- 第5关节(wrist_roll)锁定在 -67.74度
"""

import sys
sys.path.insert(0, "/home/jer/ws_issac/thirdparty/lerobot-0.5.0/src")

import socket
import json
import math
import time

from lerobot.teleoperators.so_leader import SO101Leader, SOLeaderTeleopConfig


SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8765


# 真机夹爪校准范围（角度，use_degrees=True 时的值）
# 1466 编码器 → 约 -49.6°
# 2691 编码器 → 约 49.6°
GRIPPER_DEG_MIN = -49.6
GRIPPER_DEG_MAX = 49.6


def gripper_deg_to_percentage(deg):
    """将真机夹爪角度转为百分比 (0=闭合, 1=张开)"""
    pct = (deg - GRIPPER_DEG_MIN) / (GRIPPER_DEG_MAX - GRIPPER_DEG_MIN)
    return max(0.0, min(1.0, pct))


def main():
    print("=" * 80)
    print("🚀 SO101 真机遥操作客户端")
    print("=" * 80)
    print(f"夹爪角度范围: {GRIPPER_DEG_MIN}° ~ {GRIPPER_DEG_MAX}°")

    print("\n[1] 连接通信服务器...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5.0)

    try:
        sock.connect((SERVER_HOST, SERVER_PORT))
        sock.settimeout(1.0)
        print("✅ 通信服务器连接成功!")
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        print("   请先启动仿真服务器!")
        return

    print("\n[2] 初始化真实主臂...")
    try:
        leader_config = SOLeaderTeleopConfig(
            port="/dev/ttySO101_LEADER",
            id="j_leader",
            use_degrees=True,
        )
        leader = SO101Leader(leader_config)
        leader.connect(calibrate=False)

        if not leader.is_connected:
            print("❌ 主臂连接失败!")
            sock.close()
            return

        print("✅ 真实主臂连接成功!")
    except Exception as e:
        print(f"❌ 主臂初始化失败: {e}")
        sock.close()
        return

    print("\n[3] 开始遥操作...")
    print("按 Ctrl+C 停止")

    try:
        while True:
            action = leader.get_action()

            joint_map = [
                "shoulder_pan", "shoulder_lift", "elbow_flex",
                "wrist_flex", "wrist_roll", "gripper"
            ]

            joint_pos = []
            for joint_name in joint_map:
                key = f"{joint_name}.pos"
                if key in action:
                    val_deg = action[key]
                    val_rad = math.radians(val_deg)
                    joint_pos.append(val_rad)
                else:
                    joint_pos.append(0.0)

            fixed_joints = {"wrist_roll": math.radians(-90.0)}
            for joint_name, fixed_angle in fixed_joints.items():
                if joint_name in joint_map:
                    idx = joint_map.index(joint_name)
                    joint_pos[idx] = fixed_angle

            cmd = {"joint_pos": joint_pos}
            sock.sendall((json.dumps(cmd) + "\n").encode('utf-8'))

            time.sleep(0.016)

    except KeyboardInterrupt:
        print("\n用户中断")
    except Exception as e:
        print(f"\n错误: {e}")
    finally:
        print("\n[4] 断开连接...")
        leader.disconnect()
        sock.close()
        print("✅ 已断开")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()

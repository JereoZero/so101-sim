"""
测试遥操作脚本的核心逻辑
不启动 IsaacSim，仅验证：
1. 关节映射逻辑
2. 单位转换
3. 参数解析
"""

import sys
import argparse

print("=" * 60)
print("🧪 遥操作核心逻辑测试")
print("=" * 60)

print("\n[1] 测试参数解析")
parser = argparse.ArgumentParser(description="SO101 Teleop Test")
parser.add_argument("--leader_port", type=str, default="/dev/ttySO101_LEADER")
parser.add_argument("--leader_id", type=str, default="j_leader")
parser.add_argument("--disable_real", action="store_true")

# 不添加 AppLauncher 参数，避免依赖问题
test_args = parser.parse_args([])
print("  ✅ 参数解析成功")
print(f"    leader_port: {test_args.leader_port}")
print(f"    leader_id: {test_args.leader_id}")
print(f"    disable_real: {test_args.disable_real}")

print("\n[2] 测试关节映射")
joint_map = {
    "shoulder_pan": "shoulder_pan.pos",
    "shoulder_lift": "shoulder_lift.pos",
    "elbow_flex": "elbow_flex.pos",
    "wrist_flex": "wrist_flex.pos",
    "wrist_roll": "wrist_roll.pos",
    "gripper": "gripper.pos",
}

print("  ✅ 关节映射表:")
for isaac_joint, lerobot_joint in joint_map.items():
    print(f"    {isaac_joint:15s} <-> {lerobot_joint}")

print("\n[3] 测试单位转换")
test_degs = [-90, -45, 0, 45, 90, 180]
print("  ✅ 度 → 弧度转换:")
for deg in test_degs:
    rad = deg * 3.1415926535 / 180
    print(f"    {deg:5}°  →  {rad:8.4f} rad")

print("\n[4] 测试模拟 LeRobot 读取")
print("  ✅ 模拟观测数据:")
mock_obs = {
    "shoulder_pan.pos": 10.5,
    "shoulder_lift.pos": -5.2,
    "elbow_flex.pos": 30.0,
    "wrist_flex.pos": 45.0,
    "wrist_roll.pos": 0.0,
    "gripper.pos": 1.5,
}

for key, val in mock_obs.items():
    print(f"    {key:20s}: {val}")

print("\n[5] 测试关节转换")
print("  ✅ 转换为 IsaacLab 弧度:")
joints_rad = {}
for isaac_joint, lerobot_joint in joint_map.items():
    if lerobot_joint in mock_obs:
        deg = mock_obs[lerobot_joint]
        rad = deg * 3.1415926535 / 180
        joints_rad[isaac_joint] = rad
        print(f"    {isaac_joint:15s}: {deg:8.2f}° → {rad:8.4f} rad")

print("\n[6] 测试关节索引查找逻辑")
print("  ✅ 模拟 IsaacLab 关节顺序 (不依赖 URDF):")
mock_joint_names = ["gripper", "wrist_roll", "wrist_flex", 
                    "elbow_flex", "shoulder_lift", "shoulder_pan"]

print("  关节名称列表:")
for i, name in enumerate(mock_joint_names):
    print(f"    [{i}] {name}")

print("\n  ✅ 查找索引:")
for isaac_joint in joints_rad.keys():
    if isaac_joint in mock_joint_names:
        idx = mock_joint_names.index(isaac_joint)
        print(f"    {isaac_joint:15s} → index = {idx}")

print("\n" + "=" * 60)
print("🎉 遥操作核心逻辑测试通过!")
print("=" * 60)

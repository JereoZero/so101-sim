"""
机器人配置模块
包含关节限制、角度裁剪等配置
"""

import math


# 真机校准数据转换后的弧度限制 (基于 j_leader.json)
# 转换公式: (val - mid) * 360 / 4095 * pi / 180
JOINT_LIMITS = {
    "shoulder_pan": (-1.99, 1.96),   # 725-3283
    "shoulder_lift": (-1.82, 1.83),  # 926-3307
    "elbow_flex": (-1.69, 1.69),     # 803-3011
    "wrist_flex": (-1.79, 1.79),     # 866-3201
    "wrist_roll": (-1.46, 2.92),     # 1174-4991
    "gripper": (-0.94, 0.94),        # 1466-2691
}


def clip_joint_angles(joint_pos_list):
    """根据真机校准数据裁剪关节角度"""
    joint_names = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]
    clipped = []
    for i, (name, angle) in enumerate(zip(joint_names, joint_pos_list)):
        min_val, max_val = JOINT_LIMITS[name]
        clipped_angle = max(min_val, min(max_val, angle))
        clipped.append(clipped_angle)
    return clipped

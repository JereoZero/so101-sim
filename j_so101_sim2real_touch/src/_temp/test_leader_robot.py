"""
测试真实 SO101 主臂读取
不启动 IsaacSim，仅测试真实手臂连接和关节读取
"""

import sys
import time

sys.path.insert(0, "/home/jer/ws_issac/lerobot_so101/workspace/projects/lerobot/src")


def test_leader_robot():
    """测试真实主臂"""
    print("=" * 60)
    print("🧪 测试真实 SO101 主臂")
    print("=" * 60)

    try:
        print("\n[1] 导入 LeRobot 模块...")
        from lerobot.robots.so_follower import SO101Follower
        from lerobot.robots.so_follower import SO101FollowerConfig
        print("✅ LeRobot 模块导入成功!")

        print("\n[2] 配置主臂...")
        config = SO101FollowerConfig(
            port="/dev/ttySO101_LEADER",
            id="j_leader",
            cameras={},
        )
        print("✅ 配置创建成功!")

        print("\n[3] 连接主臂...")
        robot = SO101Follower(config)
        robot.connect(calibrate=False)
        print("✅ 主臂连接成功!")

        print("\n[4] 测试关节读取 (10次)...")
        joint_map = {
            "shoulder_pan": "shoulder_pan.pos",
            "shoulder_lift": "shoulder_lift.pos",
            "elbow_flex": "elbow_flex.pos",
            "wrist_flex": "wrist_flex.pos",
            "wrist_roll": "wrist_roll.pos",
            "gripper": "gripper.pos",
        }

        for i in range(10):
            obs = robot.get_observation()
            print(f"\n  --- 第 {i+1} 次读取 ---")
            
            joints_deg = {}
            for isaac_joint, lerobot_joint in joint_map.items():
                if lerobot_joint in obs:
                    deg = obs[lerobot_joint]
                    rad = deg * 3.14159 / 180.0
                    joints_deg[isaac_joint] = (deg, rad)
                    print(f"    {isaac_joint:15s}: {deg:8.2f}°  ({rad:8.4f} rad)")
            
            time.sleep(0.5)

        print("\n[5] 断开连接...")
        robot.disconnect()
        print("✅ 主臂已断开!")

        print("\n" + "=" * 60)
        print("🎉 测试成功!")
        print("=" * 60)

    except Exception as e:
        print(f"\n[ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        print("\n" + "=" * 60)
        print("❌ 测试失败!")
        print("=" * 60)
        return False

    return True


def check_paths():
    """检查所有必要路径"""
    print("=" * 60)
    print("📁 路径检查")
    print("=" * 60)

    paths = {
        "LeRobot 源码": "/home/jer/ws_issac/lerobot_so101/workspace/projects/lerobot/src",
        "SO101 URDF": "/home/jer/ws_issac/thirdparty/SO-ARM100/Simulation/SO101/so101_new_calib.urdf",
        "IsaacLab 源码": "/home/jer/ws_issac/thirdparty/IsaacLab/source",
    }

    import os
    all_ok = True
    for name, path in paths.items():
        exists = os.path.exists(path)
        status = "✅" if exists else "❌"
        print(f"  {status} {name:20s}: {path}")
        if not exists:
            all_ok = False

    print()
    if all_ok:
        print("✅ 所有路径检查通过!")
    else:
        print("❌ 部分路径不存在!")

    print("=" * 60)
    return all_ok


if __name__ == "__main__":
    print()
    print("选择测试:")
    print("  1. 检查路径")
    print("  2. 测试真实主臂")
    print("  3. 全部测试")
    print()

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", type=int, default=3, choices=[1, 2, 3],
                        help="1=路径检查, 2=主臂测试, 3=全部")
    args = parser.parse_args()

    success = True

    if args.test in [1, 3]:
        success &= check_paths()

    if args.test in [2, 3]:
        print()
        success &= test_leader_robot()

    sys.exit(0 if success else 1)

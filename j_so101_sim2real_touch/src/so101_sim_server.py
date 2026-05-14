"""
SO101 仿真 + 通信服务器（无摄像头）- IsaacLab 环境

运行命令：
终端1:
cd /home/jer/ws_issac/thirdparty/IsaacLab
conda activate isaaclab
export ISAACSIM_ASSETS_PATH=~/isaacsim/Assets/Assets/Isaac/5.1
./isaaclab.sh -p /home/jer/ws_issac/ws/j_so101_sim2real_touch/src/so101_sim_server.py

终端2:
conda activate lerobot_issac
python /home/jer/ws_issac/ws/j_so101_sim2real_touch/src/so101_real_teleop_client.py

通信协议：
- TCP 服务器，监听端口 8765
- 接收 JSON 格式的关节命令：{"joint_pos": [6个角度值]}
"""

import sys
import argparse
import json
import socket
import threading

sys.path.insert(0, "/home/jer/ws_issac/thirdparty/isaac_so_arm101/src")
sys.path.insert(0, "/home/jer/ws_issac/ws/j_so101_sim2real_touch/src")

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser()
AppLauncher.add_app_launcher_args(parser)
parser.add_argument("--port", type=int, default=8765, help="通信端口")
args = parser.parse_args()

app_launcher = AppLauncher(args)
sim_app = app_launcher.app

import torch
from isaaclab.sim import SimulationContext

from scene_config import design_scene
from physics_config import configure_gripper_physics
from robot_config import clip_joint_angles


joint_pos_target = None


def handle_client(client_socket, client_addr):
    """处理客户端连接"""
    global joint_pos_target
    print(f"[TCP] 客户端连接: {client_addr}")

    try:
        while True:
            data = client_socket.recv(1024)
            if not data:
                break

            try:
                msg = json.loads(data.decode('utf-8'))
                if "joint_pos" in msg:
                    joint_pos_target = msg["joint_pos"]
                    print(f"[TCP] 收到关节位置: {[f'{x:.3f}' for x in joint_pos_target]}")
            except json.JSONDecodeError:
                print("[TCP] JSON 解析错误")

    except Exception as e:
        print(f"[TCP] 连接错误: {e}")
    finally:
        client_socket.close()
        print(f"[TCP] 客户端断开: {client_addr}")


def main():
    """主函数"""
    global joint_pos_target

    print("=" * 80)
    print("🚀 SO101 仿真 + TCP 通信服务器")
    print("=" * 80)

    print("\n[1] 初始化仿真上下文...")
    import isaaclab.sim as sim_utils
    sim_cfg = sim_utils.SimulationCfg(
        physx=sim_utils.PhysxCfg(
            solver_type="TGS",
            enable_stabilization=True,
            friction_correlation_distance=0.001,
            friction_offset_threshold=0.001,
            gpu_found_lost_pairs_capacity=1024,
            gpu_total_aggregate_pairs_capacity=1024,
        )
    )
    sim = SimulationContext(sim_cfg)
    sim.set_camera_view([1.5, 0.0, 1.5], [0.35, 0.0, 0.3])
    print("✅ 仿真上下文初始化成功!")

    print("\n[2] 设计场景...")
    entities, origins = design_scene()
    origins = origins.to(sim.device)
    robot = entities["robot"]
    print("✅ 场景设计完成!")
    print("   - 木桌: 100cm x 50cm x 75cm, kinematic固定")
    print("   - 方块: 3.5cm, 重量50g, 高摩擦材质")
    print("   - 盘子: 直径8cm, kinematic固定")

    print("\n[3] 重置仿真...")
    sim.reset()
    print("✅ 仿真重置成功!")

    print("\n[3.5] 配置夹爪物理材质...")
    configure_gripper_physics()

    print(f"\n[4] 启动 TCP 服务器，端口 {args.port}...")
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('0.0.0.0', args.port))
    server_socket.listen(1)
    print(f"[TCP] 服务器监听端口 {args.port}")

    tcp_thread = None
    client_connected = False

    print("\n[5] 运行仿真循环...")
    print("    按 Ctrl+C 退出")

    sim_dt = sim.get_physics_dt()
    count = 0

    try:
        while sim_app.is_running():
            if count % 500 == 0:
                count = 0
                root_state = robot.data.default_root_state.clone()
                root_state[:, :3] += origins
                robot.write_root_pose_to_sim(root_state[:, :7])
                robot.write_root_velocity_to_sim(root_state[:, 7:])
                joint_pos = robot.data.default_joint_pos.clone()
                robot.write_joint_state_to_sim(joint_pos, robot.data.default_joint_vel.clone())
                robot.reset()
                print("[INFO]: Resetting robot state...")

            # TCP 连接处理
            if not client_connected:
                try:
                    server_socket.settimeout(0.001)
                    try:
                        client_socket, client_addr = server_socket.accept()
                        tcp_thread = threading.Thread(target=handle_client, args=(client_socket, client_addr))
                        tcp_thread.daemon = True
                        tcp_thread.start()
                        client_connected = True
                        print(f"[TCP] 已连接: {client_addr}")
                    except socket.timeout:
                        pass
                except:
                    pass

            # 关节控制
            if joint_pos_target is not None:
                clipped_angles = clip_joint_angles(joint_pos_target)
                joint_pos = torch.tensor([[clipped_angles[i] for i in range(6)]], device=sim.device)
                robot.set_joint_position_target(joint_pos)
            else:
                current_pos = robot.data.joint_pos.clone()
                robot.set_joint_position_target(current_pos)

            # 仿真步进
            robot.write_data_to_sim()
            sim.step()
            robot.update(sim_dt)

            count += 1
            if count % 30 == 0:
                print(f"Step {count} 完成")

    except KeyboardInterrupt:
        print("\n用户中断")

    print("\n[6] 关闭仿真...")
    server_socket.close()
    sim_app.close()

    print("\n" + "=" * 80)
    print("✅ 仿真结束")
    print("=" * 80)


if __name__ == "__main__":
    main()

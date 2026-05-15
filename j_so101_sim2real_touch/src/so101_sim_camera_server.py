"""
SO101 仿真 + 通信服务器（带摄像头）- IsaacLab 环境

运行命令：
终端1:
cd /home/jer/ws_issac/thirdparty/IsaacLab
conda activate lerobot_issac
export ISAACSIM_ASSETS_PATH=~/isaacsim/Assets/Assets/Isaac/5.1
./isaaclab.sh -p /home/jer/ws_issac/ws/j_so101_sim2real_touch/src/so101_sim_camera_server.py --enable_cameras

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
from isaaclab.sensors.camera import Camera, CameraCfg

# 导入配置模块
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


def design_scene_with_cameras():
    """设计带摄像头的完整场景"""
    import isaaclab.sim as sim_utils
    from isaaclab.assets import Articulation, RigidObject, RigidObjectCfg

    # 地面
    ground_cfg = sim_utils.GroundPlaneCfg(
        usd_path="/home/jer/isaacsim/Assets/Assets/Isaac/5.1/Isaac/Environments/Grid/default_environment.usd"
    )
    ground_cfg.func("/World/defaultGroundPlane", ground_cfg)

    # 灯光
    light_cfg = sim_utils.DomeLightCfg(intensity=3000.0, color=(0.75, 0.75, 0.75))
    light_cfg.func("/World/Light", light_cfg)

    # 桌子
    wood_physics = sim_utils.RigidBodyMaterialCfg(
        static_friction=0.8,
        dynamic_friction=0.6,
        restitution=0.1,
    )
    wood_cfg = RigidObjectCfg(
        prim_path="/World/WoodTable",
        spawn=sim_utils.CuboidCfg(
            size=(1.0, 1.0, 0.75),
            rigid_props=sim_utils.RigidBodyPropertiesCfg(kinematic_enabled=True),
            mass_props=sim_utils.MassPropertiesCfg(mass=5.0),
            collision_props=sim_utils.CollisionPropertiesCfg(),
            visual_material=sim_utils.PreviewSurfaceCfg(
                diffuse_color=(0.6, 0.4, 0.2),
                roughness=0.7,
                metallic=0.0,
            ),
            physics_material=wood_physics,
        ),
        init_state=RigidObjectCfg.InitialStateCfg(
            pos=(0.5, 0.0, 0.375),
            rot=(1.0, 0.0, 0.0, 0.0),
        ),
    )
    wood_table = RigidObject(cfg=wood_cfg)

    # 机器人基座
    origins = [[0.5, 0.0, 0.75]]
    sim_utils.create_prim("/World/RobotBase", "Xform", translation=origins[0])

    # 机器人
    from isaac_so_arm101.robots.trs_so101.so_arm101 import SO_ARM101_CFG
    robot_cfg = SO_ARM101_CFG.copy()
    robot_cfg.prim_path = "/World/RobotBase/Robot"
    robot = Articulation(cfg=robot_cfg)

    # 方块
    cube_physics = sim_utils.RigidBodyMaterialCfg(
        static_friction=0.8,
        dynamic_friction=0.6,
        restitution=0.1,
    )
    cube_cfg = RigidObjectCfg(
        prim_path="/World/Cube",
        spawn=sim_utils.CuboidCfg(
            size=(0.035, 0.035, 0.035),
            rigid_props=sim_utils.RigidBodyPropertiesCfg(
                max_linear_velocity=100.0,
                max_angular_velocity=100.0,
                max_depenetration_velocity=10.0,
                solver_position_iteration_count=128,
                solver_velocity_iteration_count=16,
            ),
            mass_props=sim_utils.MassPropertiesCfg(mass=0.05),
            collision_props=sim_utils.CollisionPropertiesCfg(
                contact_offset=0.001,
                rest_offset=0.0001,
            ),
            visual_material=sim_utils.PreviewSurfaceCfg(
                diffuse_color=(1.0, 0.2, 0.05),
                roughness=0.95,
                metallic=0.0,
            ),
            physics_material=cube_physics,
        ),
        init_state=RigidObjectCfg.InitialStateCfg(
            pos=(0.74, 0.0, 0.768),
            rot=(1.0, 0.0, 0.0, 0.0),
        ),
    )
    cube = RigidObject(cfg=cube_cfg)

    # 盘子
    plate_physics = sim_utils.RigidBodyMaterialCfg(
        static_friction=1.2,
        dynamic_friction=0.8,
        restitution=0.1,
    )
    plate_cfg = RigidObjectCfg(
        prim_path="/World/Plate",
        spawn=sim_utils.CylinderCfg(
            radius=0.04,
            height=0.015,
            rigid_props=sim_utils.RigidBodyPropertiesCfg(kinematic_enabled=True),
            mass_props=sim_utils.MassPropertiesCfg(mass=0.3),
            collision_props=sim_utils.CollisionPropertiesCfg(
                contact_offset=0.001,
                rest_offset=0.0001,
            ),
            visual_material=sim_utils.PreviewSurfaceCfg(
                diffuse_color=(0.1, 0.9, 0.25),
                roughness=0.3,
                metallic=0.1,
            ),
            physics_material=plate_physics,
        ),
        init_state=RigidObjectCfg.InitialStateCfg(
            pos=(0.79, 0.0, 0.758),
            rot=(1.0, 0.0, 0.0, 0.0),
        ),
    )
    plate = RigidObject(cfg=plate_cfg)

    # 腕部摄像头（挂在夹爪gripper_link上，随夹爪一起动，朝前拍摄工作区域）
    wrist_camera_cfg = CameraCfg(
        prim_path="/World/RobotBase/Robot/gripper_link/camera_wrist",
        update_period=0.033,
        height=120,
        width=160,
        data_types=["rgb"],
        spawn=sim_utils.PinholeCameraCfg(
            focal_length=1.85,
            horizontal_aperture=3.1,
            focus_distance=0.1,
            clipping_range=(0.01, 2.0),
        ),
        offset=CameraCfg.OffsetCfg(
            pos=(0.015, 0.04, 0.02),
            rot=(0.0, 0.0, 1.0, 0.0),
            convention="ros",
        ),
    )
    wrist_camera = Camera(cfg=wrist_camera_cfg)

    # 第三视角摄像头（最终确定：30号 Y+4 Z-2）
    sim_utils.create_prim("/World/CameraTripod", "Xform", translation=(0.9, -0.05, 1.12))
    overhead_camera_cfg = CameraCfg(
        prim_path="/World/CameraTripod/camera_third_person",
        update_period=0.033,
        height=120,
        width=160,
        data_types=["rgb"],
        spawn=sim_utils.PinholeCameraCfg(
            focal_length=3.42,
            horizontal_aperture=13.1,
            focus_distance=0.37,
            clipping_range=(0.01, 2.0),
        ),
        offset=CameraCfg.OffsetCfg(
            pos=(0.0, 0.0, 0.0),
            rot=(-0.1895, 0.7471, 0.6277, -0.1089),
        ),
    )
    overhead_camera = Camera(cfg=overhead_camera_cfg)

    return {
        "robot": robot,
        "wood": wood_table,
        "cube": cube,
        "plate": plate,
        "wrist_camera": wrist_camera,
        "overhead_camera": overhead_camera,
    }, torch.tensor(origins)


def main():
    """主函数"""
    global joint_pos_target

    print("=" * 80)
    print("🚀 SO101 仿真 + TCP 通信服务器（带摄像头）")
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
    entities, origins = design_scene_with_cameras()
    origins = origins.to(sim.device)
    robot = entities["robot"]
    wrist_camera = entities["wrist_camera"]
    overhead_camera = entities["overhead_camera"]
    print("✅ 场景设计完成!")
    print("   - 木桌: 100cm x 100cm x 75cm, kinematic固定")
    print("   - 方块: 3.5cm, 重量50g, 高摩擦材质")
    print("   - 盘子: 直径8cm, kinematic固定")
    print("   - 腕部摄像头: 160x120, 30FPS")
    print("   - 第三视角摄像头: 160x120, 30FPS")

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
            if count == 0:
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

            # 更新摄像头
            wrist_camera.update(dt=sim_dt)
            overhead_camera.update(dt=sim_dt)

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

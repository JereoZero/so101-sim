"""
SO101 带摄像头的仿真 + 通信服务器 - IsaacLab 环境

运行命令：
终端1:
cd /home/jer/ws_issac/thirdparty/IsaacLab
conda activate isaaclab
export ISAACSIM_ASSETS_PATH=~/isaacsim/Assets/Assets/Isaac/5.1
./isaaclab.sh -p /home/jer/ws_issac/ws/j_so101_sim2real_touch/src/so101_sim_camera_server.py --enable_cameras

终端2:
conda activate lerobot_issac
python /home/jer/ws_issac/ws/j_so101_sim2real_touch/src/so101_real_teleop_client.py

通信协议：
- TCP 服务器，监听端口 8765
- 接收 JSON 格式的关节命令：{"joint_pos": [6个角度值]}
"""

import os

os.environ.setdefault("ISAACSIM_ASSETS_PATH", os.path.expanduser("~/isaacsim/Assets/Assets/Isaac/5.1"))

import sys
import argparse
import json
import socket
import threading

sys.path.insert(0, "/home/jer/ws_issac/thirdparty/isaac_so_arm101/src")

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser()
AppLauncher.add_app_launcher_args(parser)
parser.add_argument("--port", type=int, default=8765, help="通信端口")
args = parser.parse_args()

app_launcher = AppLauncher(args)
sim_app = app_launcher.app

import torch
import isaaclab.sim as sim_utils
from isaaclab.assets import Articulation, RigidObject, RigidObjectCfg
from isaaclab.sim import SimulationContext
from isaaclab.sensors.camera import Camera, CameraCfg

from isaac_so_arm101.robots.trs_so101.so_arm101 import SO_ARM101_CFG


joint_pos_target = None
count = 0


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


def design_scene():
    """设计场景"""
    # 地面
    ground_cfg = sim_utils.GroundPlaneCfg()
    ground_cfg.func("/World/defaultGroundPlane", ground_cfg)

    # 灯光
    light_cfg = sim_utils.DomeLightCfg(intensity=3000.0, color=(0.75, 0.75, 0.75))
    light_cfg.func("/World/Light", light_cfg)

    # 桌子
    wood_cfg = RigidObjectCfg(
        prim_path="/World/WoodTable",
        spawn=sim_utils.CuboidCfg(
            size=(1.0, 1.0, 0.75),
            rigid_props=sim_utils.RigidBodyPropertiesCfg(kinematic_enabled=True),
            mass_props=sim_utils.MassPropertiesCfg(mass=5.0),
            collision_props=sim_utils.CollisionPropertiesCfg(),
            visual_material=sim_utils.PreviewSurfaceCfg(
                diffuse_color=(0.82, 0.71, 0.57),
                roughness=0.4,
                metallic=0.0,
            ),
        ),
        init_state=RigidObjectCfg.InitialStateCfg(
            pos=(0.5, 0.0, 0.375),
            rot=(1.0, 0.0, 0.0, 0.0),
        ),
    )
    wood_table = RigidObject(cfg=wood_cfg)

    # 机器人
    origins = [[0.5, 0.0, 0.75]]
    sim_utils.create_prim("/World/RobotBase", "Xform", translation=origins[0])

    robot_cfg = SO_ARM101_CFG.copy()
    robot_cfg.prim_path = "/World/RobotBase/Robot"
    robot = Articulation(cfg=robot_cfg)

    # 方块
    cube_cfg = RigidObjectCfg(
        prim_path="/World/Cube",
        spawn=sim_utils.CuboidCfg(
            size=(0.035, 0.035, 0.035),
            rigid_props=sim_utils.RigidBodyPropertiesCfg(),
            mass_props=sim_utils.MassPropertiesCfg(mass=0.0019),
            collision_props=sim_utils.CollisionPropertiesCfg(),
            visual_material=sim_utils.PreviewSurfaceCfg(
                diffuse_color=(1.0, 0.4, 0.2),
                roughness=0.95,
                metallic=0.0,
            ),
        ),
        init_state=RigidObjectCfg.InitialStateCfg(
            pos=(0.67, 0.0, 0.768),
            rot=(1.0, 0.0, 0.0, 0.0),
        ),
    )
    cube = RigidObject(cfg=cube_cfg)

    # 盘子
    plate_cfg = RigidObjectCfg(
        prim_path="/World/Plate",
        spawn=sim_utils.CylinderCfg(
            radius=0.04,
            height=0.015,
            rigid_props=sim_utils.RigidBodyPropertiesCfg(),
            mass_props=sim_utils.MassPropertiesCfg(mass=0.1),
            collision_props=sim_utils.CollisionPropertiesCfg(),
            visual_material=sim_utils.PreviewSurfaceCfg(
                diffuse_color=(0.2, 0.8, 0.4),
                roughness=0.3,
                metallic=0.1,
            ),
        ),
        init_state=RigidObjectCfg.InitialStateCfg(
            pos=(0.76, 0.0, 0.758),
            rot=(1.0, 0.0, 0.0, 0.0),
        ),
    )
    plate = RigidObject(cfg=plate_cfg)

    # 腕部摄像头 - 使用 CameraCfg
    sim_utils.create_prim("/World/RobotBase/Robot/gripper_link", "Xform")
    wrist_camera_cfg = CameraCfg(
        prim_path="/World/RobotBase/Robot/gripper_link/camera_wrist",
        update_period=0.2,
        height=128,
        width=128,
        data_types=["rgb", "distance_to_image_plane"],
        spawn=sim_utils.PinholeCameraCfg(
            focal_length=1.85,
            horizontal_aperture=3.1,
            focus_distance=0.5,
            clipping_range=(0.01, 10.0),
        ),
    )
    wrist_cam = Camera(cfg=wrist_camera_cfg)
    wrist_cam.set_world_poses(
        positions=torch.tensor([[0.5, 0.04, 0.78]], device="cuda"),
        orientations=torch.tensor([[0.259, 0.0, 0.0, 0.966]], device="cuda"),
        convention="ros"
    )

    # 俯视摄像头 - 使用 CameraCfg
    overhead_camera_cfg = CameraCfg(
        prim_path="/World/OverheadCamera/camera_overhead",
        update_period=0.2,
        height=128,
        width=128,
        data_types=["rgb", "distance_to_image_plane"],
        spawn=sim_utils.PinholeCameraCfg(
            focal_length=3.42,
            horizontal_aperture=13.1,
            focus_distance=0.37,
            clipping_range=(0.01, 2.0),
        ),
    )
    overhead_cam = Camera(cfg=overhead_camera_cfg)
    overhead_cam.set_world_poses(
        positions=torch.tensor([[0.5, 0.0, 1.12]], device="cuda"),
        orientations=torch.tensor([[0.5, 0.5, -0.5, -0.5]], device="cuda"),
        convention="ros"
    )

    return robot, cube, plate, wrist_cam, overhead_cam


def main():
    global joint_pos_target, count

    # 创建仿真上下文
    sim_cfg = sim_utils.SimulationCfg()
    sim = SimulationContext(sim_cfg)
    sim.set_camera_view([1.5, 0.0, 1.5], [0.35, 0.0, 0.3])

    # 设计场景
    print("[1] 创建场景...")
    robot, cube, plate, wrist_cam, overhead_cam = design_scene()

    print("[2] 重置场景...")
    sim.reset()

    print(f"[3] 启动 TCP 服务器，端口 {args.port}...")
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('0.0.0.0', args.port))
    server_socket.listen(1)
    print(f"[TCP] 服务器监听端口 {args.port}")

    tcp_thread = None
    client_connected = False

    print("[4] 开始仿真循环...")
    print("    按 Ctrl+C 退出")

    sim_dt = sim.get_physics_dt()

    while sim_app.is_running():
        if not client_connected:
            try:
                server_socket.settimeout(1.0)
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

        if joint_pos_target is not None:
            joint_pos = torch.tensor([[joint_pos_target[i] for i in range(6)]], device=sim.device)
            robot.set_joint_position_target(joint_pos)

        robot.write_data_to_sim()
        sim.step()
        robot.update(sim_dt)

        # 更新摄像头数据
        wrist_cam.update(dt=sim_dt)
        overhead_cam.update(dt=sim_dt)

        count += 1
        if count % 30 == 0:
            print(f"[Step {count}] 完成")

    print("[5] 关闭仿真...")
    server_socket.close()
    sim_app.close()


if __name__ == "__main__":
    main()

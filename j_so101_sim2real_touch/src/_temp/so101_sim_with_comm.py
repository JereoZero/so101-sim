"""
SO101 仿真 + 通信服务器 - IsaacLab 环境

运行命令：
cd /home/jer/ws_issac/thirdparty/IsaacLab
conda activate isaaclab
export ISAACSIM_ASSETS_PATH=~/isaacsim/Assets/Assets/Isaac/5.1
./isaaclab.sh -p /home/jer/ws_issac/ws/j_so101_sim2real_touch/src/so101_sim_with_comm.py

通信协议：
- TCP 服务器，监听端口 8765
- 接收 JSON 格式的关节命令：{"joint_pos": [6个角度值]}
"""

import sys
import argparse
import json
import socket
import threading
import math

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
from isaaclab.sim.spawners.materials import RigidBodyMaterialCfg

from isaac_so_arm101.robots.trs_so101.so_arm101 import SO_ARM101_CFG


joint_pos_target = None
client_socket = None


def design_scene():
    """设计场景"""
    ground_cfg = sim_utils.GroundPlaneCfg()
    ground_cfg.func("/World/defaultGroundPlane", ground_cfg)

    light_cfg = sim_utils.DomeLightCfg(intensity=3000.0, color=(0.75, 0.75, 0.75))
    light_cfg.func("/World/Light", light_cfg)

    # 桌面物理材质 - 木质桌面，中等摩擦
    wood_physics_material = RigidBodyMaterialCfg(
        static_friction=0.8,   # 木质桌面摩擦
        dynamic_friction=0.6,
        restitution=0.2,
    )

    wood_cfg = RigidObjectCfg(
        prim_path="/World/WoodTable",
        spawn=sim_utils.CuboidCfg(
            size=(1.0, 1.0, 0.75),
            rigid_props=sim_utils.RigidBodyPropertiesCfg(
                kinematic_enabled=True,
            ),
            mass_props=sim_utils.MassPropertiesCfg(mass=5.0),
            collision_props=sim_utils.CollisionPropertiesCfg(),
            visual_material=sim_utils.PreviewSurfaceCfg(
                diffuse_color=(0.6, 0.4, 0.2),
                roughness=0.7,
                metallic=0.0,
            ),
            physics_material=wood_physics_material,
        ),
        init_state=RigidObjectCfg.InitialStateCfg(
            pos=(0.5, 0.0, 0.375),
            rot=(1.0, 0.0, 0.0, 0.0),
        ),
    )
    wood_table = RigidObject(cfg=wood_cfg)

    origins = [[0.5, 0.0, 0.75]]
    sim_utils.create_prim("/World/RobotBase", "Xform", translation=origins[0])

    robot_cfg = SO_ARM101_CFG.copy()
    robot_cfg.prim_path = "/World/RobotBase/Robot"
    robot = Articulation(cfg=robot_cfg)

    # 方块材质：高密度泡沫垫 - 硬且高摩擦
    cube_physics_material = RigidBodyMaterialCfg(
        static_friction=1.5,  # 高静摩擦
        dynamic_friction=1.2,  # 高动摩擦
        restitution=0.1,  # 低弹性（不Q弹）
    )

    cube_cfg = RigidObjectCfg(
        prim_path="/World/Cube",
        spawn=sim_utils.CuboidCfg(
            size=(0.035, 0.035, 0.035),
            rigid_props=sim_utils.RigidBodyPropertiesCfg(
                max_depenetration_velocity=10.0,  # 减少形变
                solver_position_iteration_count=8,  # 增加求解器迭代次数，更硬
            ),
            mass_props=sim_utils.MassPropertiesCfg(mass=0.0019),
            collision_props=sim_utils.CollisionPropertiesCfg(),
            visual_material=sim_utils.PreviewSurfaceCfg(
                diffuse_color=(1.0, 0.4, 0.2),
                roughness=0.95,  # 非常粗糙的表面（沙沙感）
                metallic=0.0,
            ),
            physics_material=cube_physics_material,
        ),
        init_state=RigidObjectCfg.InitialStateCfg(
            pos=(0.67, 0.0, 0.768),
            rot=(1.0, 0.0, 0.0, 0.0),
        ),
    )
    cube = RigidObject(cfg=cube_cfg)

    # 盘子物理材质 - 光滑陶瓷/塑料材质
    plate_physics_material = RigidBodyMaterialCfg(
        static_friction=0.4,   # 光滑表面
        dynamic_friction=0.3,
        restitution=0.1,
    )

    plate_cfg = RigidObjectCfg(
        prim_path="/World/Plate",
        spawn=sim_utils.CylinderCfg(
            radius=0.04,
            height=0.015,
            rigid_props=sim_utils.RigidBodyPropertiesCfg(),
            mass_props=sim_utils.MassPropertiesCfg(mass=0.1),
            collision_props=sim_utils.CollisionPropertiesCfg(),
            visual_material=sim_utils.PreviewSurfaceCfg(
                diffuse_color=(0.9, 0.9, 0.9),
                roughness=0.3,
                metallic=0.1,
            ),
            physics_material=plate_physics_material,
        ),
        init_state=RigidObjectCfg.InitialStateCfg(
            pos=(0.76, 0.0, 0.758),
            rot=(1.0, 0.0, 0.0, 0.0),
        ),
    )
    plate = RigidObject(cfg=plate_cfg)

    return {"robot": robot, "wood": wood_table, "cube": cube, "plate": plate}, torch.tensor(origins)


def handle_client(client, address):
    """处理客户端连接"""
    global joint_pos_target, client_socket
    print(f"[通信] 客户端连接: {address}")
    client_socket = client

    try:
        buffer = ""
        while sim_app.is_running():
            data = client.recv(1024).decode('utf-8')
            if not data:
                break

            buffer += data
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                try:
                    cmd = json.loads(line)
                    if "joint_pos" in cmd and len(cmd["joint_pos"]) >= 6:
                        joint_pos_target = cmd["joint_pos"]
                        print(f"[通信] 收到关节命令: {joint_pos_target[:3]}...")
                except json.JSONDecodeError:
                    pass

    except Exception as e:
        print(f"[通信] 客户端断开: {e}")
    finally:
        client_socket = None
        joint_pos_target = None
        client.close()


def comm_server(port):
    """通信服务器线程"""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('127.0.0.1', port))
    server.listen(1)
    print(f"[通信] 服务器启动，监听端口 {port}")

    while sim_app.is_running():
        server.settimeout(0.1)
        try:
            client, address = server.accept()
            thread = threading.Thread(target=handle_client, args=(client, address), daemon=True)
            thread.start()
        except socket.timeout:
            continue


def main():
    """主函数"""
    global joint_pos_target

    print("=" * 80)
    print("🚀 SO101 仿真 + 通信服务器")
    print("=" * 80)

    print("\n[1] 初始化仿真上下文...")
    # 设置全局默认物理材质 - PLA 3D打印材料摩擦系数
    default_physics_material = RigidBodyMaterialCfg(
        static_friction=0.6,   # PLA静摩擦
        dynamic_friction=0.4,  # PLA动摩擦
        restitution=0.1,       # 低弹性
    )

    sim_cfg = sim_utils.SimulationCfg(
        physics_material=default_physics_material,
    )
    sim = SimulationContext(sim_cfg)
    sim.set_camera_view([1.5, 0.0, 1.5], [0.5, 0.0, 0.5])
    print("✅ 仿真上下文初始化成功!")

    print("\n[2] 设计场景...")
    entities, origins = design_scene()
    origins = origins.to(sim.device)
    robot = entities["robot"]
    print("✅ 场景设计完成!")
    print("   - 木桌: 1m x 1m x 0.75m, kinematic固定")
    print("   - 方块: 3.5cm, 重量1.9g")
    print("   - 盘子: 直径8cm, 重量100g")

    print("\n[3] 重置仿真...")
    sim.reset()
    print("✅ 仿真重置成功!")

    comm_thread = threading.Thread(target=comm_server, args=(args.port,), daemon=True)
    comm_thread.start()
    print(f"\n[4] 启动通信服务器 (端口 {args.port})...")

    print("\n[5] 运行仿真循环...")
    sim_dt = sim.get_physics_dt()
    count = 0

    try:
        while sim_app.is_running():
            if joint_pos_target is not None:
                joint_pos = torch.tensor([[joint_pos_target[i] for i in range(6)]], device=sim.device)
                robot.set_joint_position_target(joint_pos)

            robot.write_data_to_sim()
            sim.step()
            robot.update(sim_dt)

            count += 1
            if count % 30 == 0:
                print(f"Step {count} 完成")

    except KeyboardInterrupt:
        print("\n用户中断")

    print("\n[6] 关闭仿真...")
    if client_socket:
        client_socket.close()
    sim_app.close()

    print("\n" + "=" * 80)
    print("✅ 仿真结束")
    print("=" * 80)


if __name__ == "__main__":
    main()

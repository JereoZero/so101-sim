"""
SO101 数据采集环境 - IsaacLab 环境

运行命令：
cd /home/jer/ws_issac/thirdparty/IsaacLab
conda activate isaaclab
export ISAACSIM_ASSETS_PATH=~/isaacsim/Assets/Assets/Isaac/5.1
./isaaclab.sh -p /home/jer/ws_issac/ws/j_so101_sim2real_touch/src/so101_sim_data_collection.py --enable_cameras
"""

import sys
import argparse

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
import numpy as np
import isaaclab.sim as sim_utils
from isaaclab.sim import SimulationContext
from isaaclab.sensors.camera import Camera, CameraCfg
from isaaclab.assets import Articulation, RigidObject, RigidObjectCfg
from isaac_so_arm101.robots.trs_so101.so_arm101 import SO_ARM101_CFG
from physics_config import configure_gripper_physics
from robot_config import clip_joint_angles
from hdf5_recorder import HDF5Recorder
from tcp_server import TCPServer

# 物体初始位置（基准位置）
PLATE_BASE_POS = np.array([0.79, 0.0, 0.758])
CUBE_BASE_POS = np.array([0.74, 0.0, 0.768])
ROBOT_ORIGINS = np.array([0.5, 0.0, 0.75])
RECORD_DIR = "/home/jer/ws_issac/ws/j_so101_sim2real_touch/datasets/sim_hdf5"


def randomize_scene_lighting(light_prim):
    """随机化灯光：亮度 ±20%，色温微小变化"""
    # 亮度：原始 50000，范围 40000~60000
    intensity = np.random.uniform(40000.0, 60000.0)
    
    # 色温：通过 RGB 色温模拟，原始 (1.0, 1.0, 1.0)，范围 偏冷/偏暖
    color_r = np.random.uniform(0.95, 1.0)
    color_g = np.random.uniform(0.93, 1.0)
    color_b = np.random.uniform(0.90, 1.0)
    
    light_prim.GetAttribute("inputs:intensity").Set(intensity)
    light_prim.GetAttribute("inputs:color").Set((color_r, color_g, color_b))


def randomize_object_positions(cube, plate, sim):
    """随机化物体位置：盘子 ±5cm，方块距盘子 2-10cm"""
    plate_offset_x = np.random.uniform(-0.05, 0.05)
    plate_offset_y = np.random.uniform(-0.05, 0.05)
    new_plate_pos = PLATE_BASE_POS + np.array([plate_offset_x, plate_offset_y, 0.0])

    distance = np.random.uniform(0.06, 0.14)
    angle = np.random.uniform(0, 2 * np.pi)
    new_cube_pos = CUBE_BASE_POS + np.array([distance * np.cos(angle), distance * np.sin(angle), 0.0])

    # 方块随机旋转（增加泛化性）
    cube_yaw = np.random.uniform(-np.pi / 6, np.pi / 6)
    cube_quat = [np.cos(cube_yaw / 2), 0, 0, np.sin(cube_yaw / 2)]

    cube_state = cube.data.default_root_state.clone()
    cube_state[:, :3] = torch.tensor([[new_cube_pos[0], new_cube_pos[1], new_cube_pos[2]]], device=sim.device)
    cube_state[:, 3:7] = torch.tensor([[cube_quat[0], cube_quat[1], cube_quat[2], cube_quat[3]]], device=sim.device)
    cube.write_root_pose_to_sim(cube_state[:, :7])
    cube.write_root_velocity_to_sim(torch.zeros_like(cube_state[:, 7:]))

    plate_state = plate.data.default_root_state.clone()
    plate_state[:, :3] = torch.tensor([[new_plate_pos[0], new_plate_pos[1], new_plate_pos[2]]], device=sim.device)
    plate.write_root_pose_to_sim(plate_state[:, :7])
    plate.write_root_velocity_to_sim(torch.zeros_like(plate_state[:, 7:]))

    print(f"[随机化] 盘子: ({new_plate_pos[0]:.3f}, {new_plate_pos[1]:.3f}), 方块: ({new_cube_pos[0]:.3f}, {new_cube_pos[1]:.3f}), 旋转: {np.degrees(cube_yaw):.1f}°")


def reset_environment(cube, plate, robot, origins, sim, light_prim=None):
    """重置环境：机器人归位 + 物体随机化"""
    root_state = robot.data.default_root_state.clone()
    root_state[:, :3] += origins
    robot.write_root_pose_to_sim(root_state[:, :7])
    robot.write_root_velocity_to_sim(root_state[:, 7:])
    robot.write_joint_state_to_sim(robot.data.default_joint_pos.clone(), robot.data.default_joint_vel.clone())
    robot.reset()
    
    if light_prim:
        randomize_scene_lighting(light_prim)
    
    randomize_object_positions(cube, plate, sim)
    print("[重置] 完成!\n")


def design_scene():
    """设计完整场景"""
    # 地面
    ground_cfg = sim_utils.GroundPlaneCfg(
        usd_path="/home/jer/isaacsim/Assets/Assets/Isaac/5.1/Isaac/Environments/Grid/default_environment.usd"
    )
    ground_cfg.func("/World/defaultGroundPlane", ground_cfg)

    # 灯光（圆盘灯，位于机械臂和摄像头中间上方 2.5m）
    light_cfg = sim_utils.CylinderLightCfg(
        intensity=50000.0,
        color=(1.0, 1.0, 1.0),
        length=0.3,
        radius=0.15,
    )
    light_cfg.func("/World/DiskLight", light_cfg, translation=(0.7, 0.0, 2.5))

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

    # 机器人
    origins = [[ROBOT_ORIGINS[0], ROBOT_ORIGINS[1], ROBOT_ORIGINS[2]]]
    sim_utils.create_prim("/World/RobotBase", "Xform", translation=origins[0])
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
            collision_props=sim_utils.CollisionPropertiesCfg(contact_offset=0.001, rest_offset=0.0001),
            visual_material=sim_utils.PreviewSurfaceCfg(
                diffuse_color=(1.0, 0.2, 0.05),
                roughness=0.95,
                metallic=0.0,
            ),
            physics_material=cube_physics,
        ),
        init_state=RigidObjectCfg.InitialStateCfg(
            pos=CUBE_BASE_POS.tolist(),
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
            collision_props=sim_utils.CollisionPropertiesCfg(contact_offset=0.001, rest_offset=0.0001),
            visual_material=sim_utils.PreviewSurfaceCfg(diffuse_color=(0.1, 0.9, 0.25), roughness=0.3, metallic=0.1),
            physics_material=plate_physics,
        ),
        init_state=RigidObjectCfg.InitialStateCfg(
            pos=PLATE_BASE_POS.tolist(),
            rot=(1.0, 0.0, 0.0, 0.0),
        ),
    )
    plate = RigidObject(cfg=plate_cfg)

    # 腕部摄像头（640x480，与真机分辨率一致）
    wrist_camera_cfg = CameraCfg(
        prim_path="/World/RobotBase/Robot/gripper_link/camera_wrist",
        update_period=0.033, height=480, width=640, data_types=["rgb"],
        spawn=sim_utils.PinholeCameraCfg(focal_length=1.85, horizontal_aperture=3.1, focus_distance=0.1, clipping_range=(0.01, 2.0)),
        offset=CameraCfg.OffsetCfg(pos=(0.015, 0.04, 0.02), rot=(0.0, 0.0, 1.0, 0.0), convention="ros"),
    )
    wrist_camera = Camera(cfg=wrist_camera_cfg)

    # 第三视角摄像头（640x480，与真机分辨率一致）
    sim_utils.create_prim("/World/CameraTripod", "Xform", translation=(0.9, -0.05, 1.12))
    overhead_camera_cfg = CameraCfg(
        prim_path="/World/CameraTripod/camera_third_person",
        update_period=0.033, height=480, width=640, data_types=["rgb"],
        spawn=sim_utils.PinholeCameraCfg(focal_length=3.42, horizontal_aperture=13.1, focus_distance=0.37, clipping_range=(0.01, 2.0)),
        offset=CameraCfg.OffsetCfg(pos=(0.0, 0.0, 0.0), rot=(-0.1895, 0.7471, 0.6277, -0.1089)),
    )
    overhead_camera = Camera(cfg=overhead_camera_cfg)

    return {
        "robot": robot, "cube": cube, "plate": plate,
        "wrist_camera": wrist_camera, "overhead_camera": overhead_camera,
    }, torch.tensor(origins)


def main():
    """主函数"""
    print("=" * 60 + "\n🚀 SO101 数据采集环境\n" + "=" * 60)

    # 初始化仿真
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

    # 构建场景
    entities, origins = design_scene()
    origins = origins.to(sim.device)
    robot = entities["robot"]
    cube = entities["cube"]
    plate = entities["plate"]
    wrist_camera = entities["wrist_camera"]
    overhead_camera = entities["overhead_camera"]

    sim.reset()

    from pxr import UsdGeom, Gf

    # 获取灯光 prim 用于随机化
    stage = sim.stage
    light_prim = stage.GetPrimAtPath("/World/DiskLight")
    if not light_prim:
        print("[警告] 未找到 DiskLight，灯光随机化将跳过")
    else:
        randomize_scene_lighting(light_prim)

    configure_gripper_physics()

    # 启动录制器和 TCP 服务器
    recorder = HDF5Recorder(RECORD_DIR)
    tcp_server = TCPServer(args.port)

    # 设置键盘控制
    import carb
    import omni.kit.app

    def setup_keyboard():
        def kb_cb(event):
            if event.type != carb.input.KeyboardEventType.KEY_PRESS:
                return
            key = event.input

            if key == carb.input.KeyboardInput.Z:
                if not recorder.is_recording:
                    recorder.start()
                    print(f"\n[录制] 开始录制 Episode {recorder.current_demo_index}...")
                else:
                    recorder.stop()
                    print(f"\n[录制] 录制已停止，请确认:")
                    print(f"       Y=保存 ✅  |  C=放弃+刷新场景\n")
            elif key == carb.input.KeyboardInput.Y and recorder.recording_paused:
                recorder.save_episode()
                print(f"[录制] 准备下一条，按 Z 开始录制\n")
            elif key == carb.input.KeyboardInput.C:
                recorder.discard_and_clear()
                print("\n[刷新] 场景已重置，物体位置随机化...")
                reset_environment(cube, plate, robot, origins, sim, light_prim)

        app_interface = omni.kit.app.get_app_interface()
        carb.input.acquire_input_interface().subscribe_to_keyboard_events(None, kb_cb)
        print("[快捷键] Z=开始/停止 | Y=确认保存 | C=放弃+刷新场景")

    setup_keyboard()

    # 仿真循环
    sim_dt = sim.get_physics_dt()
    count = 0

    try:
        while sim_app.is_running():
            # TCP 连接
            tcp_server.accept_connection()

            # 关节控制
            target = tcp_server.joint_pos_target
            if target is not None:
                clipped = clip_joint_angles(target)
                robot.set_joint_position_target(torch.tensor([[clipped[i] for i in range(6)]], device=sim.device))
            else:
                robot.set_joint_position_target(robot.data.joint_pos.clone())

            # 仿真步进
            robot.write_data_to_sim()
            sim.step()
            robot.update(sim_dt)

            # 摄像头更新
            wrist_camera.update(dt=sim_dt)
            overhead_camera.update(dt=sim_dt)

            # 数据采集
            if recorder.is_recording:
                cam1_rgb = wrist_camera.data.output["rgb"][0].cpu().numpy()
                cam2_rgb = overhead_camera.data.output["rgb"][0].cpu().numpy()
                joint_state = robot.data.joint_pos.cpu().numpy()[0].tolist()
                recorder.add_frame(cam1_rgb, cam2_rgb, target if target is not None else joint_state, joint_state)

            # 状态提示
            count += 1
            if count % 300 == 0:
                status = '🔴录制中' if recorder.is_recording else '⏹未录制'
                print(f"[Step {count}] | {status} | Ep {recorder.current_demo_index}")

    except KeyboardInterrupt:
        pass
    finally:
        tcp_server.close()
        sim_app.close()
        print("✅ 仿真结束")


if __name__ == "__main__":
    main()

"""
ACT 直接推理 - 在 Isaac Sim 环境中直接加载模型

不需要 TCP 服务器！模型直接在这里推理！

运行命令：
cd /home/jer/ws_issac/thirdparty/IsaacLab
conda activate isaaclab
export ISAACSIM_ASSETS_PATH=~/isaacsim/Assets/Assets/Isaac/5.1
./isaaclab.sh -p /home/jer/ws_issac/ws/j_so101_sim2real_touch/src/act_direct_inference.py --enable_cameras
"""

import sys
sys.path.insert(0, "/home/jer/ws/workspace/projects/lerobot/src")
sys.path.insert(0, "/home/jer/ws_issac/thirdparty/isaac_so_arm101/src")
sys.path.insert(0, "/home/jer/ws_issac/ws/j_so101_sim2real_touch/src")

import argparse
import time

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser()
AppLauncher.add_app_launcher_args(parser)
parser.add_argument("--n_episodes", type=int, default=5)
parser.add_argument("--max_steps", type=int, default=1800)
args = parser.parse_args()

app_launcher = AppLauncher(args)
sim_app = app_launcher.app

import torch
import numpy as np
import cv2
from pathlib import Path

import isaaclab.sim as sim_utils
from isaaclab.sim import SimulationContext
from isaaclab.sensors.camera import Camera, CameraCfg
from isaaclab.assets import Articulation, RigidObject, RigidObjectCfg
from isaac_so_arm101.robots.trs_so101.so_arm101 import SO_ARM101_CFG

from lerobot.datasets.lerobot_dataset import LeRobotDatasetMetadata
from lerobot.policies.act.modeling_act import ACTPolicy
from lerobot.policies.factory import make_pre_post_processors
from lerobot.policies.utils import build_inference_frame, make_robot_action

# 路径配置
CHECKPOINT_PATH = "/home/jer/ws_issac/ws/j_so101_sim2real_touch/models/act_sim_v1/checkpoints/012000"
DATASET_DIR = "/home/jer/ws_issac/ws/j_so101_sim2real_touch/datasets/sim_lerobot_act"

PLATE_BASE_POS = np.array([0.79, 0.0, 0.758])
CUBE_BASE_POS = np.array([0.74, 0.0, 0.768])
ROBOT_ORIGINS = np.array([0.5, 0.0, 0.75])

JOINT_NAMES = [
    "shoulder_pan.pos",
    "shoulder_lift.pos",
    "elbow_flex.pos",
    "wrist_flex.pos",
    "wrist_roll.pos",
    "gripper.pos"
]


def randomize_scene_lighting(light_prim):
    intensity = np.random.uniform(40000.0, 60000.0)
    color_r = np.random.uniform(0.95, 1.0)
    color_g = np.random.uniform(0.93, 1.0)
    color_b = np.random.uniform(0.90, 1.0)
    light_prim.GetAttribute("inputs:intensity").Set(intensity)
    light_prim.GetAttribute("inputs:color").Set((color_r, color_g, color_b))


def randomize_object_positions(cube, plate, sim):
    plate_offset_x = np.random.uniform(-0.05, 0.05)
    plate_offset_y = np.random.uniform(-0.05, 0.05)
    new_plate_pos = PLATE_BASE_POS + np.array([plate_offset_x, plate_offset_y, 0.0])

    distance = np.random.uniform(0.06, 0.14)
    angle = np.random.uniform(0, 2 * np.pi)
    new_cube_pos = CUBE_BASE_POS + np.array([distance * np.cos(angle), distance * np.sin(angle), 0.0])

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

    print(f"[随机化] 盘子: ({new_plate_pos[0]:.3f}, {new_plate_pos[1]:.3f}), 方块: ({new_cube_pos[0]:.3f}, {new_cube_pos[1]:.3f})")


def reset_environment(cube, plate, robot, origins, sim, light_prim=None):
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
    ground_cfg = sim_utils.GroundPlaneCfg(
        usd_path="/home/jer/isaacsim/Assets/Assets/Isaac/5.1/Isaac/Environments/Grid/default_environment.usd"
    )
    ground_cfg.func("/World/defaultGroundPlane", ground_cfg)

    light_cfg = sim_utils.CylinderLightCfg(
        intensity=50000.0,
        color=(1.0, 1.0, 1.0),
        length=0.3,
        radius=0.15,
    )
    light_cfg.func("/World/DiskLight", light_cfg, translation=(0.7, 0.0, 2.5))

    wood_physics = sim_utils.RigidBodyMaterialCfg(
        static_friction=0.8, dynamic_friction=0.6, restitution=0.1,
    )
    wood_cfg = RigidObjectCfg(
        prim_path="/World/WoodTable",
        spawn=sim_utils.CuboidCfg(
            size=(1.0, 1.0, 0.75),
            rigid_props=sim_utils.RigidBodyPropertiesCfg(kinematic_enabled=True),
            mass_props=sim_utils.MassPropertiesCfg(mass=5.0),
            collision_props=sim_utils.CollisionPropertiesCfg(),
            visual_material=sim_utils.PreviewSurfaceCfg(diffuse_color=(0.6, 0.4, 0.2), roughness=0.7, metallic=0.0),
            physics_material=wood_physics,
        ),
        init_state=RigidObjectCfg.InitialStateCfg(pos=(0.5, 0.0, 0.375), rot=(1.0, 0.0, 0.0, 0.0)),
    )
    wood_table = RigidObject(cfg=wood_cfg)

    origins = [[ROBOT_ORIGINS[0], ROBOT_ORIGINS[1], ROBOT_ORIGINS[2]]]
    sim_utils.create_prim("/World/RobotBase", "Xform", translation=origins[0])
    robot_cfg = SO_ARM101_CFG.copy()
    robot_cfg.prim_path = "/World/RobotBase/Robot"
    robot = Articulation(cfg=robot_cfg)

    cube_physics = sim_utils.RigidBodyMaterialCfg(
        static_friction=0.8, dynamic_friction=0.6, restitution=0.1,
    )
    cube_cfg = RigidObjectCfg(
        prim_path="/World/Cube",
        spawn=sim_utils.CuboidCfg(
            size=(0.035, 0.035, 0.035),
            rigid_props=sim_utils.RigidBodyPropertiesCfg(
                max_linear_velocity=100.0, max_angular_velocity=100.0,
                max_depenetration_velocity=10.0, solver_position_iteration_count=128,
                solver_velocity_iteration_count=16,
            ),
            mass_props=sim_utils.MassPropertiesCfg(mass=0.05),
            collision_props=sim_utils.CollisionPropertiesCfg(contact_offset=0.001, rest_offset=0.0001),
            visual_material=sim_utils.PreviewSurfaceCfg(diffuse_color=(1.0, 0.2, 0.05), roughness=0.95, metallic=0.0),
            physics_material=cube_physics,
        ),
        init_state=RigidObjectCfg.InitialStateCfg(pos=CUBE_BASE_POS.tolist(), rot=(1.0, 0.0, 0.0, 0.0)),
    )
    cube = RigidObject(cfg=cube_cfg)

    plate_physics = sim_utils.RigidBodyMaterialCfg(
        static_friction=1.2, dynamic_friction=0.8, restitution=0.1,
    )
    plate_cfg = RigidObjectCfg(
        prim_path="/World/Plate",
        spawn=sim_utils.CylinderCfg(
            radius=0.04, height=0.015,
            rigid_props=sim_utils.RigidBodyPropertiesCfg(kinematic_enabled=True),
            mass_props=sim_utils.MassPropertiesCfg(mass=0.3),
            collision_props=sim_utils.CollisionPropertiesCfg(contact_offset=0.001, rest_offset=0.0001),
            visual_material=sim_utils.PreviewSurfaceCfg(diffuse_color=(0.1, 0.9, 0.25), roughness=0.3, metallic=0.1),
            physics_material=plate_physics,
        ),
        init_state=RigidObjectCfg.InitialStateCfg(pos=PLATE_BASE_POS.tolist(), rot=(1.0, 0.0, 0.0, 0.0)),
    )
    plate = RigidObject(cfg=plate_cfg)

    wrist_camera_cfg = CameraCfg(
        prim_path="/World/RobotBase/Robot/gripper_link/camera_wrist",
        update_period=0.033, height=480, width=640, data_types=["rgb"],
        spawn=sim_utils.PinholeCameraCfg(focal_length=1.85, horizontal_aperture=3.1, focus_distance=0.1, clipping_range=(0.01, 2.0)),
        offset=CameraCfg.OffsetCfg(pos=(0.015, 0.04, 0.02), rot=(0.0, 0.0, 1.0, 0.0), convention="ros"),
    )
    wrist_camera = Camera(cfg=wrist_camera_cfg)

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
    print("=" * 60)
    print("🤖 ACT 直接推理（无 TCP）")
    print("=" * 60)

    # 加载 ACT 模型
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[ACT] 加载模型: {CHECKPOINT_PATH}")
    
    pretrained_dir = Path(CHECKPOINT_PATH) / "pretrained_model"
    if not pretrained_dir.exists():
        pretrained_dir = Path(CHECKPOINT_PATH)
    
    policy = ACTPolicy.from_pretrained(str(pretrained_dir))
    policy.eval()
    policy.to(device)
    print("[ACT] 模型加载完成")

    # 加载数据集元数据
    print(f"[ACT] 加载数据集: {DATASET_DIR}")
    dataset_metadata = LeRobotDatasetMetadata(Path(DATASET_DIR))
    print(f"[ACT] 数据集: {dataset_metadata.total_episodes} episodes, {dataset_metadata.total_frames} frames")

    # 创建预/后处理器
    preprocess, postprocess = make_pre_post_processors(
        policy.config, 
        dataset_stats=dataset_metadata.stats
    )
    print("[ACT] 预/后处理器初始化完成")

    # 初始化仿真
    sim_cfg = sim_utils.SimulationCfg(
        physx=sim_utils.PhysxCfg(
            solver_type="TGS",
            enable_stabilization=True,
            friction_correlation_distance=0.001,
            friction_offset_threshold=0.001,
        )
    )
    sim = SimulationContext(sim_cfg)
    sim.set_camera_view([1.5, 0.0, 1.5], [0.35, 0.0, 0.3])

    entities, origins = design_scene()
    origins = origins.to(sim.device)
    robot = entities["robot"]
    cube = entities["cube"]
    plate = entities["plate"]
    wrist_camera = entities["wrist_camera"]
    overhead_camera = entities["overhead_camera"]

    sim.reset()

    from pxr import UsdGeom, Gf
    stage = sim.stage
    light_prim = stage.GetPrimAtPath("/World/DiskLight")
    if not light_prim:
        print("[警告] 未找到 DiskLight")
    else:
        randomize_scene_lighting(light_prim)

    sim_dt = sim.get_physics_dt()
    
    # 等待仿真稳定
    for _ in range(200):
        robot.set_joint_position_target(robot.data.joint_pos.clone())
        robot.write_data_to_sim()
        sim.step()
        robot.update(sim_dt)
        wrist_camera.update(dt=sim_dt)
        overhead_camera.update(dt=sim_dt)

    print("\n[推理] 仿真已稳定")
    print(f"[推理] 关节名称: {list(robot.data.joint_names)[:6]}")
    print(f"[推理] 当前状态: {[f'{j:.3f}' for j in robot.data.joint_pos[0].cpu().numpy()[:6]]}")
    print("=" * 60)

    episode = 0
    count = 0
    
    try:
        while sim_app.is_running():
            # 获取观测
            cam1_rgb = wrist_camera.data.output["rgb"][0].cpu().numpy()
            cam2_rgb = overhead_camera.data.output["rgb"][0].cpu().numpy()
            joint_state = robot.data.joint_pos.cpu().numpy()[0][:6].tolist()

            # 构建观测字典（和录制时一致）
            obs = {name: joint_state[i] for i, name in enumerate(JOINT_NAMES)}
            obs["camera1"] = cam1_rgb
            obs["camera2"] = cam2_rgb

            # 构建推理帧
            obs_frame = build_inference_frame(
                observation=obs,
                ds_features=dataset_metadata.features,
                device=device
            )

            # 预处理
            obs_processed = preprocess(obs_frame)

            # 推理
            action = policy.select_action(obs_processed)

            # 后处理
            action = postprocess(action)

            # 转换为机器人动作
            action_dict = make_robot_action(action, dataset_metadata.features)

            # 提取动作列表
            target = [action_dict[name] for name in JOINT_NAMES]

            # 锁定 wrist_roll
            target[4] = -1.57

            # 执行动作
            robot.set_joint_position_target(torch.tensor([[target[i] for i in range(6)]], device=sim.device))

            # 打印状态
            if count % 30 == 0:
                diff = [target[i] - joint_state[i] for i in range(6)]
                print(f"\n[推理] step={count}")
                print(f"  当前状态: {[f'{j:.3f}' for j in joint_state]}")
                print(f"  目标位置: {[f'{a:.3f}' for a in target]}")
                print(f"  差值:     {[f'{d:.3f}' for d in diff]}")

            # 仿真步进
            robot.write_data_to_sim()
            sim.step()
            robot.update(sim_dt)
            wrist_camera.update(dt=sim_dt)
            overhead_camera.update(dt=sim_dt)

            count += 1
            if count % 300 == 0:
                print(f"\n[Step {count}] | Episode: {episode}")

            if count >= args.max_steps:
                episode += 1
                if episode >= args.n_episodes:
                    break
                print(f"\n[Episode {episode}] 完成，重置环境...")
                reset_environment(cube, plate, robot, origins, sim, light_prim)
                count = 0

    except KeyboardInterrupt:
        pass
    finally:
        sim_app.close()
        print(f"\n✅ 推理结束，共完成 {episode} 个 episodes")


if __name__ == "__main__":
    main()

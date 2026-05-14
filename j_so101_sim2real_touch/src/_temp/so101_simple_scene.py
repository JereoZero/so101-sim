"""
SO101 Sim2Real - IsaacLab 场景配置

基于官方 isaac_so_arm101 配置

场景布局：
- 75cm 高的桌子 (50cm × 100cm)
- SO101 机械臂在桌子长边中间
- 夹爪摄像头 (GC0308, RGB only) - 附加到 gripper_link
- 第三视角摄像头 (斜上方39cm)
- 哑光灰色地砖地面
"""

import sys
import argparse
sys.path.insert(0, "/home/jer/ws_issac/thirdparty/IsaacLab/source")
sys.path.insert(0, "/home/jer/ws_issac/thirdparty/isaac_so_arm101/src")

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser(description="SO101 Sim2Real IsaacLab Scene")
AppLauncher.add_app_launcher_args(parser)
args = parser.parse_args()

app_launcher = AppLauncher(args)
sim_app = app_launcher.app

import torch

import isaaclab.sim as sim_utils
from isaaclab.actuators import ImplicitActuatorCfg
from isaaclab.assets import ArticulationCfg, AssetBaseCfg
from isaaclab.scene import InteractiveScene, InteractiveSceneCfg
from isaaclab.sensors.camera import Camera, CameraCfg
from isaaclab.sim import SimulationContext
from isaaclab.sim.spawners.from_files.from_files_cfg import UrdfFileCfg, GroundPlaneCfg
from isaaclab.sim.spawners.shapes.shapes_cfg import CuboidCfg
from isaaclab.utils import configclass

SO101_URDF_PATH = "/home/jer/ws_issac/thirdparty/SO-ARM100/Simulation/SO101/so101_new_calib.urdf"

TABLE_HEIGHT = 0.75
TABLE_LENGTH = 1.0
TABLE_WIDTH = 0.5


@configclass
class SimpleSceneCfg(InteractiveSceneCfg):
    """SO101 场景配置（基于官方 isaac_so_arm101）"""

    num_envs = 1
    env_spacing = 2.0

    table = AssetBaseCfg(
        prim_path="{ENV_REGEX_NS}/Table",
        init_state=AssetBaseCfg.InitialStateCfg(pos=[0.0, 0.0, TABLE_HEIGHT / 2]),
        spawn=CuboidCfg(
            size=(TABLE_LENGTH, TABLE_WIDTH, TABLE_HEIGHT),
            visual_material=sim_utils.PreviewSurfaceCfg(
                diffuse_color=(0.82, 0.71, 0.57),
                metallic=0.0,
                roughness=0.4,
            ),
        ),
    )

    robot = ArticulationCfg(
        prim_path="{ENV_REGEX_NS}/Robot",
        spawn=UrdfFileCfg(
            asset_path=SO101_URDF_PATH,
            fix_base=True,
            replace_cylinders_with_capsules=True,
            activate_contact_sensors=False,
            rigid_props=sim_utils.RigidBodyPropertiesCfg(
                disable_gravity=False,
                max_depenetration_velocity=5.0,
            ),
            articulation_props=sim_utils.ArticulationRootPropertiesCfg(
                enabled_self_collisions=True,
                solver_position_iteration_count=8,
                solver_velocity_iteration_count=0,
            ),
            joint_drive=UrdfFileCfg.JointDriveCfg(
                gains=UrdfFileCfg.JointDriveCfg.PDGainsCfg(stiffness=0, damping=0)
            ),
        ),
        init_state=ArticulationCfg.InitialStateCfg(
            pos=[0.1675, -0.2093, TABLE_HEIGHT],
            rot=(0.7071, 0.0, 0.0, 0.7071),
            joint_pos={
                "shoulder_pan": 0.0,
                "shoulder_lift": 0.0,
                "elbow_flex": -0.0,
                "wrist_flex": 1.57,
                "wrist_roll": -0.0,
                "gripper": 0.0,
            },
            joint_vel={".*": 0.0},
        ),
        actuators={
            "arm": ImplicitActuatorCfg(
                joint_names_expr=["shoulder_.*", "elbow_flex", "wrist_.*"],
                effort_limit_sim=1.9,
                velocity_limit_sim=1.5,
                stiffness={
                    "shoulder_pan": 200.0,
                    "shoulder_lift": 170.0,
                    "elbow_flex": 120.0,
                    "wrist_flex": 80.0,
                    "wrist_roll": 50.0,
                },
                damping={
                    "shoulder_pan": 80.0,
                    "shoulder_lift": 65.0,
                    "elbow_flex": 45.0,
                    "wrist_flex": 30.0,
                    "wrist_roll": 20.0,
                },
            ),
            "gripper": ImplicitActuatorCfg(
                joint_names_expr=["gripper"],
                effort_limit_sim=2.5,
                velocity_limit_sim=1.5,
                stiffness=60.0,
                damping=20.0,
            ),
        },
        soft_joint_pos_limit_factor=0.9,
    )

    wrist_camera = CameraCfg(
        prim_path="{ENV_REGEX_NS}/Robot/gripper_link/wrist_camera",
        update_period=0.033,
        height=480,
        width=640,
        data_types=["rgb"],
        colorize_semantic_segmentation=False,
        offset=CameraCfg.OffsetCfg(
            pos=(0.02, 0.0, 0.03),
            rot=(0.7071, 0.0, 0.7071, 0.0),
            convention="ros",
        ),
        spawn=sim_utils.PinholeCameraCfg(
            focal_length=1.85,
            focus_distance=0.5,
            horizontal_aperture=3.6,
            clipping_range=(0.01, 10.0),
        ),
    )

    third_view_camera = CameraCfg(
        prim_path="/World/ThirdViewCamera",
        update_period=0.033,
        height=480,
        width=640,
        data_types=["rgb", "distance_to_image_plane"],
        colorize_semantic_segmentation=False,
        offset=CameraCfg.OffsetCfg(
            pos=(0.218, 0.359, TABLE_HEIGHT + 0.408),
            rot=(-0.8714, 0.1272, -0.3071, 0.3609),
            convention="world",
        ),
        spawn=sim_utils.PinholeCameraCfg(
            focal_length=3.42,
            focus_distance=0.3,
            horizontal_aperture=13.1,
            clipping_range=(0.05, 20.0),
        ),
    )

    ground = AssetBaseCfg(
        prim_path="/World/GroundPlane",
        spawn=GroundPlaneCfg(
            color=(0.88, 0.85, 0.82),
        ),
    )

    light = AssetBaseCfg(
        prim_path="/World/light",
        spawn=sim_utils.DomeLightCfg(color=(0.75, 0.75, 0.75), intensity=3000.0),
    )


def main():
    """主函数"""
    print("=" * 60)
    print("🚀 启动 SO101 IsaacLab 场景 (基于官方配置)")
    print("=" * 60)

    print("\n[1] 初始化仿真上下文...")
    sim_cfg = sim_utils.SimulationCfg(device=args.device)
    sim = SimulationContext(sim_cfg)
    sim.set_camera_view([1.0, -0.8, 1.2], [0.0, 0.0, TABLE_HEIGHT])
    print("✅ 仿真上下文初始化成功!")

    print("\n[2] 创建场景...")
    scene_cfg = SimpleSceneCfg(num_envs=1, env_spacing=2.0)
    scene = InteractiveScene(scene_cfg)
    print("✅ 场景创建成功!")
    print(f"   桌子: {TABLE_LENGTH*100}cm × {TABLE_WIDTH*100}cm × {TABLE_HEIGHT*100}cm")
    print(f"   机器人位置: 桌子长边中间")
    print(f"   配置来源: 官方 isaac_so_arm101")

    if args.enable_cameras:
        print("\n[3] 摄像头配置...")
        print("   - 夹爪摄像头: 附加到 gripper_link, 640×480 RGB @ 30fps")
        print("   - 第三视角摄像头: 640×480 RGB+深度 @ 30fps")
    else:
        print("\n[3] 跳过摄像头 (使用 --enable_cameras 启用)")

    print("\n[4] 重置仿真...")
    sim.reset()
    print("✅ 仿真重置成功!")

    print("\n[5] 运行仿真循环...")
    sim_dt = sim.get_physics_dt()
    count = 0

    while sim_app.is_running():
        if count % 500 == 0:
            count = 0
            scene.reset()
            print(f"[INFO] 场景已重置 (count={count})")

        scene.write_data_to_sim()
        sim.step()
        count += 1
        scene.update(sim_dt)

        if args.enable_cameras:
            wrist_camera = scene["wrist_camera"]
            third_camera = scene["third_view_camera"]
            if wrist_camera is not None:
                wrist_camera.update(dt=sim_dt)
            if third_camera is not None:
                third_camera.update(dt=sim_dt)

        if count >= 500:
            break

    print("\n[6] 关闭仿真...")
    sim_app.close()

    print("\n" + "=" * 60)
    print("🎉 SO101 场景测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()

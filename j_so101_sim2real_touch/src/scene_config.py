"""
场景配置模块
包含桌子、方块、盘子、摄像头等场景元素的配置
"""

import sys
import torch
import isaaclab.sim as sim_utils
from isaaclab.assets import Articulation, RigidObject, RigidObjectCfg
from isaaclab.sensors.camera import Camera, CameraCfg

sys.path.insert(0, "/home/jer/ws_issac/thirdparty/isaac_so_arm101/src")
from isaac_so_arm101.robots.trs_so101.so_arm101 import SO_ARM101_CFG


def create_ground():
    """创建地面"""
    ground_cfg = sim_utils.GroundPlaneCfg(
        usd_path="/home/jer/isaacsim/Assets/Assets/Isaac/5.1/Isaac/Environments/Grid/default_environment.usd"
    )
    ground_cfg.func("/World/defaultGroundPlane", ground_cfg)


def create_light():
    """创建灯光"""
    light_cfg = sim_utils.DomeLightCfg(intensity=3000.0, color=(0.75, 0.75, 0.75))
    light_cfg.func("/World/Light", light_cfg)


def create_table():
    """创建桌子"""
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
    return RigidObject(cfg=wood_cfg)


def create_cube():
    """创建方块"""
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
    return RigidObject(cfg=cube_cfg)


def create_plate():
    """创建盘子"""
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
    return RigidObject(cfg=plate_cfg)


def create_wrist_camera():
    """创建腕部摄像头（挂在夹爪gripper_link上，朝前拍摄工作区域）"""
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
    return Camera(cfg=wrist_camera_cfg)


def create_overhead_camera():
    """创建第三视角摄像头（通过 CameraTripod Xform 定位，offset 只设旋转）"""
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
    return Camera(cfg=overhead_camera_cfg)


def design_scene():
    """设计完整场景（包含机器人）"""
    create_ground()
    create_light()

    wood_table = create_table()

    origins = [[0.5, 0.0, 0.75]]
    sim_utils.create_prim("/World/RobotBase", "Xform", translation=origins[0])

    robot_cfg = SO_ARM101_CFG.copy()
    robot_cfg.prim_path = "/World/RobotBase/Robot"
    robot = Articulation(cfg=robot_cfg)

    cube = create_cube()
    plate = create_plate()

    return {
        "robot": robot,
        "wood": wood_table,
        "cube": cube,
        "plate": plate,
    }, torch.tensor(origins)

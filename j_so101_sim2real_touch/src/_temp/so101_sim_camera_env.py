"""
SO101 带摄像头的仿真环境

摄像头配置:
- Wrist (腕部): GC0308, 128x128, 5fps, 焦距1.85mm, FOV 80°
- Overhead (俯视): GC2083, 128x128, 5fps, 焦距3.42mm, FOV 125°
"""

import sys
sys.path.insert(0, "/home/jer/ws_issac/thirdparty/isaac_so_arm101/src")

import torch
from isaaclab.app import AppLauncher

# 解析参数
import argparse

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser()
AppLauncher.add_app_launcher_args(parser)
args = parser.parse_args()

# 启动应用
app_launcher = AppLauncher(args)
sim_app = app_launcher.app

import isaaclab.sim as sim_utils
from isaaclab.assets import Articulation, RigidObject, RigidObjectCfg
from isaaclab.scene import InteractiveScene, InteractiveSceneCfg
from isaaclab.sensors import Camera, CameraCfg
from isaaclab.utils import configclass

from isaac_so_arm101.robots.trs_so101.so_arm101 import SO_ARM101_CFG


@configclass
class SO101CameraSceneCfg(InteractiveSceneCfg):
    """带摄像头的场景配置"""
    num_envs: int = 1
    env_spacing: float = 2.0

    # 机器人
    robot: Articulation = SO_ARM101_CFG.replace(prim_path="{ENV_REGEX_NS}/Robot")

    # 桌子
    table = RigidObjectCfg(
        prim_path="{ENV_REGEX_NS}/Table",
        spawn=sim_utils.CuboidCfg(
            size=(1.0, 1.0, 0.75),
            rigid_props=sim_utils.RigidBodyPropertiesCfg(kinematic_enabled=True),
            mass_props=sim_utils.MassPropertiesCfg(mass=5.0),
            visual_material=sim_utils.PreviewSurfaceCfg(
                diffuse_color=(0.82, 0.71, 0.57),  # 浅橡木色
                roughness=0.4,
                metallic=0.0,
            ),
        ),
        init_state=RigidObjectCfg.InitialStateCfg(
            pos=(0.5, 0.0, 0.375),
        ),
    )

    # 方块
    cube = RigidObjectCfg(
        prim_path="{ENV_REGEX_NS}/Cube",
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
        ),
    )

    # 盘子
    plate = RigidObjectCfg(
        prim_path="{ENV_REGEX_NS}/Plate",
        spawn=sim_utils.CylinderCfg(
            radius=0.04,
            height=0.015,
            rigid_props=sim_utils.RigidBodyPropertiesCfg(),
            mass_props=sim_utils.MassPropertiesCfg(mass=0.1),
            visual_material=sim_utils.PreviewSurfaceCfg(
                diffuse_color=(0.2, 0.8, 0.4),
                roughness=0.3,
                metallic=0.1,
            ),
        ),
        init_state=RigidObjectCfg.InitialStateCfg(
            pos=(0.76, 0.0, 0.758),
        ),
    )


def create_cameras(scene: InteractiveScene):
    """创建摄像头"""
    
    # ========== 腕部摄像头 (Wrist Camera) ==========
    # 硬件: GC0308, 焦距1.85mm, FOV 80°
    # 位置: 夹爪侧面, 左侧4cm, 上方3cm, 向下看
    wrist_camera_cfg = CameraCfg(
        prim_path="{ENV_REGEX_NS}/Robot/gripper_link/camera_wrist",
        offset=CameraCfg.OffsetCfg(
            pos=(0.0, 0.04, 0.03),  # 左侧4cm, 上方3cm
            rot=(0.259, 0.0, 0.0, 0.966),  # 俯仰-30度 (向下看)
            convention="ros",
        ),
        data_types=["rgb"],
        spawn=sim_utils.PinholeCameraCfg(
            focal_length=1.85,  # mm
            horizontal_aperture=3.1,  # mm (80° FOV)
            focus_distance=0.5,  # m
            clipping_range=(0.01, 10.0),  # m
        ),
        width=128,
        height=128,
        update_period=0.2,  # 5 fps
    )
    
    # ========== 俯视摄像头 (Overhead Camera) ==========
    # 硬件: GC2083, 焦距3.42mm, FOV 125°
    # 位置: 桌面正上方37cm (桌面高度0.75m + 0.37m = 1.12m)
    overhead_camera_cfg = CameraCfg(
        prim_path="{ENV_REGEX_NS}/overhead_camera",
        offset=CameraCfg.OffsetCfg(
            pos=(0.5, 0.0, 1.12),  # 桌面中心上方1.12m
            rot=(0.5, 0.5, -0.5, -0.5),  # 向下看
            convention="ros",
        ),
        data_types=["rgb"],
        spawn=sim_utils.PinholeCameraCfg(
            focal_length=3.42,  # mm
            horizontal_aperture=13.1,  # mm (125° FOV)
            focus_distance=0.37,  # m (桌面距离)
            clipping_range=(0.01, 2.0),  # m
        ),
        width=128,
        height=128,
        update_period=0.2,  # 5 fps
    )
    
    # 创建摄像头
    wrist_camera = Camera(cfg=wrist_camera_cfg)
    overhead_camera = Camera(cfg=overhead_camera_cfg)
    
    # 添加到场景
    scene.add_sensor(wrist_camera, "camera_wrist")
    scene.add_sensor(overhead_camera, "camera_overhead")
    
    return wrist_camera, overhead_camera


def main():
    """主函数 - 测试带摄像头的环境"""
    from isaaclab.sim import SimulationContext
    
    # 创建场景配置
    scene_cfg = SO101CameraSceneCfg()
    
    # 创建场景
    print("[1] 创建场景...")
    scene = InteractiveScene(scene_cfg)
    
    # 创建摄像头
    print("[2] 创建摄像头...")
    wrist_cam, overhead_cam = create_cameras(scene)
    
    # 获取仿真上下文
    sim = SimulationContext.instance()
    
    # 重置场景
    print("[3] 重置场景...")
    scene.reset()
    
    # 主循环
    print("[4] 开始仿真循环...")
    print("    按 Ctrl+C 退出")
    
    count = 0
    while sim_app.is_running():
        # 执行仿真步
        scene.write_data_to_sim()
        sim.step()
        scene.update(1.0 / 60.0)
        
        # 每30帧打印一次摄像头信息
        count += 1
        if count % 30 == 0:
            # 获取摄像头数据
            wrist_rgb = wrist_cam.data.output.get("rgb")
            overhead_rgb = overhead_cam.data.output.get("rgb")
            
            if wrist_rgb is not None:
                print(f"[Frame {count}] Wrist camera: {wrist_rgb.shape}")
            if overhead_rgb is not None:
                print(f"[Frame {count}] Overhead camera: {overhead_rgb.shape}")
    
    # 清理
    print("[5] 关闭仿真...")
    scene.close()
    sim_app.close()


if __name__ == "__main__":
    main()

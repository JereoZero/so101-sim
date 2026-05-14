"""
SO101 仿真场景 - IsaacLab 环境

运行命令：
cd /home/jer/ws_issac/thirdparty/IsaacLab
conda activate isaaclab
export ISAACSIM_ASSETS_PATH=~/isaacsim/Assets/Assets/Isaac/5.1
./isaaclab.sh -p /home/jer/ws_issac/ws/j_so101_sim2real_touch/src/so101_sim_scene.py

说明：此脚本只测试仿真场景，不连接真机
"""

import sys
import argparse

sys.path.insert(0, "/home/jer/ws_issac/thirdparty/isaac_so_arm101/src")

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser()
AppLauncher.add_app_launcher_args(parser)
args = parser.parse_args()

app_launcher = AppLauncher(args)
sim_app = app_launcher.app

import torch
import isaaclab.sim as sim_utils
from isaaclab.assets import Articulation, RigidObject, RigidObjectCfg
from isaaclab.sim import SimulationContext

from isaac_so_arm101.robots.trs_so101.so_arm101 import SO_ARM101_CFG


def design_scene():
    """设计场景"""
    ground_cfg = sim_utils.GroundPlaneCfg()
    ground_cfg.func("/World/defaultGroundPlane", ground_cfg)

    light_cfg = sim_utils.DomeLightCfg(intensity=3000.0, color=(0.75, 0.75, 0.75))
    light_cfg.func("/World/Light", light_cfg)

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

    cube_cfg = RigidObjectCfg(
        prim_path="/World/Cube",
        spawn=sim_utils.CuboidCfg(
            size=(0.035, 0.035, 0.035),
            rigid_props=sim_utils.RigidBodyPropertiesCfg(),
            mass_props=sim_utils.MassPropertiesCfg(mass=0.0019),
            collision_props=sim_utils.CollisionPropertiesCfg(),
            visual_material=sim_utils.PreviewSurfaceCfg(
                diffuse_color=(1.0, 0.4, 0.2),
                roughness=0.8,
                metallic=0.0,
            ),
        ),
        init_state=RigidObjectCfg.InitialStateCfg(
            pos=(0.67, 0.0, 0.768),
            rot=(1.0, 0.0, 0.0, 0.0),
        ),
    )
    cube = RigidObject(cfg=cube_cfg)

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
        ),
        init_state=RigidObjectCfg.InitialStateCfg(
            pos=(0.76, 0.0, 0.758),
            rot=(1.0, 0.0, 0.0, 0.0),
        ),
    )
    plate = RigidObject(cfg=plate_cfg)

    return {"robot": robot, "wood": wood_table, "cube": cube, "plate": plate}, torch.tensor(origins)


def main():
    """主函数"""
    print("=" * 80)
    print("🚀 SO101 仿真场景测试")
    print("=" * 80)

    print("\n[1] 初始化仿真上下文...")
    sim_cfg = sim_utils.SimulationCfg()
    sim = SimulationContext(sim_cfg)
    sim.set_camera_view([1.5, 0.0, 1.5], [0.35, 0.0, 0.3])
    print("✅ 仿真上下文初始化成功!")

    print("\n[2] 设计场景...")
    entities, origins = design_scene()
    origins = origins.to(sim.device)
    robot = entities["robot"]
    print("✅ 场景设计完成!")
    print("   - 木桌: 100cm x 50cm x 75cm, kinematic固定")
    print("   - 方块: 3.5cm, 重量1.9g")
    print("   - 盘子: 直径8cm, 重量100g")

    print("\n[3] 重置仿真...")
    sim.reset()
    print("✅ 仿真重置成功!")

    print("\n[4] 运行仿真循环...")
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

            robot.write_data_to_sim()
            sim.step()
            robot.update(sim_dt)

            count += 1
            if count % 30 == 0:
                print(f"Step {count} 完成")

    except KeyboardInterrupt:
        print("\n用户中断")

    print("\n[5] 关闭仿真...")
    sim_app.close()

    print("\n" + "=" * 80)
    print("✅ 仿真结束")
    print("=" * 80)


if __name__ == "__main__":
    main()

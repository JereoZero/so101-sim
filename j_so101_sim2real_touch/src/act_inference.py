"""
SO101 ACT 模型推理 - 在 Isaac Sim 中测试训练好的模型

运行命令：
cd /home/jer/ws_issac/thirdparty/IsaacLab
conda activate isaaclab
export ISAACSIM_ASSETS_PATH=~/isaacsim/Assets/Assets/Isaac/5.1
./isaaclab.sh -p /home/jer/ws_issac/ws/j_so101_sim2real_touch/src/act_inference.py --enable_cameras

模型路径：
/home/jer/ws_issac/ws/j_so101_sim2real_touch/models/act_sim_v0/checkpoints/
"""

import sys
import argparse
import json

sys.path.insert(0, "/home/jer/ws_issac/thirdparty/isaac_so_arm101/src")
sys.path.insert(0, "/home/jer/ws_issac/ws/j_so101_sim2real_touch/src")
sys.path.insert(0, "/home/jer/ws/workspace/projects/lerobot/src")

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser()
AppLauncher.add_app_launcher_args(parser)
parser.add_argument("--checkpoint", type=str,
    default="/home/jer/ws_issac/ws/j_so101_sim2real_touch/models/act_sim_v0/checkpoints/final",
    help="ACT 模型 checkpoint 路径")
parser.add_argument("--n_episodes", type=int, default=20, help="测试 episode 数量")
parser.add_argument("--max_steps", type=int, default=300, help="每个 episode 最大步数")
args = parser.parse_args()

app_launcher = AppLauncher(args)
sim_app = app_launcher.app

import torch
import torch.nn.functional as F
import numpy as np
import cv2
import time
import isaaclab.sim as sim_utils
from isaaclab.sim import SimulationContext
from isaaclab.sensors.camera import Camera, CameraCfg
from isaaclab.assets import Articulation, RigidObject, RigidObjectCfg
from isaac_so_arm101.robots.trs_so101.so_arm101 import SO_ARM101_CFG
from physics_config import configure_gripper_physics
from robot_config import clip_joint_angles
from tcp_server import TCPServer

# 物体初始位置
PLATE_BASE_POS = np.array([0.79, 0.0, 0.758])
CUBE_BASE_POS = np.array([0.74, 0.0, 0.768])
ROBOT_ORIGINS = np.array([0.5, 0.0, 0.75])

# ACT 推理参数
CHUNK_SIZE = 100
N_ACTION_STEPS = 1
FPS = 30
DT = 1.0 / FPS

# 关节名称（与训练时一致）
JOINT_NAMES = ["shoulder_pan.pos", "shoulder_lift.pos", "elbow_flex.pos",
               "wrist_flex.pos", "wrist_roll.pos", "gripper.pos"]


def preprocess_image(rgb_np, device):
    """预处理图像：resize, normalize, 转 tensor"""
    img = cv2.resize(rgb_np, (640, 480))
    img_tensor = torch.from_numpy(img).permute(2, 0, 1).float().to(device)
    img_tensor = img_tensor / 255.0
    # ImageNet 归一化
    mean = torch.tensor([0.485, 0.456, 0.406], device=device).view(3, 1, 1)
    std = torch.tensor([0.229, 0.224, 0.225], device=device).view(3, 1, 1)
    img_tensor = (img_tensor - mean) / std
    return img_tensor.unsqueeze(0)


def reset_environment(cube, plate, robot, origins, sim, light_prim=None):
    """重置环境"""
    root_state = robot.data.default_root_state.clone()
    root_state[:, :3] += origins
    robot.write_root_pose_to_sim(root_state[:, :7])
    robot.write_root_velocity_to_sim(root_state[:, 7:])
    robot.write_joint_state_to_sim(robot.data.default_joint_pos.clone(), robot.data.default_joint_vel.clone())
    robot.reset()
    
    if light_prim:
        intensity = np.random.uniform(40000.0, 60000.0)
        color_r = np.random.uniform(0.95, 1.0)
        color_g = np.random.uniform(0.93, 1.0)
        color_b = np.random.uniform(0.90, 1.0)
        light_prim.GetAttribute("inputs:intensity").Set(intensity)
        light_prim.GetAttribute("inputs:color").Set((color_r, color_g, color_b))
    
    # 方块随机位置
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
    
    plate_offset_x = np.random.uniform(-0.05, 0.05)
    plate_offset_y = np.random.uniform(-0.05, 0.05)
    new_plate_pos = PLATE_BASE_POS + np.array([plate_offset_x, plate_offset_y, 0.0])
    plate_state = plate.data.default_root_state.clone()
    plate_state[:, :3] = torch.tensor([[new_plate_pos[0], new_plate_pos[1], new_plate_pos[2]]], device=sim.device)
    plate.write_root_pose_to_sim(plate_state[:, :7])
    plate.write_root_velocity_to_sim(torch.zeros_like(plate_state[:, 7:]))


def design_scene():
    """设计场景"""
    ground_cfg = sim_utils.GroundPlaneCfg(
        usd_path="/home/jer/isaacsim/Assets/Assets/Isaac/5.1/Isaac/Environments/Grid/default_environment.usd"
    )
    ground_cfg.func("/World/defaultGroundPlane", ground_cfg)

    light_cfg = sim_utils.CylinderLightCfg(
        intensity=50000.0, color=(1.0, 1.0, 1.0), length=0.3, radius=0.15,
    )
    light_cfg.func("/World/DiskLight", light_cfg, translation=(0.7, 0.0, 2.5))

    wood_physics = sim_utils.RigidBodyMaterialCfg(static_friction=0.8, dynamic_friction=0.6, restitution=0.1)
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

    cube_physics = sim_utils.RigidBodyMaterialCfg(static_friction=0.8, dynamic_friction=0.6, restitution=0.1)
    cube_cfg = RigidObjectCfg(
        prim_path="/World/Cube",
        spawn=sim_utils.CuboidCfg(
            size=(0.035, 0.035, 0.035),
            rigid_props=sim_utils.RigidBodyPropertiesCfg(max_linear_velocity=100.0, max_angular_velocity=100.0, max_depenetration_velocity=10.0),
            mass_props=sim_utils.MassPropertiesCfg(mass=0.05),
            collision_props=sim_utils.CollisionPropertiesCfg(contact_offset=0.001, rest_offset=0.0001),
            visual_material=sim_utils.PreviewSurfaceCfg(diffuse_color=(1.0, 0.2, 0.05), roughness=0.95, metallic=0.0),
            physics_material=cube_physics,
        ),
        init_state=RigidObjectCfg.InitialStateCfg(pos=CUBE_BASE_POS.tolist(), rot=(1.0, 0.0, 0.0, 0.0)),
    )
    cube = RigidObject(cfg=cube_cfg)

    plate_physics = sim_utils.RigidBodyMaterialCfg(static_friction=1.2, dynamic_friction=0.8, restitution=0.1)
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


class ACTInference:
    """ACT 模型推理器"""
    
    def __init__(self, checkpoint_path, device="cuda"):
        self.device = device
        self.action_queue = []
        
        print(f"[ACT] 加载模型: {checkpoint_path}")
        
        # 加载 LeRobot ACT 模型
        from lerobot.policies.act.modeling_act import ACTPolicy, ACTPolicyConfig
        from lerobot.policies.act.configuration_act import ACTConfig
        
        # 从 checkpoint 加载配置
        import os
        config_path = os.path.join(checkpoint_path, "config.json")
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config_dict = json.load(f)
            
            policy_config = ACTConfig(
                chunk_size=100,
                n_action_steps=30,
                dim_model=512,
                n_encoder_layers=4,
                n_heads=8,
                use_vae=True,
                latent_dim=32,
                dropout=0.1,
                kl_weight=10.0,
                vision_backbone="resnet18",
                pretrained_backbone_weights="ResNet18_Weights.IMAGENET1K_V1",
                temporal_ensemble_coeff=None,
                use_amp=True,
                device=device,
            )
            
            self.policy = ACTPolicy(policy_config)
            
            # 加载权重
            import glob
            ckpt_files = glob.glob(os.path.join(checkpoint_path, "*.pt"))
            if ckpt_files:
                state_dict = torch.load(ckpt_files[0], map_location=device)
                if "state_dict" in state_dict:
                    state_dict = state_dict["state_dict"]
                self.policy.load_state_dict(state_dict, strict=False)
                print(f"[ACT] 权重加载成功: {ckpt_files[0]}")
            else:
                print("[警告] 未找到权重文件")
        else:
            print(f"[警告] 未找到配置文件: {config_path}")
            return
        
        self.policy.eval()
        self.policy.to(device)
        print("[ACT] 模型加载完成，推理就绪")
    
    def predict_action_chunk(self, state, cam1_img, cam2_img):
        """预测一组未来动作"""
        with torch.no_grad():
            # 预处理
            state_tensor = torch.tensor(state, dtype=torch.float32, device=self.device).unsqueeze(0)
            cam1_tensor = preprocess_image(cam1_img, self.device)
            cam2_tensor = preprocess_image(cam2_img, self.device)
            
            batch = {
                "observation.state": state_tensor,
                "observation.images.camera1": cam1_tensor,
                "observation.images.camera2": cam2_tensor,
            }
            
            actions = self.policy.predict_action_chunk(batch)
            actions_np = actions.cpu().numpy().squeeze(0)
        
        return actions_np
    
    def get_action(self, state, cam1_img, cam2_img):
        """获取当前步动作（管理动作队列）"""
        if len(self.action_queue) == 0:
            actions = self.predict_action_chunk(state, cam1_img, cam2_img)
            self.action_queue = actions.tolist()
        
        if len(self.action_queue) > 0:
            action = self.action_queue.pop(0)
            return action
        return state


def main():
    """主函数"""
    print("=" * 60)
    print("🚀 SO101 ACT 模型推理 - Isaac Sim 测试")
    print("=" * 60)
    
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
    
    configure_gripper_physics()
    
    # 初始化 ACT 推理器
    inference = ACTInference(args.checkpoint, device=sim.device)
    
    # 设置键盘控制
    import carb
    import omni.kit.app
    
    manual_mode = False
    
    def setup_keyboard():
        nonlocal manual_mode
        def kb_cb(event):
            nonlocal manual_mode
            if event.type != carb.input.KeyboardEventType.KEY_PRESS:
                return
            key = event.input
            if key == carb.input.KeyboardInput.M:
                manual_mode = not manual_mode
                print(f"\n[模式] {'手动' if manual_mode else '自动推理'}")
            elif key == carb.input.KeyboardInput.R:
                print("\n[重置] 环境已重置...")
                reset_environment(cube, plate, robot, origins, sim, light_prim)
        
        app_interface = omni.kit.app.get_app_interface()
        carb.input.acquire_input_interface().subscribe_to_keyboard_events(None, kb_cb)
        print("[快捷键] M=切换手动/自动 | R=重置环境 | ESC=退出")
    
    setup_keyboard()
    
    sim_dt = sim.get_physics_dt()
    count = 0
    episode = 0
    step_in_episode = 0
    total_success = 0
    
    try:
        while sim_app.is_running():
            robot.set_joint_position_target(robot.data.joint_pos.clone())
            robot.write_data_to_sim()
            sim.step()
            robot.update(sim_dt)
            
            wrist_camera.update(dt=sim_dt)
            overhead_camera.update(dt=sim_dt)
            
            if not manual_mode and inference.policy is not None:
                cam1_rgb = wrist_camera.data.output["rgb"][0].cpu().numpy()
                cam2_rgb = overhead_camera.data.output["rgb"][0].cpu().numpy()
                joint_state = robot.data.joint_pos.cpu().numpy()[0].tolist()
                
                action = inference.get_action(joint_state, cam1_rgb, cam2_rgb)
                action_clipped = clip_joint_angles(action)
                
                robot.set_joint_position_target(
                    torch.tensor([[action_clipped[i] for i in range(6)]], device=sim.device)
                )
                
                step_in_episode += 1
                
                if step_in_episode >= args.max_steps:
                    episode += 1
                    step_in_episode = 0
                    inference.action_queue = []
                    print(f"\n[Episode {episode}] 完成，重置环境...")
                    reset_environment(cube, plate, robot, origins, sim, light_prim)
            
            count += 1
            if count % 300 == 0:
                mode = "自动推理" if not manual_mode else "手动"
                print(f"[Step {count}] | 模式: {mode} | Episode: {episode}")
    
    except KeyboardInterrupt:
        pass
    finally:
        sim_app.close()
        print(f"✅ 推理结束，共完成 {episode} 个 episodes")


if __name__ == "__main__":
    main()

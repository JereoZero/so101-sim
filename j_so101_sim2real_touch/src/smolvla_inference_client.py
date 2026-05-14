"""
SmolVLA 推理客户端 - 运行在 Isaac Sim 环境中

连接 SmolVLA 推理服务器，发送图像和关节状态，接收并执行动作

运行命令：
cd /home/jer/ws_issac/thirdparty/IsaacLab
conda activate isaaclab
export ISAACSIM_ASSETS_PATH=~/isaacsim/Assets/Assets/Isaac/5.1
./isaaclab.sh -p /home/jer/ws_issac/ws/j_so101_sim2real_touch/src/smolvla_inference_client.py --enable_cameras
"""

import sys
import argparse
import socket
import json
import cv2
import numpy as np
import base64
import time

sys.path.insert(0, "/home/jer/ws_issac/thirdparty/isaac_so_arm101/src")
sys.path.insert(0, "/home/jer/ws_issac/ws/j_so101_sim2real_touch/src")

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser()
AppLauncher.add_app_launcher_args(parser)
parser.add_argument("--server_ip", type=str, default="127.0.0.1")
parser.add_argument("--server_port", type=int, default=9877)
parser.add_argument("--n_episodes", type=int, default=20)
parser.add_argument("--max_steps", type=int, default=1800)
args = parser.parse_args()

app_launcher = AppLauncher(args)
sim_app = app_launcher.app

import torch
import isaaclab.sim as sim_utils
from isaaclab.sim import SimulationContext
from isaaclab.sensors.camera import Camera, CameraCfg
from isaaclab.assets import Articulation, RigidObject, RigidObjectCfg
from isaac_so_arm101.robots.trs_so101.so_arm101 import SO_ARM101_CFG
from physics_config import configure_gripper_physics
from robot_config import clip_joint_angles

PLATE_BASE_POS = np.array([0.79, 0.0, 0.758])
CUBE_BASE_POS = np.array([0.74, 0.0, 0.768])
ROBOT_ORIGINS = np.array([0.5, 0.0, 0.75])

FPS = 30
DT = 1.0 / FPS


def encode_image(rgb_np):
    """编码图像为 base64"""
    _, buf = cv2.imencode('.png', cv2.cvtColor(rgb_np, cv2.COLOR_RGB2BGR))
    return base64.b64encode(buf).decode('utf-8')


def reset_environment(cube, plate, robot, origins, sim, light_prim=None):
    """重置环境"""
    root_state = robot.data.default_root_state.clone()
    root_state[:, :3] += origins
    
    init_pos = robot.data.default_joint_pos.clone()
    joint_names = list(robot.data.joint_names)
    if "wrist_roll" in joint_names:
        idx = joint_names.index("wrist_roll")
        init_pos[0, idx] = -1.57
    
    robot.write_root_pose_to_sim(root_state[:, :7])
    robot.write_root_velocity_to_sim(root_state[:, 7:])
    robot.write_joint_state_to_sim(init_pos, torch.zeros_like(robot.data.default_joint_vel))
    robot.reset()
    
    if light_prim:
        intensity = np.random.uniform(40000.0, 60000.0)
        color_r = np.random.uniform(0.95, 1.0)
        color_g = np.random.uniform(0.93, 1.0)
        color_b = np.random.uniform(0.90, 1.0)
        light_prim.GetAttribute("inputs:intensity").Set(intensity)
        light_prim.GetAttribute("inputs:color").Set((color_r, color_g, color_b))
    
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

    light_cfg = sim_utils.CylinderLightCfg(intensity=50000.0, color=(1.0, 1.0, 1.0), length=0.3, radius=0.15)
    light_cfg.func("/World/DiskLight", light_cfg, translation=(0.7, 0.0, 2.5))

    wood_physics = sim_utils.RigidBodyMaterialCfg(static_friction=0.8, dynamic_friction=0.6, restitution=0.1)
    wood_cfg = RigidObjectCfg(
        prim_path="/World/WoodTable",
        spawn=sim_utils.CuboidCfg(size=(1.0, 1.0, 0.75), rigid_props=sim_utils.RigidBodyPropertiesCfg(kinematic_enabled=True), mass_props=sim_utils.MassPropertiesCfg(mass=5.0), collision_props=sim_utils.CollisionPropertiesCfg(), visual_material=sim_utils.PreviewSurfaceCfg(diffuse_color=(0.6, 0.4, 0.2), roughness=0.7, metallic=0.0), physics_material=wood_physics),
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
        spawn=sim_utils.CuboidCfg(size=(0.035, 0.035, 0.035), rigid_props=sim_utils.RigidBodyPropertiesCfg(max_linear_velocity=100.0, max_angular_velocity=100.0, max_depenetration_velocity=10.0), mass_props=sim_utils.MassPropertiesCfg(mass=0.05), collision_props=sim_utils.CollisionPropertiesCfg(contact_offset=0.001, rest_offset=0.0001), visual_material=sim_utils.PreviewSurfaceCfg(diffuse_color=(1.0, 0.2, 0.05), roughness=0.95, metallic=0.0), physics_material=cube_physics),
        init_state=RigidObjectCfg.InitialStateCfg(pos=CUBE_BASE_POS.tolist(), rot=(1.0, 0.0, 0.0, 0.0)),
    )
    cube = RigidObject(cfg=cube_cfg)

    plate_physics = sim_utils.RigidBodyMaterialCfg(static_friction=1.2, dynamic_friction=0.8, restitution=0.1)
    plate_cfg = RigidObjectCfg(
        prim_path="/World/Plate",
        spawn=sim_utils.CylinderCfg(radius=0.04, height=0.015, rigid_props=sim_utils.RigidBodyPropertiesCfg(kinematic_enabled=True), mass_props=sim_utils.MassPropertiesCfg(mass=0.3), collision_props=sim_utils.CollisionPropertiesCfg(contact_offset=0.001, rest_offset=0.0001), visual_material=sim_utils.PreviewSurfaceCfg(diffuse_color=(0.1, 0.9, 0.25), roughness=0.3, metallic=0.1), physics_material=plate_physics),
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

    return {"robot": robot, "cube": cube, "plate": plate, "wrist_camera": wrist_camera, "overhead_camera": overhead_camera}, torch.tensor(origins)


class SmolVLAClient:
    def __init__(self, server_ip, server_port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((server_ip, server_port))
        self.sock.settimeout(5.0)
        print(f"[SmolVLA客户端] 已连接推理服务器 {server_ip}:{server_port}")
    
    def get_action(self, state, cam1_np, cam2_np):
        cam1_b64 = encode_image(cam1_np)
        cam2_b64 = encode_image(cam2_np)
        
        msg = json.dumps({
            "state": state,
            "cam1": cam1_b64,
            "cam2": cam2_b64,
        }) + "\n"
        
        self.sock.sendall(msg.encode('utf-8'))
        
        buffer = ""
        while "\n" not in buffer:
            data = self.sock.recv(4096)
            if not data:
                raise ConnectionError("服务器断开")
            buffer += data.decode('utf-8')
        
        response = json.loads(buffer.split("\n")[0])
        return response["action"]
    
    def close(self):
        self.sock.close()


def main():
    print("=" * 60)
    print("🚀 SO101 SmolVLA 模型推理 - Isaac Sim 客户端")
    print("=" * 60)
    
    sim_cfg = sim_utils.SimulationCfg(physx=sim_utils.PhysxCfg(solver_type="TGS", enable_stabilization=True))
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
    
    sim_dt = sim.get_physics_dt()
    
    from pxr import UsdGeom, Gf, UsdPhysics
    stage = sim.stage
    light_prim = stage.GetPrimAtPath("/World/DiskLight")
    
    configure_gripper_physics()
    
    print("\n" + "="*60)
    print("[关节驱动] 检查并修复配置...")
    
    robot_prim_path = "/World/RobotBase/Robot"
    robot_prim = stage.GetPrimAtPath(robot_prim_path)
    
    try:
        def find_all_joints(prim, depth=0):
            joints = []
            for child in prim.GetAllChildren():
                if child.GetTypeName() == "PhysicsRevoluteJoint":
                    joints.append(child)
                joints.extend(find_all_joints(child, depth+1))
            return joints
        
        all_joints = find_all_joints(robot_prim)
        print(f"[关节驱动] 找到 {len(all_joints)} 个关节")
        
        for joint_prim in all_joints:
            joint_name = joint_prim.GetName()
            
            drive_api = UsdPhysics.DriveAPI(joint_prim, "angular")
            
            if drive_api:
                drive_api.GetStiffnessAttr().Set(1000.0)
                drive_api.GetDampingAttr().Set(100.0)
                drive_api.GetMaxForceAttr().Set(50.0)
                
                print(f"[关节驱动] {joint_name}: stiffness=1000, damping=100, max_force=50")
            else:
                print(f"[关节驱动] ⚠ {joint_name} 未找到 DriveAPI")
        
        print("[关节驱动] ✅ 关节驱动参数已强制设置")
    except Exception as e:
        print(f"[关节驱动] ❌ 设置失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("="*60 + "\n")
    
    for _ in range(200):
        init_pos = robot.data.joint_pos.clone()
        wf_idx = list(robot.data.joint_names).index("wrist_flex")
        wr_idx = list(robot.data.joint_names).index("wrist_roll")
        init_pos[0, wf_idx] = 1.57
        init_pos[0, wr_idx] = -1.57
        robot.set_joint_position_target(init_pos)
        robot.write_data_to_sim()
        sim.step()
        robot.update(sim_dt)
    
    print("[连接] 正在连接 SmolVLA 推理服务器...")
    time.sleep(2)
    client = SmolVLAClient(args.server_ip, args.server_port)
    
    import carb
    import omni.kit.app
    
    manual_mode = False
    
    cam1_rgb = wrist_camera.data.output["rgb"][0].cpu().numpy()
    cam2_rgb = overhead_camera.data.output["rgb"][0].cpu().numpy()
    print(f"\n[摄像头] 腕部摄像头: {cam1_rgb.shape}, 均值: {cam1_rgb.mean():.1f}")
    print(f"[摄像头] 第三视角:  {cam2_rgb.shape}, 均值: {cam2_rgb.mean():.1f}")
    if cam1_rgb.mean() > 10 and cam2_rgb.mean() > 10:
        print("[摄像头] ✅ 摄像头输入正常")
    else:
        print("[摄像头] ❌ 摄像头可能未正常捕获数据！")
    
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
    
    init_target = robot.data.joint_pos.clone()
    robot.set_joint_position_target(init_target)
    robot.write_data_to_sim()
    sim.step()
    robot.update(sim_dt)
    
    for _ in range(100):
        robot.set_joint_position_target(robot.data.joint_pos.clone())
        robot.write_data_to_sim()
        sim.step()
        robot.update(sim_dt)
    
    manual_mode = False
    
    joint_names = robot.data.joint_names
    print(f"\n[推理] 仿真已稳定")
    print(f"[推理] 关节名称: {joint_names}")
    print(f"[推理] 当前关节状态: {[f'{j:.3f}' for j in robot.data.joint_pos[0].cpu().numpy()[:6]]}")
    print("=" * 60)
    
    # Chunk 队列管理 - 30Hz推理 + receding horizon
    import collections
    CHUNK_SIZE = 50  # 每次取前50步
    INFERENCE_INTERVAL = 1  # 每帧都推理（30Hz）
    
    action_queue = collections.deque()
    inference_count = 0
    frame_count = 0
    
    try:
        while sim_app.is_running():
            if not manual_mode:
                frame_count += 1
                
                # 每3帧推理一次，新推理到达后替换旧队列
                if len(action_queue) == 0 or frame_count % INFERENCE_INTERVAL == 0:
                    try:
                        cam1_rgb = wrist_camera.data.output["rgb"][0].cpu().numpy()
                        cam2_rgb = overhead_camera.data.output["rgb"][0].cpu().numpy()
                        joint_state = robot.data.joint_pos.cpu().numpy()[0].tolist()
                        
                        action_chunk = client.get_action(joint_state, cam1_rgb, cam2_rgb)
                        # 新推理到达，替换整个队列
                        if len(action_chunk) > 6:
                            chunk_actions = []
                            for i in range(0, len(action_chunk), 6):
                                chunk_actions.append(action_chunk[i:i+6])
                            action_queue = collections.deque(chunk_actions[:CHUNK_SIZE])
                        else:
                            action_queue = collections.deque([action_chunk])
                        
                        inference_count += 1
                        if inference_count % 30 == 0:
                            print(f"[推理] inference={inference_count}, step={count}, chunk_size={len(action_queue)}")
                    except Exception as e:
                        print(f"[错误] 推理失败: {e}")
                        if inference_count == 0:
                            continue
                
                # 从队列中取出动作执行
                if len(action_queue) > 0:
                    action_clipped = clip_joint_angles(action_queue.popleft())
                    
                    joint_names_list = list(robot.data.joint_names)
                    wr_idx = joint_names_list.index("wrist_roll")
                    action_clipped[wr_idx] = -1.57
                    
                    target = torch.tensor([[action_clipped[i] for i in range(6)]], device=sim.device)
                    robot.set_joint_position_target(target)
                
                step_in_episode += 1
                
                if step_in_episode >= args.max_steps:
                    episode += 1
                    step_in_episode = 0
                    action_queue.clear()
                    print(f"\n[Episode {episode}] 完成，重置环境...")
                    reset_environment(cube, plate, robot, origins, sim, light_prim)
            
            robot.write_data_to_sim()
            sim.step()
            robot.update(sim_dt)
            
            wrist_camera.update(dt=sim_dt)
            overhead_camera.update(dt=sim_dt)
            
            count += 1
            if count % 300 == 0:
                mode = "自动推理" if not manual_mode else "手动"
                print(f"[Step {count}] | 模式: {mode} | Episode: {episode} | Queue: {len(action_queue)}")
    
    except KeyboardInterrupt:
        pass
    finally:
        client.close()
        sim_app.close()
        print(f"✅ SmolVLA 推理结束，共完成 {episode} 个 episodes")


if __name__ == "__main__":
    main()

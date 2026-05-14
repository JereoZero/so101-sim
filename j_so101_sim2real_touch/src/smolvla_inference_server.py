"""
SmolVLA 推理服务器 - 运行在 lerobot 环境中

使用 SmolVLA 模型进行语言条件推理
"""

import sys
sys.path.insert(0, "/home/jer/ws/workspace/projects/lerobot/src")

import socket
import json
import torch
import numpy as np
import cv2
import base64
from pathlib import Path

from lerobot.policies.smolvla.modeling_smolvla import SmolVLAPolicy
from lerobot.datasets.lerobot_dataset import LeRobotDatasetMetadata
from lerobot.policies.factory import make_pre_post_processors
from lerobot.policies.utils import build_inference_frame, make_robot_action

CHECKPOINT_PATH = "/home/jer/ws_issac/ws/j_so101_sim2real_touch/models/smolvla_sim_v7/checkpoints/002000"
DATASET_DIR = "/home/jer/ws_issac/ws/j_so101_sim2real_touch/datasets/sim_lerobot_smolvla"
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 9877
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
TASK_DESCRIPTION = "put small orange block in plate"


class SmolVLAInferenceServer:
    def __init__(self, checkpoint_path, dataset_dir, task_description, device="cuda"):
        self.device = torch.device(device)
        self.task_description = task_description
        
        print(f"[SmolVLA] 加载模型: {checkpoint_path}")
        
        pretrained_dir = Path(checkpoint_path) / "pretrained_model" if (Path(checkpoint_path) / "pretrained_model").exists() else Path(checkpoint_path)
        
        import os
        os.environ["HF_HUB_OFFLINE"] = "1"
        
        self.policy = SmolVLAPolicy.from_pretrained(str(pretrained_dir))
        self.policy.eval()
        self.policy.to(self.device)
        
        print("[SmolVLA] 模型加载完成")
        
        print(f"[SmolVLA] 加载数据集元数据: {dataset_dir}")
        self.dataset_metadata = LeRobotDatasetMetadata(Path(dataset_dir))
        print(f"[SmolVLA] 数据集: {self.dataset_metadata.total_episodes} episodes, {self.dataset_metadata.total_frames} frames")
        
        self.preprocess, self.postprocess = make_pre_post_processors(
            self.policy.config,
            dataset_stats=self.dataset_metadata.stats
        )
        
        print(f"[SmolVLA] 任务描述: {task_description}")
        print("[SmolVLA] 预/后处理器初始化完成")
    
    def predict(self, state_list, cam1_np, cam2_np):
        """
        SmolVLA 推理流程
        
        Args:
            state_list: [shoulder_pan, shoulder_lift, elbow_flex, wrist_flex, wrist_roll, gripper]
            cam1_np, cam2_np: (H,W,3) 图像
        """
        joint_names = [
            "shoulder_pan.pos",
            "shoulder_lift.pos",
            "elbow_flex.pos",
            "wrist_flex.pos",
            "wrist_roll.pos",
            "gripper.pos"
        ]
        
        state_list[4] = -1.5708
        
        obs = {name: val for name, val in zip(joint_names, state_list)}
        obs["camera1"] = cam1_np
        obs["camera2"] = cam2_np
        
        print(f"\n[输入] state: {[round(x,3) for x in state_list]}")
        print(f"[输入] cam1 shape: {cam1_np.shape}, dtype: {cam1_np.dtype}")
        print(f"[输入] cam2 shape: {cam2_np.shape}, dtype: {cam2_np.dtype}")
        
        obs_frame = build_inference_frame(
            observation=obs,
            ds_features=self.dataset_metadata.features,
            device=self.device
        )
        
        obs_frame["language_instruction"] = [self.task_description]
        
        print(f"[调试] obs_frame state shape: {obs_frame['observation.state'].shape}")
        
        obs_processed = self.preprocess(obs_frame)
        
        print(f"[调试] obs_processed state: {[round(x,3) for x in obs_processed['observation.state'].squeeze().tolist()]}")
        
        action_tensor = self.policy.predict_action_chunk(obs_processed)
        print(f"[调试] predict_action_chunk shape: {action_tensor.shape}")
        print(f"[调试] 预测chunk前3个动作: {action_tensor.squeeze(0)[:3].cpu().numpy().tolist()}")
        action_tensor = self.postprocess(action_tensor)
        print(f"[调试] postprocess后前3个动作: {action_tensor.squeeze(0)[:3].cpu().numpy().tolist()}")
        
        # 返回完整的 action chunk [chunk_size, 6]
        action_chunk = action_tensor.squeeze(0).cpu().numpy()
        
        print(f"[输出] chunk_size: {action_chunk.shape[0]}")
        print(f"[输出] 第1步: {[round(x,3) for x in action_chunk[0].tolist()]}")
        
        action_list = action_chunk.flatten().tolist()
        
        return action_list


def main():
    server = SmolVLAInferenceServer(CHECKPOINT_PATH, DATASET_DIR, TASK_DESCRIPTION, DEVICE)
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((SERVER_HOST, SERVER_PORT))
    sock.listen(1)
    print(f"\n[SmolVLA服务器] 监听 {SERVER_HOST}:{SERVER_PORT}")
    print("[SmolVLA服务器] 等待 Isaac Sim 连接...")
    
    while True:
        client_sock, addr = sock.accept()
        print(f"[SmolVLA服务器] 已连接: {addr}")
        buffer = ""
        try:
            while True:
                data = client_sock.recv(65536)
                if not data:
                    break
                buffer += data.decode('utf-8')
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        msg = json.loads(line)
                        if "state" in msg and "cam1" in msg and "cam2" in msg:
                            cam1_np = cv2.imdecode(np.frombuffer(base64.b64decode(msg["cam1"]), np.uint8), cv2.IMREAD_COLOR)
                            cam1_np = cv2.cvtColor(cam1_np, cv2.COLOR_BGR2RGB)
                            cam2_np = cv2.imdecode(np.frombuffer(base64.b64decode(msg["cam2"]), np.uint8), cv2.IMREAD_COLOR)
                            cam2_np = cv2.cvtColor(cam2_np, cv2.COLOR_BGR2RGB)
                            
                            action = server.predict(msg["state"], cam1_np, cam2_np)
                            action = [float(x) for x in action]
                            response = json.dumps({"action": action}) + "\n"
                            client_sock.sendall(response.encode('utf-8'))
                    except json.JSONDecodeError:
                        pass
        except Exception as e:
            import traceback
            print(f"[SmolVLA服务器] 连接错误: {e}")
            traceback.print_exc()
        finally:
            client_sock.close()
            print(f"[SmolVLA服务器] 客户端断开: {addr}")


if __name__ == "__main__":
    main()

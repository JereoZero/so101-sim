"""
ACT 推理服务器 - 运行在 lerobot 环境中

完全按照官方示例！
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

from lerobot.datasets.lerobot_dataset import LeRobotDatasetMetadata
from lerobot.policies.act.modeling_act import ACTPolicy
from lerobot.policies.factory import make_pre_post_processors
from lerobot.policies.utils import build_inference_frame, make_robot_action

CHECKPOINT_PATH = "/home/jer/ws_issac/ws/j_so101_sim2real_touch/models/act_sim_v2/checkpoints/008000"
DATASET_DIR = "/home/jer/ws_issac/ws/j_so101_sim2real_touch/datasets/sim_lerobot_act"
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 9876
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


class ACTInferenceServer:
    def __init__(self, checkpoint_path, dataset_dir, device="cuda"):
        self.device = torch.device(device)
        
        print(f"[ACT] 加载模型: {checkpoint_path}")
        
        pretrained_dir = Path(checkpoint_path) / "pretrained_model" if (Path(checkpoint_path) / "pretrained_model").exists() else Path(checkpoint_path)
        self.policy = ACTPolicy.from_pretrained(str(pretrained_dir))
        self.policy.eval()
        self.policy.to(self.device)
        
        print("[ACT] 模型加载完成")
        
        print(f"[ACT] 加载数据集元数据: {dataset_dir}")
        self.dataset_metadata = LeRobotDatasetMetadata(Path(dataset_dir))
        print(f"[ACT] 数据集: {self.dataset_metadata.total_episodes} episodes, {self.dataset_metadata.total_frames} frames")
        
        self.preprocess, self.postprocess = make_pre_post_processors(
            self.policy.config, 
            dataset_stats=self.dataset_metadata.stats
        )
        
        print("[ACT] 预/后处理器初始化完成")
    
    def predict(self, state_list, cam1_np, cam2_np):
        """
        官方推理流程！
        
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
        
        # 固定wrist_roll为-1.57，避免录制数据不一致影响推理
        state_list[4] = -1.5708
        
        obs = {name: val for name, val in zip(joint_names, state_list)}
        obs["camera1"] = cam1_np
        obs["camera2"] = cam2_np
        
        print(f"\n[输入] state: {[round(x,3) for x in state_list]}")
        print(f"[输入] cam1 shape: {cam1_np.shape}, dtype: {cam1_np.dtype}")
        print(f"[输入] cam2 shape: {cam2_np.shape}, dtype: {cam2_np.dtype}")
        print(f"[输入] cam1 前3个像素: {cam1_np[:2, :2, :]}")
        
        obs_frame = build_inference_frame(
            observation=obs, 
            ds_features=self.dataset_metadata.features, 
            device=self.device
        )
        
        print(f"[调试] obs_frame state shape: {obs_frame['observation.state'].shape}")
        
        obs_processed = self.preprocess(obs_frame)
        
        print(f"[调试] obs_processed state: {[round(x,3) for x in obs_processed['observation.state'].squeeze().tolist()]}")
        
        # 使用 predict_action_chunk 获取完整 chunk
        action_tensor = self.policy.predict_action_chunk(obs_processed)
        print(f"[调试] predict_action_chunk shape: {action_tensor.shape}")
        print(f"[调试] 预测chunk前3个动作: {action_tensor.squeeze(0)[:3].cpu().numpy().tolist()}")
        action_tensor = self.postprocess(action_tensor)
        print(f"[调试] postprocess后前3个动作: {action_tensor.squeeze(0)[:3].cpu().numpy().tolist()}")
        
        # 取第一个动作
        action = action_tensor.squeeze(0)[0].cpu().numpy()
        
        print(f"[输出] action: {[round(x,3) for x in action.tolist()]}")
        print(f"[输出] diff:  {[round(action[i]-state_list[i],3) for i in range(6)]}")
        
        # 转成字典再转回列表
        action_dict = {name: action[i] for i, name in enumerate(joint_names)}
        
        # 固定wrist_roll输出为-1.57
        action_dict["wrist_roll.pos"] = -1.5708
        
        # 返回5个关节 + wrist_roll
        return [action_dict[name] for name in joint_names]


def main():
    server = ACTInferenceServer(CHECKPOINT_PATH, DATASET_DIR, DEVICE)
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((SERVER_HOST, SERVER_PORT))
    sock.listen(1)
    print(f"\n[服务器] 监听 {SERVER_HOST}:{SERVER_PORT}")
    print("[服务器] 等待 Isaac Sim 连接...")
    
    while True:
        client_sock, addr = sock.accept()
        print(f"[服务器] 已连接: {addr}")
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
                            # 转换为Python float，避免JSON序列化错误
                            action = [float(x) for x in action]
                            response = json.dumps({"action": action}) + "\n"
                            client_sock.sendall(response.encode('utf-8'))
                    except json.JSONDecodeError:
                        pass
        except Exception as e:
            import traceback
            print(f"[服务器] 连接错误: {e}")
            traceback.print_exc()
        finally:
            client_sock.close()
            print(f"[服务器] 客户端断开: {addr}")


if __name__ == "__main__":
    main()

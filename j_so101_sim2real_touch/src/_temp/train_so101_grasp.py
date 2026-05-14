"""
SO101 抓取方块 PPO 训练脚本

运行命令:
cd /home/jer/ws_issac/thirdparty/IsaacLab
conda activate isaaclab
./isaaclab.sh -p /home/jer/ws_issac/ws/j_so101_sim2real_touch/src/train_so101_grasp.py --headless
"""

import sys
sys.path.insert(0, "/home/jer/ws_issac/thirdparty/isaac_so_arm101/src")
sys.path.insert(0, "/home/jer/ws_issac/ws/j_so101_sim2real_touch/src")

from isaaclab.app import AppLauncher

# 解析参数
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--headless", action="store_true", help="无头模式训练")
AppLauncher.add_app_launcher_args(parser)
args = parser.parse_args()

# 启动应用
app_launcher = AppLauncher(args)
sim_app = app_launcher.app

import torch
import os

from isaaclab.envs import ManagerBasedRLEnv
from isaaclab_rl.rsl_rl import RslRlVecEnvWrapper

from so101_grasp_rl_env import SO101GraspEnv, SO101GraspEnvCfg
from so101_grasp_ppo_cfg import SO101GraspPPORunnerCfg


def main():
    """主训练函数"""
    
    # 创建环境配置
    env_cfg = SO101GraspEnvCfg()
    
    # 创建环境
    print("[1] 创建环境...")
    env = SO101GraspEnv(cfg=env_cfg)
    
    # 包装为 RSL-RL 环境
    print("[2] 包装环境...")
    env = RslRlVecEnvWrapper(env)
    
    # 创建 PPO 配置
    print("[3] 创建 PPO 配置...")
    ppo_cfg = SO101GraspPPORunnerCfg()
    
    # 创建日志目录
    log_dir = os.path.join("logs", ppo_cfg.experiment_name)
    os.makedirs(log_dir, exist_ok=True)
    
    # 导入 RSL-RL 训练器
    from rsl_rl.runners import OnPolicyRunner
    
    # 创建训练器
    print("[4] 创建训练器...")
    runner = OnPolicyRunner(
        env=env,
        train_cfg=ppo_cfg.to_dict(),
        log_dir=log_dir,
        device=env.device,
    )
    
    # 开始训练
    print(f"[5] 开始训练! 日志目录: {log_dir}")
    print(f"    环境数: {env.num_envs}")
    print(f"    观测维度: {env.num_obs}")
    print(f"    动作维度: {env.num_actions}")
    
    runner.learn(
        num_learning_iterations=ppo_cfg.max_iterations,
        init_at_random_ep_len=True,
    )
    
    # 保存最终模型
    final_model_path = os.path.join(log_dir, "final_model.pt")
    runner.save(final_model_path)
    print(f"[6] 训练完成! 模型保存到: {final_model_path}")
    
    # 关闭环境
    env.close()
    sim_app.close()


if __name__ == "__main__":
    main()

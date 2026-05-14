"""
SO101 抓取方块 RL 环境

任务：控制机械臂抓取桌面上的方块
观测：关节角度 + 夹爪状态
动作：关节位置增量 + 夹爪开合
奖励：稠密奖励（接近、抓取、抬起）
"""

import sys
sys.path.insert(0, "/home/jer/ws_issac/thirdparty/isaac_so_arm101/src")

import torch
import numpy as np
from typing import Dict, Tuple

import isaaclab.sim as sim_utils
from isaaclab.assets import Articulation, RigidObject, RigidObjectCfg
from isaaclab.envs import ManagerBasedRLEnv, ManagerBasedRLEnvCfg
from isaaclab.managers import (
    ObservationManager,
    RewardManager,
    TerminationManager,
    SceneEntityCfg,
)
from isaaclab.scene import InteractiveScene, InteractiveSceneCfg
from isaaclab.utils import configclass
from isaaclab.sim import SimulationContext

from isaac_so_arm101.robots.trs_so101.so_arm101 import SO_ARM101_CFG


@configclass
class SO101GraspSceneCfg(InteractiveSceneCfg):
    """场景配置"""
    num_envs: int = 1024
    env_spacing: float = 2.0

    # 机器人
    robot: Articulation = SO_ARM101_CFG.replace(prim_path="{ENV_REGEX_NS}/Robot")

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


@configclass
class SO101GraspEnvCfg(ManagerBasedRLEnvCfg):
    """环境配置"""
    scene: SO101GraspSceneCfg = SO101GraspSceneCfg()

    # 观测空间
    observations: str = "so101_grasp"

    # 动作空间
    actions: str = "so101_grasp"

    # 奖励
    rewards: str = "so101_grasp"

    # 终止条件
    terminations: str = "so101_grasp"

    # 仿真步长
    decimation: int = 4  # 每4个仿真步执行一次策略
    sim_dt: float = 1.0 / 60.0
    episode_length_s: float = 10.0  # 10秒一回合


def compute_observations(env: ManagerBasedRLEnv) -> torch.Tensor:
    """计算观测"""
    # 获取机器人
    robot: Articulation = env.scene["robot"]

    # 关节位置 (6 joints + gripper)
    joint_pos = robot.data.joint_pos[:, :7]

    # 关节速度 (可选)
    joint_vel = robot.data.joint_vel[:, :7]

    # 末端执行器位置
    ee_pos = robot.data.body_pos_w[:, -1, :]  # gripper frame

    # 方块位置
    cube: RigidObject = env.scene["cube"]
    cube_pos = cube.data.root_pos_w

    # 组合观测
    obs = torch.cat([
        joint_pos,      # 7
        joint_vel,      # 7
        ee_pos,         # 3
        cube_pos,       # 3
    ], dim=-1)  # 总维度: 20

    return obs


def compute_rewards(env: ManagerBasedRLEnv) -> torch.Tensor:
    """计算奖励"""
    robot: Articulation = env.scene["robot"]
    cube: RigidObject = env.scene["cube"]

    # 末端执行器位置
    ee_pos = robot.data.body_pos_w[:, -1, :]

    # 方块位置
    cube_pos = cube.data.root_pos_w

    # 夹爪开合 (gripper joint)
    gripper_opening = robot.data.joint_pos[:, -1]

    # 1. 接近奖励：末端到方块的距离
    dist_to_cube = torch.norm(ee_pos - cube_pos, dim=-1)
    r_approach = -dist_to_cube * 2.0  # 距离越近奖励越高

    # 2. 抓取奖励：夹爪闭合且靠近方块
    gripper_closed = (gripper_opening < 0.05).float()
    close_to_cube = (dist_to_cube < 0.05).float()
    r_grasp = gripper_closed * close_to_cube * 5.0

    # 3. 抬起奖励：方块高度
    cube_height = cube_pos[:, 2]
    r_lift = (cube_height - 0.768) * 10.0  # 高度越高奖励越高

    # 4. 成功奖励：方块被抬起超过阈值
    success = (cube_height > 0.80).float()
    r_success = success * 100.0

    # 总奖励
    total_reward = r_approach + r_grasp + r_lift + r_success

    return total_reward


def check_terminations(env: ManagerBasedRLEnv) -> torch.Tensor:
    """检查终止条件"""
    cube: RigidObject = env.scene["cube"]
    cube_pos = cube.data.root_pos_w

    # 终止条件：
    # 1. 方块掉落（高度太低）
    dropped = cube_pos[:, 2] < 0.7

    # 2. 方块被成功抬起（可以在这里终止，也可以继续）
    # success = cube_pos[:, 2] > 0.80

    # 3. 回合时间结束（由环境自动处理）

    return dropped


class SO101GraspEnv(ManagerBasedRLEnv):
    """SO101 抓取方块环境"""

    cfg: SO101GraspEnvCfg

    def __init__(self, cfg: SO101GraspEnvCfg, **kwargs):
        super().__init__(cfg, **kwargs)

    def _get_observations(self) -> Dict[str, torch.Tensor]:
        """获取观测"""
        obs = compute_observations(self)
        return {"policy": obs}

    def _get_rewards(self) -> torch.Tensor:
        """获取奖励"""
        return compute_rewards(self)

    def _get_dones(self) -> Tuple[torch.Tensor, torch.Tensor]:
        """获取终止信号"""
        time_out = self.episode_length_buf >= self.max_episode_length
        terminated = check_terminations(self)
        return terminated, time_out


def main():
    """测试环境"""
    from isaaclab.app import AppLauncher

    app_launcher = AppLauncher(headless=False)
    sim_app = app_launcher.app

    # 创建环境
    env_cfg = SO101GraspEnvCfg()
    env = SO101GraspEnv(cfg=env_cfg)

    # 重置环境
    obs, info = env.reset()

    # 随机动作测试
    for _ in range(1000):
        # 随机动作
        actions = torch.randn(env.num_envs, 7, device=env.device) * 0.1

        # 执行动作
        obs, reward, terminated, truncated, info = env.step(actions)

        # 打印信息
        if _ % 100 == 0:
            print(f"Step {_}: reward={reward.mean().item():.3f}")

    env.close()
    sim_app.close()


if __name__ == "__main__":
    main()

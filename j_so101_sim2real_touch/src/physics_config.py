"""
物理配置模块
包含夹爪物理材质、碰撞属性等配置
"""


def configure_gripper_physics():
    """配置夹爪物理材质和碰撞属性 - 在仿真启动后调用"""
    try:
        from pxr import Usd, UsdPhysics, PhysxSchema
        import omni.usd

        stage = omni.usd.get_context().get_stage()

        # 夹爪链接路径
        gripper_links = [
            "/World/RobotBase/Robot/gripper_link",
            "/World/RobotBase/Robot/moving_jaw_so101_v1_link",
        ]

        # 创建高摩擦物理材质
        material_path = "/World/GripperPhysicsMaterial"
        material_prim = stage.GetPrimAtPath(material_path)

        if not material_prim:
            # 创建材质 prim
            material_prim = stage.DefinePrim(material_path, "PhysicsMaterial")
            material = UsdPhysics.MaterialAPI.Apply(material_prim)
            material.CreateStaticFrictionAttr().Set(3.0)  # 极高静摩擦
            material.CreateDynamicFrictionAttr().Set(2.5)  # 极高动摩擦
            material.CreateRestitutionAttr().Set(0.05)
            print(f"[Physics] Created gripper material: static=3.0, dynamic=2.5")

        # 递归查找所有碰撞体并应用材质和碰撞属性
        def configure_colliders(prim_path):
            prim = stage.GetPrimAtPath(prim_path)
            if not prim:
                return 0

            count = 0
            # 检查当前 prim 是否有碰撞属性
            if prim.HasAPI(UsdPhysics.CollisionAPI) or prim.GetTypeName() in ["CollisionPlane", "Sphere", "Cube", "Capsule", "Cylinder", "Mesh"]:
                # 应用材质绑定
                binding_api = UsdPhysics.MaterialBindingAPI.Apply(prim)
                binding_api.AddDirectBinding(material_path)

                # 配置碰撞属性 - 防止穿透
                collision_api = UsdPhysics.CollisionAPI.Apply(prim)
                collision_api.CreateContactOffsetAttr().Set(-0.001)  # 负值让碰撞体更小
                collision_api.CreateRestOffsetAttr().Set(-0.0005)    # 负rest offset减少间隙

                # 关键：修改碰撞网格近似方式为使用原始网格（而非凸包）
                mesh_collision_api = UsdPhysics.MeshCollisionAPI.Apply(prim)
                # "none" 表示使用原始网格，不进行凸包近似
                mesh_collision_api.CreateApproximationAttr().Set(UsdPhysics.Tokens.none)

                # 启用碰撞
                prim.GetAttribute("physics:collisionEnabled").Set(True)

                count += 1
                print(f"[Physics] Configured collider (using original mesh): {prim_path}")

            # 递归检查子 prim
            for child in prim.GetChildren():
                count += configure_colliders(child.GetPath())

            return count

        # 配置夹爪
        total_applied = 0
        for link_path in gripper_links:
            applied = configure_colliders(link_path)
            total_applied += applied
            print(f"[Physics] Configured {link_path}: {applied} colliders")

        print(f"[Physics] Gripper physics configured: {total_applied} colliders total")
    except Exception as e:
        import traceback
        print(f"[Physics] Warning: Could not configure gripper physics: {e}")
        traceback.print_exc()

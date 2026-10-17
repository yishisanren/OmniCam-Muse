# Find X9s Pro 安装变更范围

候选版已安装，挂载、资源分发与原厂 SDK 登记已通过重启验证，核心拍摄实拍通过。实验性功能边界见 PORT_STATUS.md。以下记录本次安装范围。

已读取并备份：当前固件和相机信息、原始 ODM 相机配置及相关底层库、LSPosed 数据库、相机偏好和模式数据库、相册 GR 功能偏好。原始 ODM 在私有挂载命名空间内读取，现有挂载不受影响。备份位于忽略的 `evidence/device-20261017/`。

本次安装范围：

1. 另外保存 Aura 模块和现有 LSPosed 状态，以便回退。停用 Aura 自己的 KernelSU 模块和 LSPosed 开关，其他模块保持现状。
2. 安装 Muse 设置 APK，启用它的系统框架、相机、相册作用域。目标为 `local.jiege.camera`。
3. 安装独立 KernelSU 模块 `omnicam_muse_x9spro`。启动时验证 PME110、固件 `.103`、相机 APK 和原始算法库指纹；不匹配时停止激活。
4. 对 `/odm/lib64`、`/odm/etc/camera/config`、`/odm/etc/camera/meishe_lut`、`/odm/etc/camera/basictone` 使用可卸载的只读 OverlayFS，镜像保存在模块自己的目录内。保留原始 MTK 算法库和相机 ID，不写系统分区。
   Mountify 遮挡原厂相机 SDK 登记时，校验原厂 SDK 与登记文件，额外只读挂载 `/my_product/product_overlay/etc/permissions` 到 `/product/etc/permissions` 的上层，仅恢复该固件原有的相机登记及权限文件。
5. 相机专用目录涉及 `files/ricoh_gr`、`files/jiege`、`files/pop_port`、`files/odm`、`files/mode_limit_watermark`，相册涉及 `files/ricoh_gr_styles` 和 `files/jiege_ipu`。先保存已有内容，再分发模块资源并验证指纹；全部成功后才允许 Hook 激活。
6. 只调整相机 `override_config_data.xml` 中与 GR/POP、模式列表版本、HDR 模式、移轴和闪光亮度有关的配置，以及相册 `business_featureSwitch_config.xml` 中的 GR 功能项。

修正后的方案不删除数据库、不清除应用数据，不替换全局音频策略、Qualcomm ISP 或 gamma 配置。相机需要在测试时关闭并重新打开；本次重启及后续验收已获用户明确允许。

回退：停用 Muse、恢复备份的相机专用资源和配置，恢复 Aura 自身的启用状态和作用域；其他模块及用户照片保留。

当前保留开发候选标记，不作为所有上游功能均通过的正式发行版。本次没有发布 Muse 的 GitHub Release。

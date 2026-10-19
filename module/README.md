# OmniCam Muse · Find X9s Pro

目标：PME110 / MT6993，17.0.0.103(CN01)，相机 7.006.121，相册 17.10.36；17.10.7 已通过符号回放兼容检查。

KernelSU ID：`omnicam_muse_x9spro`。配对 APK：`local.jiege.camera`。LSPosed 作用域：系统框架、相机、相册。

安装前停用 Aura 的 KernelSU 和 LSPosed 模块，保留数据与回退资料。只读 OverlayFS 在固件检查通过后挂载，资源指纹一致后才激活 Hook；不删除相机数据库或替换系统音频策略。安装不自动重启。

当前为开发候选。功能实测状态、构建步骤及限制见仓库根目录 README.md。

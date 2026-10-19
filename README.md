# OmniCam Muse · Find X9s Pro

基于 [OmniCam-Muse](https://github.com/benbaobaoshigemi/OmniCam-Muse) 4.0.0，固定上游提交 `8f373e10b17c95532a3ff2f41c4777ca797da947`。本分支适配 OPPO Find X9s Pro，保留 MTK 原始相机管线。

当前适配版本：**4.0.0-x9spro.3**，已适配相册 17.10.36 并安装到目标真机；修复详情见 [相册兼容性记录](docs/GALLERY_17_10_36_FIX.md)。本版本保留预发布候选标记。下表中的完整拍摄矩阵为 `.2` 的验收记录，`.3` 另完成相册专项回归。

下载：[4.0.0-x9spro.3 Release](https://github.com/yishisanren/OmniCam-Muse/releases/tag/v4.0.0-x9spro.3)，包含配对 APK、KernelSU ZIP 和 SHA256SUMS。具体实测范围与限制见 [发行说明](docs/RELEASE_NOTES_4.0.0-x9spro.3.md)。已安装 `.2` 的用户也应使用同版配对包升级，不能仅替换 APK 而保留旧的配对标记。

## 支持环境

| 项目 | 当前适配目标 |
| --- | --- |
| 机型 / 平台 | Find X9s Pro · PME110 / MT6993 |
| 系统 | PME110_17.0.0.103(CN01)，Android 17 / API 37 |
| 系统相机 | 7.006.121，产品分区原始 APK |
| 相册 | `.3` 专项验收：17.10.36；17.10.7 符号回放兼容 |
| 模块 | KernelSU + Mountify；LSPosed 2.2.1（7927） |
| APK / KernelSU ID | `local.jiege.camera` / `omnicam_muse_x9spro` |

固件、相机 APK 或核心资源不匹配时停止激活。其他系统和相机版本需要重新适配。

## 机型适配

- 保留本机相机 ID、传感器调校、原始算法管线、ISP、gamma 和 `libAlgoInterface.so`。
- GR/POP 从本机已有模式派生，使用本机 BasicTone 作为 X9 后端；保留本机 15 / 23 / 65 mm 镜头关系。
- GR native 地址受本机 ELF Build ID 约束；相机启动前验证 APK 与配对资源指纹。
- GR 保留 MTK 原生 Meishe V2 硬件缓冲区管线；不套用旧 V1 节点，避免绿色废片。验收同时检查成片内容，不能只检查 JPEG 解码成功。
- 25MP 放宽改为 MTK 的三个普通拍照节点，不导入 Ultra 的 lighthouse 配置；保留镜头、2DOL、闪光等硬件条件。开关关闭时使用原生配置。
- 本机 2 亿像素原生决策没有人脸门槛，因此不提供多余的解除开关；保留光线、ISO、HDR 等系统条件。
- 大师色彩使用本机三个后摄的 Camera2 公开 ForwardMatrix 和中性 HueSatMap，替换 Ultra 的 Adobe DCP 前置数据；未进行色卡准确度标定。
- 使用四个相机目录只读 OverlayFS；Mountify 遮挡 ColorOS 原厂相机 SDK 登记时，额外恢复原厂权限目录的只读挂载，校验原厂 SDK 与登记文件指纹。资源分发完成前不启动 Hook，安装和资源分发保留回退资料。
- 不删除相机数据库，不替换系统音频策略，不修改其他 LSPosed 模块。

上游功能与实现说明保留在 [上游 README](docs/UPSTREAM_README.md) 和 [MODULE.md](docs/MODULE.md)。上游针对 Ultra 的硬件条件与验证结论不能直接作为本机验收结果。

## 当前验证状态

| 检查 | 结果 |
| --- | --- |
| 原始配置差异与管线保留 | 通过 |
| 相机 / 相册符号定位 | 254 / 31，全部匹配 |
| 色彩资源目录 | 189 个 look、148 个 lattice，通过 |
| JVM 离线测试 | 4 组全部通过 |
| Release 构建 / Android lint | 通过，lint 0 error |
| 真机启动、挂载与作用域 | 重启通过，原厂相机 SDK 登记恢复；相机自身命名空间 52 项资源与四个只读 ODM 挂载通过 |
| 相机 / 相册注入 | 254 / 31 个符号，注入状态正常 |
| 普通照片 / GR / POP | 成片完整解码，GR 正片、黑白均通过；零平面绿片已修复 |
| 哈苏超清 5000 万像素 | 6144 × 8160，通过 |
| 2 亿像素标准 / 清透 | 均为 12288 × 16320，最终文件稳定、哈希一致、完整解码；清透请求确认为 `qing_tou.bin` |
| 4K60 普通录像 | 最终版本实录 3840 × 2160，约 60fps，27 秒 / 1628 帧，时间戳连续，全片解码通过 |
| 自然化 / 25MP 放宽 | 自然化编辑配置已被底层读取；普通照片输出 4416 × 5888。未做画质提升量化与所有门槛场景对照 |
| 大师色彩 | MTK 动态 gamma 与四表 LMT；HNCS 三颗后摄、主摄 Film Portra、Lumix 单色和 0/50/100% 混合通过；未逐一验证全部 look |
| 进一步柔化 | 本机 GDF 节点 0/50/100% 参数及成片通过；大师、GR、50MP 隔离通过 |
| 物理柔光 HDF / 黑柔 / 白柔 | 本轮候选三档 P010 处理及最终成片通过，均为 4352 × 5780；未完成原厂同档对照和光学标定 |
| 额外颗粒 | 标准滤镜强度 86 与重置 0、清透强度 100 下大小 0/100 均通过；修复非胶片滤镜漏传颗粒类型，最终像素确认效果生效；未逐一验证所有滤镜 |
| 和光物理胶片 | 开启、关闭均完成 3072 × 4080 实拍，保存、解码及目视检查通过；未做光学标定 |
| XPAN 显影实况 | 实拍、相册按钮回放、另存视频通过；85 帧 / 2.83 秒显影动画与 AAC 快门声完整，最终 JPEG 2912 × 7872 |
| XPAN 取景净化 | 小窗、大窗暗边分别开关及隔离通过；拍摄显影动画关闭通过，实况文件仍保留 85 帧显影视频 |
| 4K60 普通视频滤镜 | 反差黑白实录 2160 × 3840、26.37 秒 / 1586 帧，约 60.15fps；抽帧确认黑白效果，全片解码通过 |
| 专业视频 ISZ / OLog2 | 主摄 1→2×、长焦 2.8→5.6×的原厂传感器场景切换已核对；5.6× SDR 与 2× O-Log2 的 4K30 实录通过，后者确认为 HEVC Main 10 / 10bit |

媒体检查针对最终内容，包含实际尺寸、传输前后哈希与完整解码，并检查已复现的 GR 绿色异常。大师色彩读取本机实际 gamma 并烘焙对应色表；无有效元数据时保留原厂处理。本机公开矩阵不能代替色卡精校，柔光为计算模拟。验收详情见 [PORT_STATUS.md](docs/PORT_STATUS.md)。

## 安装

1. 备份当前 Aura 模块、LSPosed 状态和相机专用资源。不要清除相机或相册数据。
2. 停用 Aura 的 KernelSU 模块和 LSPosed 开关。
3. 刷入与目标相册版本对应的配对 KSU ZIP（当前为 `OmniCam-Muse-4.0.0-x9spro.3-KSU.zip`），其中包含同版已签名设置 APK；签名不一致时保留原有应用并报告安装失败。
4. 在 LSPosed 启用 OmniCam Muse，作用域选择 **系统框架、相机、相册**。
5. 重启并解锁，使只读挂载与资源分发生效。安装程序不自动重启手机。
6. 打开 Muse 查看注入状态，再进入相机。新设置会在重新打开相机后生效。

完整操作边界与回退方案见 [INSTALL_PLAN.md](docs/INSTALL_PLAN.md)。Aura 与 Muse 不应同时运行。

## 构建

需要 JDK 21、Android SDK 37、NDK 29.0.14206865、CMake 3.22.1，以及含 numpy、cryptography 的 Python 3。Gradle/Maven 依赖由 wrapper 获取。

首次准备：

```sh
export JAVA_HOME=/path/to/jdk21
export ANDROID_HOME=/path/to/android-sdk
export MUSE_PYTHON=/path/to/python3
export MUSE_DEVICE_SERIAL=your-device-serial
"$MUSE_PYTHON" tools/snapshot_device.py
adb -s "$MUSE_DEVICE_SERIAL" pull /product/app/OplusCamera/OplusCamera.apk evidence/device-20261017/OplusCamera-7.006.121.apk
"$MUSE_PYTHON" tools/read_camera_profiles.py
"$MUSE_PYTHON" tools/create_signing.py
```

本机私有快照、凭据、照片和日志均位于忽略目录中，不能提交。生成目标配置需要本机快照；上游 Git 对象用于取得原始功能增量。

```sh
sh tools/build_x9spro.sh
```

产物位于 `dist/`，附 `SHA256SUMS`。签名密钥 `port.keystore` 和私有 `evidence/signing.env` 仅保存在本机；后续升级须沿用同一身份。也可通过上游 `OMNICAM_KEYSTORE` 等环境变量使用自己的密钥。

## 回退

停用 Muse，恢复备份的相机专用资源与配置，再恢复 Aura 自身的启用状态和作用域并重启。只恢复本次变更的模块和资源，保留照片及其他模块设置。私有备份目录由安装记录列出。

## 后续适配与 Skill

[omnicam-x9spro-port](skills/omnicam-x9spro-port/SKILL.md) 收录了源码合并、MTK 管线适配、签名构建、拍摄验收、设置恢复、回退和发行流程，以及本轮遇到的问题和修复依据。可将整个 `skills/omnicam-x9spro-port` 目录安装到自己的 Codex skills 目录，使用 `$omnicam-x9spro-port` 调用；Skill 目录自带行为测试。

已验收上游基线记录在 [maintenance/upstream.json](maintenance/upstream.json)。检查器比较上游 main 提交和最新公开 Release（含预发布及资产变化），不会安装手机或自动推进验收基线：

```sh
python3 skills/omnicam-x9spro-port/scripts/check_upstream.py --workspace "$PWD" --output evidence/maintenance/upstream-latest.json
```

更新按“发现 → 构建 → 真机验收 → 发布”推进。手机未连接或无法独占时保留候选，待完成实拍再提醒更新。检查失败会明确报错，不能当作没有更新。

## 许可与致谢

本项目沿用上游 **GPL-3.0**，保留 [NOTICE.md](NOTICE.md) 和 [LICENSES](LICENSES)。本机配置合并、固件守卫和挂载方案复用此前 Aura 的 MTK 适配实现，相关 MIT 许可保留在 [LICENSES/OmniCam-Aura-MIT.txt](LICENSES/OmniCam-Aura-MIT.txt)。

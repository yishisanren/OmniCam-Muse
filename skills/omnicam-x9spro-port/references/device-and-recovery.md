# PME110 真机验收与恢复

## 接机和恢复点

明确 `MUSE_DEVICE_SERIAL`，不能自动选第一台设备。新鲜核对机型/平台、固件、相机路径/版本/SHA、相册、原始算法 ELF Build ID/SHA、KSU/Mountify/LSPosed 和用户设置。具体值从 profile 和现场取得。

确认当次已连接、解锁、可独占。未知前台出现就停止输入。用户确认的自动 BigBang 只能按当次标志关闭精确 `app.textboom.revived/com.smartisan.textboom.ui.boom.BoomActivity`，不关闭服务/无障碍。相机 ScreenOffActivity 按观察到的控件唤醒。

安装前用新目录备份 APK、模块、LSPosed、原模块设置及涉及的相机设置；已有恢复点不覆盖。保留签名/UID，不清相机相册数据、不重建外部已移除的 Aura。snapshot_device.py 在私有挂载命名空间读原厂 ODM，先确认解除的是项目覆盖层，不能把当前移植层当原厂。

## 安装与挂载

install_x9spro.py 为首次安装，upgrade_x9spro.py 是本轮升级夹具；下一版先改目标版本和证据目录。KSU 官方安装会装内置 APK；ColorOS 拦截 shell 流式安装时用已验证 root package-manager，不改系统安全配置。

只有活动 profile 完全一致才可用 update_candidate_apk.py 做增量 APK 修复，否则完整配对升级。更新后重启相机/相册避免旧 APK Hook 缓存。启动层、SDK 登记或载荷变化时按当次授权重启手机。

check_boot.py --camera 检查相机自己的 mount namespace：四个只读 ODM 层、基线 52 资源及原厂 SDK 登记（未来数量以新 profile 为准）。Mountify 2.0.5 曾遮住 /product/etc 原厂相机 SDK 登记，即使停用全部 Hook 也闪退；恢复方案必须验证原厂 SDK/登记指纹。verify_installed.py 检查实际/内置 APK 与运行文件；KSU 正常删除 README/customize.sh 安装文件，不为凑哈希重建，其余差异不得放过。

## 媒体与功能

device_media.py 有前台校验/UI 排他锁。照片打开相册触发 ColorOS 延迟主图，再等内容稳定、传输哈希、尺寸和完整解码。长时间稳定的占位 JPEG 也不能通过。核心矩阵：普通照片、GR 正片/单色、POP、50MP、200MP、4K60；GR 曾产生能解码的零 YUV 绿片，必须看真实像素。BW 控件中文名是“单色”。

录像检查源 PTS/DTS 严格递增、间隔和全解码，保留解复用时间基，防止验证工具量化出重复 DTS。横/竖 4K 均有效。

按修改区域补测：

- 大师：MTK 有效色温为 com.mediatek.3afeature.awbColorTemperature；物理 ID 2 主摄、3 超广、4 长焦。解码实际 257 点非均匀 BPS gamma，匹配四表 LMT，主图要有 /live/m... 已应用路径和像素证据，不能只测预览/缩略图。无有效元数据保留原厂。三镜头 HNCS、Film/Lumix、混合0/50/100是代表性案例，不是全部 look/色卡精校。
- 进一步柔化：本机 tmc_upsample_merge_fastgdf 为14参数，epsilon下标7，需匹配本机 Build ID/实参；0保留原厂，50/100相对原厂100/10000倍。六个帧作用域只准普通拍照。测关闭后残留删除，GR/大师/高像素隔离。
- 物理柔光：HDF弱、黑柔中、白柔强验证主图 P010 0x36 的尺寸/处理返回/最终媒体。预检平面、步长、锁生命周期，未知输入回原厂。正常出片不等于原厂同档光学标定。
- 颗粒：原始 MTK Meishe V2 参数 API，不换算法库。标准和非胶片滤镜都测；清透曾漏传类型成为-1，应补齐显式负值额外颗粒元数据，不能放松原生类型守卫。核对type2、amount、size和像素，再测关闭/重置及大小边界。
- 和光：开关对照要同滤镜/曝光/镜头、固定场景，分别记录处理和媒体差异，不能把电脑屏幕亮度变化算收益。
- XPAN：最终 JPEG 内嵌 MP4、85帧（旧计划84有误）、负片显影、AAC声音、相册按钮回放、另存视频均实测。小窗/大窗/动画净化独立开关测隔离；去界面动画不应删文件内实况。长按被 BigBang 拦截就用播放按钮，不改无障碍。
- 视频：4K60滤镜要看实际像素；专业视频读 dumpsys media.camera 的 latest received/last request。本机主摄1→2x、长焦2.8→5.6x，不搬Ultra3/6x。场景变化证明ISZ路径，不代替解析力量化。O-Log2核对Main10/10bit，不把容器bt709标签虚称HLG/PQ。

## UI与收尾

先观察再输入。自定义控件可能忽略 adb MOVE；TouchProbe.c 针对已验证 touchpanel、轴范围和释放机制，使用前重新确认输入布局，不能跨分辨率套坐标。恢复大师滤镜用约350px/1000ms的小幅手势避免跳过；每次读回实际值。用户说“颗粒100”也需核对，曾实际只有86。

逐项恢复本次测试设置。只有确认期间模块 XML 只有测试改动时才恢复原字节；相机不整体回灌旧 MMKV/媒体 DB。保留后来新增的设置和照片，读回 UI、原厂库指纹。诊断私有归档后清除临时追踪/探针/安装副本，保留回退 APK；发行代码不含常量色表、gamma/frame/视频追踪探针。

最终检查应用注入健康、冷启动、挂载和配对。collect_experiment_acceptance.py 的日期/案例白名单只适合本轮，下一版须用新证据目录与实际案例，不能混入失败/调试媒体或把旧版实测当新版。

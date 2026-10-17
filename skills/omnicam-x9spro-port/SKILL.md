---
name: omnicam-x9spro-port
description: 适配 OmniCam-Muse 上游更新到 OPPO Find X9s Pro（PME110/MT6993），完成源码合并、配对构建、真机拍摄验收、回退及 GitHub 发布；也用于每周检查该上游。其他机型必须重新采集和验证，不能沿用本机指纹。
---

# OmniCam Find X9s Pro 适配

版本源：`yishisanren/OmniCam-Muse` 的 `find-x9s-pro` 分支；上游：`benbaobaoshigemi/OmniCam-Muse`。先定位真实 Git checkout，读取 `maintenance/upstream.json`、`module/profile.json`、`docs/PORT_STATUS.md`、工作状态与最近授权。本 Skill 本身不是对其他设备、仓库或后续重启的授权。

## 按任务进入

- **上游检查或每周维护**：读 [更新与发布](references/source-and-release.md)，运行 `scripts/check_upstream.py --workspace <checkout> --output <checkout>/evidence/maintenance/upstream-latest.json`。只读 GitHub、写检查结果，不操作手机或推进已验收基线。
- **有变化，需要移植**：独立 checkout/worktree 处理差异，保留已验收分支和原签名。按更新参考构建；不把 Ultra 硬件配置整包覆盖到本机。
- **安装、实拍或诊断**：读 [设备验收与恢复](references/device-and-recovery.md)。取得当次连接、解锁且可独占测试的确认，再操作手机；重启按当次授权处理。
- **发布、提醒更新**：完成约定验收，确认安装 APK、内置 APK、发行资产一致，再发布并匿名回读。真机条件不足只能叫“候选待真机验收”，不能说“已适配完成、可更新”。

## 不可丢失的约束

1. 以新鲜设备读回与 `module/profile.json` 为准。OTA、相机/相册、底层 ELF Build ID 变化后重新采集定位和实测，不能只改白名单。
2. 保留 MTK 原厂 ISP、gamma、相机 ID、决策树、音频策略与 `libAlgoInterface.so`。沿用原厂 Meishe V2/BasicTone；不恢复曾导致 GR 绿片的 V1 替换。
3. 开关、日志、构建和挂载不能代替最终媒体。照片等待后处理，录像检查源时间戳、完整解码和真实像素，兼容横竖屏 4K。
4. 保留照片、签名、UID、其他模块及无障碍服务，逐项恢复测试设置。不能整体回灌旧相机 MMKV/数据库覆盖用户后来产生的数据。
5. 区分功能证据和量化结论：ISZ 场景切换不等于解析力测量，公开矩阵不等于色卡精校，物理柔光是计算模拟。只写实际通过的版本/镜头/规格。

## 每周状态

`maintenance/upstream.json` 只记录**已验收**上游提交与发行指纹。新候选写私有 `evidence/maintenance/candidate-state.json`，记录提交、分支、阶段、证据、已通知阶段；阶段用 `detected / built / needs_device / device_passed / published / failed`。

- 无变化且无新的待处理事项时保持安静；网络/权限失败不能写成没有更新。
- 同一候选已待真机时保留现场，不重复构建或每周重复催促；候选、阻塞或所需动作变化才通知。
- 有更新就完成可独立做的源码适配、构建与离线检查。需要手机时发一次明确的连接验收请求。
- 真机通过后更新已验收基线、发布配对资产并通知下载链接；抓取或构建成功不能提前推进基线。

既定每周适配和本仓库发布已获授权时连续执行，不为例行步骤重复开工确认；范围、硬件或操作边界改变再对齐。

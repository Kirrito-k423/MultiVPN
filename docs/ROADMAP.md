# 开发路线与交付门槛

目标：同一产品面向 Windows 与 macOS，同时访问至少两个由 UniVPN 接入的内网，提供按连接区分的 SSH/IDE 与浏览器入口。

## 阶段 0：公开开发基础

- 双平台设计、平台限制、贡献流程、Issue/PR 模板。
- 无平台依赖的 Rust 连接生命周期核心。
- Windows x64、Mac ARM、Mac Intel 核心构建与模型测试 CI。
- 兼容性证据模板与公开任务。

交付边界：上述内容不构成 VPN 应用；不包含桌面窗口、虚拟机管理或网络转发。

## 阶段 1：两平台分别验证原厂客户端与隔离环境

Mac ARM 优先验证 macOS guest；Mac Intel 验证独立 guest + SSH 接入路线。Windows x64 优先验证 Hyper-V 独立 guest，并记录系统版本与功能限制。先选匹配客户端和实际认证方式，再讨论减小镜像或资源占用。

验收：每个平台至少两个独立环境同时认证并访问已知目标；VPN 全隧道后宿主管理通道仍可用；网段和域名重叠可以通过显式连接入口区分。不能用一条连接、模拟服务或编译结果代替这些结果。

依赖：可用原厂客户端、用户授权的两个网关/测试目标、需要用户完成的交互认证。遇到准入或管理通道限制时记录阻断和备选路线。

## 阶段 2：共用访问层与平台适配器

实现 SSH guest 接入、每连接代理、远端 DNS、主机密钥隔离、取消与超时，以及 guest 转发的出口限制。为 Mac 与 Windows 分别适配启动和停止操作。

验收：普通互联网与已有代理共存；连接 A/B 地址相同时仍归属正确；断线、认证失效、改变默认路由、guest 服务崩溃和宿主恢复时不会回退到错误出口。既检查新连接，也检查已建立连接的处置。

## 阶段 3：桌面产品与平台安装包

使用 GPUI Kit 实现连接列表、原厂登录入口、SSH/浏览器启动、状态解释和诊断。平台能力不足时显示实际限制；首版允许用户自行安装 guest 并在原厂 UI 完成认证。

验收：Windows 与 Mac 各自构建与交互检查；用户能从未连接状态完成登录和访问；重复操作、取消、恢复不会错误发布入口；读取记录与实际可达性一致。

## 阶段 4：首个可用版本

收集两平台真实端到端、故障、DNS、地址重叠与容量证据，发布版本说明和签名状态。拟产物为 Windows 安装包、Mac 应用包；对暂未验证的平台和能力逐项标记。

当前不发布占位安装包，也不把核心 CI 产物称为可用 VPN 客户端。

## 阶段 5：系统透明访问与资源优化

Mac 评估 Network Extension，Windows 评估 WFP。通过独立设计和验证后再增加透明 TCP/UDP、DNS 或包级能力。Linux namespace/container、原厂 SDK、多会话原生隧道和镜像优化均由新的证据驱动，不视为首版前提。

正式任务：[#1 Mac 兼容性](https://github.com/Kirrito-k423/MultiVPN/issues/1)、[#2 Windows 兼容性](https://github.com/Kirrito-k423/MultiVPN/issues/2)、[#3 共用访问层](https://github.com/Kirrito-k423/MultiVPN/issues/3)、[#4 桌面界面](https://github.com/Kirrito-k423/MultiVPN/issues/4)、[#5 发布验收](https://github.com/Kirrito-k423/MultiVPN/issues/5)。

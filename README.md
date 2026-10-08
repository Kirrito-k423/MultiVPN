# MultiVPN

面向 **Windows 与 macOS** 的多 VPN 桌面管理应用，计划复用原厂 UniVPN 客户端，在独立环境中运行多条连接，提供各自的 SSH、IDE 与浏览器访问入口。

**当前阶段：公开设计与连接生命周期基础。** 已实现的 Rust 核心只管理连接状态与转发许可，不启动虚拟机、不拨号、不提供网络代理。桌面界面、平台后端与真实双 VPN 连接仍待实现和验证。

本项目独立开发，与 UniVPN 原厂没有从属关系。仓库仅包含本项目代码与文档，原厂客户端由用户从授权渠道自行安装。

## 目标平台

| 平台 | 目标架构 | 运行环境方案 | 当前证据 |
|---|---|---|---|
| Windows 11 | x86_64 | 独立 Hyper-V guest 或通过 SSH 接入外部独立 guest | 核心代码由 Windows CI 构建/测试；真实 VPN 待验证 |
| macOS 15+ | Apple silicon | 独立 guest，拟用 Apple Virtualization 管理 | 核心代码由 ARM Mac CI 构建/测试；真实 VPN 待验证 |
| macOS 15+ | Intel | 通过 SSH 接入独立 guest，自动虚拟机后端待选型 | 核心代码由 Intel Mac CI 构建/测试；真实 VPN 待验证 |

CI 结果见 [Actions](https://github.com/Kirrito-k423/MultiVPN/actions)。编译成功只代表本阶段核心可构建，不能代表桌面应用、虚拟机、认证或多 VPN 可用。Windows Home 的虚拟机自动管理后端、Windows ARM 与较旧系统另行评估；通过 SSH 接入的路径也需要实际认证与网络验证。

## 文档与开发

- [双平台软件设计](docs/design/multi-vpn-software-design.md)
- [开发路线与交付门槛](docs/ROADMAP.md)
- [公开开发流程](CONTRIBUTING.md)
- [兼容性证据模板](docs/validation/compatibility-template.md)
- [当前验证记录](docs/validation/bootstrap.md)
- [开发任务](https://github.com/Kirrito-k423/MultiVPN/issues)

```sh
cargo test --workspace --locked
cargo fmt --all -- --check
cargo clippy --workspace --all-targets --locked -- -D warnings
python3 scripts/check_docs.py
```

Windows 使用 `python scripts/check_docs.py`。核心 crate 当前不含第三方依赖。桌面技术选型为 Rust + [GPUI Kit](https://gpui-kit.com/docs/installation/)，虚拟机控制与凭据存储由平台适配层实现。

所有阶段通过 Issue 定义目标和验收，使用 `codex/` 特性分支和 Pull Request 提交实现与证据。正式安装包只在对应平台验收后发布。

License: [MIT](LICENSE)。

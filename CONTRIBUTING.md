# 公开开发流程

MultiVPN 的设计、开发任务、Pull Request、自动检查结果和发布记录都在[公开 GitHub 仓库](https://github.com/Kirrito-k423/MultiVPN)维护。初始化提交直接建立 `main`；后续功能使用 `codex/<feature>` 分支，经 PR 合并。

## 工作顺序

1. 用 Issue 写明用户场景、目标平台、需求 ID、范围与验收条件。改变架构的选择先修改[设计](docs/design/multi-vpn-software-design.md)，记录候选方案和代价。
2. 实现最小可验证部分。共享逻辑与 Windows/macOS 适配器分离；能力未实现时返回明确的“不支持”，不要用模拟结果显示真实连接成功。
3. 按改动运行本机检查，提交测试与必要的文档。需要真实 VPN 的改动，额外填写[兼容性证据](docs/validation/compatibility-template.md)。
4. 提交 PR，描述问题、最终行为、测试、平台范围和未验证项，关联 Issue。三个核心 CI 作业通过后才能合并；桌面、驱动和网络改动还需要对应平台的验收结果。
5. 合并后更新任务与验证记录。正式安装包按平台分别发布，记录提交、构建环境、签名状态与已验证能力。

## 检查

```sh
cargo fmt --all -- --check
cargo build --workspace --locked
cargo test --workspace --locked
cargo clippy --workspace --all-targets --locked -- -D warnings
python3 scripts/check_docs.py
```

Windows 使用 `python`。CI 在 Windows x64、Mac ARM 和 Mac Intel 上执行这些核心检查；它不具有用户的网关和凭据，也不负责原厂拨号或真实内网测试。

当前 Rust edition 为 2024，开发与 CI 工具链固定为 `rust-toolchain.toml` 中的 1.97.0。核心最低 Rust 版本声明为 1.85，但最低版本构建尚未单独验证。引入 GPUI 或升级工具链时须更新依赖、lockfile 与三个平台的 CI 证据。项目源码采用 MIT，第三方依赖和原厂客户端保持各自许可。

## 可公开的证据

发布操作系统/架构、原厂版本、认证类别、匿名目标标签、测试步骤、服务身份校验结论与脱敏统计。网关地址、账号、密码、证书、会话令牌、真实内网拓扑、原始流量、镜像与原厂安装包放在本地 `private/` 或 `local/`，不上传到 Issue、PR 或 CI artifact。

文档验证器可检查链接和常见本地材料路径，但不能代替发布前的内容审查。不同证据只支持对应范围：生命周期模型测试证明状态语义；UI 构建证明构建；真实双连接、DNS 和故障测试分别证明相应网络行为。

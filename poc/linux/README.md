# Linux 隔离环境诊断 PoC

关联 [Issue #7](https://github.com/Kirrito-k423/MultiVPN/issues/7)。此工具用于开发者验证原厂客户端、独立网络和 SSH 管理通道，不是桌面 VPN 产品。

Mac Apple silicon 使用 Linux ARM 原厂包；Windows x64 / Mac Intel 应使用匹配的 Linux x86_64 包和 Linux 容器运行时。首次安装 Docker、启用虚拟化和重启应由用户明确安排。本工具不会启用这些功能或修改宿主机路由。

## 先决条件

- 已配置 Docker 的 Linux 引擎、Python 3 和 OpenSSH 客户端。
- 从[联软官方渠道](https://www.leagsoft.com/doc/article/103197.html)取得允许使用的原厂安装包，核对发布版本、架构及校验值。当前 Linux ARM 条目为 Ubuntu 26.04 LTS；厂商 MD5 对应 ZIP 内的 `.run` 文件，ZIP 本身还包含证书文件。
- 用户授权的网关、认证方式、已知 IPv4 TCP 测试目标和现有 SSH 公钥。只复制公钥到容器，私钥留在宿主机。

安装包、目标列表、网关、账户、凭据、镜像和原始日志放在 `local/` 或 `private/`。安装了客户端的镜像仅保留本机，不推送镜像仓库。

## 构建和启动

先按原厂校验值验证 `.run`；再计算该文件的 SHA256，用实际值替换以下 `VERIFIED_SHA256`。构建上下文只包含安装包与本项目运行脚本，不会上传整个工作目录。

```sh
python poc/linux/poc.py build --installer local/vendor/client.run --sha256 VERIFIED_SHA256
```

需要构建代理时，可加 `--proxy http://host.docker.internal:7890`。该参数仅用于当前构建，不改变 Docker Desktop 的全局代理设置。基础镜像使用固定 digest 的官方 Ubuntu 26.04 镜像；`--base-image` 可显式选择其他版本，随后必须重新验证兼容性。

在私有目录建立已知目标列表，例如 `local/lab-targets.json`：

```json
[{"host": "192.0.2.10", "port": 22}]
```

这里的文档示例地址需要替换成用户授权的目标；不能把扫描地址段当成测试。

```sh
python poc/linux/poc.py start --name multivpn-poc-a --port 22261 --public-key local/mac.pub --targets local/lab-targets.json
python poc/linux/poc.py start --name multivpn-poc-b --port 22262 --public-key local/mac.pub --targets local/lab-targets.json
python poc/linux/poc.py export --name multivpn-poc-a --directory local/ssh-a
python poc/linux/poc.py export --name multivpn-poc-b --directory local/ssh-b
```

容器分别拥有独立进程/网络命名空间、文件系统、原厂后台端口和 SSH 主机密钥。宿主管理端口仅绑定 `127.0.0.1`；容器获得 `NET_ADMIN` 和 `/dev/net/tun`，不使用 `--privileged` 或 host 网络。它们仍共享 Docker Linux VM 的内核，不能作为独立虚拟机的安全等价物。

导出的 SSH 配置按容器区分管理与目标身份，并从本机 Docker 控制通道固定管理主机公钥；公钥变化时拒绝自动替换。真实内网目标的 SSH 主机密钥仍须核验。配置不会自动修改用户已有 `~/.ssh/config`。

## 登录与允许测试流量

```sh
python poc/linux/poc.py login --name multivpn-poc-a --directory local/ssh-a
```

此命令固定管理主机身份后，通过真实 SSH 登录会话打开原厂 CLI；直接 `docker exec` 会话在本次原厂版本中保存配置失败。CLI 在 guest 内的 `multivpn-univpn` tmux 会话中运行，管理 SSH 断开时终端继续存在，VPN 不随管理窗口关闭而退出。再次执行 `login` 会接入同一会话；按 `Ctrl-b` 后按 `d` 可退出管理窗口。需要断开 VPN 时在原厂菜单选择 `q`，或停止本工具创建的容器。容器停止或重启不会自动重新认证。

按原厂菜单配置连接、输入现有用户名/密码；工具不把密码放入命令参数、环境变量或镜像，不自动确认证书告警。Linux CLI 的认证兼容性需逐个网关验证，不承诺原厂图形界面的全部 MFA/扫码能力。tmux 会话位于 guest 内；含认证状态的容器仍作为本机敏感资产管理，不发布镜像或终端记录。

登录后另开终端检查并允许目标：

```sh
python poc/linux/poc.py status --name multivpn-poc-a
python poc/linux/poc.py allow --name multivpn-poc-a
ssh -F local/ssh-a/multivpn-poc-a.conf multivpn-poc-a-target-1
```

启动时固定目标策略快照；SSH 导出和守卫使用同一快照，修改宿主列表不会动态扩大当前环境的允许范围。初始 iptables 规则拒绝列表中目标的 TCP 请求；`allow` 要求所有目标实际路由均走 TUN/TAP 设备，再插入按目标、端口和该设备限定的允许规则。回退到普通网卡的包仍命中拒绝规则。`deny` 将拒绝插到已有允许规则前，不通过清空链打开短暂放行窗口。

这只是受限 IPv4/TCP 诊断防护：不能推导为完整 R6 已实现。原厂仍拥有容器内网络管理权限，可能修改防火墙；管理命令会检查守卫钩子，但不存在已验证的持续监督服务。DNS、IPv6、UDP、浏览器、隧道重建、并发竞态及规则被原厂改写的行为仍待验证。未满足出口限制时不要发布产品代理入口。

```sh
python poc/linux/poc.py deny --name multivpn-poc-a
python poc/linux/poc.py stop --name multivpn-poc-a
```

管理操作同时验证名称和所有权标签，拒绝操作其他 Docker 工作负载；`stop` 保留容器、配置和主机密钥卷，可由用户恢复或检查。清理只针对本次创建的容器和卷，禁止全局 prune。

## 接入不读取 SSH 配置的应用

上面的 `ssh -F` 使用 guest 跳板。应用如果只支持主机和端口，直接填内网 IP 仍会走宿主网络，不能因此认定 guest VPN 不通。认证及 `allow` 检查通过后，可为一个已声明的目标建立本地 TCP 入口。以下是 Mac 上的手动诊断示例；先确认本地端口未占用，将示例目标替换为已授权目标：

```sh
ssh -F local/ssh-a/multivpn-poc-a.conf -N \
  -o BatchMode=yes -o ExitOnForwardFailure=yes \
  -o ServerAliveInterval=15 -o ServerAliveCountMax=3 \
  -L 127.0.0.1:22301:192.0.2.10:22 multivpn-poc-a-guest
```

应用的 SSH 主机填写 `127.0.0.1`、端口填写 `22301`，认证仍使用目标服务器的账号和密钥。为不同目标分配不同的本地端口；不绑定其他网卡，不扩大 guest 的目标策略。应用的主机指纹存储可能独立于 OpenSSH，必须把本地入口收到的指纹与可信目标记录核对后再批准。

该命令需要保持运行，`Ctrl-C` 只关闭这条转发；guest 中的 tmux 登录会话继续存在。入口不是系统路由，不能让所有应用直接访问内网 IP。当前没有自动启动、重启恢复或桌面入口管理；Windows 真实接入仍需单独验证。经 SSH 读取远端回环 Agent 的监控应用，只需这条 SSH 入口，无需额外开放 Agent 的入站端口。

## 验收记录

参见[本机 PoC 验证记录](../../docs/validation/linux-isolation-poc.md)。控制测试命令：

```sh
python -m unittest discover -s poc/linux/tests
```

控制测试使用替身，不拨号、不启动 Docker；原厂 CLI 启动、真实认证、双连接目标访问、断开隔离分别记录结果，互不替代。

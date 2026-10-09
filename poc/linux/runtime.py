"""Linux guest diagnostic runtime; no unattended VPN authentication."""
import ipaddress
import json
import os
from pathlib import Path
import re
import subprocess
import sys

CHAIN = 'MULTIVPN_POC'
SOURCE_CONFIG = Path('/run/multivpn/targets.json')
CONFIG = Path('/run/multivpn-effective-targets.json')


def targets():
    rows = json.loads(CONFIG.read_text(encoding='utf-8'))
    if not isinstance(rows, list) or not rows:
        raise ValueError('Provide a nonempty list of explicit IPv4 TCP targets')
    normalized = []
    for row in rows:
        host = str(ipaddress.IPv4Address(row['host']))
        port = row['port']
        if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
            raise ValueError('Invalid target TCP port')
        item = (host, port)
        if item not in normalized:
            normalized.append(item)
    return normalized


def snapshot_targets():
    CONFIG.write_text(SOURCE_CONFIG.read_text(encoding='utf-8'), encoding='utf-8')
    CONFIG.chmod(0o600)
    return targets()


def run(args, **kwargs):
    return subprocess.run(args, check=True, text=True, **kwargs)


def guard_hook():
    exists = subprocess.run(['iptables', '-w', '-C', 'OUTPUT', '-j', CHAIN],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if exists.returncode:
        raise RuntimeError('Target guard hook missing; stop the guest before forwarding')


def deny():
    # First put rejects ahead of existing allows; no flush that briefly permits traffic.
    for host, port in targets():
        run(['iptables', '-w', '-I', CHAIN, '1', '-d', host, '-p', 'tcp',
             '--dport', str(port), '-j', 'REJECT'])


def allow():
    guard_hook()
    rows = targets()
    interfaces = {}
    for host, port in rows:
        route = json.loads(run(['ip', '-j', 'route', 'get', host], capture_output=True).stdout)[0]
        device = route['dev']
        if not re.fullmatch(r'[A-Za-z0-9_.-]{1,15}', device):
            raise RuntimeError('Invalid route interface')
        link = json.loads(run(['ip', '-j', '-d', 'link', 'show', 'dev', device],
                              capture_output=True).stdout)[0]
        kind = link.get('linkinfo', {}).get('info_kind')
        if kind != 'tun':
            raise RuntimeError('Target route is not a TUN/TAP device; leave forwarding denied')
        interfaces[(host, port)] = device
    # Rules keep packets on the observed tunnel; a fallback to eth0 hits REJECT.
    for (host, port), device in interfaces.items():
        run(['iptables', '-w', '-I', CHAIN, '1', '-d', host, '-o', device,
             '-p', 'tcp', '--dport', str(port), '-j', 'ACCEPT'])
    guard_hook()
    print(json.dumps({'target_count': len(rows), 'tunnel_interfaces': sorted(set(interfaces.values()))}))


def status():
    guard_hook()
    print(json.dumps({'targets': [{'host': host, 'port': port} for host, port in targets()],
                      'rules': run(['iptables', '-w', '-S', CHAIN], capture_output=True).stdout.splitlines(),
                      'routes': json.loads(run(['ip', '-j', 'route'], capture_output=True).stdout)}))


def boot():
    import pwd
    os.umask(0o077)
    rows = snapshot_targets()
    parts = Path('/run/multivpn/mac.pub').read_text(encoding='utf-8').split()
    if len(parts) < 2 or parts[0] not in ('ssh-ed25519', 'ssh-rsa', 'ecdsa-sha2-nistp256'):
        raise ValueError('Supply an OpenSSH public key; never mount a private key')
    key_dir = Path('/var/lib/multivpn/ssh')
    key_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    host_key = key_dir / 'ssh_host_ed25519_key'
    if not host_key.exists():
        run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(host_key)])
    account = pwd.getpwnam('vpn')
    ssh_dir = Path(account.pw_dir) / '.ssh'
    ssh_dir.mkdir(mode=0o700, exist_ok=True)
    authorized = ssh_dir / 'authorized_keys'
    authorized.write_text(' '.join(parts[:2]) + '\n', encoding='utf-8')
    authorized.chmod(0o600)
    for path in (ssh_dir, authorized):
        os.chown(path, account.pw_uid, account.pw_gid)
    permit_open = ' '.join(f'{host}:{port}' for host, port in rows)
    Path('/run/multivpn-sshd.conf').write_text(f'''Port 22
HostKey {host_key}
PidFile /run/multivpn-sshd.pid
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
UsePAM no
AllowUsers vpn
AllowTcpForwarding local
AllowAgentForwarding no
X11Forwarding no
PermitTunnel no
GatewayPorts no
PermitOpen {permit_open}
AuthorizedKeysFile .ssh/authorized_keys
''', encoding='utf-8')
    run(['iptables', '-w', '-N', CHAIN])
    deny()
    run(['iptables', '-w', '-I', 'OUTPUT', '1', '-j', CHAIN])
    run(['/usr/sbin/sshd', '-t', '-f', '/run/multivpn-sshd.conf'])
    Path('/run/sshd').mkdir(exist_ok=True)
    # The original client's helper runs only in this container's PID/network namespace.
    log = open('/var/log/multivpn-promote.log', 'a')
    subprocess.Popen(['/usr/local/UniVPN/promote/UniVPNPromoteService'],
                     cwd='/usr/local/UniVPN/promote', stdout=log, stderr=log)
    os.execv('/usr/sbin/sshd', ['/usr/sbin/sshd', '-D', '-e', '-f', '/run/multivpn-sshd.conf'])


if __name__ == '__main__':
    operations = {'boot': boot, 'allow': allow, 'deny': deny, 'status': status}
    if len(sys.argv) != 2 or sys.argv[1] not in operations:
        raise SystemExit('Use boot, allow, deny, or status')
    operations[sys.argv[1]]()

ARG BASE_IMAGE=public.ecr.aws/ubuntu/ubuntu:26.04@sha256:51e35c02a42cf2a6646c5879f5752b38098ed0a20056a989f0af3a3c5e697c9a
FROM ${BASE_IMAGE}

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    ca-certificates iproute2 iptables openssh-server procps python3 tini tmux \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /usr/share/fonts /run/sshd \
    && useradd --create-home --shell /bin/sh vpn \
    && usermod --password '*' vpn \
    && rm -f /etc/ssh/ssh_host_*

# The user supplies the verified original installer. It is never in Git.
COPY client.run /tmp/client.run
RUN cd /tmp && /bin/sh ./client.run > /tmp/vendor-install.log 2>&1 \
    && test -x /usr/local/UniVPN/serviceclient/UniVPNCS \
    && rm -f /tmp/client.run /tmp/vendor-install.log

COPY runtime.py /usr/local/lib/multivpn/runtime.py
LABEL io.multivpn.poc="linux-isolation"
ENTRYPOINT ["/usr/bin/tini", "--", "/usr/bin/python3", "/usr/local/lib/multivpn/runtime.py", "boot"]

#!/bin/bash
# 用户自定义启动脚本：设置SSH密码

SSH_PASSWORD="your_password_here"

if [ -n "$SSH_PASSWORD" ] && [ "$SSH_PASSWORD" != 'your_password_here' ]; then
    echo "root:$SSH_PASSWORD" | chpasswd
    echo "SSH password has been set"

    # 开启密码登录
    sed -i 's/^PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config
    sed -i 's/^PermitRootLogin without-password/PermitRootLogin yes/' /etc/ssh/sshd_config

    # 重启SSH服务
    service ssh restart
    echo "SSH service restarted with password authentication enabled"
else
    echo "Please set SSH_PASSWORD in the script"
fi

#!/usr/bin/env bash

# host信息
host_ip="202.120.39.3" # 传参
host_port="54366" #
host_user="epcc" #

# 变量
# error=0

# 复制公钥
ssh-copy-id -i ~/.ssh/id_rsa.pub epcc@202.120.39.3 -p 54366

# 连接到host
ssh -p ${host_port} ${host_user}@${host_ip} "sudo apt update;sudo apt install apt-transport-https ca-certificates curl software-properties-common -y;curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -;sudo add-apt-repository 'deb [arch=amd64] https://download.docker.com/linux/ubuntu bionic stable';sudo apt update;sudo apt-get install docker-ce -y;sudo curl -L 'https://github.com/docker/compose/releases/download/1.22.0/docker-compose-$(uname -s)-$(uname -m)' -o /usr/local/bin/docker-compose;
sudo chmod +x /usr/local/bin/docker-compose;sudo usermod -aG docker ${host_user};exit;"

# 安装docker
#sudo apt update
#sudo apt install apt-transport-https ca-certificates curl software-properties-common -y
#curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
#sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu bionic stable"
#sudo apt update
#sudo apt-get install docker-ce -y
#
#sudo curl -L "https://github.com/docker/compose/releases/download/1.22.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
#sudo chmod +x /usr/local/bin/docker-compose
#
## add yourself to the docker group and re-login
#sudo usermod -aG docker ${host_user}
#exit
ssh -p ${host_port} ${host_user}@${host_ip} "sudo curl -L 'https://github.com/docker/compose/releases/download/1.23.1/docker-compose-$(uname -s)-$(uname -m)' -o /usr/local/bin/docker-compose;sudo chmod +x /usr/local/bin/docker-compose;sudo apt-get install git -y;git clone https://github.com/olegabu/fabric-starter.git;exit;"

# 安装docker-compose
#sudo curl -L "https://github.com/docker/compose/releases/download/1.23.1/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
#sudo chmod +x /usr/local/bin/docker-compose

# git clone fabric-starter
#sudo apt-get install git -y
#git clone https://github.com/olegabu/fabric-starter.git
#
## 验证前三步是否完成并退出
#exit
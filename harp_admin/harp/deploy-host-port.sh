#!/usr/bin/env bash

# 获取参数
host_user="root"
host_port=""

while getopts :ip:user:port: ARGS
do
case $ARGS in
    ip)
        host_ip=$OPTARG
        ;;
    user)
        host_user=$OPTARG
        ;;
    port)
        host_port=$OPTARG
        ;;
    *)
        echo "Invalid arguments: $ARGS"
        exit 1;;
esac
done

ssh-copy-id -i ~/.ssh/id_rsa.pub ${host_user}@${host_ip} -p ${host_port}

# -p ${host_port}
ssh -p ${host_port} ${host_user}@${host_ip} "sudo apt update;sudo apt install apt-transport-https ca-certificates curl software-properties-common -y;curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -;sudo add-apt-repository 'deb [arch=amd64] https://download.docker.com/linux/ubuntu bionic stable';sudo apt update;sudo apt-get install docker-ce -y;sudo curl -L 'https://github.com/docker/compose/releases/download/1.22.0/docker-compose-$(uname -s)-$(uname -m)' -o /usr/local/bin/docker-compose;
sudo chmod +x /usr/local/bin/docker-compose;sudo usermod -aG docker ${host_user};exit;"

ssh -p ${host_port} ${host_user}@${host_ip} "sudo curl -L 'https://github.com/docker/compose/releases/download/1.23.1/docker-compose-$(uname -s)-$(uname -m)' -o /usr/local/bin/docker-compose;sudo chmod +x /usr/local/bin/docker-compose;sudo apt-get install git -y;git clone https://github.com/olegabu/fabric-starter.git;exit;"


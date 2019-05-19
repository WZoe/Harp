#!/usr/bin/env bash

docker_name=""
host_ip=""
host_user="root"
ssh_port=""
api_port="4000"
daemon_port="2376"
orderer='202.120.39.3:54366'

while getopts :name:ip:user:ssh_port:api_port:daemon_port: ARGS
do
case $ARGS in
    name)
        docker_name=$OPTARG
        ;;
    ip)
        host_ip=$OPTARG
        ;;
    user)
        host_user=$OPTARG
        ;;
    ssh_port)
        ssh_port=$OPTARG
        ;;
    api_port)
        api_port=$OPTARG
        ;;
    daemon_port)
        daemon_port=$OPTARG
        ;;
    *)
        echo "Invalid arguments: $ARGS"
        exit 1;;
esac
done

# create remote docker
docker-machine create --driver generic --generic-ssh-key ~/.ssh/id_rsa --generic-ssh-user ${host_user} --generic-ip-address ${host_ip} --generic-ssh-port ${ssh_port} --generic-engine-port ${daemon_port} ${docker_name}
# In Multihost use (otherwise, commented):
# export MULTIHOST=true
export ORG=${docker_name}
cd ../fabric-starter
docker-machine scp -r templates ${docker_name}:templates
docker-machine scp -r chaincode ${docker_name}:chaincode
docker-machine scp -r webapp ${docker_name}:webapp

# connect remote docker client
eval "$(docker-machine env ${docker_name})"
export API_PORT=${api_port}
export BOOTSTRAP_IP=${orderer}
./generate-peer.sh

# In Multihost use:
# docker-compose -f docker-compose.yaml -f multihost.yaml up -d

# Otherwise use:
docker-compose up -d
docker-compose -f docker-compose.yaml -f docker-compose-couchdb.yaml -f docker-compose-api-port.yaml up -d

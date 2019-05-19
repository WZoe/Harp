import json
import os
import shlex
import subprocess

import requests
from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort

from harp.auth import login_required, admin_required
from harp.db import get_db
from . import codes

bp = Blueprint('status', __name__, url_prefix='/status')


@bp.route('/')
@login_required
def index():
    # db = get_db()
    # orgs = db.execute(
    #     'SELECT o.id, orgname, u.id, username'
    #     ' FROM organization o JOIN user u ON o.id = u.org_id'
    #     ' ORDER BY o.id ASC'
    # ).fetchall()
    org_info = None
    ip = None
    docker_list = []

    # user界面
    if g.user['id'] and g.user['usertype'] == 1:
        org_info = get_db().execute(
            'SELECT o.id, orgname'
            ' FROM organization o JOIN user u on o.id = u.org_id'
            ' WHERE u.id = ?',
            (g.user['id'],)
        ).fetchone()
        ip = get_db().execute(
            'SELECT ip'
            ' FROM organization o JOIN host h ON o.host_id = h.id'
            ' WHERE o.id = ?',
            (org_info[0],)
        ).fetchone()

    # admin界面：master机中docker machine中正在运行docker列表
    # 默认master级为admin所在机，如果需要多机登录admin，ssh到master host
    else:
        cmd = shlex.split('docker-machine ls')
        child = subprocess.Popen(cmd, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        child.wait()
        response = child.communicate()
        response = str(response[0])[2:-3].split('\\n')
        for item in response[1:]:
            if item:
                docker_list.append(item.split())
                if len(docker_list[-1]) == 6:
                    docker_list[-1].append(' ')

                docker_name = docker_list[-1][0]
                if docker_name != 'orderer':
                    id = get_db().execute(
                        'SELECT id'
                        '   FROM organization'
                        '   WHERE orgname=?',
                        (docker_name,)
                    ).fetchone()
                    docker_list[-1].append(id[0])
                else:
                    docker_list[-1].append(None)
    return render_template('status/index.html', org_info=org_info, ip=ip, docker_list=docker_list)


# 创建新docker
# docker类型：orderer或peer/organization
# 通过docker machine由master向worker节点部署
@bp.route('/new', methods=('GET', 'POST'))
@login_required
@admin_required
def new():
    if request.method == 'POST':
        name = request.form['name']
        ip_id = request.form['id']
        api_port = request.form['api_port']
        docker_type = request.form['type']
        d_port = request.form['d_port']

        db = get_db()
        error = None

        if not name:
            error = 'Name is required.'
        elif not ip_id:
            error = 'Host ID is required.'
        elif not api_port:
            error = 'API Port is required.'
        elif not d_port:
            error = 'Docker Daemon Port is required.'
        elif (int(ip_id) < 1) or (int(ip_id) > max(db.execute('SELECT id FROM host').fetchall()[0])):
            error = 'Invalid Host ID.'
        elif db.execute(
                'SELECT id FROM organization WHERE orgname = ?', (name,)
        ).fetchone() is not None:
            error = 'Name {} already exists.'.format(name)

        if error is None:
            if int(docker_type) == 1:
                # 配置新org

                # 查询host信息
                host = db.execute(
                    'SELECT ip, user, port'
                    ' FROM host'
                    ' WHERE h.id = ?',
                    (ip_id,)
                ).fetchone()

                # 新建docker
                cmd = shlex.split(os.path.dirname(
                    os.path.abspath(__file__)) + '/create-org-docker.sh -docker_name ' + name + ' -host_ip ' + host[
                                      0] + ' -host_user ' + host[1] + ' ssh_port ' + host[
                                      2] + ' api_port ' + api_port + ' daemon_port ' + d_port)
                child = subprocess.Popen(cmd, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                child.wait()
                logs = child.communicate()

                db.execute(
                    'INSERT INTO organization (orgname, host_id, api_port, daemon_port) VALUES (?, ?, ?,?)',
                    (name, ip_id, api_port, d_port)
                )
                db.commit()
                flash('Successfully added and deployed! Deployment logs: \n' + str(logs))
                # flash(logs)
                return redirect(url_for('status.index'))
            else:
                pass

        flash(error)

    return render_template('status/new.html')


# 从db中读取org的api登录信息，并检查当前登录user是否属于这个org
def get_org(id, check_user=True):
    org_info = get_db().execute(
        'SELECT orgname, ip, api_port'
        ' FROM organization o JOIN host h ON o.host_id = h.id'
        ' WHERE o.id = ?',
        (id,)
    ).fetchone()

    if org_info is None:
        abort(404, "organization id {0} doesn't exist.".format(id))

    if check_user and id != g.user['org_id'] and g.user['usertype'] == 1:
        abort(403)

    return org_info


# 生成JWT
def get_jwt(id, api_url):
    # 这里的id是user id
    username = get_db().execute(
        'SELECT username FROM user WHERE id=?', (id,)
    ).fetchone()

    if username is None:
        abort(404, "User id {0} doesn't exist.".format(id))

    # response = requests.post(api_url+'/users', headers={'Content-Type': 'application/json'}, data='{"username":"' + username[0] + '","password":"pass"}')
    response = requests.post(api_url + '/users', headers={'Content-Type': 'application/json'},
                             json={"username": username[0] + '_' + str(id), "password": 'pass'})

    # return str(jwt).replace('"', '')
    if response.status_code == 200:
        return json.loads(response.content.decode('utf-8'))
    else:
        # abort(404, "JWT Failed.")
        return None
        # return json.loads(response.content.decode('utf-8'))


# 管理org及查看状态
# 每个org对应不同的id、ip、api端口
@bp.route('/<int:id>/admin', methods=('GET', 'POST'))
@login_required
def admin(id):
    (name, ip, port) = get_org(id)
    api_url = 'http://' + str(ip) + ':' + str(port)
    jwt = get_jwt(g.user['id'], api_url)
    headers = {'Authorization': 'Bearer ' + jwt}
    data_headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + jwt}

    # channels joined
    rchannels = requests.get(api_url + '/channels', headers=headers)
    if rchannels.status_code == 200:
        channels = json.loads(rchannels.content.decode('utf-8'))
    else:
        channels = None

    allchannels = []
    for item in channels:
        allchannels.append(item['channel_id'])

    # 加入或新建channel\
    ###
    # TODO: FIX BUG - return None 已解决
    ###
    if request.method == 'POST':
        chaname = request.form['chaname']
        error = None

        if not chaname:
            error = 'Channel name required.'

        if error is not None:
            flash(error)
        else:
            if chaname not in allchannels:
                # 创建并加入
                ##
                # TODO: 和加入已有channel功能分开，初创时应为channel设定密码
                ##
                rnewch = requests.post(api_url + '/channels', headers=data_headers, json={'channelId': chaname})
                if rnewch.status_code == 200:
                    newch = json.loads(rnewch.content.decode('utf-8'))
                    flash(newch)
                else:
                    newch = None
                    abort(404, "Failed.")
            else:
                # 直接加入
                ###
                # TODO：加入已存在channel需要知道由初创者设置的channel密码
                ###
                rjoin = requests.post(api_url + '/channels/' + chaname, headers=data_headers)
                if rjoin.status_code == 200:
                    join = json.loads(rjoin.content.decode('utf-8'))
                    flash(join)
                else:
                    join = None
                    abort(404, "Failed.")
    return render_template('status/admin.html', id=id, name=name, ip=ip, channels=channels)


@bp.route('/<int:id>/admin/<string:channel>', methods=('GET', 'POST'))
@login_required
def channel(id, channel):
    (name, ip, port) = get_org(id)
    api_url = 'http://' + str(ip) + ':' + str(port)
    jwt = get_jwt(g.user['id'], api_url)
    headers = {'Authorization': 'Bearer ' + jwt}

    # channels joined
    rchannels = requests.get(api_url + '/channels', headers=headers)
    if rchannels.status_code == 200:
        channels = json.loads(rchannels.content.decode('utf-8'))
    else:
        channels = None

    ##
    #   TODO:检查当前channel是否属于当前org，防止通过域名直达
    ##

    # if request.method == 'POST':
    #     # 获取信息
    #     channel = request.form['channel']
    #### 把这个分成一个新的功能，/status/<id>/admin/<channel>
    # channel status
    rstatus = requests.get(api_url + '/channels/' + channel, headers=headers)
    if rstatus.status_code == 200:
        status = json.loads(rstatus.content.decode('utf-8'))
    else:
        status = None

    # channel chaincodes
    rchaincodes = requests.get(api_url + '/channels/' + channel + '/chaincodes', headers=headers)
    if rchaincodes.status_code == 200:
        chaincodes = json.loads(rchaincodes.content.decode('utf-8'))
    else:
        chaincodes = None

    # channel orgs
    rorgs = requests.get(api_url + '/channels/' + channel + '/orgs', headers=headers)
    if rorgs.status_code == 200:
        orgs = json.loads(rorgs.content.decode('utf-8'))
    else:
        orgs = None

    if request.method == 'POST':

        if request.form['action'] == 'QueryBlock':
            query_num = request.form['query_num']
            # channel blocks
            rblocks = requests.get(api_url + '/channels/' + channel + '/blocks/' + query_num, headers=headers)
            if rblocks.status_code == 200:
                blocks = json.loads(rblocks.content.decode('utf-8'))
            else:
                blocks = None
            flash('The contents of block ' + query_num + ' are:\n' + str(blocks))
        elif request.form['action'] == 'QueryTransaction':
            query_id = request.form['query_id']
            # channel transactions
            rtran = requests.get(api_url + '/channels/' + channel + '/transactions/' + query_id, headers=headers)
            if rtran.status_code == 200:
                tran = json.loads(rtran.content.decode('utf-8'))
            else:
                tran = None
            flash('The contents of transaction ' + query_id + ' are:\n' + str(tran))

        # install and instantiate chaincode
        ###
        # TODO：install和instantiate分开
        ###
        elif 'file' in request.files and request.form['action'] == 'Upload':
            version = request.form['version']
            language = request.form['language']
            targets = request.form['targets']
            fcn = request.form['fcn']
            headers = {'Content-Type': 'multipart/form-data', 'Authorization': 'Bearer ' + jwt}

            # INSTALL
            filename = codes.save(request.files['file'])
            flash("Successfully uploaded.")
            rf = requests.post(api_url + '/chaincodes', headers=headers, data=request.form)
            if rf.status_code == 200:
                f = json.loads(rf.content.decode('utf-8'))

                # INSTANTIATE
                headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + jwt}
                rf = requests.post(api_url + '/channels/' + channel + '/chaincodes', headers=headers,
                                   json={'fcn': fcn})
                if rf.status_code == 200:
                    f = json.loads(rf.content.decode('utf-8'))
                else:
                    f = None
                    abort(404, "Failed.")
            else:
                f = None
                abort(404, "Failed.")
            flash(f)

    return render_template('status/channel.html', id=id, name=name, ip=ip, channel=channel,
                           channels=channels, status=status, chaincodes=chaincodes,
                           orgs=orgs)


# 查看某channel上某org安装的chaincode
@bp.route('/<int:id>/admin/<string:channel>/<string:chaincode>', methods=('GET', 'POST'))
@login_required
def chaincode(id, channel, chaincode):
    (name, ip, port) = get_org(id)
    api_url = 'http://' + str(ip) + ':' + str(port)
    jwt = get_jwt(g.user['id'], api_url)
    headers = {'Authorization': 'Bearer ' + jwt}
    data_headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + jwt}

    ##
    #   TODO:检查当前chaincode是否属于当前channel和当前org，防止通过域名直达
    ##

    # invoke
    if request.method == 'POST':
        fcn = request.form['fcn']
        arg = request.form['arg']
        target = request.form['target']
        error = None

        if not fcn:
            error = 'Function name required.'
        elif not arg:
            error = 'Arguments required.'

        if error is not None:
            flash(error)
        else:
            ###
            # TODO: Test
            ###
            if request.form['action'] == 'Invoke':
                if target:
                    data = {"fcn": fcn, "args": '[' + arg + ']', "targets": '[' + target + ']'}
                else:
                    data = {"fcn": fcn, "args": '[' + arg + ']'}
                    rin_code = requests.post(api_url + '/channels/' + channel + '/' + chaincode,
                                             headers=data_headers, json=data)
                    if rin_code.status_code == 200:
                        in_code = json.loads(rin_code.content.decode('utf-8'))
                    else:
                        in_code = None
                    flash('The invoke returns: ' + str(in_code))
            elif request.form['action'] == 'Query':
                if target:
                    url = api_url + '/channels/' + channel + '/' + chaincode + \
                          '/fcn=' + fcn + '&arg=%5B%22' + arg + '%22%5D&targets=%5B%22' + target + '%22%5D'
                else:
                    url = api_url + '/channels/' + channel + '/' + chaincode + \
                          '/fcn=' + fcn + '&arg=%5B%22' + arg + '%22%5D'
                    rq_code = requests.get(url, headers=headers)
                    if rq_code.status_code == 200:
                        q_code = json.loads(rq_code.content.decode('utf-8'))
                    else:
                        q_code = None
                    flash('The query returns: ' + str(q_code))

    return render_template('status/chaincode.html', id=id, name=name, ip=ip, channel=channel,
                           chaincode=chaincode)

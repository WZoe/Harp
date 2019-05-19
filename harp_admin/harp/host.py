import os
import shlex
import subprocess

from flask import (
    Blueprint, flash, redirect, render_template, request, url_for
)

from harp.auth import login_required, admin_required
from harp.db import get_db

bp = Blueprint('host', __name__, url_prefix='/host')


# 所有host列表
@bp.route('/')
@login_required
@admin_required
def index():
    db = get_db()
    hosts = db.execute(
        'SELECT id, ip, port'
        ' FROM host'
        ' ORDER BY id ASC '
    ).fetchall()
    return render_template('host/index.html', hosts=hosts)


###
# 当前host下面所有的docker（org），org可以点进去转到/admin
###
@bp.route('/<int:id>')
@login_required
@admin_required
def org(id):
    db = get_db()
    orgs = db.execute(
        'SELECT o.id, orgname, h.ip'
        ' FROM host h JOIN organization o on h.id = o.host_id'
        ' WHERE h.id = ?',
        (id,)
    ).fetchall()

    if len(orgs) == 0:
        error = 'No organization on this host!'
        flash(error)
        return redirect(url_for('host.index'))

    return render_template('host/org.html', orgs=orgs, id=id)


# 创建新host，提供环境部署
# 前提条件：新host上的user必须为NOPASSWD类型root权限用户
@bp.route('/new', methods=('GET', 'POST'))
@login_required
@admin_required
def new():
    if request.method == 'POST':
        ip = request.form['ip']
        user = request.form['user']
        port = request.form['port']
        deployornot = request.form['deployornot']

        db = get_db()
        error = None

        if not ip:
            error = 'IP is required.'
        elif not user:
            error = 'User is required.'
        elif db.execute(
                'SELECT id FROM host WHERE ip = ?', (ip,)
        ).fetchone() is not None:
            error = 'IP {} already exists.'.format(ip)

        if error is None:
            logs = 'NO DEPLOYMENT'
            if int(deployornot) == 1:
                # 配置新服务器
                cmd = shlex.split(os.path.dirname(
                    os.path.abspath(__file__)) + '/deploy-host-port.sh -ip ' + ip + ' -user ' + user + ' -port ' + port)

                # 测试用
                # cmd=shlex.split(os.path.dirname(os.path.abspath(__file__))+'/deploy-host-dev.sh -ip '+ip+' -user '+user+ ' -port '+port)
                #

                child = subprocess.Popen(cmd, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                child.wait()
                logs = child.communicate()
            db.execute(
                'INSERT INTO host (ip, user, port) VALUES (?, ?, ?)',
                (ip, user, port)
            )
            db.commit()
            flash('Successfully added and deployed! Deployment logs: \n' + str(logs))
            # flash(logs)
            return redirect(url_for('host.index'))

        flash(error)

    return render_template('host/new.html')

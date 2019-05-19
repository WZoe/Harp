import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash

from harp.db import get_db

bp = Blueprint('auth', __name__, url_prefix='/')


# index，登录页面
@bp.route('/', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        error = None
        user = db.execute(
            'SELECT * FROM user WHERE username = ?', (username,)
        ).fetchone()

        if user is None:
            error = 'Incorrect username.'
        elif not check_password_hash(user['password'], password):
            error = 'Incorrect password.'

        if error is None:
            session.clear()
            session['user_id'] = user['id']
            return redirect(url_for('index'))

        flash(error)

    return render_template('auth/index.html')


@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute(
            'SELECT * FROM user WHERE id = ?', (user_id,)
        ).fetchone()


@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


# 装饰器：检查是否已登录
def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            error = "Please log in first!"
            flash(error)
            return redirect(url_for('index'))

        return view(**kwargs)

    return wrapped_view


# 装饰器：检查是否为admin权限
def admin_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user['usertype'] is 1:
            error = "Your user group does not have the privilege!"
            flash(error)
            return redirect(url_for('index'))

        return view(**kwargs)

    return wrapped_view


@bp.route('/register', methods=('GET', 'POST'))
@login_required
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # usertype:
        # 0 - admin
        # 1 - normal user
        if g.user['usertype'] == 0:
            usertype = request.form['usertype']
            org_id = request.form['org_id']
        else:
            org_id = g.user['org_id']
            usertype = 1

        if int(usertype) == 0:
            org_id = None
        db = get_db()
        error = None

        if not username:
            error = 'Username is required.'
        elif not password:
            error = 'Password is required.'
        elif not org_id:
            if int(usertype) == 1:
                error = 'Organization ID is required.'
        elif (int(org_id) < 1) or (int(org_id) > max(db.execute('SELECT id FROM organization').fetchall()[0])):
            error = 'Invalid organization ID.'
        elif db.execute(
                'SELECT id FROM user WHERE username = ?', (username,)
        ).fetchone() is not None:
            error = 'User {} is already registered.'.format(username)

        if error is None:
            # 如果没有填写org_id:
            if not org_id:
                db.execute(
                    'INSERT INTO user (username, password, usertype) VALUES (?, ?, ?)',
                    (username, generate_password_hash(password), int(usertype))
                )
            # 如果填写了org_id：
            else:
                db.execute(
                    'INSERT INTO user (username, password, usertype, org_id) VALUES (?, ?, ?, ?)',
                    (username, generate_password_hash(password), int(usertype), int(org_id))
                )
            db.commit()
            flash('Successfully added!')
            return redirect(url_for('index'))

        flash(error)

    return render_template('auth/register.html')

import os
from datetime import timedelta

from flask import Flask
from flask_uploads import ARCHIVES, UploadSet, configure_uploads

codes = UploadSet('codes')
keys = UploadSet('keys')


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'harp.sqlite'),
    )
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = timedelta(seconds=300)

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # UPLOAD configs
    # chaincode sourse code
    app.config['UPLOADED_CODES_ALLOW'] = ARCHIVES
    app.config['UPLOADED_CODES_DEST'] = './uploaded_file/chaincodes/'
    app.config['UPLOADED_KEYS_DEST'] = './uploaded_file/keys/'
    configure_uploads(app, (codes, keys))

    # database
    from . import db
    db.init_app(app)

    # index and user authorization
    from . import auth
    app.register_blueprint(auth.bp)
    app.add_url_rule('/', endpoint='index')

    # running status
    from . import status
    app.register_blueprint(status.bp)

    # hosts
    from . import host
    app.register_blueprint(host.bp)

    return app

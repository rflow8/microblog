import logging  # noqa: I001
from logging.handlers import RotatingFileHandler, SMTPHandler # dictate where logs are sent
import os

from flask import Flask, request, current_app
from flask_babel import Babel, lazy_gettext as _l
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy

from config import Config
from elasticsearch import Elasticsearch


def get_locale():
    return request.accept_languages.best_match(current_app.config['LANGS'])
    # return 'sw'
    
# initializing extensions(phase 1: extension instances)
db = SQLAlchemy() # represents the database
migrate = Migrate() # database migration engine
login = LoginManager()
login.login_view = 'login' # type: ignore
login.login_message = _l('Please log in to access this page.') # type: ignore
mail = Mail()
moment = Moment() # for local time
babel = Babel()

# factory function
def create_app(config_class=Config): # constructs a Flask application instance, and eliminate the global variable
    app = Flask(__name__) # flask application instance
    app.config.from_object(config_class) # loads config settings from Config class

    # use init_app method to bind extension instances to known application
    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    mail.init_app(app)
    moment.init_app(app)
    babel.init_app(app, locale_selector=get_locale)
    app.elasticsearch = Elasticsearch([app.config['ELASTICSEARCH_URL']]) \
        if app.config['ELASTICSEARCH_URL'] else None

    # blueprint registeration
    from app.errors import bp as errors_bp
    app.register_blueprint(errors_bp)

    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    from app.cli import bp as cli_bp
    app.register_blueprint(cli_bp)

    if not app.debug and app.testing: # when app is not in debug mode, in production or in unit tests
        if app.config['MAIL_SERVER']: # when the email server exists
            auth = None
            if app.config['MAIL_USERNAME'] or app.config['MAIL_PASSWORD']:
                auth = (app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            secure = None
            if app.config['MAIL_USE_TLS']:
                secure = ()
            mail_handler = SMTPHandler(
                mailhost=(app.config['MAIL_SERVER'], app.config['MAIL_PORT']),
                fromaddr='no-reply@' + app.config['MAIL_SERVER'],
                toaddrs=app.config['ADMINS'], subject='Microblog Failure',
                credentials=auth, secure=secure)
            mail_handler.setLevel(logging.ERROR)
            app.logger.addHandler(mail_handler)
        # logging to a file
        if not os.path.exists('logs'):
            os.mkdir('logs')
        # creates a handler that writes logs to a file, rotating it when it hits 10KB
        file_handler = RotatingFileHandler('logs/microblog.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info('Microblog startup')

    return app
# This brings in URL routes, database models and errors
from app import models

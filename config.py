import os

from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    # class configuration variables
    # secret key is useful when generating signatures and tokens
    SECRET_KEY = os.getenv('SECRET_KEY') or 'you_will_never_know' 
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', '').replace(
        'postgres://', 'postgresql://') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    # can also use os.environ.get, same purpose SECRET_KEY = os.environ.get('SECRET_KEY') or 'you_will_never_know'
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.getenv('MAIL_PORT') or 25)
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    ADMINS = ['youremail@example.com'] # noqa: RUF012
    POSTS_PER_PAGE = 8
    LANGS = ['en', 'sw']  # noqa: RUF012
    MS_TRANSLATOR_KEY = os.getenv('MS_TRANSLATOR_KEY')
    ELASTICSEARCH_URL = os.getenv('ELASTICSEARCH_URL')
    REDIS_URL = os.getenv('REDIS_URL') or 'redis://'

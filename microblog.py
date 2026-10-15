# MAIN PYTHON FILE, is pointed to by export FLASK_APP='microblog.py'
# It is the entry point to the server. Points Flask to your application package, app/
import sqlalchemy as sa  # noqa: I001
import sqlalchemy.orm as so
from app import create_app
from app import db
from app.models import User, Post, Notification, Message, Task

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {'sa': sa, 'so': so, 'db': db, 'User': User, 'Post': Post, 'Message': Message, 'Notification': Notification, 'Task': Task}

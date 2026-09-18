from flask_mail import Message # noqa: I001
from threading import Thread
from app import mail
from flask import current_app

def send_asyc_email(app, msg): # send application instance
    with app.app_context():
        mail.send(msg)

def send_email(subject, sender, recipients, text_body, html_body):
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    # current_app._get_current_object() expression extracts the actual application instance from inside the proxy object
    Thread(target=send_asyc_email, args=(current_app._get_current_object(), msg)).start()

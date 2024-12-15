import smtplib
from email.mime.text import MIMEText
from PyQt5.QtCore import QObject

class AlertSystem(QObject):
    def __init__(self, email_config):
        super().__init__()
        self.email_config = email_config

    def send_email_alert(self, subject, body):
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = self.email_config['from']
        msg['To'] = self.email_config['to']

        with smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port']) as server:
            server.starttls()
            server.login(self.email_config['username'], self.email_config['password'])
            server.send_message(msg)


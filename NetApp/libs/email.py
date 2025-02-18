import smtplib
import pathlib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

file_name = pathlib.Path(__file__).name

def send_email(config, subject='', body='', mailto=None, mailfrom=None, high_priority=False):

    # Email configuration
    smtp_server = config.settings['settings']['SMTP']['server']
    smtp_port = int(config.settings['settings']['SMTP']['port'])
    smtp_user = config.settings['settings']['SMTP']['user']
    smtp_password = config.settings['settings']['SMTP']['password']
    auth = config.settings['settings']['SMTP']['auth']

    if not mailto:
        logging.error(f"{file_name} : No To Email address specified")
    if not mailfrom:
        logging.error(f"{file_name} : No From Email address specified")

    # Create the email message
    msg = MIMEMultipart()
    msg['From'] = mailfrom
    msg['To'] = mailto
    msg['Subject'] = subject
    if high_priority:
        msg['X-Priority'] = '1'  # High priority
        msg['X-MSMail-Priority'] = 'High'  # High priority for MS Outlook
    msg.attach(MIMEText(body, 'plain'))

    # Send the email
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        # server.starttls()
        if auth == 'True':
            server.login(smtp_user, smtp_password)
        server.sendmail(mailfrom, mailto, msg.as_string())
        server.quit()
    except Exception as e:
        logging.error(f"{file_name} : Failed to send email: {smtp_server} {e}")

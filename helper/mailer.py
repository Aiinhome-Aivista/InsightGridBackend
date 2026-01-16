import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_email(to_email, subject, html_body):
    gmail_user = os.getenv("GMAIL_USER_COMPANY")
    gmail_pass = os.getenv("GMAIL_APP_PASSWORD_COMPANY")

    msg = MIMEMultipart("alternative")
    msg["From"] = gmail_user
    msg["To"] = to_email
    msg["Subject"] = subject

    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_user, gmail_pass)
            server.send_message(msg)
            print("Mail sent successfully to", to_email)
        return True
    except Exception as e:
        print("MAIL ERROR:", e)
        return False

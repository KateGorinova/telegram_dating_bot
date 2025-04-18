from email.mime.text import MIMEText
from validate_email import validate_email #pip install py3dns (?)
import smtplib


def my_valid_email(email):
    for s in email:
        if s not in 'qwertyuiopasdfghjklzxcvbnm1234567890_.@QWERTYUIOPASDFGHJKLZXCVBNM':
            return False
    if len(email)>50:
        return False
    return True

def send_verification_email(user_email, verification_code, user_id):
    sender_email = "noreplytwinkl@rambler.ru"
    sender_password = ""
    
    smtp_server = "smtp.rambler.ru"
    smtp_port = 587  # для TLS
    server = smtplib.SMTP(smtp_server, smtp_port)
    server.ehlo()
    
    subject = "Подтверждение почты TWINKL"
    message_body = f"Здравствуйте!\n\nДанный почтовый адрес был использован для регистрации в TG-боте @@twinkl_datebot\n\nЕсли это не вы - проигнорируйте данное письмо\n\nИначе, ваш код подтверждения: \n\n{verification_code}\n\nОтвечать на данное сообщение не нужно."
    
    # Создаем сообщение
    msg = MIMEText(message_body)
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = user_email
    
    # Отправляем письмо
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, user_email, msg.as_string())

"""
Envio de email com a chave de licença após pagamento confirmado
"""
import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import settings

logger = logging.getLogger(__name__)


def _build_html(license_key: str, customer_email: str, expires_at: datetime) -> str:
    expires_str = expires_at.strftime("%d/%m/%Y")
    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:Arial,sans-serif;background:#f4f4f4;padding:30px;">
  <div style="max-width:600px;margin:auto;background:#fff;border-radius:10px;padding:40px;">
    <h1 style="color:#ee4d2d;">🛒 {settings.PRODUCT_NAME}</h1>
    <h2 style="color:#333;">Sua licença está pronta!</h2>
    <p>Obrigado pela compra, <strong>{customer_email}</strong>.</p>

    <div style="background:#f8f8f8;border-left:4px solid #ee4d2d;padding:20px;margin:20px 0;border-radius:5px;">
      <p style="margin:0;font-size:13px;color:#666;">Chave de licença:</p>
      <p style="font-size:22px;font-weight:bold;letter-spacing:2px;color:#333;margin:8px 0;">{license_key}</p>
      <p style="margin:0;font-size:12px;color:#999;">Válida até: {expires_str}</p>
    </div>

    <h3>Como ativar:</h3>
    <ol>
      <li>Baixe o bot no link que você recebeu</li>
      <li>Execute o arquivo <strong>ShopeeAffiliateBot.exe</strong></li>
      <li>Cole sua chave de licença na tela de ativação</li>
      <li>Clique em <strong>"Ativar"</strong></li>
    </ol>

    <p style="color:#e74c3c;font-size:12px;">
      ⚠️ A licença fica vinculada ao seu computador após a 1ª ativação.<br>
      Guarde esta chave em local seguro.
    </p>

    <hr style="border:none;border-top:1px solid #eee;margin:30px 0;">
    <p style="color:#999;font-size:12px;">
      Suporte via WhatsApp: (21) 99792-7927<br>
      Este email foi gerado automaticamente.
    </p>
  </div>
</body>
</html>
"""


def send_license_email(
    customer_email: str,
    license_key: str,
    expires_at: datetime,
) -> bool:
    """Envia email com a chave de licença."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"✅ Sua licença {settings.PRODUCT_NAME} — {license_key}"
    msg["From"] = f"{settings.EMAIL_FROM_NAME} <{settings.SMTP_USER}>"
    msg["To"] = customer_email

    html = _build_html(license_key, customer_email, expires_at)
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(settings.SMTP_USER, settings.SMTP_PASS)
            smtp.sendmail(settings.SMTP_USER, customer_email, msg.as_string())
        logger.info(f"Email enviado para {customer_email} — chave: {license_key}")
        return True
    except Exception as e:
        logger.error(f"Erro ao enviar email para {customer_email}: {e}")
        return False

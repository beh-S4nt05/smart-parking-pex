"""Mensagens transacionais Smart Parking: versão texto + HTML acessível.

Templates não incluem credenciais nem URLs não verificadas. O código de
confirmação é inserido somente na mensagem ao destinatário autorizado.
"""
from email.message import EmailMessage
from html import escape
import re


def montar_email_transacional(remetente: str, destino: str, assunto: str, texto: str) -> EmailMessage:
    """Constrói MIME multipart/alternative sem imagens/fontes remotas."""
    msg = EmailMessage()
    msg["From"] = remetente
    msg["To"] = destino
    msg["Subject"] = assunto
    msg.set_content(texto)

    # Código exibido com destaque apenas no e-mail (nunca na resposta API).
    match = re.search(r"(?m)^Seu código de confirmação Smart Parking é: ([0-9]{6})$", texto)
    destaque = (
        '<p style="margin:20px 0;text-align:center;font-size:35px;'
        'font-weight:800;letter-spacing:9px;color:#1d4ed8">'
        f'{match.group(1)}</p>'
        if match else ""
    )
    linhas = "<br>".join(escape(texto).splitlines())
    corpo = f"""<!doctype html>
<html lang="pt-BR">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="margin:0;background:#f3f7fd;padding:28px 12px;font-family:Arial,Helvetica,sans-serif;color:#17253f">
<table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="max-width:540px;margin:auto;border-collapse:collapse;background:#ffffff;border:1px solid #dbe5f3;border-radius:16px">
<tr><td style="background:#0f1e38;color:#ffffff;padding:24px;border-radius:16px 16px 0 0">
  <div style="font-size:20px;font-weight:800;letter-spacing:.5px">SMART PARKING</div>
  <div style="font-size:13px;color:#bbd0eb;margin-top:6px">Segurança da sua conta</div>
</td></tr>
<tr><td style="padding:28px 24px">
  <h1 style="font-size:22px;line-height:1.25;margin:0 0 20px;color:#14233d">{escape(assunto)}</h1>
  {destaque}
  <p style="font-size:15px;line-height:1.7;color:#334155;margin:0">{linhas}</p>
  <p style="font-size:13px;line-height:1.6;color:#64748b;margin:25px 0 0">
    Esta é uma mensagem automática de segurança. Nunca informe o código a terceiros.
  </p>
</td></tr>
<tr><td style="padding:16px 24px;border-top:1px solid #e3eaf4;color:#64748b;font-size:12px">
  Smart Parking · Notificação transacional
</td></tr>
</table>
</body></html>"""
    msg.add_alternative(corpo, subtype="html")
    return msg

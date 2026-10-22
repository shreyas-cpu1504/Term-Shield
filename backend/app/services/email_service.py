import logging
from urllib.parse import quote_plus

import httpx

from app.core.config import get_settings

logger = logging.getLogger("term_shield.email_service")


async def send_password_reset_email(to_email: str, reset_token: str) -> bool:
    """
    Send a password reset email using Resend.

    Security:
    - Never logs the raw reset token or Resend API key.
    - If Resend is not configured, logs a clear server-side error.
    """
    settings = get_settings()

    if not settings.resend_api_key or not settings.resend_api_key.strip():
        logger.error(
            "Password reset email could not be sent: RESEND_API_KEY is not configured in environment/.env."
        )
        return False

    frontend_base = settings.frontend_url.rstrip("/")
    reset_url = f"{frontend_base}/reset-password?token={quote_plus(reset_token)}"

    subject = "Reset your Term Shield password"
    sender = settings.email_from or "Term Shield <onboarding@resend.dev>"

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Reset your Term Shield password</title>
</head>
<body style="margin: 0; padding: 0; background-color: #060814; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #f1f5f9;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color: #060814; padding: 40px 16px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" style="max-width: 560px; background-color: #0b1120; border: 1px solid #1e293b; border-radius: 16px; overflow: hidden; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);" cellspacing="0" cellpadding="0" border="0">
          <!-- Header -->
          <tr>
            <td style="padding: 32px 32px 20px 32px; text-align: center; border-bottom: 1px solid #1e293b; background: linear-gradient(180deg, rgba(30, 41, 59, 0.5) 0%, rgba(11, 17, 32, 0) 100%);">
              <div style="display: inline-block; width: 44px; height: 44px; line-height: 44px; border-radius: 12px; background: rgba(56, 189, 248, 0.12); border: 1px solid rgba(56, 189, 248, 0.3); text-align: center; margin-bottom: 12px;">
                <span style="font-size: 22px;">🛡️</span>
              </div>
              <h1 style="margin: 0; font-size: 20px; font-weight: 700; color: #f8fafc; letter-spacing: -0.02em;">Term Shield</h1>
              <p style="margin: 4px 0 0 0; font-size: 13px; color: #94a3b8; font-weight: 500;">Contract Intelligence</p>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding: 32px;">
              <h2 style="margin: 0 0 16px 0; font-size: 18px; font-weight: 600; color: #f8fafc;">Reset your password</h2>
              <p style="margin: 0 0 20px 0; font-size: 14px; line-height: 1.6; color: #cbd5e1;">
                We received a request to reset the password for your Term Shield account associated with <strong style="color: #38bdf8;">{to_email}</strong>.
              </p>
              <p style="margin: 0 0 28px 0; font-size: 14px; line-height: 1.6; color: #cbd5e1;">
                Click the secure button below to set a new password:
              </p>

              <!-- Action Button -->
              <table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin: 0 auto 28px auto;">
                <tr>
                  <td align="center" style="border-radius: 8px; background: #2563eb;">
                    <a href="{reset_url}" target="_blank" rel="noopener noreferrer" style="display: inline-block; padding: 13px 28px; font-size: 14px; font-weight: 600; color: #ffffff; text-decoration: none; border-radius: 8px; background: #2563eb; letter-spacing: 0.01em;">
                      Reset Password
                    </a>
                  </td>
                </tr>
              </table>

              <!-- Notice Box -->
              <div style="background-color: #0f172a; border: 1px solid #1e293b; border-left: 3px solid #38bdf8; border-radius: 8px; padding: 14px 16px; margin-bottom: 24px;">
                <p style="margin: 0; font-size: 13px; line-height: 1.5; color: #94a3b8;">
                  ⏱️ <strong>Link expiration:</strong> This single-use reset link will expire in <strong>30 minutes</strong>.
                </p>
              </div>

              <!-- Fallback Link -->
              <p style="margin: 0 0 8px 0; font-size: 12px; color: #64748b; line-height: 1.5;">
                If the button above doesn't work, copy and paste this URL into your browser:
              </p>
              <p style="margin: 0 0 24px 0; font-size: 12px; line-height: 1.5; word-break: break-all;">
                <a href="{reset_url}" target="_blank" rel="noopener noreferrer" style="color: #38bdf8; text-decoration: underline;">
                  {reset_url}
                </a>
              </p>

              <hr style="border: 0; border-top: 1px solid #1e293b; margin: 24px 0;" />

              <p style="margin: 0; font-size: 12px; line-height: 1.5; color: #64748b;">
                🛡️ <strong>Didn't request this?</strong> If you did not ask to reset your password, you can safely ignore this email. Your password will not change and your account remains secure.
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding: 16px 32px 24px 32px; text-align: center; border-top: 1px solid #1e293b; background-color: #070b14;">
              <p style="margin: 0; font-size: 12px; color: #475569;">
                &copy; Term Shield. Secure Contract Intelligence.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    text_content = f"""Term Shield — Reset your password

We received a request to reset the password for your Term Shield account ({to_email}).

Please click or open the link below to set a new password:
{reset_url}

This link is valid for 30 minutes and can only be used once.

If you did not request a password reset, you can safely ignore this email. Your password will remain unchanged.

— Term Shield
"""

    payload = {
        "from": sender,
        "to": [to_email],
        "subject": subject,
        "html": html_content,
        "text": text_content,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {settings.resend_api_key.strip()}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )

            if response.status_code in (200, 201):
                logger.info("Password reset email sent successfully to %s", to_email)
                return True

            logger.error(
                "Resend API error dispatching email to %s (Status: %s): %s",
                to_email,
                response.status_code,
                response.text,
            )
            return False

    except Exception as ex:
        logger.error(
            "Network exception while communicating with Resend for %s: %s",
            to_email,
            str(ex),
        )
        return False

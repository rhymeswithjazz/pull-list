"""Email service for sending authentication and notification emails."""

import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def send_magic_link_email(email: str, token: str) -> bool:
    """Send a magic link email to the user.

    Returns True if email was sent successfully, False otherwise.
    """
    if not settings.smtp_configured:
        logger.warning("SMTP not configured, cannot send magic link email")
        return False

    magic_link_url = f"{settings.app_url}/auth/magic-link/{token}"

    # Create message
    message = MIMEMultipart("alternative")
    message["Subject"] = "Wednesday Login Link"
    message["From"] = settings.smtp_from_email
    message["To"] = email

    # Plain text version
    text_content = f"""
Wednesday Login

Click the link below to log in to Wednesday:

{magic_link_url}

This link will expire in {settings.magic_link_expire_minutes} minutes.

If you didn't request this login link, you can safely ignore this email.
"""

    # HTML version
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 10px 10px 0 0; text-align: center;">
        <h1 style="color: white; margin: 0; font-size: 28px;">Wednesday</h1>
        <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0;">Your Comic Book Dashboard</p>
    </div>

    <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; border: 1px solid #eee; border-top: none;">
        <h2 style="margin-top: 0; color: #333;">Login Link</h2>

        <p>Click the button below to log in to Wednesday:</p>

        <div style="text-align: center; margin: 30px 0;">
            <a href="{magic_link_url}"
               style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px 40px; text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 16px;">
                Log In to Wednesday
            </a>
        </div>

        <p style="color: #666; font-size: 14px;">
            This link will expire in <strong>{settings.magic_link_expire_minutes} minutes</strong>.
        </p>

        <p style="color: #666; font-size: 14px;">
            If you didn't request this login link, you can safely ignore this email.
        </p>

        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">

        <p style="color: #999; font-size: 12px; margin-bottom: 0;">
            If the button doesn't work, copy and paste this link into your browser:<br>
            <a href="{magic_link_url}" style="color: #667eea; word-break: break-all;">{magic_link_url}</a>
        </p>
    </div>
</body>
</html>
"""

    message.attach(MIMEText(text_content, "plain"))
    message.attach(MIMEText(html_content, "html"))

    try:
        if settings.smtp_use_tls:
            await aiosmtplib.send(
                message,
                hostname=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_username if settings.smtp_username else None,
                password=settings.smtp_password if settings.smtp_password else None,
                start_tls=True,
            )
        else:
            await aiosmtplib.send(
                message,
                hostname=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_username if settings.smtp_username else None,
                password=settings.smtp_password if settings.smtp_password else None,
            )
        logger.info(f"Magic link email sent to {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send magic link email to {email}: {e}")
        return False


async def send_password_reset_email(email: str, token: str) -> bool:
    """Send a password reset email to the user.

    Returns True if email was sent successfully, False otherwise.
    """
    if not settings.smtp_configured:
        logger.warning("SMTP not configured, cannot send password reset email")
        return False

    reset_url = f"{settings.app_url}/reset-password/{token}"

    # Create message
    message = MIMEMultipart("alternative")
    message["Subject"] = "Wednesday Password Reset"
    message["From"] = settings.smtp_from_email
    message["To"] = email

    # Plain text version
    text_content = f"""
Wednesday Password Reset

Click the link below to reset your password:

{reset_url}

This link will expire in {settings.magic_link_expire_minutes} minutes.

If you didn't request a password reset, you can safely ignore this email.
"""

    # HTML version
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 10px 10px 0 0; text-align: center;">
        <h1 style="color: white; margin: 0; font-size: 28px;">Wednesday</h1>
        <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0;">Your Comic Book Dashboard</p>
    </div>

    <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; border: 1px solid #eee; border-top: none;">
        <h2 style="margin-top: 0; color: #333;">Password Reset</h2>

        <p>Click the button below to reset your password:</p>

        <div style="text-align: center; margin: 30px 0;">
            <a href="{reset_url}"
               style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px 40px; text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 16px;">
                Reset Password
            </a>
        </div>

        <p style="color: #666; font-size: 14px;">
            This link will expire in <strong>{settings.magic_link_expire_minutes} minutes</strong>.
        </p>

        <p style="color: #666; font-size: 14px;">
            If you didn't request a password reset, you can safely ignore this email.
        </p>

        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">

        <p style="color: #999; font-size: 12px; margin-bottom: 0;">
            If the button doesn't work, copy and paste this link into your browser:<br>
            <a href="{reset_url}" style="color: #667eea; word-break: break-all;">{reset_url}</a>
        </p>
    </div>
</body>
</html>
"""

    message.attach(MIMEText(text_content, "plain"))
    message.attach(MIMEText(html_content, "html"))

    try:
        if settings.smtp_use_tls:
            await aiosmtplib.send(
                message,
                hostname=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_username if settings.smtp_username else None,
                password=settings.smtp_password if settings.smtp_password else None,
                start_tls=True,
            )
        else:
            await aiosmtplib.send(
                message,
                hostname=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_username if settings.smtp_username else None,
                password=settings.smtp_password if settings.smtp_password else None,
            )
        logger.info(f"Password reset email sent to {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send password reset email to {email}: {e}")
        return False


async def send_pulllist_notification_email(
    week_id: str,
    items_count: int,
    items: list[dict] | None = None,
) -> bool:
    """Send a pull-list notification email.

    Args:
        week_id: The week ID (e.g., "2024-W48")
        items_count: Number of issues found
        items: Optional list of dicts with series_name and book_number

    Returns True if email was sent successfully, False otherwise.
    """
    if not settings.notifications_enabled:
        logger.debug("Notifications not enabled, skipping pull-list email")
        return False

    dashboard_url = settings.app_url

    # Build items list for email
    items_html = ""
    items_text = ""
    if items:
        items_html = "<ul style='margin: 10px 0; padding-left: 20px;'>"
        for item in items:
            items_html += f"<li style='margin: 5px 0;'><strong>{item['series_name']}</strong> #{item['book_number']}</li>"
            items_text += f"  - {item['series_name']} #{item['book_number']}\n"
        items_html += "</ul>"

    # Create message
    message = MIMEMultipart("alternative")
    message["Subject"] = f"Wednesday Ready: {items_count} issue{'s' if items_count != 1 else ''} for {week_id}"
    message["From"] = settings.smtp_from_email
    message["To"] = settings.notification_email

    # Plain text version
    text_content = f"""
Wednesday Ready!

Your weekly pull-list for {week_id} is ready with {items_count} issue{'s' if items_count != 1 else ''}.

{items_text if items_text else ''}
View your pull-list: {dashboard_url}
"""

    # HTML version
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #FCD34D 0%, #F59E0B 100%); padding: 30px; border-radius: 10px 10px 0 0; text-align: center;">
        <h1 style="color: #1F2937; margin: 0; font-size: 28px;">📚 Wednesday</h1>
        <p style="color: #374151; margin: 10px 0 0 0;">Your Comic Book Dashboard</p>
    </div>

    <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; border: 1px solid #eee; border-top: none;">
        <h2 style="margin-top: 0; color: #333;">New Comics Available!</h2>

        <p>Your weekly pull-list for <strong>{week_id}</strong> is ready with <strong>{items_count} issue{'s' if items_count != 1 else ''}</strong>.</p>

        {items_html if items_html else ''}

        <div style="text-align: center; margin: 30px 0;">
            <a href="{dashboard_url}"
               style="display: inline-block; background: linear-gradient(135deg, #FCD34D 0%, #F59E0B 100%); color: #1F2937; padding: 15px 40px; text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 16px;">
                View Wednesday
            </a>
        </div>

        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">

        <p style="color: #999; font-size: 12px; margin-bottom: 0; text-align: center;">
            A readlist has been created in Komga for easy reading.
        </p>
    </div>
</body>
</html>
"""

    message.attach(MIMEText(text_content, "plain"))
    message.attach(MIMEText(html_content, "html"))

    try:
        if settings.smtp_use_tls:
            await aiosmtplib.send(
                message,
                hostname=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_username if settings.smtp_username else None,
                password=settings.smtp_password if settings.smtp_password else None,
                start_tls=True,
            )
        else:
            await aiosmtplib.send(
                message,
                hostname=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_username if settings.smtp_username else None,
                password=settings.smtp_password if settings.smtp_password else None,
            )
        logger.info(f"Pull-list notification email sent to {settings.notification_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send pull-list notification email: {e}")
        return False

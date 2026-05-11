import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
FROM_NAME = os.getenv("FROM_NAME", "Telite LMS")
APP_URL = os.getenv("TELITE_APP_URL", "http://localhost:5173").rstrip("/")


def send_welcome_email(
    to_email: str,
    name: str,
    username: str,
    password: str,
    role: str,
    college: str,
    branch: str,
) -> bool:
    if not SMTP_USER or not SMTP_PASSWORD:
        print(_build_console_preview(to_email, name, username, password, role, branch))
        return False

    subject = f"Welcome to Telite LMS - Your {role} account is ready"
    html_body = _build_email_html(name, username, password, role, college, branch)
    plain_body = _build_email_plain(name, username, password, role, college, branch)

    try:
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{FROM_NAME} <{SMTP_USER}>"
        message["To"] = to_email

        message.attach(MIMEText(plain_body, "plain"))
        message.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to_email, message.as_string())

        print(f"[EMAIL SENT] Welcome email sent to {to_email}")
        return True
    except smtplib.SMTPAuthenticationError:
        print("[EMAIL ERROR] Gmail authentication failed. Check SMTP_USER and SMTP_PASSWORD in .env")
        print("[EMAIL HINT] Use an App Password, not your Gmail password.")
        print("[EMAIL HINT] Go to myaccount.google.com > Security > App passwords")
        return False
    except Exception as exc:
        print(f"[EMAIL ERROR] {exc}")
        return False


def send_password_reset_email(to_email: str, name: str, token: str, expires_at: str) -> bool:
    reset_url = f"{APP_URL}/reset-password?token={token}"
    if not SMTP_USER or not SMTP_PASSWORD:
        print(
            "\n".join(
                [
                    "-" * 48,
                    "[EMAIL NOT SENT - SMTP not configured]",
                    f"To: {to_email}",
                    "Subject: Reset your Telite LMS password",
                    f"Name: {name}",
                    f"Reset URL: {reset_url}",
                    f"Expires At: {expires_at}",
                    "-" * 48,
                ]
            )
        )
        return False

    subject = "Reset your Telite LMS password"
    plain_body = f"""
Hello {name},

We received a request to reset your Telite LMS password.

Reset link:
  {reset_url}

This link expires at {expires_at}.

If you did not request a reset, you can ignore this email.
    """.strip()
    html_body = f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f8fafc;font-family:sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f8fafc;padding:40px 0;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:12px;border:1px solid #e5e7eb;overflow:hidden;">
        <tr>
          <td style="background:linear-gradient(135deg,#0f766e,#2563eb);padding:28px 32px;">
            <div style="font-size:22px;font-weight:700;color:#fff;">Telite LMS</div>
            <div style="font-size:14px;color:rgba(255,255,255,0.8);margin-top:4px;">Password reset requested</div>
          </td>
        </tr>
        <tr>
          <td style="padding:32px;">
            <p style="font-size:16px;color:#374151;margin:0 0 20px;">Hello <strong>{name}</strong>,</p>
            <p style="font-size:14px;color:#6b7280;margin:0 0 24px;">
              We received a request to reset your Telite LMS password. Use the button below to choose a new one.
            </p>
            <p style="margin:0 0 24px;">
              <a href="{reset_url}" style="display:inline-block;background:#2563eb;color:#fff;text-decoration:none;padding:12px 20px;border-radius:8px;font-weight:600;">
                Reset Password
              </a>
            </p>
            <p style="font-size:13px;color:#6b7280;margin:0 0 12px;">This link expires at {expires_at}.</p>
            <p style="font-size:13px;color:#9ca3af;margin:0;">If you did not request this, you can safely ignore this email.</p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
    """.strip()

    try:
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{FROM_NAME} <{SMTP_USER}>"
        message["To"] = to_email
        message.attach(MIMEText(plain_body, "plain"))
        message.attach(MIMEText(html_body, "html"))
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to_email, message.as_string())
        print(f"[EMAIL SENT] Password reset email sent to {to_email}")
        return True
    except smtplib.SMTPAuthenticationError:
        print("[EMAIL ERROR] Gmail authentication failed. Check SMTP_USER and SMTP_PASSWORD in .env")
        print("[EMAIL HINT] Use an App Password, not your Gmail password.")
        return False
    except Exception as exc:
        print(f"[EMAIL ERROR] {exc}")
        return False


def _build_console_preview(
    to_email: str,
    name: str,
    username: str,
    password: str,
    role: str,
    branch: str,
) -> str:
    return "\n".join(
        [
            "-" * 48,
            "[EMAIL NOT SENT - SMTP not configured]",
            f"To: {to_email}",
            "Subject: Welcome to Telite LMS - Your account is ready",
            f"Name: {name} | Role: {role} | Branch: {branch}",
            f"Username: {username} | Password: {password}",
            "-" * 48,
        ]
    )


def _build_email_plain(name, username, password, role, college, branch):
    return f"""
Hello {name},

Your {role} account on Telite LMS has been verified and created.

Login details:
  Platform : http://localhost:8082
  Username : {username}
  Password : {password}
  Role     : {role}
  College  : {college}
  Branch   : {branch}

Please log in and change your password after first login.

Regards,
Telite LMS Team
    """.strip()


def _build_email_html(name, username, password, role, college, branch):
    role_color = {
        "Student": "#6366f1",
        "Faculty": "#0891b2",
    }.get(role, "#374151")

    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f8fafc;font-family:sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f8fafc;padding:40px 0;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0"
             style="background:#fff;border-radius:12px;border:1px solid #e5e7eb;overflow:hidden;">
        <tr>
          <td style="background:{role_color};padding:28px 32px;">
            <div style="font-size:22px;font-weight:700;color:#fff;">Telite LMS</div>
            <div style="font-size:14px;color:rgba(255,255,255,0.8);margin-top:4px;">
              Your account is ready
            </div>
          </td>
        </tr>
        <tr>
          <td style="padding:32px;">
            <p style="font-size:16px;color:#374151;margin:0 0 20px;">
              Hello <strong>{name}</strong>,
            </p>
            <p style="font-size:14px;color:#6b7280;margin:0 0 24px;">
              Your <strong>{role}</strong> account on Telite LMS has been
              <span style="color:#16a34a;font-weight:600;">verified and created</span>.
              You can now log in using the details below.
            </p>
            <table width="100%" cellpadding="0" cellspacing="0"
                   style="background:#f8fafc;border:1px solid #e5e7eb;
                          border-radius:8px;margin-bottom:24px;">
              <tr>
                <td style="padding:20px;">
                  <table width="100%" cellpadding="4" cellspacing="0"
                         style="font-size:14px;color:#374151;">
                    <tr>
                      <td style="color:#6b7280;width:100px;">Platform</td>
                      <td>
                        <a href="http://localhost:8082" style="color:{role_color};">
                          http://localhost:8082
                        </a>
                      </td>
                    </tr>
                    <tr>
                      <td style="color:#6b7280;">Username</td>
                      <td><strong style="font-family:monospace;">{username}</strong></td>
                    </tr>
                    <tr>
                      <td style="color:#6b7280;">Password</td>
                      <td><strong style="font-family:monospace;">{password}</strong></td>
                    </tr>
                    <tr>
                      <td style="color:#6b7280;">Role</td>
                      <td>
                        <span style="background:{role_color};color:#fff;
                                     font-size:11px;padding:2px 8px;
                                     border-radius:4px;font-weight:600;">
                          {role}
                        </span>
                      </td>
                    </tr>
                    <tr>
                      <td style="color:#6b7280;">College</td>
                      <td>{college}</td>
                    </tr>
                    <tr>
                      <td style="color:#6b7280;">Branch</td>
                      <td>{branch}</td>
                    </tr>
                  </table>
                </td>
              </tr>
            </table>
            <p style="font-size:13px;color:#9ca3af;margin:0;">
              Please change your password after your first login.
            </p>
          </td>
        </tr>
        <tr>
          <td style="padding:16px 32px;border-top:1px solid #f3f4f6;">
            <p style="font-size:12px;color:#9ca3af;margin:0;">
              Telite LMS - {college}
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
    """.strip()


def send_signup_approval_email(to_email: str, name: str, role: str, username: str) -> bool:
    """Send an email when a signup request is approved."""
    if not SMTP_USER or not SMTP_PASSWORD:
        print(f"[MOCK EMAIL] Approval -> {to_email} | Role: {role} | Username: {username}")
        return False

    subject = f"Your Telite LMS account has been approved!"
    html_body = f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f8fafc;font-family:sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f8fafc;padding:40px 0;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0"
             style="background:#fff;border-radius:12px;border:1px solid #e5e7eb;overflow:hidden;">
        <tr>
          <td style="background:linear-gradient(135deg,#059669,#0891b2);padding:28px 32px;">
            <div style="font-size:22px;font-weight:700;color:#fff;">Telite LMS</div>
            <div style="font-size:14px;color:rgba(255,255,255,0.8);margin-top:4px;">
              Registration Approved ✓
            </div>
          </td>
        </tr>
        <tr>
          <td style="padding:32px;">
            <p style="font-size:16px;color:#374151;margin:0 0 20px;">
              Hello <strong>{name}</strong>,
            </p>
            <p style="font-size:14px;color:#6b7280;margin:0 0 24px;">
              Great news! Your registration for the role of <strong>{role}</strong> has been
              <span style="color:#16a34a;font-weight:600;">approved</span> by our administrators.
            </p>
            <table width="100%" cellpadding="0" cellspacing="0"
                   style="background:#f8fafc;border:1px solid #e5e7eb;
                          border-radius:8px;margin-bottom:24px;">
              <tr>
                <td style="padding:20px;">
                  <table width="100%" cellpadding="4" cellspacing="0"
                         style="font-size:14px;color:#374151;">
                    <tr>
                      <td style="color:#6b7280;width:100px;">Username</td>
                      <td><strong style="font-family:monospace;">{username}</strong></td>
                    </tr>
                    <tr>
                      <td style="color:#6b7280;">Role</td>
                      <td>
                        <span style="background:#059669;color:#fff;
                                     font-size:11px;padding:2px 8px;
                                     border-radius:4px;font-weight:600;">
                          {role}
                        </span>
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
            </table>
            <p style="font-size:14px;color:#6b7280;margin:0 0 12px;">
              You can now log in to the platform using the password you set during registration.
            </p>
            <p style="font-size:13px;color:#9ca3af;margin:0;">
              If you did not register, please contact support immediately.
            </p>
          </td>
        </tr>
        <tr>
          <td style="padding:16px 32px;border-top:1px solid #f3f4f6;">
            <p style="font-size:12px;color:#9ca3af;margin:0;">
              Telite LMS — Automated notification
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
    """.strip()

    try:
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{FROM_NAME} <{SMTP_USER}>"
        message["To"] = to_email
        message.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to_email, message.as_string())

        print(f"[EMAIL SENT] Approval email sent to {to_email}")
        return True
    except Exception as exc:
        print(f"[EMAIL ERROR] Approval email failed: {exc}")
        return False


def send_signup_rejection_email(to_email: str, name: str, role: str, reason: str) -> bool:
    """Send an email when a signup request is rejected."""
    if not SMTP_USER or not SMTP_PASSWORD:
        print(f"[MOCK EMAIL] Rejection -> {to_email} | Role: {role} | Reason: {reason}")
        return False

    subject = "Update on your Telite LMS registration"
    html_body = f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f8fafc;font-family:sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f8fafc;padding:40px 0;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0"
             style="background:#fff;border-radius:12px;border:1px solid #e5e7eb;overflow:hidden;">
        <tr>
          <td style="background:linear-gradient(135deg,#dc2626,#f97316);padding:28px 32px;">
            <div style="font-size:22px;font-weight:700;color:#fff;">Telite LMS</div>
            <div style="font-size:14px;color:rgba(255,255,255,0.8);margin-top:4px;">
              Registration Update
            </div>
          </td>
        </tr>
        <tr>
          <td style="padding:32px;">
            <p style="font-size:16px;color:#374151;margin:0 0 20px;">
              Hello <strong>{name}</strong>,
            </p>
            <p style="font-size:14px;color:#6b7280;margin:0 0 16px;">
              We regret to inform you that your registration for the role of
              <strong>{role}</strong> has not been approved at this time.
            </p>
            <div style="background:#fef2f2;border:1px solid #fecaca;border-radius:8px;padding:16px;margin-bottom:24px;">
              <p style="font-size:13px;color:#dc2626;margin:0;font-weight:600;">Reason provided:</p>
              <p style="font-size:14px;color:#374151;margin:8px 0 0;">{reason}</p>
            </div>
            <p style="font-size:13px;color:#9ca3af;margin:0;">
              If you believe this is a mistake, please contact the system administrator.
            </p>
          </td>
        </tr>
        <tr>
          <td style="padding:16px 32px;border-top:1px solid #f3f4f6;">
            <p style="font-size:12px;color:#9ca3af;margin:0;">
              Telite LMS — Automated notification
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
    """.strip()

    try:
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{FROM_NAME} <{SMTP_USER}>"
        message["To"] = to_email
        message.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to_email, message.as_string())

        print(f"[EMAIL SENT] Rejection email sent to {to_email}")
        return True
    except Exception as exc:
        print(f"[EMAIL ERROR] Rejection email failed: {exc}")
        return False

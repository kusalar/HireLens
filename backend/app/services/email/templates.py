import html
from datetime import datetime
from typing import Optional, Tuple
from app.core.timezone import convert_utc_to_timezone, DEFAULT_TIMEZONE


def format_interview_ist_range(start_utc: datetime, end_utc: datetime) -> str:
    """Format start and end times in Asia/Kolkata with explicit IST (UTC+05:30) label."""
    if not start_utc or not end_utc:
        return "TBD"
    ist_start = convert_utc_to_timezone(start_utc, DEFAULT_TIMEZONE)
    ist_end = convert_utc_to_timezone(end_utc, DEFAULT_TIMEZONE)

    date_str = ist_start.strftime("%d %b %Y")
    start_time = ist_start.strftime("%I:%M %p")
    end_time = ist_end.strftime("%I:%M %p")
    return f"{date_str}, {start_time} - {end_time} IST (UTC+05:30)"


def _wrap_base_html(title: str, content_html: str, agency_name: str) -> str:
    safe_title = html.escape(title)
    safe_agency = html.escape(agency_name)
    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{safe_title}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; color: #1e293b; margin: 0; padding: 24px; }}
    .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; }}
    .header {{ background-color: #0f172a; color: #ffffff; padding: 24px 32px; text-align: left; }}
    .header h1 {{ margin: 0; font-size: 20px; font-weight: 600; letter-spacing: -0.02em; }}
    .header p {{ margin: 4px 0 0; font-size: 13px; color: #94a3b8; }}
    .content {{ padding: 32px; font-size: 14px; line-height: 1.6; color: #334155; }}
    .badge {{ display: inline-block; padding: 4px 10px; background-color: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; border-radius: 4px; font-weight: 600; font-size: 12px; }}
    .info-card {{ background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 16px 20px; margin: 20px 0; }}
    .info-row {{ display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px; }}
    .info-label {{ color: #64748b; font-weight: 500; }}
    .info-val {{ color: #0f172a; font-weight: 600; text-align: right; }}
    .btn {{ display: inline-block; background-color: #2563eb; color: #ffffff; text-decoration: none; padding: 10px 20px; border-radius: 6px; font-size: 13px; font-weight: 600; margin-top: 16px; }}
    .footer {{ background-color: #f8fafc; border-top: 1px solid #e2e8f0; padding: 16px 32px; text-align: center; font-size: 12px; color: #94a3b8; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>{safe_agency}</h1>
      <p>Recruitment Communication Service</p>
    </div>
    <div class="content">
      {content_html}
    </div>
    <div class="footer">
      <p>Sent via HireLens AI Multi-Tenant Workspace &bull; All times formatted in Indian Standard Time (IST).</p>
    </div>
  </div>
</body>
</html>"""


def render_interview_invitation(
    recipient_name: str,
    job_title: str,
    round_name: str,
    start_utc: datetime,
    end_utc: datetime,
    interview_mode: str,
    meeting_url: Optional[str] = None,
    location: Optional[str] = None,
    agency_name: str = "HireLens Agency",
    is_candidate: bool = True,
) -> Tuple[str, str, str]:
    """Generate subject, html, and plain text for an interview invitation."""
    subject = f"Interview Scheduled: {round_name} for {job_title}"
    time_str = format_interview_ist_range(start_utc, end_utc)
    safe_recip = html.escape(recipient_name)
    safe_job = html.escape(job_title)
    safe_round = html.escape(round_name)
    safe_mode = html.escape(interview_mode)

    meeting_info_html = ""
    meeting_info_text = ""
    if meeting_url:
        safe_url = html.escape(meeting_url)
        meeting_info_html = f'<div class="info-row"><span class="info-label">Meeting URL:</span><span class="info-val"><a href="{safe_url}" style="color:#2563eb;">Join Meeting</a></span></div>'
        meeting_info_text = f"\nMeeting URL: {meeting_url}"
    elif location:
        safe_loc = html.escape(location)
        meeting_info_html = f'<div class="info-row"><span class="info-label">Location:</span><span class="info-val">{safe_loc}</span></div>'
        meeting_info_text = f"\nLocation: {location}"

    role_intro = (
        f"<p>Hello <strong>{safe_recip}</strong>,</p><p>You have been invited to participate in an interview for the position of <strong>{safe_job}</strong>.</p>"
        if is_candidate
        else f"<p>Hello <strong>{safe_recip}</strong>,</p><p>You are scheduled as an interviewer for <strong>{safe_job}</strong>.</p>"
    )

    body_html = _wrap_base_html(
        title=subject,
        agency_name=agency_name,
        content_html=f"""
        {role_intro}
        <div class="info-card">
          <div class="info-row"><span class="info-label">Round:</span><span class="info-val">{safe_round}</span></div>
          <div class="info-row"><span class="info-label">Date & Time:</span><span class="info-val">{time_str}</span></div>
          <div class="info-row"><span class="info-label">Format:</span><span class="info-val">{safe_mode}</span></div>
          {meeting_info_html}
        </div>
        <p style="font-size:12px; color:#64748b;">Please be available 5 minutes prior to the scheduled start time.</p>
        """,
    )

    body_text = f"""Hello {recipient_name},

An interview has been scheduled for {job_title}.

Round: {round_name}
Date & Time: {time_str}
Format: {interview_mode}{meeting_info_text}

Please be prepared 5 minutes prior to start.

Regards,
{agency_name} Recruitment Team
(HireLens AI)
"""
    return subject, body_html, body_text


def render_interview_rescheduled(
    recipient_name: str,
    job_title: str,
    round_name: str,
    new_start_utc: datetime,
    new_end_utc: datetime,
    old_start_utc: Optional[datetime],
    old_end_utc: Optional[datetime],
    reason: Optional[str] = None,
    meeting_url: Optional[str] = None,
    agency_name: str = "HireLens Agency",
) -> Tuple[str, str, str]:
    """Generate subject, html, and plain text for an interview rescheduling event."""
    subject = f"Interview Rescheduled: {round_name} for {job_title}"
    new_time_str = format_interview_ist_range(new_start_utc, new_end_utc)
    old_time_str = format_interview_ist_range(old_start_utc, old_end_utc) if (old_start_utc and old_end_utc) else "Previously Scheduled Slot"

    safe_recip = html.escape(recipient_name)
    safe_job = html.escape(job_title)
    safe_round = html.escape(round_name)
    safe_reason = html.escape(reason) if reason else "Schedule adjustment"

    link_html = f'<div class="info-row"><span class="info-label">Meeting URL:</span><span class="info-val"><a href="{html.escape(meeting_url)}" style="color:#2563eb;">Join Meeting</a></span></div>' if meeting_url else ""
    link_text = f"\nMeeting URL: {meeting_url}" if meeting_url else ""

    body_html = _wrap_base_html(
        title=subject,
        agency_name=agency_name,
        content_html=f"""
        <p>Hello <strong>{safe_recip}</strong>,</p>
        <p>Your interview round for <strong>{safe_job}</strong> has been rescheduled to a new time slot.</p>
        <div class="info-card">
          <div class="info-row"><span class="info-label">Round:</span><span class="info-val">{safe_round}</span></div>
          <div class="info-row"><span class="info-label">New Date & Time:</span><span class="info-val" style="color:#2563eb;">{new_time_str}</span></div>
          <div class="info-row"><span class="info-label">Previous Slot:</span><span class="info-val" style="color:#94a3b8; text-decoration:line-through;">{old_time_str}</span></div>
          <div class="info-row"><span class="info-label">Reason:</span><span class="info-val">{safe_reason}</span></div>
          {link_html}
        </div>
        <p style="font-size:12px; color:#64748b;">Please review your calendar accordingly.</p>
        """,
    )

    body_text = f"""Hello {recipient_name},

Your interview round for {job_title} has been rescheduled.

Round: {round_name}
New Date & Time: {new_time_str}
Previous Slot: {old_time_str}
Reason: {reason or 'Schedule adjustment'}{link_text}

Regards,
{agency_name} Recruitment Team
"""
    return subject, body_html, body_text


def render_interview_confirmed(
    recipient_name: str,
    job_title: str,
    round_name: str,
    start_utc: datetime,
    end_utc: datetime,
    agency_name: str = "HireLens Agency",
) -> Tuple[str, str, str]:
    """Generate subject, html, and plain text for an interview confirmation."""
    subject = f"Interview Confirmed: {round_name} for {job_title}"
    time_str = format_interview_ist_range(start_utc, end_utc)

    safe_recip = html.escape(recipient_name)
    safe_job = html.escape(job_title)
    safe_round = html.escape(round_name)

    body_html = _wrap_base_html(
        title=subject,
        agency_name=agency_name,
        content_html=f"""
        <p>Hello <strong>{safe_recip}</strong>,</p>
        <p>Your interview round has been officially <strong>confirmed</strong>.</p>
        <div class="info-card">
          <div class="info-row"><span class="info-label">Job:</span><span class="info-val">{safe_job}</span></div>
          <div class="info-row"><span class="info-label">Round:</span><span class="info-val">{safe_round}</span></div>
          <div class="info-row"><span class="info-label">Date & Time:</span><span class="info-val">{time_str}</span></div>
        </div>
        """,
    )

    body_text = f"""Hello {recipient_name},

Your interview round for {job_title} ({round_name}) on {time_str} has been confirmed.

Regards,
{agency_name} Recruitment Team
"""
    return subject, body_html, body_text


def render_interview_cancelled(
    recipient_name: str,
    job_title: str,
    round_name: str,
    start_utc: datetime,
    end_utc: datetime,
    reason: Optional[str] = None,
    agency_name: str = "HireLens Agency",
) -> Tuple[str, str, str]:
    """Generate subject, html, and plain text for an interview cancellation."""
    subject = f"Interview Cancelled: {round_name} for {job_title}"
    time_str = format_interview_ist_range(start_utc, end_utc)

    safe_recip = html.escape(recipient_name)
    safe_job = html.escape(job_title)
    safe_round = html.escape(round_name)
    safe_reason = html.escape(reason) if reason else "Operational requirement"

    body_html = _wrap_base_html(
        title=subject,
        agency_name=agency_name,
        content_html=f"""
        <p>Hello <strong>{safe_recip}</strong>,</p>
        <p>The following interview round has been cancelled.</p>
        <div class="info-card">
          <div class="info-row"><span class="info-label">Job:</span><span class="info-val">{safe_job}</span></div>
          <div class="info-row"><span class="info-label">Round:</span><span class="info-val">{safe_round}</span></div>
          <div class="info-row"><span class="info-label">Slot:</span><span class="info-val">{time_str}</span></div>
          <div class="info-row"><span class="info-label">Reason:</span><span class="info-val">{safe_reason}</span></div>
        </div>
        <p style="font-size:12px; color:#64748b;">Our recruiting team will reach out with any further updates.</p>
        """,
    )

    body_text = f"""Hello {recipient_name},

The interview for {job_title} ({round_name}) scheduled for {time_str} has been cancelled.
Reason: {reason or 'Operational requirement'}

Regards,
{agency_name} Recruitment Team
"""
    return subject, body_html, body_text


def render_application_status_update(
    recipient_name: str,
    job_title: str,
    new_stage: str,
    agency_name: str = "HireLens Agency",
    is_candidate: bool = True,
) -> Tuple[str, str, str]:
    """Generate subject, html, and plain text for application stage updates.
    NOTE: Internal recruiter notes and private evaluation data are STRICTLY EXCLUDED.
    """
    subject = f"Application Status Update: {job_title}"
    safe_recip = html.escape(recipient_name)
    safe_job = html.escape(job_title)
    formatted_stage = new_stage.replace("_", " ").title()
    safe_stage = html.escape(formatted_stage)

    body_html = _wrap_base_html(
        title=subject,
        agency_name=agency_name,
        content_html=f"""
        <p>Hello <strong>{safe_recip}</strong>,</p>
        <p>There is an update on the application for the position of <strong>{safe_job}</strong>.</p>
        <div class="info-card">
          <div class="info-row"><span class="info-label">Current Status:</span><span class="info-val"><span class="badge">{safe_stage}</span></span></div>
        </div>
        <p style="font-size:12px; color:#64748b;">Thank you for your interest in {html.escape(agency_name)}.</p>
        """,
    )

    body_text = f"""Hello {recipient_name},

There is an update on the application for {job_title}.

Current Status: {formatted_stage}

Regards,
{agency_name} Recruitment Team
"""
    return subject, body_html, body_text

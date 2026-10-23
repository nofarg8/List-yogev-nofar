#!/usr/bin/env python3
"""Email Yogev and Nofar about everything that was ADDED to data.json.

Usage: notify.py OLD_JSON NEW_JSON
Env:   MAIL_USERNAME, MAIL_PASSWORD (Gmail app password), MAIL_TO (comma separated),
       SITE_URL (optional), DRY_RUN=1 to print instead of sending.
"""
import html
import json
import os
import smtplib
import sys
from email.message import EmailMessage

WHO = {"yogev": "יוגב", "nofar": "נופר", "both": "שנינו"}
DAYS = ["שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת", "ראשון"]  # date.weekday() order
SITE = os.environ.get("SITE_URL", "https://nofarg8.github.io/List-yogev-nofar/")


def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def fmt_day(iso):
    import datetime
    try:
        d = datetime.date.fromisoformat(iso)
    except (TypeError, ValueError):
        return iso or ""
    return f"{d:%d.%m.%y} · יום {DAYS[d.weekday()]}"


def personal(data):
    out = {}
    for owner, corner in (data.get("personal") or {}).items():
        for lst in (corner or {}).get("lists", []):
            out[(owner, lst.get("id"))] = lst
    return out


def diff(old, new):
    """Return the additions as a list of (section, who_added, text)."""
    adds = []
    old_days = {d.get("id") for d in old.get("days", [])}
    for d in new.get("days", []):
        if d.get("id") not in old_days:
            adds.append(("יום חדש", WHO.get(d.get("by"), ""), fmt_day(d.get("date"))))
    old_tasks = {t.get("id") for t in old.get("tasks", [])}
    for t in new.get("tasks", []):
        if t.get("id") not in old_tasks:
            resp = WHO.get(t.get("who"), "")
            text = t.get("text", "")
            meta = fmt_day(t.get("day")) + (f" · אחראי: {resp}" if resp else "")
            adds.append(("משימה חדשה", WHO.get(t.get("by"), ""), f"{text}||{meta}"))
    old_p, new_p = personal(old), personal(new)
    for key, lst in new_p.items():
        owner = key[0]
        corner = f"{WHO.get(owner, owner)} בלבד"
        if key not in old_p:
            adds.append((corner, WHO.get(owner, ""), f"רשימה חדשה: {lst.get('title', '')}||"))
        old_items = {i.get("id") for i in (old_p.get(key) or {}).get("items", [])}
        for it in lst.get("items", []):
            if it.get("id") not in old_items:
                adds.append((corner, WHO.get(owner, ""), f"{it.get('text', '')}||ברשימה: {lst.get('title', '')}"))
    return adds


def build(adds):
    who = sorted({w for _, w, _ in adds if w})
    by = " ו".join(who) if who else "מישהו"
    verb = "הוסיפו" if len(who) > 1 else ("הוסיפה" if who == ["נופר"] else "הוסיף")
    n = len(adds)
    what = "דבר אחד" if n == 1 else f"{n} דברים"
    subject = f"To Go List: {by} {verb} {what} לרשימה"
    rows_txt, rows_html = [], []
    for section, w, text in adds:
        main, _, meta = text.partition("||")
        rows_txt.append(f"• [{section}] {main}" + (f" ({meta})" if meta else "") + (f" – נוסף ע״י {w}" if w else ""))
        rows_html.append(
            '<tr><td style="padding:12px 14px;border-bottom:1px solid #EADFD5">'
            f'<div style="font-size:12px;font-weight:700;color:#B8692C">{html.escape(section)}'
            + (f" · נוסף ע״י {html.escape(w)}" if w else "") + "</div>"
            f'<div style="font-size:16px;font-weight:700;color:#221C19;margin-top:2px">{html.escape(main)}</div>'
            + (f'<div style="font-size:13px;color:#6E615A;margin-top:2px">{html.escape(meta)}</div>' if meta else "")
            + "</td></tr>"
        )
    text = "\n".join([f"{by} {verb} לרשימה:", "", *rows_txt, "", f"לפתיחת הרשימה: {SITE}"])
    body = f"""<!doctype html><html lang="he" dir="rtl"><body style="margin:0;background:#FBF6F1;font-family:Arial,Helvetica,sans-serif">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#FBF6F1"><tr><td align="center" style="padding:24px 12px">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" dir="rtl" style="max-width:560px;background:#FFFFFF;border-radius:14px;overflow:hidden;text-align:right">
<tr><td style="padding:0"><img src="{SITE}assets/og-image.jpg" width="560" alt="To Go List" style="display:block;width:100%;height:auto"></td></tr>
<tr><td style="padding:20px 18px 6px"><div style="font-size:22px;font-weight:700;color:#221C19">משהו חדש ברשימה 🐾</div>
<div style="font-size:15px;color:#6E615A;margin-top:4px">{html.escape(by)} {verb} {what}:</div></td></tr>
<tr><td style="padding:6px 18px"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" dir="rtl" style="background:#FFF9F2;border-radius:10px">{''.join(rows_html)}</table></td></tr>
<tr><td align="center" style="padding:20px 18px 26px"><a href="{SITE}" style="display:inline-block;background:#1F1A18;color:#FFF7EF;text-decoration:none;font-weight:700;font-size:16px;padding:12px 26px;border-radius:10px">לפתיחת הרשימה</a></td></tr>
<tr><td align="center" style="padding:0 18px 20px;font-size:12px;color:#6E615A">דברים לעשות – יוגב ונופר · אוקסי שומרת על הרשימה</td></tr>
</table></td></tr></table></body></html>"""
    return subject, text, body


def main():
    old, new = load(sys.argv[1]), load(sys.argv[2])
    adds = diff(old, new)
    if not adds:
        print("Nothing was added; no email.")
        return
    subject, text, body = build(adds)
    if os.environ.get("DRY_RUN"):
        print(subject)
        print(text)
        return
    user, pw = os.environ["MAIL_USERNAME"], os.environ["MAIL_PASSWORD"]
    to = [a.strip() for a in os.environ.get("MAIL_TO", user).split(",") if a.strip()]
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = subject, f"To Go List <{user}>", ", ".join(to)
    msg.set_content(text)
    msg.add_alternative(body, subtype="html")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(user, pw)
        s.send_message(msg)
    print(f"Sent: {subject} -> {len(to)} recipient(s)")


if __name__ == "__main__":
    main()

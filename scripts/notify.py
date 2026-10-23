#!/usr/bin/env python3
"""Email Yogev / Nofar about what the OTHER one added or deleted in data.json.

Usage: notify.py OLD_JSON NEW_JSON
Env:   MAIL_USERNAME (Nofar's Gmail, also the sender), MAIL_PASSWORD (Gmail app password),
       MAIL_TO (comma separated: Nofar's and Yogev's addresses), SITE_URL (optional),
       DRY_RUN=1 to print instead of sending.
"""
import datetime
import html
import json
import os
import smtplib
import sys
from email.message import EmailMessage

NAME = {"yogev": "יוגב", "nofar": "נופר", "both": "שנינו"}
WEEKDAY = ["שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת", "ראשון"]  # date.weekday() order
SITE = os.environ.get("SITE_URL", "https://nofarg8.github.io/List-yogev-nofar/")


def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def day_name(iso):
    try:
        d = datetime.date.fromisoformat(iso)
    except (TypeError, ValueError):
        return iso or ""
    return f"יום {WEEKDAY[d.weekday()]} {d:%d.%m.%y}"


def verb(who, male, female):
    return female if who == "nofar" else male


def lists_of(data):
    out = {}
    for owner, corner in (data.get("personal") or {}).items():
        for lst in (corner or {}).get("lists", []):
            out[(owner, lst.get("id"))] = lst
    return out


def changes(old, new):
    """Every addition / task deletion as a dict: who, line (sentence), detail."""
    out = []
    old_days = {d.get("id") for d in old.get("days", [])}
    for d in new.get("days", []):
        if d.get("id") not in old_days:
            w = d.get("by")
            out.append({"who": w, "line": f"{NAME.get(w, 'מישהו')} {verb(w, 'הוסיף', 'הוסיפה')} יום חדש לרשימה: {day_name(d.get('date'))}", "label": "", "detail": ""})
    old_tasks = {t.get("id") for t in old.get("tasks", [])}
    for t in new.get("tasks", []):
        if t.get("id") not in old_tasks:
            w = t.get("by")
            out.append({"who": w, "line": f"{NAME.get(w, 'מישהו')} {verb(w, 'הוסיף', 'הוסיפה')} משימה ל{day_name(t.get('day'))}", "label": "המשימה היא:", "detail": t.get("text", "")})
    old_del = {x.get("id") for x in old.get("deleted", [])}
    for x in new.get("deleted", []):
        if x.get("id") not in old_del:
            w = x.get("by")
            out.append({"who": w, "line": f"{NAME.get(w, 'מישהו')} {verb(w, 'מחק', 'מחקה')} משימה מ{day_name(x.get('day'))}", "label": "המשימה שנמחקה:", "detail": x.get("text", ""), "gone": True})
    old_l, new_l = lists_of(old), lists_of(new)
    for (owner, lid), lst in new_l.items():
        title = lst.get("title", "")
        if (owner, lid) not in old_l:
            out.append({"who": owner, "line": f"{NAME.get(owner)} {verb(owner, 'פתח', 'פתחה')} רשימה חדשה ב\"{NAME.get(owner)} בלבד\"", "label": "שם הרשימה:", "detail": title})
        seen = {i.get("id") for i in (old_l.get((owner, lid)) or {}).get("items", [])}
        for it in lst.get("items", []):
            if it.get("id") not in seen:
                out.append({"who": owner, "line": f"{NAME.get(owner)} {verb(owner, 'הוסיף', 'הוסיפה')} לרשימה \"{title}\"", "label": "מה נכתב:", "detail": it.get("text", "")})
    return out


def build(items):
    subject = "To Go List: " + (items[0]["line"] if len(items) == 1 else f"{len(items)} עדכונים חדשים ברשימה")
    txt, rows = [], []
    for it in items:
        txt += [it["line"]] + ([f"{it['label']} {it['detail']}"] if it["detail"] else []) + [""]
        detail_style = "color:#C02A44;text-decoration:line-through" if it.get("gone") else "color:#221C19"
        rows.append(
            '<tr><td style="padding:14px 16px;border-bottom:1px solid #EADFD5">'
            f'<div style="font-size:16px;font-weight:700;color:#B8692C">{html.escape(it["line"])}</div>'
            + (f'<div style="font-size:15px;color:#6E615A;margin-top:6px">{html.escape(it["label"])}</div>'
               f'<div style="font-size:18px;font-weight:700;margin-top:2px;{detail_style}">{html.escape(it["detail"])}</div>' if it["detail"] else "")
            + "</td></tr>"
        )
    txt += [f"לפתיחת הרשימה: {SITE}"]
    body = f"""<!doctype html><html lang="he" dir="rtl"><body style="margin:0;background:#FBF6F1;font-family:Arial,Helvetica,sans-serif">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#FBF6F1"><tr><td align="center" style="padding:24px 12px">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" dir="rtl" style="max-width:560px;background:#FFFFFF;border-radius:14px;overflow:hidden;text-align:right">
<tr><td style="padding:0"><img src="{SITE}assets/og-image.jpg" width="560" alt="To Go List" style="display:block;width:100%;height:auto"></td></tr>
<tr><td style="padding:16px 18px 6px"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" dir="rtl" style="background:#FFF9F2;border-radius:10px">{''.join(rows)}</table></td></tr>
<tr><td align="center" style="padding:20px 18px 26px"><a href="{SITE}" style="display:inline-block;background:#1F1A18;color:#FFF7EF;text-decoration:none;font-weight:700;font-size:16px;padding:12px 26px;border-radius:10px">לפתיחת הרשימה</a></td></tr>
<tr><td align="center" style="padding:0 18px 20px;font-size:12px;color:#6E615A">דברים לעשות – יוגב ונופר · אוקסי שומרת על הרשימה 🐾</td></tr>
</table></td></tr></table></body></html>"""
    return subject, "\n".join(txt), body


def send(user, pw, to, items):
    subject, text, body = build(items)
    if os.environ.get("DRY_RUN"):
        print(f"-> {', '.join(to)}\n{subject}\n{text}\n")
        return
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = subject, f"To Go List <{user}>", ", ".join(to)
    msg.set_content(text)
    msg.add_alternative(body, subtype="html")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(user, pw)
        s.send_message(msg)
    print(f"Sent: {subject} -> {len(to)} recipient(s)")


def main():
    items = changes(load(sys.argv[1]), load(sys.argv[2]))
    if not items:
        print("Nothing was added or deleted; no email.")
        return
    user = os.environ.get("MAIL_USERNAME", "")
    pw = os.environ.get("MAIL_PASSWORD", "")
    everyone = [a.strip() for a in os.environ.get("MAIL_TO", user).split(",") if a.strip()]
    # Nofar's address is the sending account; everyone else on the list is Yogev.
    nofar = [a for a in everyone if a.lower() == user.lower()] or [user]
    yogev = [a for a in everyone if a.lower() != user.lower()]
    # each person hears only about what the OTHER one did (unknown author -> both)
    for to, me in ((nofar, "nofar"), (yogev, "yogev")):
        mine = [i for i in items if i["who"] != me]
        if to and mine:
            send(user, pw, to, mine)


if __name__ == "__main__":
    main()

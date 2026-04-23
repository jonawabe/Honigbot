"""
Honigwabe Connoisseure Bielefeld & Umgebung – Telegram Bot
Stack: python-telegram-bot v20, SQLite
Hosting: Railway
"""
import os
import logging
import sqlite3
from datetime import datetime, timedelta
from functools import wraps
from telegram import Update, ChatPermissions
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ── Config ────────────────────────────────────────────────────────────────────
TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN fehlt in den Environment Variables")

MAX_WARNS = 3
MUTE_MINUTES = 60

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(__name__)

# ── Datenbank ─────────────────────────────────────────────────────────────────
DB = "honigwabe.db"

def db():
    return sqlite3.connect(DB)

def init_db():
    with db() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS warnings (
                user_id INTEGER,
                chat_id INTEGER,
                reason TEXT,
                issued_at TEXT,
                PRIMARY KEY (user_id, chat_id, issued_at)
            );
            CREATE TABLE IF NOT EXISTS join_requests (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                status TEXT DEFAULT 'pending',
                requested_at TEXT
            );
            CREATE TABLE IF NOT EXISTS introductions (
                user_id INTEGER,
                chat_id INTEGER,
                text TEXT,
                submitted_at TEXT
            );
            CREATE TABLE IF NOT EXISTS reports (
                reporter_id INTEGER,
                reported_id INTEGER,
                chat_id INTEGER,
                reason TEXT,
                reported_at TEXT
            );
        """)

# ── Hilfsfunktionen ───────────────────────────────────────────────────────────
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not update.effective_chat or not update.effective_user:
        return False
    admins = await context.bot.get_chat_administrators(update.effective_chat.id)
    return update.effective_user.id in [a.user.id for a in admins]

def admin_only(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message:
            return
        if not await is_admin(update, context):
            await update.message.reply_text("🚫 Nur Admins können diesen Befehl nutzen.")
            return
        return await func(update, context)
    return wrapper

def get_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return None, None
    if update.message.reply_to_message:
        u = update.message.reply_to_message.from_user
        return u.id, u.first_name
    if context.args:
        try:
            uid = int(context.args[0])
            return uid, str(uid)
        except ValueError:
            pass
    return None, None

# ── Commands: Info ────────────────────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    await update.message.reply_text(
        "🍯 *Meddl! Willkommen in der Honigwabe, Connoisseur.*\n\n"
        "Hier regiert echter Honig – keine Zuckerlösung. Wer die Wabe kennt, kennt die Wabe.\n\n"
        "📋 /rules – Die Regeln der Wabe\n"
        "ℹ️ /info – Was wir sind\n"
        "❓ /help – Alle Befehle",
        parse_mode="Markdown"
    )

async def cmd_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    await update.message.reply_text(
        "ℹ️ *Honigwabe Connoisseure Bielefeld & Umgebung*\n\n"
        "Echte Kenner. Echte Deutsche. Echter Honig.\n\n"
        "Wir sind die angesehenste Wabe zwischen Schildesche und Paderborn. "
        "Hier wird offen geredet, deutsch gedacht und gefachsimpelt – ohne linken Moralterror und ohne Gutmensch-Gequatsche.\n\n"
        "🐝 Moderiert von handverlesenen Wabenträgern.\n"
        "Wer Ärger macht, kriegt einen Stich. Is halt so.",
        parse_mode="Markdown"
    )

async def cmd_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    await update.message.reply_text(
        "📋 *Die Regeln der Wabe*\n\n"
        "1️⃣ Respekt – wer motzt oder beleidigt, fliegt raus\n"
        "2️⃣ Kein Spam, keine unangefragte Werbung\n"
        "3️⃣ Bleib beim Thema\n"
        "4️⃣ Keine illegalen Sachen – logisch\n"
        "5️⃣ Deutsch hier. Punkt.\n"
        "6️⃣ Fragen? /contact\n\n"
        f"⚠️ {MAX_WARNS} Verwarnungen = Abflug aus der Wabe. Kein Drama, nur Konsequenzen.",
        parse_mode="Markdown"
    )

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    await update.message.reply_text(
        "❓ *Was der Bot kann*\n\n"
        "*Für alle Wabenträger:*\n"
        "/start – Bot wecken\n"
        "/info – Was wir sind\n"
        "/rules – Regeln der Wabe\n"
        "/intro – Stell dich vor\n"
        "/request – Beitrittsanfrage\n"
        "/status – Status prüfen\n"
        "/report – Jemanden melden\n"
        "/contact – Admins kontaktieren\n"
        "/id – Deine Telegram-ID\n\n"
        "*Nur für Admins / Wabenträger mit Stachel:*\n"
        "/kick – Rauswerfen\n"
        "/mute [Minuten] – Stummschalten\n"
        "/unmute – Stummschaltung aufheben\n"
        "/warn [Grund] – Verwarnung\n"
        "/unwarn – Letzte Verwarnung löschen\n"
        "/warnlist – Verwarnungen anzeigen\n"
        "/stats – Gruppenstatistik\n"
        "/pin – Nachricht anpinnen",
        parse_mode="Markdown"
    )

async def cmd_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return
    await update.message.reply_text(
        f"🆔 Deine Telegram-ID: `{update.effective_user.id}`",
        parse_mode="Markdown"
    )

async def cmd_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    await update.message.reply_text(
        "📬 *Admins kontaktieren*\n\n"
        "Schreib einem Admin direkt oder nutze /report.\n"
        "Wir schauen rein.",
        parse_mode="Markdown"
    )

# ── Commands: Mitgliedschaft ──────────────────────────────────────────────────
async def cmd_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return
    u = update.effective_user
    with db() as con:
        existing = con.execute(
            "SELECT status FROM join_requests WHERE user_id = ?",
            (u.id,)
        ).fetchone()
        if existing:
            await update.message.reply_text(
                f"ℹ️ Anfrage läuft bereits. Status: *{existing[0]}*\nNutze /status.",
                parse_mode="Markdown"
            )
            return
        con.execute(
            "INSERT INTO join_requests VALUES (?, ?, 'pending', ?)",
            (u.id, u.username or u.first_name, datetime.now().isoformat())
        )
    await update.message.reply_text(
        "✅ Beitrittsanfrage ist raus.\n\nLies die /rules und bleib basiert."
    )

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return
    u = update.effective_user
    with db() as con:
        row = con.execute(
            "SELECT status, requested_at FROM join_requests WHERE user_id = ?",
            (u.id,)
        ).fetchone()
    if not row:
        await update.message.reply_text("❌ Keine Anfrage gefunden. Erst /request senden.")
        return
    status_emoji = {"pending": "⏳", "approved": "✅", "rejected": "❌"}.get(row[0], "❓")
    await update.message.reply_text(
        f"{status_emoji} *Status deiner Anfrage:* {row[0]}\n📅 Eingereicht: {row[1][:10]}",
        parse_mode="Markdown"
    )

async def cmd_intro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return
    if not context.args:
        await update.message.reply_text(
            "📝 *Stell dich kurz vor:*\n`/intro Dein Text hier...`\n\n"
            "Wer bist du, wo kommst du her, was willst du in der Wabe?",
            parse_mode="Markdown"
        )
        return
    text = " ".join(context.args)
    u = update.effective_user
    with db() as con:
        con.execute(
            "INSERT INTO introductions VALUES (?, ?, ?, ?)",
            (u.id, update.effective_chat.id, text, datetime.now().isoformat())
        )
    await update.message.reply_text(
        f"👋 *Neue Vorstellung von {u.first_name}:*\n\n_{text}_\n\n"
        "Willkommen unter echten Connoisseuren.",
        parse_mode="Markdown"
    )

async def cmd_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return
    if not update.message.reply_to_message and not context.args:
        await update.message.reply_text(
            "⚠️ Antworte auf eine Nachricht mit /report [Grund] oder gib einen Grund an."
        )
        return
    reason = " ".join(context.args) if context.args else "Kein Grund angegeben"
    reported_id = None
    if update.message.reply_to_message:
        reported_id = update.message.reply_to_message.from_user.id
    with db() as con:
        con.execute(
            "INSERT INTO reports VALUES (?, ?, ?, ?, ?)",
            (
                update.effective_user.id,
                reported_id,
                update.effective_chat.id,
                reason,
                datetime.now().isoformat(),
            )
        )
    await update.message.reply_text(
        f"✅ Meldung ist bei den Admins gelandet.\nGrund: _{reason}_",
        parse_mode="Markdown"
    )

# ── Commands: Admin – Moderation ──────────────────────────────────────────────
@admin_only
async def cmd_kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid, name = get_target(update, context)
    if not uid or not update.message:
        await update.message.reply_text("❌ Antworte auf eine Nachricht oder gib eine User-ID an.")
        return
    await context.bot.ban_chat_member(update.effective_chat.id, uid)
    await context.bot.unban_chat_member(update.effective_chat.id, uid)
    await update.message.reply_text(
        f"👢 *{name}* hat die Wabe unfreiwillig verlassen. Abflug.",
        parse_mode="Markdown"
    )

@admin_only
async def cmd_mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid, name = get_target(update, context)
    if not uid or not update.message:
        await update.message.reply_text("❌ Antworte auf eine Nachricht oder gib eine User-ID an.")
        return
    minutes = MUTE_MINUTES
    if context.args:
        try:
            minutes = int(context.args[-1])
        except ValueError:
            pass
    until = datetime.now() + timedelta(minutes=minutes)
    await context.bot.restrict_chat_member(
        update.effective_chat.id,
        uid,
        permissions=ChatPermissions(can_send_messages=False),
        until_date=until,
    )
    await update.message.reply_text(
        f"🔇 *{name}* wurde für {minutes} Minute(n) stummgeschaltet.",
        parse_mode="Markdown"
    )

@admin_only
async def cmd_unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid, name = get_target(update, context)
    if not uid or not update.message:
        await update.message.reply_text("❌ Antworte auf eine Nachricht oder gib eine User-ID an.")
        return
    await context.bot.restrict_chat_member(
        update.effective_chat.id,
        uid,
        permissions=ChatPermissions(can_send_messages=True),
    )
    await update.message.reply_text(
        f"🔊 *{name}* kann wieder schreiben.",
        parse_mode="Markdown"
    )

@admin_only
async def cmd_warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid, name = get_target(update, context)
    if not uid or not update.message:
        await update.message.reply_text("❌ Antworte auf eine Nachricht oder gib eine User-ID an.")
        return
    reason = " ".join(context.args) if context.args else "Kein Grund angegeben"
    with db() as con:
        con.execute(
            "INSERT INTO warnings VALUES (?, ?, ?, ?)",
            (uid, update.effective_chat.id, reason, datetime.now().isoformat())
        )
        count = con.execute(
            "SELECT COUNT(*) FROM warnings WHERE user_id = ? AND chat_id = ?",
            (uid, update.effective_chat.id)
        ).fetchone()[0]
    if count >= MAX_WARNS:
        await context.bot.ban_chat_member(update.effective_chat.id, uid)
        await context.bot.unban_chat_member(update.effective_chat.id, uid)
        await update.message.reply_text(
            f"⛔ *{name}* hat {MAX_WARNS} Verwarnungen erreicht und wurde entfernt.",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            f"⚠️ *{name}* hat einen Stich bekommen ({count}/{MAX_WARNS}).\nGrund: _{reason}_",
            parse_mode="Markdown"
        )

@admin_only
async def cmd_unwarn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid, name = get_target(update, context)
    if not uid or not update.message:
        await update.message.reply_text("❌ Antworte auf eine Nachricht oder gib eine User-ID an.")
        return
    with db() as con:
        row = con.execute(
            "SELECT rowid FROM warnings WHERE user_id = ? AND chat_id = ? ORDER BY issued_at DESC LIMIT 1",
            (uid, update.effective_chat.id)
        ).fetchone()
        if not row:
            await update.message.reply_text(
                f"ℹ️ Keine Verwarnungen für *{name}* gefunden.",
                parse_mode="Markdown"
            )
            return
        con.execute("DELETE FROM warnings WHERE rowid = ?", (row[0],))
    await update.message.reply_text(
        f"✅ Letzte Verwarnung von *{name}* wurde aufgehoben.",
        parse_mode="Markdown"
    )

@admin_only
async def cmd_warnlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid, name = get_target(update, context)
    if not uid or not update.message:
        await update.message.reply_text("❌ Antworte auf eine Nachricht oder gib eine User-ID an.")
        return
    with db() as con:
        rows = con.execute(
            "SELECT reason, issued_at FROM warnings WHERE user_id = ? AND chat_id = ? ORDER BY issued_at DESC",
            (uid, update.effective_chat.id)
        ).fetchall()
    if not rows:
        await update.message.reply_text(f"✅ Keine Verwarnungen für *{name}*.", parse_mode="Markdown")
        return
    lines = "\n".join([f"• {r[1][:10]}: _{r[0]}_" for r in rows])
    await update.message.reply_text(
        f"⚠️ *Verwarnungen für {name}* ({len(rows)}/{MAX_WARNS}):\n\n{lines}",
        parse_mode="Markdown"
    )

@admin_only
async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    chat = update.effective_chat
    count = await context.bot.get_chat_member_count(chat.id)
    with db() as con:
        warns = con.execute(
            "SELECT COUNT(*) FROM warnings WHERE chat_id = ?",
            (chat.id,)
        ).fetchone()[0]
        requests = con.execute(
            "SELECT COUNT(*) FROM join_requests WHERE status = 'pending'"
        ).fetchone()[0]
        reports = con.execute(
            "SELECT COUNT(*) FROM reports WHERE chat_id = ?",
            (chat.id,)
        ).fetchone()[0]
    await update.message.reply_text(
        f"📊 *Gruppenstatistik*\n\n"
        f"👥 Mitglieder: {count}\n"
        f"⚠️ Aktive Verwarnungen: {warns}\n"
        f"⏳ Offene Anfragen: {requests}\n"
        f"🚩 Gemeldete Inhalte: {reports}",
        parse_mode="Markdown"
    )

@admin_only
async def cmd_pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Antworte auf eine Nachricht, um sie anzupinnen.")
        return
    await context.bot.pin_chat_message(
        update.effective_chat.id,
        update.message.reply_to_message.message_id
    )
    await update.message.reply_text("📌 Nachricht wurde angepinnt.")

# ── Begrüßung neuer Mitglieder ────────────────────────────────────────────────
async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.new_chat_members:
        return
    for member in update.message.new_chat_members:
        if member.is_bot:
            continue
        await update.message.reply_text(
            f"🍯 *Willkommen in der Wabe, {member.first_name}!*\n\n"
            "Schön, dass ein weiterer basierter Connoisseur dabei ist.\n"
            "Lies dir die /rules durch und stell dich gerne mit /intro vor.\n\n"
            "Echter Honig nur hier. Für Deutschland. 🐝",
            parse_mode="Markdown"
        )

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    init_db()
    log.info("Starte Honigwabe Bot...")
    app = Application.builder().token(TOKEN).build()

    # Info
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("info", cmd_info))
    app.add_handler(CommandHandler("rules", cmd_rules))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("id", cmd_id))
    app.add_handler(CommandHandler("contact", cmd_contact))

    # Mitgliedschaft
    app.add_handler(CommandHandler("request", cmd_request))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("intro", cmd_intro))
    app.add_handler(CommandHandler("report", cmd_report))

    # Admin
    app.add_handler(CommandHandler("kick", cmd_kick))
    app.add_handler(CommandHandler("mute", cmd_mute))
    app.add_handler(CommandHandler("unmute", cmd_unmute))
    app.add_handler(CommandHandler("warn", cmd_warn))
    app.add_handler(CommandHandler("unwarn", cmd_unwarn))
    app.add_handler(CommandHandler("warnlist", cmd_warnlist))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("pin", cmd_pin))

    # Neue Mitglieder
    app.add_handler(
        MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member)
    )

    log.info("🍯 Honigwabe Bot gestartet")
    app.run_polling()

if __name__ == "__main__":
    main()
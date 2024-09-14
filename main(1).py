import telebot
import os
from pytube import YouTube
import instaloader
import yt_dlp
import subprocess
import requests
from pydub import AudioSegment
from googleapiclient.discovery import build
from fpdf import FPDF
from pdf2image import convert_from_path

bot_token = "7433536184:AAHt2N_rbNEZcdKhOjDQlIB95olXkd1EJY4"
weather_api_key = "5cda5d5659a488ff0c9eb5308aae8094"
bot = telebot.TeleBot(bot_token)

languages = {'English': 'en', 'Urdu': 'ur', 'Spanish': 'es', 'French': 'fr', 'German': 'de', 'Italian': 'it', 'Russian': 'ru', 'Hindi': 'hi', 'Chinese': 'zh'}
current_language = 'en'

def translate(text, target_lang):
    translations = {'en': text, 'ur': 'یہ اردو میں ترجمہ شدہ متن ہے', 'es': 'Este es el texto traducido al español', 'fr': 'Ceci est le texte traduit en français', 'de': 'Dies ist der ins Deutsche übersetzte Text', 'it': 'Questo è il testo tradotto in italiano', 'ru': 'Это перевод текста на русский язык', 'hi': 'यह हिंदी में अनुवादित पाठ है', 'zh': '这是翻译成中文的文本'}
    return translations.get(target_lang, text)

def sanitize_url(url):
    if url:
        return url.strip()
    return None

def download_video_preview(url, platform):
    url = sanitize_url(url)
    if not url:
        return None
    if platform == 'youtube':
        yt = YouTube(url)
        return yt.thumbnail_url
    elif platform == 'instagram':
        loader = instaloader.Instaloader()
        post = instaloader.Post.from_shortcode(loader.context, url.split("/")[-2])
        return post.url
    elif platform == 'tiktok':
        return url
    return None

def download_video(url, platform, format_choice, file_name):
    url = sanitize_url(url)
    if not url:
        return None
    if platform == 'youtube':
        yt = YouTube(url)
        if format_choice == 'mp3':
            audio_stream = yt.streams.filter(only_audio=True).first()
            audio_stream.download(output_path='.', filename=f'{file_name}.mp3')
            return f'{file_name}.mp3'
        else:
            video_stream = yt.streams.get_highest_resolution()
            video_stream.download(output_path='.', filename=f'{file_name}.mp4')
            return f'{file_name}.mp4'
    elif platform == 'instagram':
        loader = instaloader.Instaloader()
        post = instaloader.Post.from_shortcode(loader.context, url.split("/")[-2])
        loader.download_post(post, target=file_name)
        return f"{file_name}.mp4"
    elif platform == 'tiktok':
        ydl_opts = {'format': 'bestaudio/best' if format_choice == 'mp3' else 'best', 'outtmpl': f'{file_name}.{"mp3" if format_choice == "mp3" else "mp4"}'}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return f'{file_name}.{"mp3" if format_choice == "mp3" else "mp4"}'

def get_weather(city):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={weather_api_key}&units=metric"
    response = requests.get(url)
    data = response.json()
    if data["cod"] != "404":
        main = data['main']
        temperature = main['temp']
        description = data['weather'][0]['description']
        return f'Temperature: {temperature}°C\nDescription: {description}'
    return "City not found"

def search_music(query):
    youtube_api_key = "AIzaSyCWSdwnDtHd6jp_-pMfEYD8326P2ff8t5c"
    youtube = build('youtube', 'v3', developerKey=youtube_api_key)
    request = youtube.search().list(q=query, part="snippet", type="video", maxResults=5)
    response = request.execute()
    results = []
    for idx, item in enumerate(response['items']):
        video_id = item['id']['videoId']
        title = item['snippet']['title']
        results.append(f"{idx + 1}. {title}\nhttps://www.youtube.com/watch?v={video_id}")
    return results if results else "No results found."

def slow_audio(input_file, output_file):
    audio = AudioSegment.from_file(input_file)
    slowed = audio.speedup(playback_speed=0.7, chunk_size=150, crossfade=25)
    slowed.export(output_file, format="mp3")

def convert_images_to_pdf(images, output_pdf):
    pdf = FPDF()
    for image in images:
        pdf.add_page()
        pdf.image(image, x=10, y=10, w=180)
    pdf.output(output_pdf)

def convert_pdf_to_images(pdf_file, output_folder):
    images = convert_from_path(pdf_file)
    for i, image in enumerate(images):
        image.save(f"{output_folder}/page_{i + 1}.jpg", "JPEG")

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2)
    itembtn1 = telebot.types.KeyboardButton(translate('TikTok Video Download', current_language))
    itembtn2 = telebot.types.KeyboardButton(translate('YouTube Video Download', current_language))
    itembtn3 = telebot.types.KeyboardButton(translate('Instagram Video Download', current_language))
    itembtn4 = telebot.types.KeyboardButton(translate('Weather', current_language))
    itembtn5 = telebot.types.KeyboardButton(translate('Music Search', current_language))
    itembtn6 = telebot.types.KeyboardButton(translate('Slow and Reverb Audio', current_language))
    itembtn7 = telebot.types.KeyboardButton(translate('Image to PDF Converter', current_language))
    itembtn8 = telebot.types.KeyboardButton(translate('PDF to Image Converter', current_language))
    itembtn9 = telebot.types.KeyboardButton(translate('Video to Audio Converter', current_language))
    itembtn10 = telebot.types.KeyboardButton(translate('Change Language', current_language))
    markup.add(itembtn1, itembtn2, itembtn3, itembtn4, itembtn5, itembtn6, itembtn7, itembtn8, itembtn9, itembtn10)
    bot.send_message(message.chat.id, translate("Choose an option:", current_language), reply_markup=markup)

@bot.message_handler(func=lambda msg: True)
def platform_choice(message):
    platform = message.text.lower()
    if 'tiktok' in platform:
        bot.send_message(message.chat.id, translate("Send TikTok video link:", current_language))
        bot.register_next_step_handler(message, tiktok_download)
        return
    elif 'youtube' in platform:
        bot.send_message(message.chat.id, translate("Send YouTube video link:", current_language))
        bot.register_next_step_handler(message, youtube_download)
        return
    elif 'instagram' in platform:
        bot.send_message(message.chat.id, translate("Send Instagram video link:", current_language))
        bot.register_next_step_handler(message, instagram_download)
        return
    elif 'weather' in platform:
        bot.send_message(message.chat.id, translate("Enter city name:", current_language))
        bot.register_next_step_handler(message, get_weather_info)
        return
    elif 'music' in platform:
        bot.send_message(message.chat.id, translate("Enter song name:", current_language))
        bot.register_next_step_handler(message, music_search)
        return
    elif 'slow' in platform:
        bot.send_message(message.chat.id, translate("Send audio file to slow the speed:", current_language))
        bot.register_next_step_handler(message, slow_audio_process)
        return
    elif 'image to pdf' in platform:
        bot.send_message(message.chat.id, translate("Send the images to convert to PDF:", current_language))
        bot.register_next_step_handler(message, image_to_pdf)
        return
    elif 'pdf to image' in platform:
        bot.send_message(message.chat.id, translate("Send the PDF to convert to images:", current_language))
        bot.register_next_step_handler(message, pdf_to_image)
        return
    elif 'video to audio' in platform:
        bot.send_message(message.chat.id, translate("Send video to convert to audio:", current_language))
        bot.register_next_step_handler(message, video_to_audio)
        return
    elif 'language' in platform:
        markup = telebot.types.ReplyKeyboardMarkup(row_width=2)
        for lang in languages.keys():
            markup.add(telebot.types.KeyboardButton(lang))
        bot.send_message(message.chat.id, translate("Choose language:", current_language), reply_markup=markup)
        bot.register_next_step_handler(message, change_language)
        return
    else:
        bot.send_message(message.chat.id, translate("Invalid option. Use /help for available commands.", current_language))

def tiktok_download(message):
    url = sanitize_url(message.text)
    if url:
        bot.send_message(message.chat.id, translate("Do you want the preview? (Yes/No)", current_language))
        bot.register_next_step_handler(message, lambda msg: tiktok_process(url, msg))
    else:
        bot.send_message(message.chat.id, translate("Invalid link.", current_language))

def tiktok_process(url, message):
    if message.text.lower() == "yes":
        preview = download_video_preview(url, 'tiktok')
        if preview:
            bot.send_photo(message.chat.id, preview)
        bot.send_message(message.chat.id, translate("Downloading video...", current_language))
    file_name = "tiktok_video"
    downloaded_file = download_video(url, 'tiktok', 'mp4', file_name)
    with open(downloaded_file, 'rb') as video:
        bot.send_video(message.chat.id, video)

def youtube_download(message):
    url = sanitize_url(message.text)
    if url:
        bot.send_message(message.chat.id, translate("Do you want the preview? (Yes/No)", current_language))
        bot.register_next_step_handler(message, lambda msg: youtube_process(url, msg))
    else:
        bot.send_message(message.chat.id, translate("Invalid link.", current_language))

def youtube_process(url, message):
    if message.text.lower() == "yes":
        preview = download_video_preview(url, 'youtube')
        if preview:
            bot.send_photo(message.chat.id, preview)
        bot.send_message(message.chat.id, translate("Downloading video...", current_language))
    file_name = "youtube_video"
    downloaded_file = download_video(url, 'youtube', 'mp4', file_name)
    with open(downloaded_file, 'rb') as video:
        bot.send_video(message.chat.id, video)

def instagram_download(message):
    url = sanitize_url(message.text)
    if url:
        bot.send_message(message.chat.id, translate("Do you want the preview? (Yes/No)", current_language))
        bot.register_next_step_handler(message, lambda msg: instagram_process(url, msg))
    else:
        bot.send_message(message.chat.id, translate("Invalid link.", current_language))

def instagram_process(url, message):
    if message.text.lower() == "yes":
        preview = download_video_preview(url, 'instagram')
        if preview:
            bot.send_photo(message.chat.id, preview)
        bot.send_message(message.chat.id, translate("Downloading video...", current_language))
    file_name = "instagram_video"
    downloaded_file = download_video(url, 'instagram', 'mp4', file_name)
    bot.send_message(message.chat.id, translate("Video downloaded.", current_language))

def get_weather_info(message):
    city = message.text
    weather_info = get_weather(city)
    bot.send_message(message.chat.id, weather_info)

def music_search(message):
    query = message.text
    results = search_music(query)
    if results != "No results found.":
        bot.send_message(message.chat.id, "\n\n".join(results) + "\n\nType the number of the song you want to download.")
        bot.register_next_step_handler(message, music_download_choice, results)
    else:
        bot.send_message(message.chat.id, results)

def music_download_choice(message, results):
    try:
        number = int(message.text) - 1
        if 0 <= number < len(results):
            video_url = results[number].split("\n")[1]
            file_name = "music_download"
            downloaded_file = download_video(video_url, 'youtube', 'mp3', file_name)
            with open(downloaded_file, 'rb') as audio_file:
                bot.send_audio(message.chat.id, audio_file)
        else:
            bot.send_message(message.chat.id, translate("Invalid choice.", current_language))
    except ValueError:
        bot.send_message(message.chat.id, translate("Please enter a valid number.", current_language))

def slow_audio_process(message):
    if message.content_type == 'audio':
        file_id = message.audio.file_id
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        input_file = "input_audio.mp3"
        output_file = "output_audio_slow.mp3"
        with open(input_file, 'wb') as new_file:
            new_file.write(downloaded_file)
        slow_audio(input_file, output_file)
        with open(output_file, 'rb') as audio_file:
            bot.send_audio(message.chat.id, audio_file)

def video_to_audio(message):
    if message.content_type == 'video':
        file_id = message.video.file_id
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        input_file = "input_video.mp4"
        output_file = "output_audio.mp3"
        with open(input_file, 'wb') as new_file:
            new_file.write(downloaded_file)
        video_to_audio_convert(input_file, output_file)
        with open(output_file, 'rb') as audio_file:
            bot.send_audio(message.chat.id, audio_file)

def video_to_audio_convert(input_file, output_file):
    AudioSegment.from_file(input_file).export(output_file, format="mp3")

def image_to_pdf(message):
    if message.content_type == 'photo':
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        image_file = "image_to_pdf.jpg"
        with open(image_file, 'wb') as new_file:
            new_file.write(downloaded_file)
        output_pdf = "output.pdf"
        convert_images_to_pdf([image_file], output_pdf)
        with open(output_pdf, 'rb') as pdf_file:
            bot.send_document(message.chat.id, pdf_file)

def pdf_to_image(message):
    if message.content_type == 'document':
        file_id = message.document.file_id
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        pdf_file = "input_pdf.pdf"
        with open(pdf_file, 'wb') as new_file:
            new_file.write(downloaded_file)
        output_folder = "pdf_images"
        os.makedirs(output_folder, exist_ok=True)
        convert_pdf_to_images(pdf_file, output_folder)
        for image_file in os.listdir(output_folder):
            with open(f"{output_folder}/{image_file}", 'rb') as img:
                bot.send_photo(message.chat.id, img)

def change_language(message):
    global current_language
    selected_lang = message.text
    if selected_lang in languages:
        current_language = languages[selected_lang]
        bot.send_message(message.chat.id, translate("Language changed successfully!", current_language))
    else:
        bot.send_message(message.chat.id, translate("Invalid language selection.", current_language))

bot.polling()

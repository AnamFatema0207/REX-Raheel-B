import pyautogui
import speech_recognition as sr
import pyttsx3
import threading
import webbrowser
import ast
import operator as op
import os
import time
from datetime import datetime
from urllib.parse import quote_plus
import sounddevice as sd
import requests
import base64
import pyperclip
import ctypes  # for lock on Windows
from gtts import gTTS
from playsound import playsound
import uuid
import random  # 🔥 for roast mode
import re  # for parsing minutes in focus 
from dotenv import load_dotenv
load_dotenv()
from queue import Queue
import keyboard
import tkinter as tk
from tkinter import simpledialog




from threading import Lock
state_lock = Lock()


rex_started = False

# state class

class RexState:
    def __init__(self):
        self.silent = False
        self.focus = False
        self.ai = False
        self.speaking = False
        self.voice_running = False
        self.voice_enabled = True


state = RexState()



# ====================== CONFIG ======================

# Put your real AudD token here (or leave dummy if you don't want song ID)
SONG_API_TOKEN = os.getenv("SONG_API_TOKEN")

# Weather config
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
DEFAULT_CITY = "Maharashtra"  # fallback city if user doesn't say any

# OpenRouter AI config (for advanced answer mode)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = "openrouter/auto"



# Put your project folder path here (Windows example)
PROJECT_FOLDER_PATH = r"D:\Projects\REX-app"  # CHANGE THIS
NOTES_FILE = "rex_notes.txt"  # notes will be saved in this file
LOG_FILE = "logs.txt"            # activity log file


DEVELOPER_NAME = "Raheel Durwesh"
DEVELOPER_INSTAGRAM = "https://www.instagram.com/raheeldurwesh?igsh=MWkxcTd0d2prbG40YQ=="



# Context for smart search (youtube / google)
last_search_platform = None     # "youtube", "google", or None

# Silent mode: if True -> no actions, no speaking, only listening
state.silent = False


# Preferred voice index for pyttsx3 (0 or 1 as per your system)
PREFERRED_VOICE_INDEX = 0  # 0 = David, 1 = Zira (from your list)
SPEECH_RATE = 175

# 🔥 Roast mode (off by default)
roast_mode = False

# Focus mode
state.focus = False
focus_end_time = None
focus_pending_stop_confirm = False

# Focus / reminders
# (Focus mode globals agar baad mein add karoge toh unke paas rakh sakte ho)
timers = []   # list of dicts: {"id", "end", "message"}

state.ai = False

speech_queue = Queue()
state.speaking = False


# Translator setup
LANG_CODES = {
    "english": "en",
    "hindi": "hi",
    "marathi": "mr",
    "spanish": "es",
    "french": "fr",
    "german": "de",
}
        #  UPDATED Flags
state.voice_enabled = True
state.voice_running = False
VOICE_THREAD = None
VOICE_ERROR_SHOWN = False




# command worker

command_queue = Queue()

def command_worker():
    while True:
        cmd = command_queue.get()
        handle_voice_command(cmd)
        command_queue.task_done()


# ================== SAFE PRINT ==================

def safe_print(*args, **kwargs):
    """Print safely; ignore Unicode errors in Windows console."""
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        # Just skip problematic unicode for console
        pass

# ================== LOGGING ==================

def log_event(message: str, level="INFO"):
    """
    Append a one-line event to logs.txt with timestamp.
    """
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    line = f"[{ts}] [{level}] {message}\n"

    # Console print (safe)
    safe_print("LOG:", line.strip())

    # File write (UTF-8)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception as e:
        safe_print("Log write error:", e)

# ================== TEXT TO SPEECH (pyttsx3) ==================

tts_lock = threading.Lock()

def detect_hindi_text(text: str) -> bool:
    """Check if text contains Hindi characters (Devanagari script)."""
    hindi_range = range(0x0900, 0x097F + 1)  # Devanagari Unicode range
    return any(ord(char) in hindi_range for char in text)

def speak(text: str):
    if state.silent:
        return

    safe_print("Rex:", text)

    # Hindi detection → gTTS
    if detect_hindi_text(text):
        speak_gtts(text, "hi")
        return

    # English → pyttsx3
    with tts_lock:
        if state.silent:
            return

        engine = pyttsx3.init("sapi5")
        voices = engine.getProperty("voices")

        voice_index = PREFERRED_VOICE_INDEX
        if voice_index < 0 or voice_index >= len(voices):
            voice_index = 0

        engine.setProperty("voice", voices[voice_index].id)
        engine.setProperty("rate", SPEECH_RATE)

        engine.say(text)
        engine.runAndWait()
        engine.stop()

def speech_worker():
    while True:
        text = speech_queue.get()
        try:
            with state_lock:
                state.speaking = True

            speak(text)

        except Exception as e:
            safe_print("Speech error:", e)

        finally:
            with state_lock:
                state.speaking = False

            speech_queue.task_done()




def speak_async(text: str):
    if state.silent:
        return
    speech_queue.put(text)



# ================== gTTS FOR TRANSLATION / HINDI ROAST ==================

def speak_gtts(text: str, lang_code: str):
    """
    Use Google TTS for translated sentences (Hindi, Marathi, etc.).
    This is separate from normal pyttsx3 speech.
    """
    if state.silent:
        return

    try:
        filename = f"tts_{uuid.uuid4().hex}.mp3"
        tts = gTTS(text=text, lang=lang_code)
        tts.save(filename)
        with tts_lock:
          playsound(filename)
        os.remove(filename)
    except Exception as e:
        safe_print("gTTS error:", e)
        # fallback to English voice if something goes wrong
        speak_async("I could not speak this text properly, sir.")

# 🔥 ROAST MODE FUNCTION

def say_roast():
    """Light, fun roast – Hindi-friendly via Google TTS 😈"""
    lines = [
        "Sir, aapka focus itna strong hai, notification aate hi turant udd jata hai.",
        "Sir, lagta hai aapka dimaag background mein pachaas tabs chala raha hai, koi ek toh close kar do.",
        "Itna time sochne mein laga dete ho, jitne time mein main teen projects bana doon, sir.",
        "Sir, aapka procrastination level legendary hai, task kal ka kal bhi pending hota hai.",
        "Code likhte waqt confidence high, run karte hi error dekh ke network lost jaisa ho jata hai, sir.",
        "Sir, aap multitasking nahi, multi distracting karte ho.",
        "Lagta hai motivation install hai, lekin auto update off kar rakha hai, sir.",
        "Sir, aap keyboard pe jitni zor se type karte ho, utni zor se bugs hasti hongi."
    ]

    line = random.choice(lines)
    speak_gtts(line, "hi")
    log_event(f"Roast: {line}")

# ================== SONG IDENTIFIER (AudD) ==================

def record_audio_snippet(seconds=8, samplerate=44100):
    """Record small audio snippet from mic for song ID."""

    if state.silent:
        return None, None
    speak_async("Listening to the music, sir.")
    log_event("Voice: identify song -> recording audio snippet")
    audio = sd.rec(int(seconds * samplerate),
                   samplerate=samplerate,
                   channels=1,
                   dtype="int16")
    sd.wait()
    return audio, samplerate


def identify_song():
    """Record from mic and send to AudD for song recognition."""

    if state.silent:
        return

    if not SONG_API_TOKEN or SONG_API_TOKEN == "YOUR_AUDD_TOKEN_HERE":
        speak_async("Song identification is not configured yet, sir. Please add your API token.")
        log_event("Voice: identify song -> skipped (missing API token)")
        return

    try:
        audio, samplerate = record_audio_snippet()
        if audio is None:
            return

        audio_bytes = audio.tobytes()
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

        url = "https://api.audd.io/"
        data = {
            "api_token": SONG_API_TOKEN,
            "return": "apple_music,spotify,timecode",
            "audio": audio_b64,
        }

        speak_async("Identifying the song, sir.")
        log_event("Voice: identify song -> sent to AudD")
        resp = requests.post(url, data=data, timeout=20)

        safe_print("DEBUG HTTP STATUS:", resp.status_code)
        try:
            result = resp.json()
        except Exception as e:
            safe_print("DEBUG: JSON parse error:", e)
            speak_async("The song service returned an invalid response, sir.")
            log_event("Voice: identify song -> JSON parse error from service")
            return

        safe_print("DEBUG API RESULT:", result)

        if result.get("status") != "success":
            error_info = result.get("error") or {}
            msg = error_info.get("error_message", "Unknown error from song service.")
            safe_print("AudD error:", msg)
            speak_async("Song service error, sir. Maybe the token or account is not active.")
            log_event(f"Voice: identify song -> service error: {msg}")
            return

        if not result.get("result"):
            speak_async("Sorry sir, I could not recognize this song.")
            log_event("Voice: identify song -> no match found")
            return

        song = result["result"].get("title", "Unknown title")
        artist = result["result"].get("artist", "Unknown artist")

        speak_async(f"This sounds like {song} by {artist}, sir.")
        log_event(f"Voice: identify song -> recognized: {song} - {artist}")

    except Exception as e:
        safe_print("Song identification error:", e)
        speak_async("Something went wrong while identifying the song, sir.")
        log_event(f"Voice: identify song -> exception: {e}")


# ================== CLIPBOARD READER ==================

def read_selected_text():
    """Copies current selection (Ctrl+C) and reads it aloud."""
    
    if state.silent:
        return
    try:
        pyautogui.hotkey("ctrl", "c")
        time.sleep(0.3)
        text = pyperclip.paste()
        if not text or not text.strip():
            speak_async("Sir, there is no text selected or clipboard is empty.")
            log_event("Voice: read selected text -> clipboard empty")
            return
        speak_async("Reading the selected text, sir.")
        speak_async(text)
        log_event("Voice: read selected text -> executed")
    except Exception as e:
        safe_print("Clipboard read error:", e)
        speak_async("I could not read the selected text, sir.")
        log_event(f"Voice: read selected text -> error: {e}")


# ================== STATE HELPERS ==================

def toggle_silent():
    with state_lock:
        state.silent = not state.silent
        return state.silent


def set_silent(value: bool):
    with state_lock:
        state.silent = value


def set_focus(value: bool):
    with state_lock:
        state.focus = value


def set_ai(value: bool):
    with state_lock:
        state.ai = value



# ================== TRANSLATION HELPERS (USING gTTS FOR SPEECH) ==================

def translate_text_remote(text: str, target_lang: str) -> str | None:
    """
    Simple translation using Google's web endpoint via requests.
    No googletrans and no extra libraries needed.
    """
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": "auto",       # source language auto-detect
            "tl": target_lang,  # target language code, e.g. 'hi'
            "dt": "t",
            "q": text,
        }
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()

        data = resp.json()
        # data[0] is a list of [translated_part, original_part, ...]
        translated = "".join(part[0] for part in data[0])
        return translated
    except Exception as e:
        safe_print("Translation HTTP error:", e)
        return None


def translate_text_command(full_text: str):
    """
    Handle commands like:
    - 'Rex, translate to hindi: How are you?'
    - 'Rex, translate in hindi I am very happy today'
    - 'Rex, translate this to english: mujhe neend aa rahi hai'
    """
    
    if state.silent:
        return

    t = full_text.lower()

    # 1) detect target language from spoken text
    target_lang = None
    lang_name = None
    for name, code in LANG_CODES.items():
        if f"to {name}" in t or f"into {name}" in t or f"in {name}" in t:
            target_lang = code
            lang_name = name
            break

    if not target_lang:
        speak_async("Which language should I translate to, sir?")
        log_event(f"Voice: translate -> missing target language in: {full_text}")
        return

    # 2) extract text after colon if possible, else after 'translate'
    text_to_translate = ""
    if ":" in full_text:
        text_to_translate = full_text.split(":", 1)[1].strip()
    else:
        idx = t.find("translate")
        if idx != -1:
            text_to_translate = full_text[idx + len("translate"):].strip()

    if not text_to_translate:
        speak_async("What should I translate, sir?")
        log_event(f"Voice: translate -> no text found in: {full_text}")
        return

    # 3) remove 'to hindi', 'into hindi', 'in hindi', etc. from the text part
    remove_phrases = [
        f"to {lang_name}",
        f"into {lang_name}",
        f"in {lang_name}",
    ]
    tmp = text_to_translate
    lower_tmp = tmp.lower()
    for ph in remove_phrases:
        idx = lower_tmp.find(ph)
        if idx != -1:
            before = tmp[:idx]
            after = tmp[idx + len(ph):]
            tmp = (before + " " + after).strip(" ,:-")
            lower_tmp = tmp.lower()
    text_to_translate = tmp.strip()

    if not text_to_translate:
        speak_async("What should I translate, sir?")
        log_event(f"Voice: translate -> text became empty after cleaning: {full_text}")
        return

        # 4) do translation (without googletrans)
    translated = translate_text_remote(text_to_translate, target_lang)

    if not translated:
        speak_async("I could not translate that, sir.")
        log_event(f"Voice: translate -> HTTP error for: {text_to_translate}")
        return

    # console logging
    try:
        safe_print(f"TRANSLATE [{lang_name}]: {text_to_translate} -> {translated}")
    except Exception:
        safe_print("TRANSLATE: [unicode text]")

    # speak with gTTS (proper accent)
    speak_gtts(translated, target_lang)
    log_event(f"Voice: translate -> {text_to_translate} -> {translated} ({lang_name})")


def translate_selected_text_command(full_text: str):
    """
    Handle commands like:
    - 'Rex, translate this text to hindi'
    - 'Rex, translate selected text to english'
    Uses currently selected text (Ctrl+C) as input.
    """
   
    if state.silent:
        return

    t = full_text.lower()

    # detect target language
    target_lang = None
    lang_name = None
    for name, code in LANG_CODES.items():
        if f"to {name}" in t or f"into {name}" in t or f"in {name}" in t:
            target_lang = code
            lang_name = name
            break

    if not target_lang:
        speak_async("Which language should I translate to, sir?")
        log_event(f"Voice: translate selected -> missing target language in: {full_text}")
        return

    # copy selected text
    try:
        pyautogui.hotkey("ctrl", "c")
        time.sleep(0.3)
        original = pyperclip.paste()
    except Exception as e:
        safe_print("Clipboard error in translate_selected_text:", repr(e))
        speak_async("I could not access the selected text, sir.")
        log_event(f"Voice: translate selected -> clipboard error: {repr(e)}")
        return

    if not original or not original.strip():
        speak_async("Sir, there is no text selected or clipboard is empty.")
        log_event("Voice: translate selected -> empty clipboard")
        return

        # translate it (without googletrans)
    translated = translate_text_remote(original, target_lang)

    if not translated:
        speak_async("I could not translate the selected text, sir.")
        log_event(f"Voice: translate selected -> HTTP error for: {original}")
        return

    try:
        safe_print(f"TRANSLATE SELECTED [{lang_name}]: {original} -> {translated}")
    except Exception:
        safe_print("TRANSLATE SELECTED: [unicode text]")

    # speak using gTTS
    speak_gtts(translated, target_lang)
    log_event(f"Voice: translate selected -> {original} -> {translated} ({lang_name})")



# ================== SYSTEM CONTROL HELPERS ==================

def shutdown_system():
   
    if state.silent:
        return
    speak_async("Shutting down the system, sir.")
    log_event("Voice: shutdown system -> executed")
    os.system("shutdown /s /t 0")


def lock_system():
    
    if state.silent:
        return
    speak_async("Locking the computer, sir.")
    try:
        ctypes.windll.user32.LockWorkStation()
        log_event("Voice: lock computer -> executed")
    except Exception as e:
        safe_print("Lock error:", e)
        speak_async("I could not lock the system, sir.")
        log_event(f"Voice: lock computer -> error: {e}")


def open_project_folder():
    
    if state.silent:
        return
    if not os.path.isdir(PROJECT_FOLDER_PATH):
        speak_async("Project folder path is not valid, sir. Please check the configuration.")
        log_event("Voice: open project folder -> invalid path")
        return
    speak_async("Opening your project folder, sir.")
    try:
        os.startfile(PROJECT_FOLDER_PATH)
        log_event("Voice: open project folder -> executed")
    except Exception as e:
        safe_print("Open folder error:", e)
        speak_async("I could not open your project folder, sir.")
        log_event(f"Voice: open project folder -> error: {e}")


def start_focus(minutes: int):
    global focus_end_time, focus_pending_stop_confirm


    if minutes <= 0:
        minutes = 1  # minimum 1 min

    state.focus = True
    focus_pending_stop_confirm = False
    focus_end_time = time.time() + minutes * 60

    speak_async(f"Focus mode activated for {minutes} minutes, sir.")
    log_event(f"Focus: focus mode started for {minutes} minutes.")

    def focus_timer_thread():
       
        # calculate remaining (in case start_state.focus called again)
        while True:
            if not state.focus or focus_end_time is None:
                return
            remaining = focus_end_time - time.time()
            if remaining <= 0:
                break
            time.sleep(1)

        # timer complete and focus still on
        if state.focus:
            state.focus = False
            focus_end_time = None
            focus_pending_stop_confirm = False
            speak_async("Your focus session is complete, sir.")
            log_event("Focus: focus mode timer completed.")

    threading.Thread(target=focus_timer_thread, daemon=True).start()


def set_timer(minutes: int, message: str):
    """
    Start a background timer that will speak a reminder after given minutes.
    Timers can be cancelled globally via 'cancel_all_timers'.
    """
    global timers

    if minutes <= 0:
        minutes = 1  # minimum 1 minute

    end_time = time.time() + minutes * 60
    timer_id = uuid.uuid4().hex

    timers.append({
        "id": timer_id,
        "end": end_time,
        "message": message,
    })

    speak_async(f"Timer set for {minutes} minutes, sir.")
    log_event(f"Timer: set for {minutes} minutes -> {message}")

    def timer_thread(local_id):
        global timers

        # Wait until it's time
        while True:
            # find this timer in list
            active = next((t for t in timers if t["id"] == local_id), None)
            if active is None:
                # timer was cancelled
                log_event(f"Timer: cancelled before finishing (id={local_id})")
                return

            remaining = active["end"] - time.time()
            if remaining <= 0:
                break
            time.sleep(min(1, remaining))

        # Final check: maybe cancelled in the last second
        active = next((t for t in timers if t["id"] == local_id), None)
        if active is None:
            log_event(f"Timer: cancelled before finishing (final check, id={local_id})")
            return

        # Remove and speak
        timers = [t for t in timers if t["id"] != local_id]
        speak_async(f"Reminder: {active['message']}, sir.")
        log_event(f"Timer: finished -> {active['message']}")

    threading.Thread(target=timer_thread, args=(timer_id,), daemon=True).start()


def show_timers_status():
    """
    Speak how many timers are active and show rough remaining times.
    """
    global timers
    if not timers:
        speak_async("You have no active timers, sir.")
        log_event("Timer: show_timers_status -> no active timers")
        return

    now = time.time()
    active_info = []
    for t in timers:
        remaining = int(t["end"] - now)
        if remaining <= 0:
            continue
        mins = remaining // 60
        secs = remaining % 60
        active_info.append((mins, secs, t["message"]))

    if not active_info:
        timers.clear()
        speak_async("You have no active timers, sir.")
        log_event("Timer: show_timers_status -> cleaned up expired timers")
        return

    speak_async(f"You have {len(active_info)} active timer or timers, sir.")
    for i, (m, s, msg) in enumerate(active_info, start=1):
        if m > 0:
            speak_async(f"Timer {i}: about {m} minutes and {s} seconds left, for {msg}.")
        else:
            speak_async(f"Timer {i}: about {s} seconds left, for {msg}.")
    log_event(f"Timer: show_timers_status -> {len(active_info)} active timers")


def cancel_all_timers():
    """
    Cancel all active timers (threads will see they are cancelled and not speak).
    """
    global timers
    if not timers:
        speak_async("You have no active timers to cancel, sir.")
        log_event("Timer: cancel_all_timers -> nothing to cancel")
        return

    timers.clear()
    speak_async("I have cancelled all active timers, sir.")
    log_event("Timer: all active timers cancelled by user")

def fetch_weather(city_name: str):
    """
    Call OpenWeatherMap current weather API for given city.
    Returns dict with main info or None on error.
    """
    if not WEATHER_API_KEY:
        speak_async("Weather API key is not configured yet, sir.")
        log_event("Weather: missing API key")
        return None

    try:
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": city_name,
            "appid": WEATHER_API_KEY,
            "units": "metric"
        }

        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code != 200:
            speak_async(f"I could not get weather for {city_name}, sir.")
            log_event(f"Weather: HTTP {resp.status_code} for {city_name}")
            return None

        data = resp.json()

        return {
            "city": data.get("name", city_name),
            "temp": data["main"].get("temp"),
            "feels_like": data["main"].get("feels_like"),
            "humidity": data["main"].get("humidity"),
            "description": data["weather"][0]["description"] if data.get("weather") else "unknown",
            "wind_speed": data["wind"].get("speed"),
        }

    except Exception as e:
        speak_async("Something went wrong while getting the weather, sir.")
        log_event(f"Weather: exception -> {e}")
        return None

    
def ask_ai_openrouter(user_text: str) -> str | None:
    """
    Send the user's question to OpenRouter and return the AI's answer text.
    """
    if not OPENROUTER_API_KEY or OPENROUTER_API_KEY.startswith("YOUR_"):
        speak_async("AI answer mode is not configured yet, sir. Please set your OpenRouter API key.")
        log_event("AI: missing OpenRouter API key")
        return None

    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        # Optional but recommended by OpenRouter for ranking/analytics :contentReference[oaicite:2]{index=2}
        "HTTP-Referer": "https://localhost/rex",
        "X-Title": "Rex Desktop Assistant",
    }

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are Rex's brain, a helpful, concise assistant. "
                    "Answer in simple English, short enough to be spoken aloud. "
                    "User may mix English and Hindi; reply mainly in English unless asked otherwise."
                ),
            },
            {
                "role": "user",
                "content": user_text,
            },
        ],
        "max_tokens": 256,
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=25)
        if resp.status_code != 200:
            safe_print("OpenRouter HTTP error:", resp.status_code, resp.text)
            log_event(f"AI: HTTP {resp.status_code} from OpenRouter")
            return None

        data = resp.json()
        # Basic extraction of first choice
        content = data["choices"][0]["message"]["content"]
        return content

    except Exception as e:
        safe_print("OpenRouter error:", e)
        log_event(f"AI: exception from OpenRouter -> {e}")
        return None



def speak_weather_for_city(city_name: str | None):
    """
    Fetch weather for given city (or DEFAULT_CITY) and speak it.
    """
    if not city_name or not city_name.strip():
        city_name = DEFAULT_CITY

    city_name_clean = city_name.strip()
    log_event(f"Weather: requested for city={city_name_clean}")

    info = fetch_weather(city_name_clean)
    if info is None:
        return

    city = info["city"]
    temp = info["temp"]
    feels = info["feels_like"]
    humidity = info["humidity"]
    desc = info["description"]
    wind_speed = info["wind_speed"]

    # Build a nice sentence
    parts = []
    if temp is not None:
        parts.append(f"The temperature in {city} is around {int(round(temp))} degree Celsius")
    else:
        parts.append(f"The weather in {city} is {desc}")

    if feels is not None:
        parts.append(f"it feels like {int(round(feels))} degree")

    if desc:
        parts.append(f"with {desc}")

    if humidity is not None:
        parts.append(f"and humidity around {humidity} percent")

    sentence = ", ".join(parts) + "."
    speak_async(sentence)

    if wind_speed is not None:
        speak_async(f"Wind speed is about {wind_speed} meters per second, sir.")

    log_event(f"Weather: spoken for {city} -> {sentence}")



# ================== CALCULATOR HELPERS ==================

ALLOWED_OPS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Pow: op.pow,
    ast.Mod: op.mod,
}

def safe_eval_expr(expr: str) -> float:
    """Safely evaluate a simple math expression."""
    def _eval(node):
        if isinstance(node, ast.Num):
            return node.n
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.BinOp):
            left = _eval(node.left)
            right = _eval(node.right)
            op_type = type(node.op)
            if op_type in ALLOWED_OPS:
                return ALLOWED_OPS[op_type](left, right)
            raise ValueError("Operator not allowed")
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            val = _eval(node.operand)
            return +val if isinstance(node.op, ast.UAdd) else -val
        raise ValueError("Invalid expression")

    tree = ast.parse(expr, mode="eval")
    return _eval(tree.body)

def build_calc_expression_from_text(full_text: str) -> str:
    """Convert spoken sentence into a math expression string."""
    t = full_text.lower()

    expr_part = full_text
    if "calculate" in t:
        expr_part = full_text.split("calculate", 1)[1]
    elif "what is" in t:
        expr_part = full_text.split("what is", 1)[1]

    for word in ["rex", "please", "answer", "for me"]:
        expr_part = expr_part.replace(word, "")

    expr = expr_part.lower()

    replacements = {
        "plus": "+",
        "minus": "-",
        "add": "+",
        "added to": "+",
        "subtract": "-",
        "subtracted from": "-",
        "times": "*",
        "into": "*",
        "multiplied by": "*",
        "multiply by": "*",
        "x": "*",
        "divide by": "/",
        "divided by": "/",
        "over": "/",
        "by": "/",
        "power": "**",
        "raised to": "**",
        "mod": "%",
        "modulo": "%",
        "remainder": "%",
    }

    for phrase, sym in sorted(replacements.items(), key=lambda x: -len(x[0])):
        expr = expr.replace(phrase, f" {sym} ")

    allowed_chars = "0123456789.+-*/()% "
    filtered = "".join(ch for ch in expr if ch in allowed_chars)
    filtered = " ".join(filtered.split())
    return filtered.strip()

def calculate_from_command(full_text: str):
    """Parse the user's speech and do calculation."""
    
    if state.silent:
        return

    expr = build_calc_expression_from_text(full_text)
    if not expr:
        speak_async("I could not find a valid expression to calculate, sir.")
        log_event(f"Voice: calculator -> no expression in: {full_text}")
        return

    try:
        result = safe_eval_expr(expr)
        speak_async(f"The answer is {result}, sir.")
        log_event(f"Voice: calculator -> {expr} = {result}")
    except Exception as e:
        safe_print("Calculator error:", repr(e))
        speak_async("I could not calculate that, sir.")
        log_event(f"Voice: calculator -> error on '{expr}': {repr(e)}")


# ================== SMART NOTES MODULE ==================

def add_note_from_command(full_text: str):
    """Extract note text and append to NOTES_FILE with timestamp."""
    
    if state.silent:
        return

    t = full_text.lower()
    note_part = ""

    if "remember this" in t:
        idx = t.find("remember this")
        note_part = full_text[idx + len("remember this"):].lstrip(" :,-")
    elif "remember that" in t:
        idx = t.find("remember that")
        note_part = full_text[idx + len("remember that"):].lstrip(" :,-")

    note_part = note_part.strip()

    if not note_part:
        speak_async("What should I remember, sir?")
        log_event("Voice: remember -> failed (empty note)")
        return

    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    line = f"[{ts}] {note_part}\n"

    try:
        with open(NOTES_FILE, "a", encoding="utf-8") as f:
            f.write(line)
        safe_print("Note added:", line.strip())
        speak_async("I have noted that, sir.")
        log_event(f"Voice: remember -> added note: {note_part}")
    except Exception as e:
        safe_print("Note write error:", e)
        speak_async("I could not save this note, sir.")
        log_event(f"Voice: remember -> error: {e}")


def show_notes():
    """Read all notes from NOTES_FILE, print them, and read them aloud."""
    
    if state.silent:
        return

    if not os.path.exists(NOTES_FILE):
        speak_async("You have no notes yet, sir.")
        log_event("Voice: show notes -> file not found")
        return

    try:
        with open(NOTES_FILE, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
    except Exception as e:
        safe_print("Note read error:", e)
        speak_async("I could not read your notes, sir.")
        log_event(f"Voice: show notes -> read error: {e}")
        return

    if not lines:
        speak_async("Your notes file is empty, sir.")
        log_event("Voice: show notes -> empty file")
        return

    safe_print("=== RexNotes ===")
    for line in lines:
        safe_print(line)

    speak_async("Here are your notes, sir.")
    for line in lines[-10:]:
        speak_async(line)
    log_event(f"Voice: show notes -> read {len(lines)} notes (last 10 spoken)")


def clear_notes():
    """Clear all notes from NOTES_FILE."""
    if state.silent:
        return

    try:
        with open(NOTES_FILE, "w", encoding="utf-8") as f:
            f.write("")
        safe_print("Notes cleared.")
        speak_async("I have cleared all your notes, sir.")
        log_event("Voice: clear notes -> executed")
    except Exception as e:
        safe_print("Clear notes error:", e)
        speak_async("I could not clear your notes, sir.")
        log_event(f"Voice: clear notes -> error: {e}")


# ================== LOG VIEW (LAST 20) ==================

def show_last_logs():
    """Reads only the last 20 log entries and prints them."""
    
    if state.silent:
        return

    if not os.path.exists(LOG_FILE):
        speak_async("No logs found, sir.")
        return

    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
    except Exception as e:
        safe_print("Log read error:", e)
        speak_async("I could not read the activity logs, sir.")
        return

    if not lines:
        speak_async("Your log file is empty, sir.")
        return

    last_20 = lines[-20:]
    safe_print("===== LAST 20 LOG ENTRIES =====")
    for line in last_20:
        safe_print(line)

    speak_async("Showing your last twenty activity logs in the console, sir.")
    log_event("Voice: show logs -> last 20 printed")

def play_song_youtube_music(full_text: str):
    """
    Voice examples:
      - 'Rex, play Kesariya on YouTube Music'
      - 'Rex play Believer on youtube music'
    """
    
    if state.silent:
        return

    t = full_text.lower()

    # make sure it is really a YT Music request
    if "play" not in t or "youtube music" not in t:
        return

    # extract part after 'play'
    try:
        after_play = full_text.split("play", 1)[1]
    except Exception:
        after_play = ""

    # remove trailing 'on youtube music'
    lowered_after_play = after_play.lower()
    for tail in ["on youtube music", "on yt music", "on youtube music app"]:
        if tail in lowered_after_play:
            idx = lowered_after_play.find(tail)
            after_play = after_play[:idx]
            break

    song_name = after_play.strip(" .,:-!").strip()

    if not song_name:
        speak_async("Which song should I play on YouTube Music, sir?")
        log_event(f"Voice: YT Music -> song name missing in: {full_text}")
        return

    # Open YouTube Music search
    url = f"https://music.youtube.com/search?q={quote_plus(song_name)}"
    speak_async(f"Playing {song_name} on YouTube Music, sir.")
    webbrowser.open(url)
    log_event(f"Voice: YT Music -> playing '{song_name}'")


def enter_type_mode():
    speak_async("Type mode activated. Please type your command.")

    try:
        root = tk.Tk()
        root.withdraw()  # hide main window
        root.attributes("-topmost", True)

        typed = simpledialog.askstring(
            "Rex - Type Mode",
            "Type your command:"
        )

        root.destroy()

        if typed and typed.strip():
            handle_voice_command(typed.strip())
        else:
            speak_async("No command entered.")

    except Exception as e:
        log_event(f"Type mode error: {e}")
        speak_async("Type mode failed.")




def rex_status():
    if state.silent:
        status = "I am currently in silent mode."
    elif state.focus:
        status = "Focus mode is currently active."
    else:
        status = "I am active and listening for commands."

    speak_async(status)
    log_event("User asked: Rex status")


def describe_rex():
    description = (
        "Certainly. I am Rex, your personal desktop assistant. "
        "I am designed to help you operate your computer efficiently using voice or typing. "

        "I can open websites and applications such as Google, YouTube, WhatsApp, and system tools. "
        "I can search the web, play videos, and help you find information quickly. "

        "I can manage daily tasks for you, including setting timers, reminders, and focus sessions. "
        "I can create and read notes so you do not forget important things. "

        "I can tell you the current weather and provide basic system controls such as locking your computer or shutting it down safely. "

        "I support both voice commands and a typing mode. "
        "If speaking is not convenient, you can say type mode and enter commands manually. "

        "I also have intelligent conversation abilities and can answer questions when artificial intelligence mode is enabled. "
        "If you ever need assistance, guidance, or help understanding my features, simply ask me."
    )

    speak_async(description)
    log_event("User asked: Describe all features")

def print_command_list():
    commands = """
==================== REX COMMAND LIST ====================

[ROAST MODE]
Rex roast mode on / enable roast mode
- Enable savage roast mode

Rex roast mode off / disable roast mode
- Disable roast mode

Rex roast me
- Rex roasts you in Hindi using gTTS


[GESTURE CONTROLS]
Rex stop gestures / disable gestures / turn off gestures
- Disable all gesture actions

Rex enable gestures / start gestures / turn on gestures
- Enable gesture actions


[WEATHER COMMANDS]
Rex what's the weather
- Default city weather

Rex what's the weather in Mumbai
- Weather for specific city

Rex weather today
- Current weather

Weather in Hyderabad
- City weather


[SONG IDENTIFICATION]
Rex what song is this / Rex identify this song / Rex which song is this
- Listens to music and identifies the song


[TRANSLATION COMMANDS]

Translate Selected Text:
Rex translate this text to hindi
- Translate selected text (Ctrl+C)

Rex translate this text to english
- Translate copied text

Translate Spoken Text:
Rex translate to hindi: how are you
- Translate spoken text

Rex translate into marathi I am happy today
- Translate and speak


[NOTES SYSTEM]
Rex remember this / remember that
- Add a note

Rex show my notes / show notes / read my notes
- Speak last 10 notes

Rex clear my notes / delete my notes / remove my notes
- Deletes all notes


[TIMER / REMINDER SYSTEM]

Set Timer:
Rex set a timer for 10 minutes
- Simple timer

Start a timer for 5 minutes
- Starts timer

Reminders:
Rex remind me in 10 minutes to drink water
- Custom reminder

Timer Management:
Rex show my timers / show active timers
- Active timers with remaining time

Rex cancel all timers / clear all timers
- Deletes all timers


[SYSTEM CONTROL]
Rex shutdown the system / shut down the system
- Shutdown PC

Rex lock the computer / lock the system
- Lock screen


[ACTIVITY LOGS]
Rex show my logs / show logs / show activity logs / show last logs
- Prints last 20 logs


[IDENTITY]
Rex who developed you / who made you / who built you
- Raheel Durwesh developed me

Rex who are you
- I am Rex


[EXIT VOICE LISTENER]
Rex bye rex
- Stops voice listener


[AI MODE]
Rex enable AI mode
- Enable AI mode

Rex ask <question>
- Answer the question

Rex disable AI mode
- Disable AI mode


[HELP / DISCOVERY COMMANDS]
Rex how do I use you
Rex give me examples
Rex what can I say
- Rex speaks one short line only
- Full command list is printed in console
- Rex does not read the full list aloud


[FEATURE EXPLANATION]
Rex what can you do
Rex describe all features
Rex describe yourself
Rex help
- Rex explains all capabilities politely and clearly


[STATUS AWARENESS]
Rex status
Rex what mode are you in
Rex what are you doing
- Rex tells whether it is active, silent mode, or focus mode


[TYPE MODE]
Rex type mode
Rex typing mode
- Opens popup input dialog
- No console needed

==========================================================
"""
    safe_print(commands)
    log_event("User requested command list")

def developer_info():
    speak_async(
        "I was developed by Raheel Durwesh. "
        "Opening his Instagram profile now."
    )
    log_event("User asked: Who developed you")
    webbrowser.open(DEVELOPER_INSTAGRAM)




# ================== VOICE COMMAND HANDLER ==================

def handle_voice_command(text: str) -> bool:
    
   

    t = text.lower().strip()

    # ---------- SHUTDOWN REX ----------
    if "shutdown rex" in t or "exit rex" in t :
        speak_async("Shutting down now. Goodbye.")
        log_event("System: Rex shutdown by user")
        time.sleep(2.5)   # allow speech to start
        os._exit(0)


    # ---------- DEVELOPER INFO ----------
    if any(phrase in t for phrase in [
        "who developed you",
        "who made you",
        "who built you"
    ]):
        developer_info()
        return True


    # ---------- REX STATUS ----------
    if any(phrase in t for phrase in [
        "what mode are you in",
        "rex status",
        "what are you doing"
    ]):
        rex_status()
        return True

    # ---------- COMMAND HELP ----------
    if any(phrase in t for phrase in [
        "how do i use you",
        "give me examples",
        "what can i say"
    ]):
        speak_async("These are the commands you can use. I have printed them for you.")
        print_command_list()
        return True


# ---------- REX FEATURE DESCRIPTION ----------
    if any(phrase in t for phrase in [
        "what can you do",
        "describe all features",
        "describe yourself",
        "about you",
        "help rex",
        "rex help"
]):
      describe_rex()
      return True


    # ---------- FOCUS MODE CONFIRMATION ----------
    if focus_pending_stop_confirm:
        if t in ["yes", "haan", "okay", "yes stop"]:
            state.focus = False
            focus_pending_stop_confirm = False
            focus_end_time = None
            speak_async("Focus mode stopped, sir.")
            log_event("Focus mode stopped by confirmation")
            return True

        # cancel silently for anything else
        focus_pending_stop_confirm = False

    # ---------- EMERGENCY STOP ----------
    if t in ["rex stop", "stop rex", "ruk jao", "band karo"]:
        state.silent = True
        try:
            speech_queue.queue.clear()
        except:
            pass
        log_event("System: silent mode enabled (emergency stop)")
        return True

    # ---------- SILENT MODE GLOBAL GATE ----------
    if state.silent:
        if any(x in t for x in [
            "hi rex", "hello rex",
            "rex wake up", "wake up rex",
            "resume rex"
        ]):
            state.silent = False
            speak_async("I am active again, sir.")
            log_event("System: silent mode disabled (wake command)")
            return True
        else:
            return True

    # ---------- TYPE MODE ----------
    if "type mode" in t or "typing mode" in t:
        enter_type_mode()
        return True



    # ---------- FOCUS MODE STOP REQUEST ----------
    if state.focus and "focus" in t and "stop" in t:
        focus_pending_stop_confirm = True
        speak_async("Are you sure you want to stop focus mode?")
        return True


    # Special case: "hi rex" / "hello rex" / Hindi greetings
    hindi_greetings = ["namaste rex", "namaskar rex", "kaise ho rex", "kya haal rex"]
    if "hi rex" in t or "hello rex" in t or any(greeting in t for greeting in hindi_greetings):
        if state.silent:
            state.silent = False
            speak_async("I am active again, sir.")
            log_event(f"Voice: {t} -> state.silent disabled (wake up via hi)")
        else:
            speak_async("Hi sir how can i assist you today.")
            log_event(f"Voice: {t} -> greeting")
        return True


        # ---------- WHO DEVELOPED YOU / IDENTITY ----------
    # if ("who developed you" in t or
    #     "who made you" in t or
    #     "who built you" in t):
    #     speak_async("Raheel Durwesh developed me, sir. I am Rex, your personal desktop assistant.")
    #     log_event(f"Voice: {t} -> who developed you reply")
    #     return True
      # ---------- AI MODE TOGGLE ----------
    if "enable ai mode" in t or "ai mode on" in t:
        state.ai = True
        speak_async("AI mode enabled, sir.")
        log_event(f"Voice: {t} -> state.ai = True")
        return True

    if "disable ai mode" in t or "ai mode off" in t:
        state.ai = False
        speak_async("AI mode disabled, sir.")
        log_event(f"Voice: {t} -> state.ai = False")
        return True


    
    if ("who are you" in t ):
        speak_async("I am Rex, your personal desktop assistant.")
        log_event(f"Voice: {t} -> who are you")
        return True


        # ---------- ROAST MODE TOGGLE & ROAST ME ----------
    
    if "roast mode on" in t or "enable roast mode" in t:
        roast_mode = True
        speak_async("Roast mode activated, sir. Ab thoda savage hoga.")
        log_event(f"Voice: {t} -> roast_mode = True")
        return True

    if "roast mode off" in t or "disable roast mode" in t:
        roast_mode = False
        speak_async("Roast mode deactivated, sir. Back to normal behaviour.")
        log_event(f"Voice: {t} -> roast_mode = False")
        return True

    if "roast me" in t or "rex roast me" in t:
        say_roast()
        return True
  
        # ---------- FOCUS MODE START/STOP ----------
    # Start focus mode
    if "focus mode" in t and ("start" in t or "turn on" in t or "enable" in t):
        # default minutes
        minutes = 25
        # try to extract number before 'minute'
        match = re.search(r"(\d+)\s+minute", t)
        if match:
            try:
                minutes = int(match.group(1))
            except ValueError:
                minutes = 25

        start_focus(minutes)
        return True

    # Simple phrase: "focus mode for 30 minutes"
    if "focus mode for" in t:
        minutes = 25
        match = re.search(r"focus mode for\s+(\d+)", t)
        if match:
            try:
                minutes = int(match.group(1))
            except ValueError:
                minutes = 25
        start_focus(minutes)
        return True

    # Ask to stop focus mode
    if "stop focus mode" in t or "exit focus mode" in t or "turn off focus mode" in t:
        if not state.focus:
            speak_async("Focus mode is not active, sir.")
            log_event(f"Voice: {t} -> stop focus mode but not active")
            return True

        focus_pending_stop_confirm = True
        speak_async("Are you sure you want to stop focus mode, sir?")
        log_event(f"Voice: {t} -> asked confirmation to stop focus mode")
        return True

    # Ask remaining time
    if state.focus and ("time left" in t or "remaining time" in t or "how much time" in t):
        if focus_end_time is None:
            speak_async("I am not sure about the remaining time, sir.")
            log_event(f"Voice: {t} -> focus mode active but focus_end_time None")
        else:
            remaining = int(max(0, focus_end_time - time.time()))
            mins = remaining // 60
            secs = remaining % 60
            if mins > 0:
                speak_async(f"About {mins} minutes and {secs} seconds remaining, sir.")
            else:
                speak_async(f"About {secs} seconds remaining, sir.")
            log_event(f"Voice: {t} -> focus mode remaining {mins}m {secs}s")
        return True


    # ---------- SHOW LOGS ----------
    if "show my logs" in t or "show logs" in t or "show activity logs" in t or "show last logs" in t:
        show_last_logs()
        return True
    
        # ---------- WEATHER INFO ----------
    # Examples:
    # "Rex, what's the weather"
    # "Rex, what's the weather in Mumbai"
    # "Rex, weather today"
    if "weather" in t and "rex" in t:
        city = None

        # try to capture: "weather in mumbai" / "weather at hyderabad"
        m = re.search(r"weather\s+(in|at)\s+([a-zA-Z\s]+)", t)
        if m:
            city = m.group(2).strip()

        # also handle "in mumbai" even if not directly after "weather"
        if city is None:
            m2 = re.search(r"in\s+([a-zA-Z\s]+)$", t)
            if m2:
                city = m2.group(1).strip()

        speak_weather_for_city(city)
        return True


    # ---------- TRANSLATE SELECTED TEXT ----------
    if ("translate this text" in t or "translate selected text" in t) and "rex" in t:
        translate_selected_text_command(text)
        return True

    # ---------- TRANSLATE NORMAL TEXT ----------
    if "translate" in t and "rex" in t:
        translate_text_command(text)
        return True

    # ---------- SMART NOTES: REMEMBER ----------
    if "remember this" in t or "remember that" in t:
        add_note_from_command(text)
        return True

    # ---------- SMART NOTES: SHOW NOTES ----------
    if "show my notes" in t or "show notes" in t or "read my notes" in t:
        show_notes()
        return True

    # ---------- SMART NOTES: CLEAR NOTES ----------
    if "clear my notes" in t or "delete my notes" in t or "remove my notes" in t:
        clear_notes()
        return True
    

    # Example: "Rex, set a timer for 20 minutes"
    if "set a timer for" in t or "start a timer for" in t or "timer for" in t:
        minutes = 1
        m = re.search(r"(?:set a timer for|start a timer for|timer for)\s+(\d+)\s+minute", t)
        if m:
            try:
                minutes = int(m.group(1))
            except ValueError:
                minutes = 1

        set_timer(minutes, "your timer is finished")
        return True
    
        # ---------- REMINDERS / TIMERS ----------
    # Example: "Rex, remind me in 10 minutes to drink water"
    if "remind me in" in t:
        minutes = 1
        m = re.search(r"remind me in\s+(\d+)\s+minute", t)
        if m:
            try:
                minutes = int(m.group(1))
            except ValueError:
                minutes = 1

        # default message
        msg = "your reminder time is over"

        # try to capture message after "to" or "about"
        m2 = re.search(r"remind me in\s+\d+\s+minute(?:s)?\s+(?:to|about)\s+(.+)", t)
        if m2:
            msg = m2.group(1).strip()

        set_timer(minutes, msg)
        return True

    # Show active timers
    if "show my timers" in t or "show timers" in t or "active timers" in t:
        show_timers_status()
        return True

    # Cancel all timers
    if ("cancel all timers" in t or "clear all timers" in t or
        "remove all timers" in t or "stop all timers" in t or "delete all timers" in t):
        cancel_all_timers()
        return True



    # ---------- CALCULATOR ----------
    # Only treat explicit "calculate" as math, not every "what is"
    if "calculate" in t and "rex" in t and "time" not in t:
       calculate_from_command(text)
       return True

    # ---------- SHUTDOWN ----------
    if "shutdown the system" in t or "shut down the system" in t:
        log_event(f"Voice: {t} -> shutdown requested")
        shutdown_system()
        return False

    # ---------- LOCK SYSTEM ----------
    if "lock the computer" in t or "lock the system" in t:
        lock_system()
        return True

    # ---------- OPEN WHATSAPP WEB ----------
    if "open whatsapp web" in t or "open whatsapp" in t:
        speak_async("Opening WhatsApp Web, sir.")
        webbrowser.open("https://web.whatsapp.com")
        last_search_platform = None
        log_event(f"Voice: {t} -> opened WhatsApp Web")
        return True

    # ---------- OPEN PROJECT FOLDER ----------
    if "open my project folder" in t or "open project folder" in t:
        open_project_folder()
        return True

    # ---------- SONG IDENTIFICATION ----------
    if ("what song is this" in t or "identify this song" in t or "which song is this" in t) and "rex" in t:
        identify_song()
        return True

    # ---------- CONTEXT-AWARE SEARCH (SMART) ----------

    if "search" in t and "rex" in t and "open youtube" not in t and "open google" not in t:
        try:
            query = t.split("search", 1)[1].strip()
        except Exception:
            query = ""

        if not query:
            speak_async("What should I search for, sir?")
            log_event(f"Voice: {t} -> search query missing")
            return True

        if last_search_platform == "youtube":
            speak_async(f"Searching {query} on YouTube, sir.")
            url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
            log_event(f"Voice: {t} -> YouTube search: {query}")
        else:
            speak_async(f"Searching {query} on Google, sir.")
            url = f"https://www.google.com/search?q={quote_plus(query)}"
            log_event(f"Voice: {t} -> Google search: {query}")

        webbrowser.open(url)
        return True


        # ---------- FOCUS MODE: BLOCK ENTERTAINMENT COMMANDS ----------
    if state.focus:
        if ("open youtube" in t or "youtube.com" in t or
            "on youtube music" in t or "play on youtube" in t or
            "play music" in t or "play song" in t or "play songs" in t):
            speak_async("Sir, you are in focus mode. To use YouTube or music, please stop focus mode first.")
            log_event(f"Voice: {t} -> blocked due to focus mode (entertainment)")
            return True

    # ---------- YOUTUBE + SEARCH ----------
    if "open youtube" in t and "search" in t:
        try:
            query = t.split("search", 1)[1].strip()
        except Exception:
            query = ""

        last_search_platform = "youtube"

        if query:
            speak_async(f"Searching {query} on YouTube, sir.")
            url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
            log_event(f"Voice: {t} -> open YouTube & search: {query}")
        else:
            speak_async("Opening YouTube home, sir.")
            url = "https://www.youtube.com/"
            log_event(f"Voice: {t} -> open YouTube home")
        webbrowser.open(url)
        return True

    # ---------- SIMPLE YOUTUBE ----------
    if "open youtube" in t:
        speak_async("Opening YouTube sir.")
        webbrowser.open("https://www.youtube.com")
        last_search_platform = "youtube"
        log_event(f"Voice: {t} -> open YouTube")
        return True

    # ---------- GOOGLE + SEARCH ----------
    if "open google" in t and "search" in t:
        try:
            query = t.split("search", 1)[1].strip()
        except Exception:
            query = ""

        last_search_platform = "google"

        if query:
            speak_async(f"Searching {query} on Google, sir.")
            url = f"https://www.google.com/search?q={quote_plus(query)}"
            log_event(f"Voice: {t} -> open Google & search: {query}")
        else:
            speak_async("Opening Google home, sir.")
            url = "https://www.google.com"
            log_event(f"Voice: {t} -> open Google home")
        webbrowser.open(url)
        return True

    # ---------- SIMPLE GOOGLE ----------
    if "open google" in t:
        speak_async("Opening Google sir.")
        webbrowser.open("https://www.google.com")
        last_search_platform = "google"
        log_event(f"Voice: {t} -> open Google")
        return True

    # ---------- YOUTUBE MUSIC AUTO PLAY ----------
    if "play" in t and "on youtube music" in t:
        query = t.replace("rex", "").replace("play", "").replace("on youtube music", "").strip()
        speak_async(f"Playing {query} on YouTube Music, sir.")

        # Step 1: Open YT Music search page
        url = f"https://music.youtube.com/search?q={quote_plus(query)}"
        webbrowser.open(url)
        log_event(f"YT Music: opened search for {query}")

        # Step 2: wait for page to load
        time.sleep(4)

        # Coordinates you gave:
        X1, Y1 = 526, 439   # FIRST song
        X2, Y2 = 535, 527   # SECOND song

        # Step 3: click FIRST song
        pyautogui.moveTo(X1, Y1, duration=0.4)
        pyautogui.click()
        log_event("YT Music: FIRST song clicked")

        # Step 4: wait few seconds
        time.sleep(3)

        # Step 5: click SECOND song
        pyautogui.moveTo(X2, Y2, duration=0.4)
        pyautogui.click()
        log_event("YT Music: SECOND song clicked")

        return True

    # ---------- READ SELECTED TEXT ----------
    if ("read this text" in t or "read this for me" in t or "read the text" in t) and "rex" in t:
        read_selected_text()
        return True

    # ---------- OPEN NOTEPAD ----------
    if "open notepad" in t:
        speak_async("Opening notepad sir.")
        os.system("notepad")
        log_event(f"Voice: {t} -> open Notepad")
        return True

    # ---------- CLOSE TAB ----------
    if "close youtube" in t or "close tab" in t:
        speak_async("Closing the current tab, sir.")
        pyautogui.hotkey("ctrl", "w")
        log_event(f"Voice: {t} -> close tab (Ctrl+W)")
        return True

    # ---------- CLOSE APP ----------
    if "close this app" in t or "close application" in t or "close this window" in t:
        speak_async("Closing the app, sir.")
        pyautogui.hotkey("alt", "f4")
        log_event(f"Voice: {t} -> close window (Alt+F4)")
        return True

        # ---------- TIME ----------
    if ("time" in t and "rex" in t) or "what is the time rex" in t:
        now = datetime.now().strftime("%H:%M")
        speak_async(f"The time is {now}, sir.")
        log_event(f"Voice: {t} -> time = {now}")
        return True

    # ---------- FULL STOP LISTENER (bye) ----------
    if "bye rex" in t:
        speak_async("Stopping voice listener, sir.")
        log_event("Voice: bye rex-> voice listener stopped")
        return False

    # ---------- UNKNOWN / GENERAL QUESTION (AI ANSWER MODE) ----------
    if "rex" in t:
        if state.ai:
            # Clean the prompt a bit for AI
            prompt_text = text
            lowered = prompt_text.lower()
            for kw in ["rex,", "rex", "hey rex", "hi rex", "hello rex", "please", "answer me"]:
                lowered = lowered.replace(kw, "")
            prompt_text = lowered.strip(" ,:-?") or text

            speak_async("Let me think, sir.")
            log_event(f"AI: sending to OpenRouter -> {prompt_text}")

            answer = ask_ai_openrouter(prompt_text)

            if answer:
                speak_async(answer)
                safe_print("AI answer:", answer)
                log_event("AI: answer spoken successfully")
            else:
                speak_async("Sorry sir, my AI brain is not responding right now.")
                log_event("AI: failed to get answer")
        else:
            # Normal non-AI fallback
            speak_async("I cannot do that yet, sir.")
            log_event(f"Voice: {t} -> not implemented")

        return True

    # No 'rex' keyword at all -> ignore
    safe_print("Ignored (no 'rex' keyword).")
    log_event(f"Voice: {t} -> ignored (no 'rex')")
    return True







# ================== VOICE LISTENER ==================
# ================== VOICE LISTENER ==================
def voice_listener():
    global VOICE_ERROR_SHOWN

    # hard stop if voice already disabled
    with state_lock:
        if not state.voice_enabled or not state.voice_running:
            return

    try:
        import pyaudio
    except ImportError:
        with state_lock:
            state.voice_enabled = False
            state.voice_running = False

        if not VOICE_ERROR_SHOWN:
            log_event("Voice disabled permanently: PyAudio not installed", "ERROR")
            VOICE_ERROR_SHOWN = True
        return   # 🔴 THIS RETURN IS ESSENTIAL

    r = sr.Recognizer()

    while True:
        with state_lock:
            if not state.voice_running:
                return

        try:
            with sr.Microphone() as source:
                audio = r.listen(source, timeout=5, phrase_time_limit=7)

            text = r.recognize_google(audio)
            command_queue.put(text)

        except sr.WaitTimeoutError:
            continue
        except sr.UnknownValueError:
            continue
        except Exception as e:
            log_event(f"Voice error: {e}", "ERROR")
            time.sleep(1)



 
    #    start stop function
def start_voice():
    with state_lock:
        if not state.voice_enabled:
            return "disabled"
        if state.voice_running:
            return "already_running"

        state.voice_running = True

    threading.Thread(target=voice_listener, daemon=True).start()
    log_event("Voice listener started manually", "SYSTEM")
    return "started"


def stop_voice():
    with state_lock:
        state.voice_running = False
    log_event("Voice listener stopped manually", "SYSTEM")
    return "stopped"





#============= eneble when you want popup=============#
# def keyboard_listener():
#     try:
#         keyboard.wait("t")  # test permission once
#     except:
#         log_event("Keyboard hook blocked (not admin). T key disabled.")
#         return

#     while True:
#         try:
#             keyboard.wait("t")
#             enter_type_mode()
#         except Exception as e:
#             log_event(f"Keyboard listener error: {e}")
#             time.sleep(1)




# ================== MAIN ==================

# ================== MAIN ==================

def main():
    global rex_started

    if rex_started:
        log_event("Rex already running, start ignored", "SYSTEM")
        return

    rex_started = True

    log_event("System: Rex started with intro", "SYSTEM")

    threading.Thread(target=command_worker, daemon=True).start()
    threading.Thread(target=speech_worker, daemon=True).start()

    speak_async("Hello. I am Rex, your personal assistant.")


if __name__ == "__main__":
    main()


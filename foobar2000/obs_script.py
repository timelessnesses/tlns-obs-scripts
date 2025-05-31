import obspython
import sys
import typing
import os
import threading
import html
import orjson

# NOTE: motherfucking hacks ahead
sys.path.append(r"c:\users\moopi\appdata\roaming\python\python310\site-packages")
# Like, why???????? WHY IN THE ACTUAL FUCK ARE YOU LINKING AGAINST 3.11??????? HELLO??????????

import requests

target_text_name = "fb2k Currently Playing"
enabled = False
host = "localhost:2233"
interval = 500
target_album_image = "fb2k Album Art"


def script_update(settings):
    global target_text_name, password, enabled, host, interval,  target_album_image, network_thread
    target_text_name = obspython.obs_data_get_string(settings, "target")
    enabled = obspython.obs_data_get_bool(settings, "enabled")
    interval = obspython.obs_data_get_int(settings, "interval")
    host = obspython.obs_data_get_string(settings, "host")
    target_album_image = obspython.obs_data_get_string(settings, "album_pic")
    
def script_defaults(settings):
    obspython.obs_data_set_default_string(settings, "target", target_text_name)
    obspython.obs_data_set_default_bool(settings, "enabled", enabled)
    obspython.obs_data_set_default_string(settings, "host", host)
    obspython.obs_data_set_default_int(settings, "interval", interval)
    obspython.obs_data_set_default_string(settings, "album_pic", target_album_image)

def script_properties():
    properties = obspython.obs_properties_create()
    obspython.obs_properties_add_text(properties, "target", "Text Target", obspython.OBS_TEXT_DEFAULT)
    obspython.obs_properties_add_text(properties, "album_pic", "Album Art image target", obspython.OBS_TEXT_DEFAULT)
    obspython.obs_properties_add_text(properties, "password", "Password for VLC API", obspython.OBS_TEXT_DEFAULT)
    obspython.obs_properties_add_bool(properties, "enabled", "Enable Script")
    obspython.obs_properties_add_text(properties, "host", "Hostname and port for foobar2k_server", obspython.OBS_TEXT_DEFAULT)
    obspython.obs_properties_add_int(properties, "interval", "Interval", 10, 10000, 500)
    return properties

def script_description():
    return "fb2k Currently Playing"

def script_load(_):
    global network_thread
    network_thread.start()
    obspython.timer_add(callback_update, interval)

def callback_update():
    global result_text, result_album_image
    set_text(target_text_name, result_text, result_album_image, target_album_image)

class CustomDictType(typing.TypedDict):
    isPlaying: str
    isPaused: str
    title: str
    artist: str
    album: str
    albumArt: str
    length: str
    currentTime: str

result_text = ""
result_album_image = ""
last_album_image = ""

def network_thread_func():
    global result_text, result_album_image
    while True:
        if not enabled:
            print("Not enabled")
            continue
        print("Reloading")
        a = requests.get("http://"+host+"/exporting/?param3=js/state.json")
        a.encoding = "utf-8"
        text = ""
        
        if a.status_code != 200:
            print(f"Failed to authenticate OR no VLC running: {a}")
            text = "Is VLC Running?"
            set_text(target_text_name, text, "", target_album_image)
            return

        print(a.text)
        parsed: CustomDictType = orjson.loads(a.text)
        
        album_art_path = "http://"+host+parsed.get("albumArt", os.path.realpath(__file__) + "/foo_httpcontrol_exporter/img/icon1rx.png")
        
        artist = html.unescape(parsed["artist"])
        title = html.unescape(parsed["title"])
        album = html.unescape(parsed["album"])
        current_time = int(parsed["currentTime"])
        length = float(parsed["length"])
        
        state = parsed["isPlaying"] == "1"
        
        text = f"{ 'PLAYING' if state else 'PAUSED' } {artist} ({album}) - {title} ({format_time(current_time)} / {format_time(length)} {round((current_time / length) * 100, 2)}%) "
        result_text = text
        result_album_image = album_art_path
        # time.sleep(interval / 1000)

network_thread = threading.Thread(target=network_thread_func)
network_thread.setDaemon(True)

def format_time(seconds: float):
    minutes, seconds = divmod(seconds, 60)
    b = int(seconds)
    a = ""
    if b < 10:
        a = "0"+str(b)
    else:
        a = str(b)
    return f"{int(minutes)}:{a}"

def set_text(target: str, text: str, album_image: str, image_target: str):
    global last_album_image
    source = obspython.obs_get_source_by_name(target)
    settings =  obspython.obs_data_create()
    obspython.obs_data_set_string(settings, "text", text)
    obspython.obs_source_update(source, settings)
    if album_image != "" and album_image != last_album_image:
        source = obspython.obs_get_source_by_name(image_target)
        settings =  obspython.obs_data_create()
        obspython.obs_data_set_string(settings, "file", album_image)
        obspython.obs_source_update(source, settings)
        last_album_image = album_image
import obspython
import sys
import typing
import os
import threading
import html
import orjson
import time
import requests

target_text_name = "fb2k Currently Playing"
enabled = False
host = "localhost:2233"
interval = 500  # milliseconds
target_album_image = "fb2k Album Art"
result_text = ""
result_album_image = ""
last_album_image = ""

enabled_event = threading.Event()
stopped_event = threading.Event()
network_thread = None
session = requests.Session()

def script_description():
    return "fb2k Currently Playing"


def script_defaults(settings):
    obspython.obs_data_set_default_string(settings, "target", target_text_name)
    obspython.obs_data_set_default_bool(settings, "enabled", enabled)
    obspython.obs_data_set_default_string(settings, "host", host)
    obspython.obs_data_set_default_int(settings, "interval", interval)
    obspython.obs_data_set_default_string(settings, "album_pic", target_album_image)


def script_properties():
    props = obspython.obs_properties_create()
    obspython.obs_properties_add_text(props, "target", "Text Target", obspython.OBS_TEXT_DEFAULT)
    obspython.obs_properties_add_text(props, "album_pic", "Album Art image target", obspython.OBS_TEXT_DEFAULT)
    obspython.obs_properties_add_bool(props, "enabled", "Enable Script")
    obspython.obs_properties_add_text(props, "host", "Hostname and port for foobar2k_server", obspython.OBS_TEXT_DEFAULT)
    obspython.obs_properties_add_int(props, "interval", "Interval (ms)", 10, 10000, 100)
    return props


def script_update(settings):
    global target_text_name, enabled, host, interval, target_album_image

    target_text_name = obspython.obs_data_get_string(settings, "target")
    enabled = obspython.obs_data_get_bool(settings, "enabled")
    host = obspython.obs_data_get_string(settings, "host")
    interval = obspython.obs_data_get_int(settings, "interval")
    target_album_image = obspython.obs_data_get_string(settings, "album_pic")

    if enabled:
        enabled_event.set()
    else:
        enabled_event.clear()

    obspython.timer_remove(callback_update)
    obspython.timer_add(callback_update, interval)


def script_load(_):
    global network_thread, session
    enabled_event.clear()
    stopped_event.clear()

    network_thread = threading.Thread(target=network_thread_func, daemon=True)
    network_thread.start()

    obspython.timer_add(callback_update, interval)


def script_unload():
    stopped_event.set()
    enabled_event.set()

    obspython.timer_remove(callback_update)

    try:
        session.close()
    except:
        pass

    if network_thread is not None:
        network_thread.join(timeout=2)


def callback_update():
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


def network_thread_func():
    global result_text, result_album_image
    while not stopped_event.is_set():
        if not enabled_event.is_set():
            time.sleep(0.1)
            continue

        try:
            resp = session.get(f"http://{host}/exporting/?param3=js/state.json", timeout=5)
            resp.encoding = "utf-8"
        except requests.RequestException:
            result_text = "Foobar2000 is not responsive... check foo_httpcontrol"
            result_album_image = os.path.join(os.path.dirname(__file__), "foo_httpcontrol_exporter/img/icon1rx.png")
            time.sleep(interval / 1000)
            continue

        if resp.status_code != 200:
            result_text = f"Error {resp.status_code} from Foobar2000"
            result_album_image = os.path.join(os.path.dirname(__file__), "foo_httpcontrol_exporter/img/icon1rx.png")
            time.sleep(interval / 1000)
            continue

        try:
            parsed: CustomDictType = orjson.loads(resp.text)
        except orjson.JSONDecodeError:
            result_text = "Failed to parse JSON from Foobar2000"
            time.sleep(interval / 1000)
            continue

        artist = html.unescape(parsed.get("artist", ""))
        title = html.unescape(parsed.get("title", ""))
        album = html.unescape(parsed.get("album", ""))
        current_time = float(parsed.get("currentTime", 0))
        length = float(parsed.get("length", 1))

        state = parsed.get("isPlaying", "0") == "1"
        percent = (current_time / length * 100) if length > 0 else 0
        result_text = f"{'PLAYING' if state else 'PAUSED'} {artist} ({album}) - {title} ({format_time(current_time)} / {format_time(length)} {percent:.2f}%)"

        art_url = parsed.get("albumArt", "")
        if art_url.startswith("/"):
            art_url = f"http://{host}{art_url}"
        result_album_image = art_url

        time.sleep(interval / 1000)

def format_time(seconds: float) -> str:
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}:{secs:02d}"


def set_text(text_source: str, text: str, image_url: str, image_source: str):
    global last_album_image
    src = obspython.obs_get_source_by_name(text_source)
    if src:
        settings = obspython.obs_data_create()
        obspython.obs_data_set_string(settings, "text", text)
        obspython.obs_source_update(src, settings)
        obspython.obs_data_release(settings)
        obspython.obs_source_release(src)

    if image_url and image_url != last_album_image: # the thing is that, obs really freaks out when you constantly kept changing the image path :(
        img_src = obspython.obs_get_source_by_name(image_source)
        if img_src:
            settings = obspython.obs_data_create()
            obspython.obs_data_set_string(settings, "file", image_url)
            obspython.obs_source_update(img_src, settings)
            obspython.obs_data_release(settings)
            obspython.obs_source_release(img_src)
        last_album_image = image_url

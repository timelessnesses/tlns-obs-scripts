import obspython
import sys

# NOTE: motherfucking hacks ahead
sys.path.append("/home/timelessnesses/.cache/pypoetry/virtualenvs/obs-scripts-mJxeFPi8-py3.10/lib/python3.10/site-packages")
# Like, why???????? WHY IN THE ACTUAL FUCK ARE YOU LINKING AGAINST 3.11??????? HELLO??????????

import xmltodict
import requests

target_text_name = "VLC Currently Playing"
password = ""
enabled = False
host = "localhost:8080"
interval = 500

def script_update(settings):
    global target_text_name, password, enabled, host, interval
    target_text_name = obspython.obs_data_get_string(settings, "target")
    password = obspython.obs_data_get_string(settings, "password")
    enabled = obspython.obs_data_get_bool(settings, "enabled")
    interval = obspython.obs_data_get_int(settings, "interval")
    host = obspython.obs_data_get_string(settings, "host")
    obspython.timer_remove(send_info)
    obspython.timer_add(send_info, interval)
    
def script_load(_):
    print(sys.path)
    obspython.timer_add(send_info, interval)
    
def script_defaults(settings):
    obspython.obs_data_set_default_string(settings, "target", target_text_name)
    obspython.obs_data_set_default_string(settings, "password", password)
    obspython.obs_data_set_default_bool(settings, "enabled", enabled)
    obspython.obs_data_set_default_string(settings, "host", host)
    obspython.obs_data_set_default_int(settings, "interval", interval)

def script_properties():
    properties = obspython.obs_properties_create()
    obspython.obs_properties_add_text(properties, "target", "Text Target", obspython.OBS_TEXT_DEFAULT)
    obspython.obs_properties_add_text(properties, "password", "Password for VLC API", obspython.OBS_TEXT_DEFAULT)
    obspython.obs_properties_add_bool(properties, "enabled", "Enable Script")
    obspython.obs_properties_add_text(properties, "host", "Hostname and port for VLC (host:port)", obspython.OBS_TEXT_DEFAULT)
    obspython.obs_properties_add_int(properties, "interval", "Interval", 10, 10000, 500)
    return properties

def script_description():
    return "VLC Currently Playing"


def send_info():
    if not enabled:
        return
    print("Reloading")
    a = requests.get("http://"+host+"/requests/status.xml", auth=("", password))
    text = ""
    
    if a.status_code != 200:
        print(f"Failed to authenticate OR no VLC running: {a}")
        text = "Is VLC Running?"
        set_text(target_text_name, text)
        return
    
    root = xmltodict.parse(a.text)["root"]
    info = root["information"]["category"][0]["info"]
    
    # unused (for now)
    album_art_path = ""
    
    artist = "None"
    title = "None"
    pos = float(root["position"])
    length = int(root["length"])
    current_time = length * pos
    
    state = root["state"] == "playing"
    for item in info:
        if item["@name"] == "artwork_url":
            album_art_path = item["#text"].strip("file://")
        if item["@name"] == "artist":
            artist = item["#text"]
        if item["@name"] == "title":
            title = item["#text"]
    text = f"{ 'PLAYING' if state else 'PAUSED' } {artist} - {title} ({format_time(current_time)} / {format_time(length)} {round(pos * 100, 2)}%) "
    print(text)
    set_text(target_text_name, text)

def format_time(seconds: float):
    minutes, seconds = divmod(seconds, 60)
    b = int(seconds)
    a = ""
    if b < 10:
        a = "0"+str(b)
    else:
        a = str(b)
    return f"{int(minutes)}:{a}"

def set_text(target: str, text: str):
    source = obspython.obs_get_source_by_name(target) # none?
    print(source)
    settings =  obspython.obs_data_create()
    print(settings)
    obspython.obs_data_set_string(settings, "text", text)
    print(settings)
    obspython.obs_source_update(source, settings)
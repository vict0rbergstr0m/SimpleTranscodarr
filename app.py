from flask import Flask, request, render_template, jsonify, Response
import os
from src.ffmpeg import *
import re
import time
import redis
from celery import Celery

app = Flask(__name__)

# Create a Redis connection
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Define a global variable
"""global_data = {
    'msg': '',
    'filtering': {
        'path': '/',
        'sub_directories': ["/"],
        'title_regex': "",
        'resolutions': [],
        'encodings': [],
        'min_size': "",
        'containers': [
            'mkv', 'mp4', 'avi', 'mov', 'wmv', 'flv', 'webm', 'ogg'
        ]
    },
    'running':
    {
        'isRunning': False,
        'progress': 0,
        'found_items': [],
        'time_left': -1,
        'time_per_item': [],
        'total_items': 0,
        'processed_items': 0,
        'total_time': 0,
    },
    'transcode_settings': 
    {
        'crf': 22,
        'codec': 'libx265',
        'resolution': 1080,
        'container': 'mkv'
    }
    }"""

def initialize_cache():
    """Initialize the cache with default values."""

    """filtering"""
    filtering = {
        'path': '/',
        'sub_directories': ["/"],
        'title_regex': "",
        'resolutions': [],
        'encodings': [],
        'min_size': "",
        'containers': [
            'mkv', 'mp4', 'avi', 'mov', 'wmv', 'flv', 'webm', 'ogg'
        ]
    }
    write_dict_to_cache("filtering", filtering)
    
    """running"""

    running = {
        'isRunning': False,
        'progress': 0,
        'time_left': -1,
        'total_items': 0,
        'processed_items': 0,
        'total_time': 0,
        "found_items": [],
        "time_per_item": []
    }

    write_dict_to_cache("running", running)

    """transcode_settings"""

    transcode_settings = {
        'crf': 22,
        'codec': 'libx265',
        'resolution': 1080,
        'container': 'mkv'
    }

    write_dict_to_cache("transcode_settings", transcode_settings)


def write_value_to_cache(key_name: str, value: str):
    try:
        r.set(key_name, value)
    except redis.exceptions.RedisError as e:
        print(f"Error writing to cache: {e}")

def write_dict_to_cache(key_name: str, dictionary: dict):
    try:
        jsontext = json.dumps(dictionary)
        r.set(key_name, jsontext)
    except redis.exceptions.RedisError as e:
        print(f"Error writing to cache: {e}")


def read_value_from_cache(key_name: str):
    try:
        return r.get(key_name)
    except redis.exceptions.RedisError as e:
        print(f"Error reading from cache: {e}")

def read_dict_from_cache(key_name: str):
    try:
        string_dict = r.get(key_name)
        if string_dict is None:
            return {}
        found_dict = json.loads(string_dict)
        return found_dict
    except redis.exceptions.RedisError as e:
        print(f"Error reading from cache: {e}")


@app.route('/apply-filter', methods=['POST'])
def apply_filter():

    running_info = read_dict_from_cache("running")
    if running_info['isRunning']:
        return {"msg": "Something is already running. Please wait for it to finish."}
    
    filter_info = read_dict_from_cache("filtering")

    data = request.get_json();
    def split_and_filter_empty(value):
        return [item for item in value.split(",") if item != ""]

    filter_info['title_regex'] = data['title_regex']
    filter_info['resolutions'] = split_and_filter_empty(data['resolutions'])
    filter_info['encodings'] = split_and_filter_empty(data['encodings'])
    filter_info['min_size'] = data['min_size']
    filter_info['containers'] = split_and_filter_empty(data['containers'])

    write_dict_to_cache("filtering", filter_info)

    return {"msg": "Filter applied successfully."}

# Endpoint for scanning and sending progress updates
@app.route('/scan', methods=['POST'])
def scan():
    running_info = read_dict_from_cache("running")
    if running_info['isRunning']:
        return {"msg": "Something is already running. Please wait for it to finish."}

    print("runnig scan")
    # data = request.get_json();
    
    filter_info = read_dict_from_cache("filtering")
    input_path = filter_info['path']
    if not os.path.exists(input_path):
        return {"msg": "Input path does not exist."}
    
    running_info = read_dict_from_cache("running")

    def scanning():
        running_info['progress'] = 0
        running_info['time_left'] = -1
        running_info['found_items'] = []
        running_info['time_per_item'] = []
        running_info['isRunning'] = True;
        running_info['total_time'] = 0
        total_files = sum([len(files) for r, d, files in os.walk(input_path)])
        running_info['total_items'] = total_files

        write_dict_to_cache("running", running_info)

        processed_files = 0
        for root, dirs, files in os.walk(input_path):
            for f in files:
                startTime = time.time()
                path = os.path.join(root, f)
                full_info = get_media_info(path);
                if full_info is None or not 'streams' in full_info or len(full_info['streams']) == 0:
                    continue;
                video_info = full_info['streams'][0]
                video = {
                    'name': f,
                    'path': path,
                    'res': video_info['height'],
                    'encoding': video_info['codec_name'],
                    'container': os.path.splitext(f)[1],
                    'size': f"{os.path.getsize(path)/ (1024 * 1024 * 1024):.2f}GB",
                }

                processed_files += 1
                running_info['processed_items'] = processed_files
                endTime = time.time()
                running_info['time_per_item'].append(endTime - startTime)
                running_info['total_time'] = sum(running_info['time_per_item'])
                running_info['time_left'] = (total_files - processed_files) * (sum(running_info['time_per_item']) / processed_files)
                running_info['progress'] = int((processed_files / total_files) * 100)
                print(f"Processed {processed_files} files out of {total_files}.")
                if not filter_moviefile(video, filter_info):
                    continue

                running_info["found_items"].append(video)

                write_dict_to_cache("running", running_info)

        running_info['processed_items'] = total_files
        running_info['progress'] = 100
        running_info['isRunning'] = False;
        write_dict_to_cache("running", running_info)
        #return success
    scanning();
    return {"msg": "Scanning started."}
def filter_moviefile(videoInfo, filter_dict):
    """    
    filter_dict['title_regex']
    filter_dict['resolutions']
    filter_dict['encodings']
    filter_dict['min_size']
    filter_dict['containers']
    """

    if "_temp." in videoInfo['name']:
        return False

    if filter_dict['title_regex'] != "" and not re.search(filter_dict['title_regex'], videoInfo['name']):
        return False
    
    if len(filter_dict['resolutions']) > 0 and not str(videoInfo['res']) in filter_dict['resolutions']:
        return False
    
    if len(filter_dict['encodings']) > 0 and not videoInfo['encoding'] in filter_dict['encodings']:
        return False
    
    if filter_dict['min_size'] != "" and float(videoInfo['size'][:-2]) < float(filter_dict['min_size']):
        return False
    
    if videoInfo['container'].replace(".", "") not in filter_dict['containers']:
        return False


    return True

@app.route('/index', methods=['POST'])
def index():
    running_info = read_dict_from_cache("running")
    if running_info['isRunning']:
        return {"msg": "Something is already running. Please wait for it to finish."}
    input_path = request.form.get('input_path')
    # path = os.path.expanduser("~") + input_path

    filter_info = read_dict_from_cache("filtering")

    path = input_path
    if os.path.exists(path):
        print("input_path: " + input_path)
        filter_info['path'] = path
        items = []
        for item in os.listdir(path):
            items.append(item)
        filter_info['sub_directories'] = items

    write_dict_to_cache("filtering", filter_info)

    return {"msg": "Found path!"}


@app.route('/transcode_video_que', methods=['POST'])
def transcode_video_que():
    running_info = read_dict_from_cache("running")
    if running_info['isRunning']:
        return {"msg": "Something is already running. Please wait for it to finish."}
    running_info['isRunning'] = True;


    global_data['transcode_settings'] = request.get_json();

    running_info['processed_items'] = 0
    running_info['progress'] = 0
    running_info['time_left'] = -1
    running_info['time_per_item'] = []
    running_info['isRunning'] = True;
    running_info['total_time'] = 0
    total_files = len(running_info['found_items'])

    processed_files = 0

    for item in running_info['found_items']:
        startTime = time.time()

        resolution = global_data['transcode_settings']['resolution'];
        if resolution == "":
            resolution = item['res'];

        for transcode_info in transcode_file(item['path'],
                    item['path'].replace(item['name'],""),
                    resolution,
                    global_data['transcode_settings']['codec'],
                    global_data['transcode_settings']['crf'],
                    "slow",
                    global_data['transcode_settings']['container'],
                    remove_original=True,
                ):
            # print(transcode_info)
            running_info['progress'] = (float(transcode_info['frame'])/float(transcode_info['NUMBER_OF_FRAMES']))*100.0
            running_info['total_time'] = time.time() - startTime
            running_info['processed_items'] = transcode_info['frame']
            running_info['total_items'] = transcode_info['NUMBER_OF_FRAMES']

            if transcode_info['fps'] != 0:
                running_info['time_left'] = (transcode_info['NUMBER_OF_FRAMES'] - transcode_info['frame'])/transcode_info['fps']

        processed_files += 1
        endTime = time.time()
        # running_info['time_per_item'].append(endTime - startTime)
        print(f"Transcoded {processed_files} files out of {total_files}.")

        endTime = time.time()

    return jsonify(global_data)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/fetch-data', methods=['GET'])
def fetch_data():
    global_data = {'filtering': read_dict_from_cache("filtering"),
                    'running': read_dict_from_cache("running"),
                    'transcode_settings': read_dict_from_cache("transcode_settings")}
    return jsonify(global_data)


initialize_cache()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8265)

    # Set a value for the key 'hello'
    print('writing hello to world/cache')
    r.set('hello', 'world')

    # Get the value for the key 'hello'
    print(r.get('hello'))
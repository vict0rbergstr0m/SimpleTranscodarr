from flask import Flask, request, render_template, jsonify, Response
import os
from src.ffmpeg import *
import re
import time

app = Flask(__name__)

# Define a global variable
global_data = {
    'msg': '',
    'filtering': {
        'path': os.path.expanduser('~'),
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
    }


def index():
    if global_data['running']['isRunning']: #if scan is already running, chill bro-
        global_data['msg'] = "Something is already running. Please wait for it to finish."
        return jsonify(global_data)  
    path = os.path.expanduser('~')
    if os.path.exists(path):
        global_data['filtering']['path'] = path
        items = []
        for item in os.listdir(path):
            items.append(item)
        global_data['filtering']['sub_directories'] = items

index();

@app.route('/apply-filter', methods=['POST'])
def apply_filter():
    if global_data['running']['isRunning']: 
        global_data['msg'] = "Something is already running. Please wait for it to finish."
        return jsonify(global_data)
    
    data = request.get_json();

    def split_and_filter_empty(value):
        return [item for item in value.split(",") if item != ""]

    global_data['filtering']['title_regex'] = data['title_regex']
    global_data['filtering']['resolutions'] = split_and_filter_empty(data['resolutions'])
    global_data['filtering']['encodings'] = split_and_filter_empty(data['encodings'])
    global_data['filtering']['min_size'] = data['min_size']
    global_data['filtering']['containers'] = split_and_filter_empty(data['containers'])

    return jsonify(global_data)

# Endpoint for scanning and sending progress updates
@app.route('/scan', methods=['POST'])
def scan():
    if global_data['running']['isRunning']: #if scan is already running, chill bro
        global_data['msg'] = "Something is already running. Please wait for it to finish."
        return jsonify(global_data)

    print("runnig scan")
    data = request.get_json();
    input_path = global_data['filtering']['path']
    if not os.path.exists(input_path):
        return jsonify(global_data)

    def scanning():
        global_data['running']['progress'] = 0
        global_data['running']['time_left'] = -1
        global_data['running']['found_items'] = []
        global_data['running']['time_per_item'] = []
        global_data['running']['isRunning'] = True;
        global_data['running']['total_time'] = 0
        total_files = sum([len(files) for r, d, files in os.walk(input_path)])
        global_data['running']['total_items'] = total_files
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
                global_data['running']['processed_items'] = processed_files
                endTime = time.time()
                global_data['running']['time_per_item'].append(endTime - startTime)
                global_data['running']['total_time'] = sum(global_data['running']['time_per_item'])
                global_data['running']['time_left'] = (total_files - processed_files) * (sum(global_data['running']['time_per_item']) / processed_files)
                global_data['running']['progress'] = int((processed_files / total_files) * 100)
                print(f"Processed {processed_files} files out of {total_files}.")
                if not filter_moviefile(video, global_data['filtering']):
                    continue

                global_data['running']['found_items'].append(video)

        global_data['running']['processed_items'] = total_files
        global_data['running']['progress'] = 100
        global_data['running']['isRunning'] = False;
        #return success
    scanning();
    return jsonify(global_data)
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
    if global_data['running']['isRunning']: #if somthing is already running, chill bro-
        global_data['msg'] = "Something is already running. Please wait for it to finish."
        return jsonify(global_data)  
    input_path = request.form.get('input_path')
    # path = os.path.expanduser("~") + input_path
    path = input_path
    if os.path.exists(path):
        print("input_path: " + input_path)
        global_data['filtering']['path'] = path
        items = []
        for item in os.listdir(path):
            items.append(item)
        global_data['filtering']['sub_directories'] = items

    return jsonify(global_data)


@app.route('/transcode_video_que', methods=['POST'])
def transcode_video_que():
    if global_data['running']['isRunning']: #if somthing is already running, chill bro-
        global_data['msg'] = "Something is already running. Please wait for it to finish."
        return jsonify(global_data)

    global_data['transcode_settings'] = request.get_json();

    global_data['running']['processed_items'] = 0
    global_data['running']['progress'] = 0
    global_data['running']['time_left'] = -1
    global_data['running']['time_per_item'] = []
    global_data['running']['isRunning'] = True;
    global_data['running']['total_time'] = 0
    total_files = len(global_data['running']['found_items'])

    processed_files = 0

    for item in global_data['running']['found_items']:
        startTime = time.time()

        resolution = global_data['transcode_settings']['resolution'];
        if resolution == "":
            resolution = item['res'];

        for output in transcode_file(item['path'],
                    item['path'].replace(item['name'],""),
                    resolution,
                    global_data['transcode_settings']['codec'],
                    global_data['transcode_settings']['crf'],
                    "slow",
                    global_data['transcode_settings']['container'],
                    # remove_original=True,
                ):
            print(output)
            print("testtest")
            pass

        processed_files += 1
        global_data['running']['processed_items'] = processed_files
        endTime = time.time()
        global_data['running']['time_per_item'].append(endTime - startTime)
        global_data['running']['total_time'] = sum(global_data['running']['time_per_item'])
        global_data['running']['time_left'] = (total_files - processed_files) * (sum(global_data['running']['time_per_item']) / processed_files)
        global_data['running']['progress'] = int((processed_files / total_files) * 100)
        print(f"Transcoded {processed_files} files out of {total_files}.")

        endTime = time.time()

    return jsonify(global_data)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/fetch-data', methods=['GET'])
def fetch_data():
    return jsonify(global_data)

if __name__ == '__main__':
    app.run(debug=True)
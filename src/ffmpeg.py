import subprocess
import json
from pathlib import Path
import os
import re

def __run_command(command):
    """Run a shell command and return the output."""
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error: {e.stderr}")
        return None

def __run_open_command(command):
    """Run a shell command and yield the output line by line."""
    os.chdir(os.path.expanduser('~'))
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    while True:
        output_err = process.stderr.readline()
        output_out = process.stdout.readline()
        if output_out == '' and process.poll() is not None:
            break
        if output_out:
            # print(output_out.strip())
            yield output_out.strip(), output_err.strip()

def get_ffmpeg_version():
    """Get the version of ffmpeg."""
    command = ["ffmpeg", "-version"]
    output = __run_command(command)
    if output:
        return output.split('\n')[0]
    return None

def get_ffprobe_version():
    """Get the version of ffprobe."""
    command = ["ffprobe", "-version"]
    output = __run_command(command)
    if output:
        return output.split('\n')[0]
    return None

def get_media_info(file_path):
    """Get detailed information about a media file using ffprobe."""
    command = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", file_path]
    output = __run_command(command)
    if output:
        return json.loads(output)
    return None

def transcode_file(input_file, output_dir, resolution, codec="libx265", crf="22", preset="slow", container="mkv", remove_original=False):
    """Convert a media file to a different format using ffmpeg."""

    final_file = output_dir + Path(input_file).stem  + "_temp." + container

    if os.path.exists(final_file):
        os.remove(final_file)

    command = [
        "ffmpeg",
        "-i", input_file,
        "-progress", "-",
        "-vf", f"scale=-1:{resolution}",
        "-c:v", codec,
        "-crf", str(crf),
        "-preset", preset,
        "-c:a", "copy",
        final_file
    ]


    # outs = []
    transcode_info = {
        'NUMBER_OF_FRAMES':-1,
        'frame':-1,
        'fps':-1
    }
    # errs = []
    for (stdout, stderr) in __run_open_command(command):
        # outs.append(stdout)
        # errs.append(stderr)
        # print(outs)

        if "NUMBER_OF_FRAMES: " in stderr and transcode_info['NUMBER_OF_FRAMES'] == -1:
            transcode_info['NUMBER_OF_FRAMES'] = int(re.sub('[^0-9\.]', '', stderr))
        if "frame=" in stdout:
            transcode_info['frame'] = int(re.sub('[^0-9\.]', '', stdout))
        if "fps=" in stdout:
            transcode_info['fps'] = float(re.sub('[^0-9\.]', '', stdout))
        
        yield transcode_info

    if remove_original:
        os.remove(input_file)

    final_file_without_temp = final_file.replace("_temp", "_transcoded")
    os.rename(final_file, final_file_without_temp)


if __name__ == "__main__":
    # Example usage
    print("FFmpeg Version:", get_ffmpeg_version())
    print("FFprobe Version:", get_ffprobe_version())


    test_input = "/home/victor/bDrive/mediaBDrive/AnimeMovies/Baki Hanma VS Kengan Ashura (2024) {imdb-tt31869664}/Baki Hanma VS Kengan Ashura 2024 1080p NF WEB-DL DDP5.1 H 264-VARYG (Hanma Baki vs. Kengan Ashura, Dual-Audio, Multi-Subs).mkv"
    test_out_dir = "/home/victor/bDrive/mediaBDrive/AnimeMovies/Baki Hanma VS Kengan Ashura (2024) {imdb-tt31869664}/"
    for info in transcode_file(test_input, test_out_dir, 720, preset="ultrafast", crf=28):
        print(info)

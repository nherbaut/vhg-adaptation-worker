__author__ = 'nherbaut'
import subprocess
import math
import os
import tempfile
import urllib
import shutil
import uuid


# config import
from settings import config

# celery import
from celery import Celery, chord

# media info wrapper import
from pymediainfo import MediaInfo

# context helpers
from context import get_transcoded_folder, get_transcoded_file, get_hls_transcoded_playlist, get_hls_transcoded_folder, \
    get_dash_folder, get_hls_folder, get_hls_global_playlist, get_dash_mpd_file_path

# main app for celery, configuration is in separate settings.ini file
app = Celery('tasks')

# inject settings into celery
app.config_from_object('adaptation.settings')


@app.task(bind=True)
def notify(*args, **kwargs):
    self = args[0]
    context = args[1]

    main_task_id = kwargs["main_task_id"]
    if "complete" in kwargs and kwargs["complete"]:
        self.update_state(main_task_id, state="COMPLETE")
    else:
        self.update_state(main_task_id, state="PARTIAL", meta={"hls": get_hls_transcoded_playlist(context)})
    return context


@app.task()
def ddo(url):
    encode_workflow.delay(url)


@app.task(bind=True)
    def encode_workflow(self, url):
    main_task_id = self.request.id
    print "(------------"
    print main_task_id
    random_uuid = uuid.uuid4().hex
    return (
        download_file.s(
            context={"url": url, "folder_out": os.path.join(config["folder_out"], random_uuid), "id": random_uuid}) |
        get_video_size.s() |
        add_playlist_header.s() |
        chord(
            [(compute_target_size.s(target_height=target_height) |
              transcode.s(bitrate=bitrate) |
              chunk_hls.s(segtime=4) |
              add_playlist_info.s() | notify.s(main_task_id=main_task_id))
             for target_height, bitrate in config["bitrates_size_dict"].items()],

            (add_playlist_footer.s() |
             chunk_dash.s() | notify.s(complete=True, main_task_id=main_task_id))
        )
    )()


@app.task()
# def download_file(url, id):
def download_file(*args, **kwargs):
    print args, kwargs
    context = kwargs["context"]
    print("downloading %s", context["url"])
    context["original_file"] = os.path.join(tempfile.mkdtemp(), context["id"])
    print("downloading in %s", context["original_file"] )
    opener = urllib.URLopener()
    opener.retrieve(context["url"], context["original_file"])
    print("downloaded in %s", context["original_file"] )
    return context


@app.task
# def get_video_size(input_file):
def get_video_size(*args, **kwargs):
    '''
    use mediainfo to compute the video size
    '''
    print args, kwargs
    context = args[0]
    media_info = MediaInfo.parse(context["original_file"])
    for track in media_info.tracks:
        if track.track_type == 'Video':
            print "video is %d, %d" % (track.height, track.width)
            context["track_width"] = track.width
            context["track_height"] = track.height
            return context
    raise AssertionError("failed to read video info from " + context["original_file"])


@app.task
# def compute_target_size(original_height, original_width, target_height):
def compute_target_size(*args, **kwargs):
    '''
    compute the new size for the video
    '''
    context = args[0]
    context["target_height"] = kwargs['target_height']

    print args, kwargs
    context["target_width"] = math.trunc(
        float(context["target_height"]) / context["track_height"] * context["track_width"] / 2) * 2
    return context


@app.task
# def transcode(file_in, folder_out, dimensions, bitrate):
def transcode(*args, **kwargs):
    '''
    transcode the video to mp4 format
    '''
    # print args, kwargs
    context = args[0]
    context["bitrate"] = kwargs['bitrate']
    dimsp = str(context["target_width"]) + ":" + str(context["target_height"])
    if not os.path.exists(get_transcoded_folder(context)):
        os.makedirs(get_transcoded_folder(context))
    subprocess.call(
        "ffmpeg -i " + context[
            "original_file"] + " -c:v libx264 -profile:v main -level 3.1 -b:v 100k -vf scale=" + dimsp + " -c:a aac -strict -2 -force_key_frames expr:gte\(t,n_forced*4\) " + get_transcoded_file(
            context),
        shell=True)
    return context


@app.task
# def chunk_hls(file_in, folder_out, dimensions, segtime=4):
def chunk_hls(*args, **kwargs):
    '''
    create hls chunks and the version specific playlist
    '''
    # print args, kwargs
    context = args[0]
    context["segtime"] = kwargs['segtime']

    if not os.path.exists(get_hls_transcoded_folder(context)):
        os.makedirs(get_hls_transcoded_folder(context))

    ffargs = "ffmpeg -i " + get_transcoded_file(
        context) + " -map 0 -flags +global_header -vcodec copy -vbsf h264_mp4toannexb -acodec copy -f segment -segment_format mpegts -segment_time " + str(
        context["segtime"]) + " -segment_wrap 0 -segment_list " + get_hls_transcoded_playlist(
        context) + " " + get_hls_transcoded_folder(context) + "/chunks_name%03d.ts"
    print ffargs
    subprocess.call(ffargs, shell=True)
    return context


@app.task
# def chunk_dash(files_in, folder_out):
def chunk_dash(*args, **kwargs):
    '''
    create dash chunks for every video in the transcoded folder
    '''
    # print args, kwargs
    context = args[0]
    if not os.path.exists(get_dash_folder(context)):
        os.makedirs(get_dash_folder(context))

    args = "MP4Box -dash 4000 -profile onDemand "
    files_in = [os.path.join(get_transcoded_folder(context), f) for f in os.listdir(get_transcoded_folder(context))]
    for i in range(0, len(files_in)):
        args += files_in[i] + "#video:id=v" + str(i) + " "

    args += " -out " + get_dash_mpd_file_path(context)
    print args
    subprocess.call(args, shell=True)
    return context


@app.task
# def add_playlist_info(main_playlist_folder, version_playlist_file, bitrate):
def add_playlist_info(*args, **kwargs):
    '''
    add this hls palylist info into the global hls playlist
    '''
    # print args, kwargs
    context = args[0]
    with open(get_hls_global_playlist(context), "a") as f:
        f.write("#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=" + str(
            context["bitrate"] * 1000) + ",RESOLUTION=" + get_hls_transcoded_playlist(context) + "\n")
    return context


@app.task
# def add_playlist_header(playlist_folder):
def add_playlist_header(*args, **kwargs):
    '''
    add the header to the global playlist, possibly remove existing hls folder and recreate it
    '''
    # print args, kwargs
    context = args[0]
    if os.path.exists(get_hls_folder(context)):
        shutil.rmtree(get_hls_folder(context))
    os.makedirs(get_hls_folder(context))

    with open(get_hls_global_playlist(context), "a") as f:
        f.write("#EXTM3U\n")
    return context


@app.task
# def add_playlist_footer(playlist_folder):
def add_playlist_footer(*args, **kwargs):
    '''
    add global hls playlist folder
    '''
    # print args, kwargs
    context = args[0][0]  # take the first context["on"] the list, since we receive more than one
    with open(get_hls_global_playlist(context), "a") as f:
        f.write("##EXT-X-ENDLIST")
    return context

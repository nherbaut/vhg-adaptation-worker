__author__ = 'nherbaut'
import subprocess
import math
import os
import urllib
import shutil
import json

import pika
from celery.utils.log import get_task_logger







# config import
from settings import *

# celery import
from celery import Celery, chord

# media info wrapper import
from pymediainfo import MediaInfo

# lxml import to edit dash playlist
from lxml import etree as LXML

# context helpers
from context import get_transcoded_folder, get_transcoded_file, get_hls_transcoded_playlist, get_hls_transcoded_folder, \
    get_dash_folder, get_hls_folder, get_hls_global_playlist, get_dash_mpd_file_path

# main app for celery, configuration is in separate settings.ini file
app = Celery('tasks')

# logger FROM CELERY, not native python
logger = get_task_logger(__name__)

# inject settings into celery
app.config_from_object('adaptation.settings')

connection = pika.BlockingConnection(pika.ConnectionParameters(
    config["broker_host"]))
channel_pika = connection.channel()
channel_pika.queue_declare(queue='transcode-result', durable=True, exclusive=False, auto_delete=False)


@app.task(bind=True)
def notify(*args, **kwargs):
    self = args[0]
    context = args[1]
    main_task_id = kwargs["main_task_id"]
    logger.debug("sending %s to result queue" % json.dumps(kwargs))
    channel_pika.basic_publish(exchange='',
                               routing_key='transcode-result',
                               body=json.dumps(kwargs))

    return context


def deploy_original_file(*args, **kwargs):
    context = args[0]
    encoding_folder = get_transcoded_folder(context)
    if not os.path.exists(encoding_folder):
        os.makedirs(encoding_folder)
    shutil.copyfile(context["original_file"], os.path.join(encoding_folder, "original.mp4"))
    return context


@app.task()
def ddo(url):
    encode_workflow.delay(url)


@app.task(bind=True)
def encode_workflow(self, url):
    main_task_id = self.request.id

    (
        download_file.s(
            context={"url": url, "folder_out": os.path.join(config["folder_out"], main_task_id), "id": main_task_id,
                     "folder_in": config["folder_in"]}) |
        deploy_original_file.s() |
        notify.s(main_task_id=main_task_id, quality='original') |
        get_video_size.s() |
        add_playlist_header.s() |
        chord(
            [(compute_target_size.s(target_height=target_height) |
              transcode.s(bitrate=bitrate, segtime=4, name=name) |
              notify.s(main_task_id=main_task_id, quality=name) |
              chunk_hls.s(segtime=4) |
              add_playlist_info.s()
             )
             for target_height, bitrate, name in config["bitrates_size_tuple_list"]],

            (add_playlist_footer.s() |
             chunk_dash.s(segtime=4) |  # Warning : segtime is already set in transcode.s(), but not in the same context
             edit_dash_playlist.s() | notify.s(complete=True, main_task_id=main_task_id))))()


@app.task(bind=True)
def encode_workflow_parallel(self, url):
    main_task_id = self.request.id

    print main_task_id
    (
        download_file.s(
            context={"url": url, "folder_out": os.path.join(config["folder_out"], main_task_id), "id": main_task_id,
                     "folder_in": config["folder_in"]}) |
        get_video_size.s() |
        add_playlist_header.s() |
        chord(
            [(compute_target_size.s(target_height=target_height) |
              transcode.s(bitrate=bitrate, segtime=4, name=name) |
              notify.s(main_task_id=main_task_id, quality=name) |
              chunk_hls.s(segtime=4) |
              add_playlist_info.s()
             )
             for target_height, bitrate, name in config["bitrates_size_tuple_list"]],

            (add_playlist_footer.s() |
             chunk_dash.s(segtime=4) |  # Warning : segtime is already set in transcode.s(), but not in the same context
             edit_dash_playlist.s() | notify.s(complete=True, main_task_id=main_task_id))))()


@app.task()
def download_file(*args, **kwargs):
    print args, kwargs
    context = kwargs["context"]
    folder_in = context["folder_in"]
    print("downloading %s", context["url"])
    context["original_file"] = os.path.join(folder_in, context["id"])
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

    context["target_width"] = math.trunc(
        float(context["target_height"]) / context["track_height"] * context["track_width"] / 2) * 2
    return context


@app.task
# def transcode(file_in, folder_out, dimensions, bitrate):
def transcode(*args, **kwargs):
    '''
    transcode the video to mp4 format
    '''
    context = args[0]
    context["bitrate"] = kwargs['bitrate']
    context["segtime"] = kwargs['segtime']
    context["name"] = kwargs['name']
    dimsp = str(context["target_width"]) + ":" + str(context["target_height"])
    if not os.path.exists(get_transcoded_folder(context)):
        try:
            os.makedirs(get_transcoded_folder(context))
        except OSError as e:
            pass

    command_line = "ffmpeg -i " + context[
        "original_file"] + " -c:v libx264 -profile:v main -level 3.1 -b:v " + str(context[
        "bitrate"]) + "k -vf scale=" + dimsp + " -c:a aac -strict -2 -force_key_frames expr:gte\(t,n_forced*" + str(
        context["segtime"]) + "\) " + get_transcoded_file(
        context)
    print("transcoding commandline %s" % command_line)
    subprocess.call(command_line,
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
    logger.info("chunking dash")
    logger.info(args)
    logger.info(kwargs)
    context = args[0]
    segtime = kwargs['segtime']
    if not os.path.exists(get_dash_folder(context)):
        os.makedirs(get_dash_folder(context))

    args = "MP4Box -dash " + str(segtime) + "000 -profile onDemand "
    files_in = [os.path.join(get_transcoded_folder(context), f) for f in os.listdir(get_transcoded_folder(context))]
    for i in range(0, len(files_in)):
        args += files_in[i] + "#video:id=v" + str(i) + " "

    args += files_in[0] + "#audio:id=a0 "
    args += " -out " + get_dash_mpd_file_path(context)
    print args
    subprocess.call(args, shell=True)
    return context


@app.task
def edit_dash_playlist(*args, **kwards):
    '''
    create dash chunks for every video in the transcoded folder
    '''
    # print args, kwargs
    context = args[0]

    tree = LXML.parse(get_dash_mpd_file_path(context))
    root = tree.getroot()
    # Namespace map
    nsmap = root.nsmap.get(None)

    # Function to find all the BaseURL
    find_baseurl = LXML.ETXPath("//{%s}BaseURL" % nsmap)
    results = find_baseurl(root)
    audio_file = results[-1].text
    results[-1].text = "audio/" + results[
        -1].text  # Warning : This is quite dirty ! We suppose the last element is the only audio element
    tree.write(get_dash_mpd_file_path(context))

    # Move audio files into audio directory
    os.makedirs(os.path.join(get_dash_folder(context), "audio"))
    shutil.move(os.path.join(get_dash_folder(context), audio_file),
                os.path.join(get_dash_folder(context), "audio", audio_file))

    # Create .htaccess for apache
    f = open(os.path.join(get_dash_folder(context), "audio", ".htaccess"), "w")
    f.write("AddType audio/mp4 .mp4 \n")
    f.close()
    return context


@app.task
# def add_playlist_info(main_playlist_folder, version_playlist_file, bitrate):
def add_playlist_info(*args, **kwargs):
    '''
    add this hls palylist info into the global hls playlist
    '''
    # print args, kwargs
    context = args[0]
    dimsp = str(context["target_width"]) + "x" + str(context["target_height"])
    with open(get_hls_global_playlist(context), "a") as f:
        f.write("#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=" + str(
            context["bitrate"] * 1000) + ",RESOLUTION=" + dimsp + "\n" + "/".join(
            get_hls_transcoded_playlist(context).split("/")[-2:]) + "\n")
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

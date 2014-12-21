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

# lxml import to edit dash playlist
from lxml import etree as LXML

# context helpers
from context import get_transcoded_folder, get_transcoded_file, get_hls_transcoded_playlist, get_hls_transcoded_folder, \
    get_dash_folder, get_hls_folder, get_hls_global_playlist, get_dash_mpd_file_path

# main app for celery, configuration is in separate settings.ini file
app = Celery('tasks')

# inject settings into celery
app.config_from_object('adaptation.settings')

def run_background(*args):
    try: 
        code = subprocess.check_call(*args, shell=True)
    except subprocess.CalledProcessError:
        print "Error"

        

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
def ddo(src, dest):
    try:
        encode_workflow(src, dest)
    except:
        print "Error while encoding_workflow"
        raise



@app.task(bind=True)
def encode_workflow(self, src, dest):
    main_task_id = self.request.id
    print "(------------"
    print main_task_id
    random_uuid = uuid.uuid4().hex
    context={"original_file": src, "folder_out": config["folder_out"] + dest, "id": random_uuid}
    context = get_video_size(context=context)
    context = add_playlist_header(context)
    for target_height, bitrate in config["bitrates_size_dict"].items():
        contextLoop = compute_target_size(context, target_height=target_height)
        contextLoop = transcode(contextLoop, bitrate=bitrate, segtime=4)
        contextLoop = chunk_hls(contextLoop)
        contextLoop = add_playlist_info(contextLoop)
        #notify.s(main_task_id=main_task_id))

    context = add_playlist_footer(context)
    context = chunk_dash(context, segtime=4) #Warning : segtime is already set in transcode.s(), but not in the same context
    context = edit_dash_playlist(context)
    #notify.s(complete=True, main_task_id=main_task_id))

@app.task
# def get_video_size(input_file):
def get_video_size(*args, **kwargs):
    '''
    use mediainfo to compute the video size
    '''
    print args, kwargs
    context = kwargs["context"]
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
    context["segtime"] = kwargs['segtime']
    dimsp = str(context["target_width"]) + ":" + str(context["target_height"])
    if not os.path.exists(get_transcoded_folder(context)):
        os.makedirs(get_transcoded_folder(context))
    run_background(
        "ffmpeg -i " + context[
            "original_file"] + " -c:v libx264 -profile:v main -level 3.1 -b:v " + str(context["bitrate"]) + "k -vf scale=" + dimsp + " -c:a aac -strict -2 -force_key_frames expr:gte\(t,n_forced*" + str(
        context["segtime"]) + "\) " + get_transcoded_file(
            context))
    return context


@app.task
# def chunk_hls(file_in, folder_out, dimensions, segtime=4):
def chunk_hls(*args, **kwargs):
    '''
    create hls chunks and the version specific playlist
    '''
    # print args, kwargs
    context = args[0]

    if not os.path.exists(get_hls_transcoded_folder(context)):
        os.makedirs(get_hls_transcoded_folder(context))

    ffargs = "ffmpeg -i " + get_transcoded_file(
        context) + " -map 0 -flags +global_header -vcodec copy -vbsf h264_mp4toannexb -acodec copy -f segment -segment_format mpegts -segment_time " + str(
        context["segtime"]) + " -segment_wrap 0 -segment_list " + get_hls_transcoded_playlist(
        context) + " " + get_hls_transcoded_folder(context) + "/chunks_name%03d.ts"
    print ffargs
    run_background(ffargs)
    return context


@app.task
# def chunk_dash(files_in, folder_out):
def chunk_dash(*args, **kwargs):
    '''
    create dash chunks for every video in the transcoded folder
    '''
    # print args, kwargs
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
    run_background(args)
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

    #Function to find all the BaseURL
    find_baseurl = LXML.ETXPath("//{%s}BaseURL" % nsmap)
    results = find_baseurl(root)
    audio_file = results[-1].text
    results[-1].text = "audio/" + results[-1].text # Warning : This is quite dirty ! We suppose the last element is the only audio element
    tree.write(get_dash_mpd_file_path(context))

    #Move audio files into audio directory
    os.makedirs(os.path.join(get_dash_folder(context), "audio"))
    shutil.move(os.path.join(get_dash_folder(context), audio_file), os.path.join(get_dash_folder(context), "audio", audio_file))

    #Create .htaccess for apache
    f = open(os.path.join(get_dash_folder(context), "audio", ".htaccess"),"w")
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
            context["bitrate"] * 1000) + ",RESOLUTION=" + dimsp + "\n" + "/".join(get_hls_transcoded_playlist(context).split("/")[-2:]) + "\n")
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
    context = args[0]  # take the first context["on"] the list, since we receive more than one
    with open(get_hls_global_playlist(context), "a") as f:
        f.write("##EXT-X-ENDLIST")
    return context

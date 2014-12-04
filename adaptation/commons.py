__author__ = 'nherbaut'
import subprocess
import math
import os
import tempfile
import urllib
import shutil

from celery import shared_task, Celery, chord, group

from context import Context


app = Celery('tasks', backend='amqp', broker='amqp://guest:guest@172.16.1.1')

from pymediainfo import MediaInfo


@app.task
@shared_task
def encoding_workflow(id, url, folder_out, bitrates_size_dict):
    

    (
        download_file.s(Context(url=url, id=id, folder_out=folder_out)) |
        get_video_size.s() |
        add_playlist_header.s(folder_out=folder_out) |
        chord(
            [(compute_target_size.s(target_height=target_height) |
              transcode.s(bitrate=bitrate) |
              chunk_hls.s(segtime=4) |
              add_playlist_info.s())

             for target_height, bitrate in bitrates_size_dict.items()],

            group(add_playlist_footer.s() |
                  chunk_dash.s())
        )
    ).apply_async()


@app.task
@shared_task
# def download_file(url, id):
def download_file(*args, **kwargs):
	'''
	download a file to a temporary folder
	'''
    #print args, kwargs
    context = args[0]

    print("downloading %s", context.url)
    context.original_file = os.path.join(tempfile.mkdtemp(), context.id)
    print("downloading in %s", context.original_file )
    opener = urllib.URLopener()
    opener.retrieve(context.url, context.original_file)
    print("downloaded in %s", context.original_file )
    return context


@app.task
@shared_task
# def get_video_size(input_file):
def get_video_size(*args, **kwargs):
    '''
    use mediainfo to compute the video size
    '''
    #print args, kwargs
    original_height = 0
    original_width = 0
    context = args[0]
    media_info = MediaInfo.parse(context.original_file)
    for track in media_info.tracks:
        if track.track_type == 'Video':
            print "video is %d, %d" % (track.height, track.width)
            context.track_width = track.width
            context.track_height = track.height
            return context
    raise AssertionError("failed to read video info from " + context.original_file)


@app.task
@shared_task
# def compute_target_size(original_height, original_width, target_height):
def compute_target_size(*args, **kwargs):
    '''
    compute the new size for the video
    '''
    context = args[0]
    context.target_height = kwargs['target_height']

    #print args, kwargs
    context.target_width = math.trunc(
        float(context.target_height) / context.track_height * context.track_width / 2) * 2
    return context


@app.task
@shared_task
# def transcode(file_in, folder_out, dimensions, bitrate):
def transcode(*args, **kwargs):
    '''
    transcode the video to mp4 format
    '''
    #print args, kwargs
    context = args[0]
    context.bitrate = kwargs['bitrate']
    dimsp = str(context.target_width) + ":" + str(context.target_height)
    if not os.path.exists(context.get_transcoded_folder()):
        os.makedirs(context.get_transcoded_folder())
    subprocess.call(
        "ffmpeg -i " + context.original_file + " -c:v libx264 -profile:v main -level 3.1 -b:v 100k -vf scale=" + dimsp + " -c:a aac -strict -2 -force_key_frames expr:gte\(t,n_forced*4\) " + context.get_transcoded_file(),
        shell=True)
    return context


@app.task
@shared_task
# def chunk_hls(file_in, folder_out, dimensions, segtime=4):
def chunk_hls(*args, **kwargs):
    '''
    create hls chunks and the version specific playlist
    '''
    #print args, kwargs
    context = args[0]
	context.segtime = kwargs['segtime']

    if not os.path.exists(context.get_hls_transcoded_folder()):
        os.makedirs(context.get_hls_transcoded_folder())

    ffargs = "ffmpeg -i " + context.get_transcoded_file() + " -map 0 -flags +global_header -vcodec copy -vbsf h264_mp4toannexb -acodec copy -f segment -segment_format mpegts -segment_time " + str(
        context.segtime) + " -segment_wrap 0 -segment_list " + context.get_hls_transcoded_playlist() + " " + context.get_hls_transcoded_folder() + "/chunks_name%03d.ts"
    print ffargs
    subprocess.call(ffargs, shell=True)
    return context


@app.task
@shared_task
# def chunk_dash(files_in, folder_out):
def chunk_dash(*args, **kwargs):
	'''
	create dash chunks for every video in the transcoded folder
	'''
    #print args, kwargs
    context = args[0]
    if not os.path.exists(context.get_dash_folder()):
        os.makedirs(context.get_dash_folder())

    args = "MP4Box -dash 4000 -profile onDemand "
    files_in = [os.path.join(context.get_transcoded_folder(), f) for f in os.listdir(context.get_transcoded_folder())]
    for i in range(0, len(files_in)):
        args += files_in[i] + "#video:id=v" + str(i) + " "

    args += " -out " + context.get_dash_mpd_file_path()
    print args
    subprocess.call(args, shell=True)


@app.task
@shared_task
# def add_playlist_info(main_playlist_folder, version_playlist_file, bitrate):
def add_playlist_info(*args, **kwargs):
	'''
	add this hls palylist info into the global hls playlist
	'''
    #print args, kwargs
    context = args[0]
    with open(context.get_hls_global_playlist(), "a") as f:
        f.write("#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=" + str(
            context.bitrate * 1000) + ",RESOLUTION=" + context.get_hls_transcoded_playlist() + "\n")
    return context


@app.task
@shared_task
# def add_playlist_header(playlist_folder):
def add_playlist_header(*args, **kwargs):
	'''
	add the header to the global playlist, possibly remove existing hls folder and recreate it
	'''
    #print args, kwargs
    context = args[0]
    context.folder_out = kwargs["folder_out"]
    if os.path.exists(context.get_hls_folder()):
        shutil.rmtree(context.get_hls_folder())
    os.makedirs(context.get_hls_folder())

    with open(context.get_hls_global_playlist(), "a") as f:
        f.write("#EXTM3U\n")
    return context


@app.task
@shared_task
# def add_playlist_footer(playlist_folder):
def add_playlist_footer(*args, **kwargs):
	'''
	add global hls playlist folder
	'''
    #print args, kwargs
    context = args[0][0]  # take the first context on the list, since we receive more than one
    with open(context.get_hls_global_playlist(), "a") as f:
        f.write("##EXT-X-ENDLIST")
    return context

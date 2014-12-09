__author__ = 'nherbaut'
import os



def get_transcoded_file(context):
    return os.path.join(get_transcoded_folder(context), context["name"] + ".mp4")


def get_transcoded_folder(context):
    return os.path.join(context["folder_out"], "encoding")


def get_hls_folder(context):
    return os.path.join(context["folder_out"], "hls")


def get_dash_folder(context):
    return os.path.join(context["folder_out"], "dash")


def get_dash_mpd_file_path(context):
    return os.path.join(get_dash_folder(context), "playlist.mpd")


def get_hls_global_playlist(context):
    return os.path.join(get_hls_folder(context), "playlist.m3u8")


def get_hls_transcoded_playlist(context):
    return os.path.join(get_hls_transcoded_folder(context), "playlist.m3u8")


def get_hls_transcoded_folder(context):
    return os.path.join(get_hls_folder(context), get_dim_as_str(context))


def get_dim_as_str(context):
    return str(context["target_width"]) + "x" + str(context["target_height"])


pass

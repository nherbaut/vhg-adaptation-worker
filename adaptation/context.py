__author__ = 'nherbaut'
import os


class Context:
    url = None
    id = None
    original_file = None
    track_width = None
    track_height = None
    target_width = None
    target_height = None
    folder_out = None
    transcoded_file = None
    segtime = None
    bitrate=None

    def __init__(self,url,id,folder_out):
        self.url=url
        self.id=id
        self.folder_out=folder_out


    def get_transcoded_file(self):
        return os.path.join(self.get_transcoded_folder(), self.get_dim_as_str() + ".mp4")

    def get_transcoded_folder(self):
        return os.path.join(self.folder_out, "encoding")

    def get_hls_folder(self):
        return os.path.join(self.folder_out, "hls")

    def get_dash_folder(self):
        return os.path.join(self.folder_out, "dash")

    def get_dash_mpd_file_path(self):
        return os.path.join(self.get_dash_folder(),"playlist.mpd")

    def get_hls_global_playlist(self):
        return os.path.join(self.get_hls_folder(), "playlist.m3u8")

    def get_hls_transcoded_playlist(self):
        return os.path.join(self.get_hls_transcoded_folder(),"playlist.m3u8")

    def get_hls_transcoded_folder(self):
        return os.path.join(self.get_hls_folder(), self.get_dim_as_str())

    def get_dim_as_str(self):
        return str(self.target_width) + "x" + str(self.target_height)


pass

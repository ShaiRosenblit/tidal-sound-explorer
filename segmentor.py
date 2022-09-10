import youtube_dl
import argparse
from path import Path
from pydub import AudioSegment

import os
import sys

from find_beats import find_beats_and_bpm, segment_and_analyze_sample


def download_youtube_audio(youtube_id: str, sample_name: str, target_folder: Path) -> Path:
    # TODO: lower download quality to accelerate stuff
    url = "https://www.youtube.com/watch?v=" + youtube_id
    file = target_folder.joinpath(f"{sample_name}/{youtube_id}.wav")

    ydl_opts = {
        'format': 'worstaudio/worst',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
            'preferredquality': '192',
        }],
        'outtmpl': str(file),
        # 'cachedir': str(target_folder)
    }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    track = AudioSegment.from_file(file)
    track.export(file, format='wav')
    print(f"File path: {file}\ntrack duration: {track.duration_seconds}")
    return file


if __name__ == '__main__':
    samples_path = Path('/Users/shai/Documents/tidal/sounds/samples-yt/')

    # track = AudioSegment.from_file('~/Documents/tidal/sounds/samples-extra/yt/sophie1.wav')
    # track = AudioSegment.from_file("/Users/shai/Documents/tidal/sounds/samples-extra/yt/sophie1.wav")
    my_parser = argparse.ArgumentParser(description="Dowload file from youtube and analyze it's audio")

    my_parser.add_argument('youtube_id',
                           type=str,
                           help='The youtube id')
    my_parser.add_argument('sample_name',
                           type=str,
                           help='Sample name')

    # Execute the parse_args() method
    args = my_parser.parse_args()
    yt_id = args.youtube_id
    samp_name = args.sample_name
    audio_file_path = download_youtube_audio(yt_id, samp_name, samples_path)
    beats_df, bpm, beats = find_beats_and_bpm(audio_file_path)
    # segments_df = find_onsets(audio_file_path)
    print(f"bpm: {bpm}")

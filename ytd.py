import glob
import os
import shutil
import sys

try:
    import yt_dlp
except ImportError:
    print("yt-dlp is not installed. Run:  python -m pip install -U yt-dlp")
    sys.exit(1)


# Files are saved to Downloads\YT Downloads by default
DOWNLOAD_FOLDER = os.path.join(os.path.expanduser("~"), "Downloads", "YT Downloads")


def find_ffmpeg():
    """Return the full path to ffmpeg, or None if it can't be found.

    Checks PATH first, then the folders winget, Chocolatey and Scoop
    usually install to (in case PATH hasn't refreshed yet).
    """
    on_path = shutil.which("ffmpeg")
    if on_path is not None:
        return on_path

    local_app_data = os.environ.get("LOCALAPPDATA", "")
    user_home = os.path.expanduser("~")
    places_to_check = [
        os.path.join(local_app_data, "Microsoft", "WinGet", "Links", "ffmpeg.exe"),
        os.path.join(local_app_data, "Microsoft", "WinGet", "Packages", "Gyan.FFmpeg*", "*", "bin", "ffmpeg.exe"),
        os.path.join("C:\\", "ProgramData", "chocolatey", "bin", "ffmpeg.exe"),
        os.path.join(user_home, "scoop", "shims", "ffmpeg.exe"),
        os.path.join("C:\\", "ffmpeg", "bin", "ffmpeg.exe"),
    ]
    for pattern in places_to_check:
        matches = glob.glob(pattern)
        if len(matches) > 0:
            return matches[0]
    return None


FFMPEG_PATH = find_ffmpeg()


def ffmpeg_available():
    return FFMPEG_PATH is not None


def show_progress(status):
    """Called by yt-dlp repeatedly while downloading."""
    if status["status"] == "downloading":
        percent = status.get("_percent_str", "").strip()
        speed = status.get("_speed_str", "").strip()
        eta = status.get("_eta_str", "").strip()
        print(f"\r  Downloading: {percent}  at {speed}  ETA {eta}     ", end="", flush=True)
    elif status["status"] == "finished":
        print("\n  Download done, processing file...")


def build_options(choice):
    """Return yt-dlp settings for the chosen format."""
    options = {
        "outtmpl": os.path.join(DOWNLOAD_FOLDER, "%(title)s.%(ext)s"),
        "progress_hooks": [show_progress],
        "noplaylist": True,          # only grab the single video, not a whole playlist
        "quiet": True,
        "no_warnings": True,
        "windowsfilenames": True,    # strip characters Windows doesn't allow in names
    }

    if FFMPEG_PATH is not None:
        options["ffmpeg_location"] = FFMPEG_PATH

    if choice == "mp3":
        options["format"] = "bestaudio/best"
        options["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]
    else:  # mp4
        if ffmpeg_available():
            # best video + best audio, merged into one mp4
            options["format"] = "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b"
            options["merge_output_format"] = "mp4"
        else:
            # without ffmpeg, only pre-merged files work (usually max 720p)
            options["format"] = "b[ext=mp4]/b"

    return options


def download(url, choice):
    if choice == "mp3" and not ffmpeg_available():
        print("  MP3 needs ffmpeg. Install it with:  winget install Gyan.FFmpeg")
        print("  Then close and reopen cmd.")
        return

    if FFMPEG_PATH is not None:
        print(f"  Using ffmpeg: {FFMPEG_PATH}")
    else:
        print("  ffmpeg not found -- MP4 will try a single-file format (may fail on many videos).")

    os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

    try:
        with yt_dlp.YoutubeDL(build_options(choice)) as ydl:
            info = ydl.extract_info(url, download=True)
            print(f"  Saved: {info.get('title', 'video')} ({choice.upper()})")
            print(f"  Folder: {DOWNLOAD_FOLDER}")
    except yt_dlp.utils.DownloadError as error:
        print(f"\n  Download failed: {error}")
        print("  Tip: run  python -m pip install -U yt-dlp  -- YouTube changes often and updates usually fix it.")


def ask_format():
    while True:
        print("\n  1) MP3 (audio only)")
        print("  2) MP4 (video)")
        pick = input("  Choose 1 or 2: ").strip()
        if pick == "1":
            return "mp3"
        if pick == "2":
            return "mp4"
        print("  Please type 1 or 2.")


def interactive_menu():
    print("=" * 40)
    print("        YouTube Downloader")
    print("=" * 40)
    if not ffmpeg_available():
        print("  Note: ffmpeg not found. MP3 won't work and MP4 is limited to ~720p.")

    while True:
        url = input("\nPaste a YouTube link (or press Enter to quit): ").strip()
        if url == "":
            print("Bye!")
            break
        choice = ask_format()
        download(url, choice)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[2].lower() in ("mp3", "mp4"):
        download(sys.argv[1], sys.argv[2].lower())
    else:
        interactive_menu()
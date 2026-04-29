import webbrowser
from urllib.parse import quote_plus
from urllib.request import Request, urlopen
import re


YOUTUBE_SEARCH_URL = "https://www.youtube.com/results?search_query={query}"
YOUTUBE_WATCH_URL = "https://www.youtube.com/watch?v={video_id}"


def search_google(query: str):
    webbrowser.open(f"https://www.google.com/search?q={quote_plus(query)}")


def open_youtube():
    webbrowser.open("https://youtube.com")


def search_youtube(query: str):
    webbrowser.open(YOUTUBE_SEARCH_URL.format(query=quote_plus(query)))


def play_youtube_first_result(query: str) -> bool:
    video_url = get_first_youtube_video_url(query)
    if not video_url:
        return False

    webbrowser.open(video_url)
    return True


def get_first_youtube_video_url(query: str) -> str | None:
    if not query:
        return None

    search_url = YOUTUBE_SEARCH_URL.format(query=quote_plus(query))
    request = Request(
        search_url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        },
    )

    try:
        with urlopen(request, timeout=8) as response:
            html = response.read().decode("utf-8", errors="ignore")
    except Exception as error:
        print("YouTube search extraction failed:", error)
        return None

    video_id = _extract_first_video_id(html)
    if not video_id:
        return None

    return YOUTUBE_WATCH_URL.format(video_id=video_id)


def _extract_first_video_id(html: str) -> str | None:
    seen = set()
    for video_id in re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', html):
        if video_id not in seen:
            return video_id
        seen.add(video_id)

    for video_id in re.findall(r"/watch\?v=([a-zA-Z0-9_-]{11})", html):
        if video_id not in seen:
            return video_id
        seen.add(video_id)

    return None


def open_github():
    webbrowser.open("https://github.com")


def open_stackoverflow():
    webbrowser.open("https://stackoverflow.com")

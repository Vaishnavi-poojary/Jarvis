import webbrowser
from urllib.parse import quote_plus


def search_google(query: str):
    webbrowser.open(f"https://www.google.com/search?q={quote_plus(query)}")


def open_youtube():
    webbrowser.open("https://youtube.com")


def search_youtube(query: str):
    webbrowser.open(f"https://www.youtube.com/results?search_query={quote_plus(query)}")


def open_github():
    webbrowser.open("https://github.com")


def open_stackoverflow():
    webbrowser.open("https://stackoverflow.com")

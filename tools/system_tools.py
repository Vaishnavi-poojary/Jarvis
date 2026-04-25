import os

def open_notepad():
    os.system("notepad")

def close_notepad():
    os.system("taskkill /f /im notepad.exe")

def open_calculator():
    os.system("calc")

def close_calculator():
    os.system("taskkill /f /im CalculatorApp.exe")

def open_chrome():
    os.system("start chrome")

def close_chrome():
    result = os.system("taskkill /f /im chrome.exe /t")
    if result != 0:
        os.system("taskkill /f /im msedge.exe /t")
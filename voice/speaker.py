import pyttsx3

def speak(text):
    print("Jarvis speaking:", text)

    engine = pyttsx3.init()   # 👈 reinitialize every time
    engine.setProperty('rate', 170)
    engine.setProperty('volume', 1.0)

    engine.say(text)
    engine.runAndWait()
    engine.stop()  # 👈 important
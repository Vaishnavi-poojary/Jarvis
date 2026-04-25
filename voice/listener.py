import speech_recognition as sr

def listen():
    recognizer = sr.Recognizer()
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = 0.8

    try:
        with sr.Microphone() as source:
            print("Listening...")
            recognizer.adjust_for_ambient_noise(source, duration=0.5)

            for attempt in range(2):
                try:
                    audio = recognizer.listen(source, timeout=5, phrase_time_limit=8)
                    command = recognizer.recognize_google(audio, language="en-IN")
                    return command.lower()
                except sr.UnknownValueError:
                    if attempt == 0:
                        print("Didn't catch that. Please repeat.")
                    else:
                        print("Didn't catch that")
                except sr.WaitTimeoutError:
                    print("No speech detected")
                    return ""
                except sr.RequestError as error:
                    print(f"Speech recognition service error: {error}")
                    return ""
    except OSError as error:
        print(f"Microphone error: {error}")
        return ""

    return ""

def choose_model(prompt: str):
    text = prompt.lower()

    if any(word in text for word in [
        "code", "program", "algorithm", "debug",
        "error", "traceback", "function", "class",
        "explain code", "write code",
    ]):
        return "llama3"

    if len(text) > 180:
        return "llama3"

    return "phi3"

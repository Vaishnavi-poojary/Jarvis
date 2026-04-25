from ai.router import choose_model


def test_casual_prompts_use_fast_model():
    assert choose_model("i feel bored") == "phi3"
    assert choose_model("suggest an idea for tonight") == "phi3"


def test_code_prompts_use_stronger_model():
    assert choose_model("debug this traceback") == "llama3"
    assert choose_model("write code for a calculator") == "llama3"


def test_long_prompts_use_stronger_model():
    prompt = "please think carefully about this " * 8

    assert choose_model(prompt) == "llama3"

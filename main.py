import time

from voice.listener import listen
from voice.speaker import speak

from ai.ai_engine import get_ai_response
from brain.planner import plan
from executor.executor import execute_plan
from memory.store import get_context_summary, remember_event


def run_jarvis():
    speak("Jarvis is online")

    while True:
        command = listen()

        if command:
            print("You said:", command)

            decision = plan(command)
            print("Decision:", decision)

            if decision.route in {"action", "ask", "multi"}:
                response = execute_plan(decision)
            elif decision.response:
                response = decision.response
            else:
                response = get_ai_response(command, context=get_context_summary())

            remember_event(command, decision, response)

            print("Jarvis:", response)
            if decision.should_speak:
                speak(response)

            time.sleep(0.5)


if __name__ == "__main__":
    run_jarvis()

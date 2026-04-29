import time
import argparse

from voice.listener import listen
from voice.speaker import speak

from ai.ai_engine import get_ai_response
from ai.quick_responses import get_quick_response, make_quick_decision
from brain.planner import plan
from executor.executor import execute_plan
from memory.store import get_context_summary, remember_event


def run_jarvis():
    speak("Jarvis is online")

    while True:
        command = listen()

        if command:
            print("You said:", command)

            quick_response = get_quick_response(command)
            if quick_response:
                decision = make_quick_decision(quick_response, command)
                response = quick_response
            else:
                decision = plan(command)
                if decision.route in {"action", "ask", "multi"}:
                    response = execute_plan(decision)
                elif decision.response:
                    response = decision.response
                else:
                    response = get_ai_response(command, context=get_context_summary())

            print("Decision:", decision)

            remember_event(command, decision, response)

            print("Jarvis:", response)
            if decision.should_speak:
                speak(response)

            time.sleep(0.5)


def run_ui():
    from gui.ui import launch_ui

    return launch_ui()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="JARVIS local assistant")
    parser.add_argument(
        "--cli",
        action="store_true",
        help="run the original voice loop instead of the PyQt UI skeleton",
    )
    args = parser.parse_args()

    if args.cli:
        run_jarvis()
    else:
        raise SystemExit(run_ui())

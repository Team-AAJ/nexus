from voice.wake_word import WakeWordDetector
from voice.speech_to_text import SpeechToText
from voice.text_to_speech import TextToSpeech
from controller import NexusController


class VoiceController:

    def __init__(self):

        self.wake = WakeWordDetector()

        self.stt = SpeechToText()

        self.tts = TextToSpeech()

        self.nexus = NexusController(
            confirm_callback=self._confirm
        )

    def _confirm(self, prompt: str) -> bool:

        self.tts.speak(
            prompt + " Haan ya nahi boliye."
        )

        print("CONFIRMATION: listening for haan/yes...")

        answer = self.stt.listen()

        print(
            "CONFIRMATION HEARD:",
            repr(answer)
        )

        if not answer:
            return False

        answer = answer.lower().strip()

        return (
            answer == "haan"
            or answer == "han"
            or answer == "yes"
            or answer == "yeah"
            or "haan" in answer
            or "yes" in answer
        )

    def _is_stop_listening(self, command: str) -> bool:

        command = command.lower().strip()

        stop_words = (

            "stop listening",
            "sleep nexus",
            "go to sleep",
            "sleep",
            "stop listening nexus"

        )

        return command in stop_words

    def _is_exit(self, command: str) -> bool:

        command = command.lower().strip()

        return command in (

            "exit",
            "quit",
            "shutdown nexus"

        )

    def run(self):

        print("Nexus Voice Started...")

        while True:

            # --------------------------------
            # WAIT FOR WAKE WORD
            # --------------------------------

            print("Waiting for wake word...")

            try:

                if not self.wake.wait():
                    continue

            except KeyboardInterrupt:

                break

            # --------------------------------
            # ACTIVE VOICE MODE
            # --------------------------------

            self.tts.speak("Yes?")

            print("Nexus is listening...")

            while True:

                try:

                    command = self.stt.listen()

                except KeyboardInterrupt:

                    return

                if not command:

                    self.tts.speak(
                        "Sorry, I didn't catch that."
                    )

                    continue

                print(
                    "USER :",
                    command
                )

                # --------------------------------
                # COMPLETE PROGRAM EXIT
                # --------------------------------

                if self._is_exit(command):

                    self.tts.speak(
                        "Goodbye."
                    )

                    return

                # --------------------------------
                # STOP ACTIVE LISTENING
                # --------------------------------

                if self._is_stop_listening(command):

                    self.tts.speak(
                        "Okay. Main sleep mode mein ja rahi hoon."
                    )

                    break

                # --------------------------------
                # NORMAL COMMAND
                # --------------------------------

                try:

                    response = self.nexus.handle(
                        command
                    )

                except Exception as error:

                    print(
                        "NEXUS ERROR:",
                        error
                    )

                    response = (
                        "Sorry, kuch gadbad ho gayi, "
                        "dobara try karo."
                    )

                print(
                    "NEXUS:",
                    response
                )

                self.tts.speak(
                    response
                )
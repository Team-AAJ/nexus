from dataclasses import dataclass


@dataclass
class Intent:

    category: str

    confidence: float

    payload: str


class IntentRouter:

    def __init__(self):

        self.browser_keywords = {

            "open",
            "search",
            "click",
            "login",
            "logout",
            "download",
            "upload",
            "book",
            "buy",
            "fill",
            "website",
            "browser",
            "github",
            "google",
            "amazon",
            "youtube",
            "gmail",
            "linkedin"
        }

        self.desktop_keywords = {

            "folder",
            "file",
            "desktop",
            "windows",
            "application",
            "notepad",
            "calculator"
        }

        self.chat_keywords = {

            "who",

            "what",

            "why",

            "how",

            "explain",

            "tell",

            "hello",

            "hi"

        }

    def route(

        self,

        text: str

    ) -> Intent:

        command = text.lower()

        for word in self.browser_keywords:

            if word in command:

                return Intent(

                    category="browser",

                    confidence=0.95,

                    payload=text

                )

        for word in self.desktop_keywords:

            if word in command:

                return Intent(

                    category="desktop",

                    confidence=0.90,

                    payload=text

                )

        for word in self.chat_keywords:

            if word in command:

                return Intent(

                    category="chat",

                    confidence=0.90,

                    payload=text

                )

        return Intent(

            category="chat",

            confidence=0.60,

            payload=text

        )
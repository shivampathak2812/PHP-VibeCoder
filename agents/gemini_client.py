import os

from dotenv import load_dotenv
from google import genai


load_dotenv()


class GeminiClient:

    def __init__(self, model="gemini-3.6-flash"):

        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY not found in .env"
            )

        self.client = genai.Client(api_key=api_key)
        self.model = model

    def generate(self, prompt):

        interaction = self.client.interactions.create(
            model=self.model,
            input=prompt,
        )

        return interaction.output_text


if __name__ == "__main__":

    print("=" * 60)
    print("PHP VibeCoder - Gemini Test")
    print("=" * 60)

    gemini = GeminiClient()

    response = gemini.generate(
        "Explain what an interface is in PHP in simple terms."
    )

    print("\nGemini Response:\n")
    print(response)
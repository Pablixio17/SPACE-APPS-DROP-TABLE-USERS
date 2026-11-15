from openai import OpenAI
from response import Response


class AIGen:
    def __init__(self, init_instructions: str | None = None) -> None:
        self.client = OpenAI()  # TODO: api_key=<CLAVE_API_CHATGPT>
        self.init_instructions = init_instructions

    def generate(self, prompt: str) -> Response:
        response = self.client.beta.chat.completions.parse(
            model="gpt-4o-mini",  # TODO: CAMBIAR A MODELO
            messages=[
                {"role": "system", "content": self.init_instructions},
                {"role": "user", "content": prompt},
            ],
            response_format=Response,
            temperature=1.2,
        )
        return response

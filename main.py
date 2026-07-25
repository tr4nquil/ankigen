import os
import json
from google import genai
from google.genai import types
from google.genai import errors
from dotenv import load_dotenv


load_dotenv()
with open("SYSTEM_PROMPT.md", "r") as f:
    system_prompt = (f.read())

json_schema = {
  "type": "array",
  "items": {
    "type": "object",
    "properties": {
      "Front": {
        "type": "string",
        "examples": [
          "Question related to the context"
        ]
      },
      "Back": {
        "type": "string",
        "examples": [
          "Answer directly related to the question"
        ]
      }
    },
    "required": [
      "Front",
      "Back"
    ]
  }
}

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

try:
    response = client.models.generate_content(
        model='gemini-3.5-flash',
        contents=types.Part.from_text(text='Big O notation'),
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0,
            top_p=0.95,
            top_k=20,
            response_mime_type='application/json',
            response_json_schema=json_schema
        ),
    )

    cards = json.loads(response.text)

    for card in cards:
        print(f"Q: {card['Front']}")
        print(f"A: {card['Back']}\n")

except errors.APIError as e:
    print(e.code)
    print(e.message)

except json.JSONDecodeError as e:
    print("Invalid JSON syntax:", e)


client.close()
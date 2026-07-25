import os
import json
import re
import genanki
import random
from google import genai
from google.genai import types
from google.genai import errors
from dotenv import load_dotenv

# src: https://www.bomberbot.com/python/mastering-file-saving-in-python-a-comprehensive-guide-to-user-defined-filenames/
def sanitize_filename(filename):
    # Remove any non-word characters (everything except numbers and letters)
    filename = re.sub(r'[^\w\-_\. ]', '_', filename)
    # Remove any runs of periods (since we don't want '../' to be in the filename)
    filename = re.sub(r'\.+', '.', filename)
    return filename

def main():
  load_dotenv()
  with open("SYSTEM_PROMPT.md", "r") as f:
      system_prompt = (f.read())

  MODEL_ID = 1607392319 # keep template shape identical for every card/deck

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


  print("Enter a topic to generate Anki cards about:")
  topic = input()

  client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

  try:
      print(f"Generating Anki cards about {topic}...")
      response = client.models.generate_content(
          model='gemini-3.5-flash',
          contents=types.Part.from_text(text=topic),
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


      # Genanki create model (note type): defines the structure of notes and how cards are generated

      my_model = genanki.Model(
          MODEL_ID,
          'Simple Model',
          fields=[
              {'name': 'Front'},
              {'name': 'Back'},
          ],
          templates=[
              {
              'name': 'Card 1',
              'qfmt': '{{Front}}',  # Question format
              'afmt': '{{Front}}<hr id="answer">{{Back}}',  # Answer format
              },
          ]
      )

      # Genanki create a deck
      deck_id = random.randrange(1 << 30, 1 << 31)

      my_deck = genanki.Deck(
          deck_id,
          topic # Deck name
      )

      # Genanki create note: contains actual content of flashcards
      # Genanki add to deck: created notes get added to a deck

      for card in cards:
          note = genanki.Note(
              model=my_model,
              fields=[card['Front'], card['Back']]
          )
          my_deck.add_note(note)

      # Genanki generate anki package:
      package = genanki.Package(my_deck)

      filename = sanitize_filename(topic)
      package.write_to_file(f"{filename}.apkg")
      print("Success: Deck created!")

  except errors.APIError as e:
      print(e.code)
      print(e.message)

  except json.JSONDecodeError as e:
      print("Invalid JSON syntax:", e)


  client.close()


if __name__ == "__main__":
    main()
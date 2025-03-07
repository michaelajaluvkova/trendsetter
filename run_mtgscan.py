import os
from dotenv import load_dotenv

load_dotenv()

print(os.getenv("AZURE_VISION_KEY"))

from mtgscan.text import MagicRecognition
from mtgscan.ocr.azure import Azure

azure = Azure()
rec = MagicRecognition(file_all_cards="all_cards.txt", file_keywords="Keywords.json")
box_texts = azure.image_to_box_texts("fire_ice.jpg")
deck = rec.box_texts_to_deck(box_texts)
print(deck)
for c, k in deck:
    print(c, k)


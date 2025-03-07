import os
from dotenv import load_dotenv
load_dotenv()

from mtgscan.text import MagicRecognition
from mtgscan.ocr.azure import Azure
import requests
import json
import logging
import pandas as pd

class CardFinder:
    def __init__(self):
        pass

    def recognize_card(self, file_path=None):
        azure = Azure()
        rec = MagicRecognition(file_all_cards="all_cards.txt", file_keywords="Keywords.json")
        box_texts = azure.image_to_box_texts(file_path)
        deck = rec.box_texts_to_deck(box_texts)
        for c, k in deck: #c is card, k is amount
            print(c, k)
        return deck

    def download_daily_price_per_card(self, cardname=None):
        url = "https://api.scryfall.com/cards/named"
        params = {"exact": cardname}

        try:
            response = requests.get(url, params=params)
            logging.info(f"Response Status Code: {response.status_code}")
            response.raise_for_status()
            #print(json.dumps(response.json(), indent=2))
            card_data = response.json()
            prices = card_data.get("prices", {})
            usd_price = prices.get("usd")
            usd_foil_price = prices.get("usd_foil")
            eur_price = prices.get("eur")
            eur_price_foil = prices.get("eur_foil")
            tix = prices.get("tix")

            df = pd.DataFrame([{
                    "card_name": cardname,
                    "price_usd": usd_price,
                    "price_usd_foil": usd_foil_price,
                    "price_eur": eur_price,
                    "price_eur_foil": eur_price_foil,
                    "tix": tix}])
            #print(df.head())

        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching data: {e}")

        return df

if __name__ == "__main__":
    card = CardFinder()
    deck = card.recognize_card(file_path="photos/fire_ice.jpg")
    all_dataframes = []
    for c, k in deck:
        single_df = card.download_daily_price_per_card(cardname=c)
        all_dataframes.append(single_df)
    dataframe = pd.concat(all_dataframes, ignore_index=True)
    dataframe = dataframe.sort_values(by="price_eur", ascending=True)
    dataframe.to_csv('full_data.csv')
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

    def get_eur_to_czk_rate(self):
        """Fetches the latest EUR to CZK exchange rate from the Czech National Bank."""
        url = "https://www.cnb.cz/en/financial_markets/foreign_exchange_market/exchange_rate_fixing/daily.txt"

        try:
            response = requests.get(url)
            response.raise_for_status()
            print("Response Text:\n", response.text)

            for line in response.text.split("\n"):
                if "|EUR|" in line:  # More robust check
                    parts = line.split("|")
                    rate = float(parts[-1])
                    return rate

        except Exception as e:
            print(f"Error: {e}")
            return None

    def download_daily_price_per_card(self, cardname=None):
        url = "https://api.scryfall.com/cards/named"
        params = {"exact": cardname}
        czk_eur_rate = self.get_eur_to_czk_rate()

        try:
            response = requests.get(url, params=params)
            logging.info(f"Response Status Code: {response.status_code}")
            response.raise_for_status()
            #print(json.dumps(response.json(), indent=2))
            card_data = response.json()
            prices = card_data.get("prices", {})
            usd_price = prices.get("usd")
            usd_foil_price = prices.get("usd_foil")
            eur_price = float(prices.get("eur")) if prices.get("eur") is not None else 0.0
            eur_price_foil = float(prices.get("eur_foil")) if prices.get("eur_foil") is not None else 0.0
            tix = prices.get("tix")
            czk_price = eur_price * czk_eur_rate
            czk_price_foil = eur_price_foil * czk_eur_rate

            df = pd.DataFrame([{
                    "card_name": cardname,
                    "price_usd": usd_price,
                    "price_usd_foil": usd_foil_price,
                    "price_eur": eur_price,
                    "price_eur_foil": eur_price_foil,
                    "price_czk": czk_price,
                    "price_czk_foil": czk_price_foil,
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
import os
from dotenv import load_dotenv
load_dotenv()
from mtgscan.text import MagicRecognition
from mtgscan.ocr.azure import Azure
import requests
import json
import logging
import pandas as pd
import cv2
from PIL import Image
import numpy as np

class CardFinder:
    def __init__(self):
        pass

    def preprocess_image(self, file_path, output_path="processed_image.jpg"):
        """ OCR fails when image is too huge. This is automated function which would improve
        the image for OCR without destroying the details.
        """
        try:
            image = cv2.imread(file_path)
            if image is None:
                raise ValueError("Error: Could not read image file.")

            # resizing
            max_width, max_height = 2000, 1500
            height, width = image.shape[:2]
            scaling_factor = min(max_width / width, max_height / height)
            new_width = int(width * scaling_factor)
            new_height = int(height * scaling_factor)
            image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)

            # improving contrast
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            l = clahe.apply(l)
            enhanced_image = cv2.merge((l, a, b))
            enhanced_image = cv2.cvtColor(enhanced_image, cv2.COLOR_LAB2BGR)

            # Apply sharpening filter
            sharpening_kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
            sharp_image = cv2.filter2D(enhanced_image, -1, sharpening_kernel)

            cv2.imwrite(output_path, sharp_image)  # save processed image
            img = Image.open(output_path) # compress image while size remains manageable
            img.save(output_path, quality=90, optimize=True)

            return output_path

        except Exception as e:
            print(f"Error in image preprocessing: {e}")
            return file_path


    def recognize_card(self, file_path=None):
        """
        The OCR function itself.
        :param file_path:
        :return: list containing card name and count of cards
        """
        azure = Azure()
        rec = MagicRecognition(file_all_cards="all_cards.txt", file_keywords="Keywords.json")
        try:
            box_texts = azure.image_to_box_texts(file_path)
            print("OCR successful on original image.")
        except Exception as e:
            print(f"Initial OCR failed: {e}. Retrying with preprocessed image...")
            processed_path = self.preprocess_image(file_path)

            try:
                box_texts = azure.image_to_box_texts(processed_path)
                print("OCR successful on preprocessed image.")

            except Exception as e:
                print(f"OCR failed even after preprocessing: {e}.")
                return []

        deck = rec.box_texts_to_deck(box_texts)
        for c, k in deck:  # c is card, k is amount
            print(c, k)

        return deck

    def get_eur_to_czk_rate(self):
        """Fetches the latest EUR to CZK exchange rate from the Czech National Bank."""
        url = "https://www.cnb.cz/en/financial_markets/foreign_exchange_market/exchange_rate_fixing/daily.txt"

        try:
            response = requests.get(url)
            response.raise_for_status()
            #print("Response Text:\n", response.text)

            for line in response.text.split("\n"):
                if "|EUR|" in line:  # More robust check
                    parts = line.split("|")
                    rate = float(parts[-1])
                    return rate

        except Exception as e:
            print(f"Error: {e}")
            return None

    def download_daily_price_per_card(self, cardname=None):
        """
        Find price for each card
        :param cardname:
        :return: dataframe with cardname, price in EUR, USD, CZK for foil and non-foil + tix
        """
        url = "https://api.scryfall.com/cards/named"
        params = {"exact": cardname}
        czk_eur_rate = self.get_eur_to_czk_rate()
        df = None

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

        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching data: {e}")

        return df
    def get_card_set(self, card_name):
        """Returns a list of (set_name, set_code) for all printings of a given card.
        ...for name, code in sets...
        """
        base_url = f"https://api.scryfall.com/cards/named?exact={card_name.replace(' ', '%20')}"
        resp = requests.get(base_url)
        if resp.status_code != 200:
            print("Error:", resp.json().get("details", "Unknown error"))
            return []

        data = resp.json()
        prints_search_uri = data.get("prints_search_uri")
        printings_resp = requests.get(prints_search_uri)
        if printings_resp.status_code != 200:
            print("Error fetching printings:", printings_resp.text)
            return []

        all_printings = printings_resp.json()
        results = set()

        for card in all_printings["data"]:
            set_name = card.get("set_name")
            set_code = card.get("set")
            if set_name and set_code:
                results.add((set_name, set_code))
        return sorted(results, key=lambda x: x[0])

    def get_card_price_for_set(self, card_name, set_code):
        """
        Fetch the current USD price of a specific card from a specific set using Scryfall.
        """
        url = f"https://api.scryfall.com/cards/named?exact={card_name.replace(' ', '%20')}&set={set_code.lower()}"
        response = requests.get(url)
        czk_eur_rate = self.get_eur_to_czk_rate()

        if response.status_code != 200:
            print("Error:", response.json().get("details", "Unknown error"))
            return None

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
            "card_name": card_name,
            "price_usd": usd_price,
            "price_usd_foil": usd_foil_price,
            "price_eur": eur_price,
            "price_eur_foil": eur_price_foil,
            "price_czk": czk_price,
            "price_czk_foil": czk_price_foil,
            "tix": tix}])

        return df

if __name__ == "__main__":
    card = CardFinder()
    deck = card.recognize_card(file_path="photos/hobitci4.jpg")
    all_dataframes = []
    for c, k in deck:
        single_df = card.download_daily_price_per_card(cardname=c)
        all_dataframes.append(single_df)
    dataframe = pd.concat(all_dataframes, ignore_index=True)
    dataframe = dataframe.sort_values(by="price_eur", ascending=True)
    dataframe.to_csv('full_data.csv')
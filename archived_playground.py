import requests
import json
import logging

def download_daily_price_per_card(cardname=None):
    url = "https://api.scryfall.com/cards/named"
    params = {"exact": cardname}

    try:
        response = requests.get(url, params=params)
        logging.info(f"Response Status Code: {response.status_code}")
        response.raise_for_status()

        card_data = response.json()
        prices = card_data.get("prices", {})
        usd_price = prices.get("usd")
        usd_foil_price = prices.get("usd_foil")
        eur_price = prices.get("eur")

        # Print results
        print(f"Prices:")
        print(f"USD (non-foil): {usd_price}")
        print(f"USD (foil): {usd_foil_price}")
        print(f"EUR: {eur_price}")

    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching data: {e}")

if __name__ == "__main__":
    cardname="Fire"
    download_daily_price_per_card(cardname)

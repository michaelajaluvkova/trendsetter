import streamlit as st
from PIL import Image
import pandas as pd
from class_cardfinder import CardFinder
import hashlib

def get_file_hash(file):
    return hashlib.md5(file.getvalue()).hexdigest()

st.title("Trend Setter")
st.markdown("""
Welcome to **Trend Setter** – your Magic: The Gathering card price companion!

**How to use?**
- Upload a clear **photo of your Magic cards**. Ensure good lighting and focus on a card name.
- The app will automatically detect and list the card names using Optical Character Recognition.

**What this app does?**
- Uses open-source [mtgscan](https://github.com/fortierq/mtgscan) library, based on [Azure Cognitive Services](https://azure.microsoft.com/en-us/products/ai-services), to recognize Magic: The Gathering cards from your image.
- Fetches live price data for each card (CZK, EUR, USD, foil & non-foil and tix), the cards are ordered from the most to the least expensive
- You can:
    - See average prices across sets for all cards in the photo
    - See prices for all cards from a single specific set.
    - See prices for various sets for various cards.

**Where do prices come from?**
We fetch data in real time from the [Scryfall API](https://scryfall.com/docs/api), which takes it from TCGPlayer for USD and Cardmarket for EUR. Tix prices are taken from CardHoarder.
CZK prices are converted via EUR/CZK exchange rate from ČNB.
The prices on Scryfall are updated once per day.

The Trend Setter does **not** store any data.
Once your image is uploaded, select what you'd like to do from the dropdown menu. 
If you'd like to **share a feedback**, please use this [form](https://docs.google.com/forms/d/e/1FAIpQLSeFbA1Gs2EIDQ1Qz-WbFmO1Z0UlpF9kHgvFuTz8xSXxKM4I4Q/viewform?usp=sharing). 
Thanks!
""")
uploaded_file = st.file_uploader("Upload a photo of your cards here, and wait for the magic!", type=["jpg", "jpeg", "png"])

if uploaded_file:
    file_hash = get_file_hash(uploaded_file)
    # check if it's a new image
    if st.session_state.get("last_file_hash") != file_hash:
        st.session_state.last_file_hash = file_hash
        st.session_state.card = CardFinder()
        st.session_state.deck = None

        # clean any card-specific dropdowns for Option 3
        keys_to_delete = [key for key in st.session_state.keys() if key.startswith("set_selection_")]
        for key in keys_to_delete:
            if key in st.session_state:
                del st.session_state[key]
            if key + "_options" in st.session_state:
                del st.session_state[key + "_options"]

    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded image", use_container_width=True)
    processing_message = st.empty()
    processing_message.info("Processing...")

    image_path = "temp_uploaded_image.jpg"
    image.convert("RGB").save(image_path)

    if st.session_state.card is None:
        st.session_state.card = CardFinder()
    card = st.session_state.card

    if st.session_state.deck is None:
        card = CardFinder()
        deck = card.recognize_card(file_path=image_path)
        st.session_state.deck = deck
    deck = st.session_state.deck

    if not deck:
        st.error("No cards recognized. Try another image.")

    else:
        # select options after OCR
        processing_message.empty()
        option = st.selectbox(
            "Choose what to do next:",
            ["Select an option", "Option 1: Show average price", "Option 2: Prices per single set", "Option 3: Prices per card per set"] )

        if option == "Option 1: Show average price":
            all_dfs = []
            for cardname, count in deck:
                df = card.download_daily_price_per_card(cardname=cardname)
                if df is not None:
                    df["count"] = count
                    all_dfs.append(df)

            if all_dfs:
                result = pd.concat(all_dfs, ignore_index=True)
                columns_to_keep = ['card_name', 'price_czk', 'price_czk_foil', 'price_eur',
                                   'price_eur_foil', 'price_usd', 'price_usd_foil',  'tix']
                result = result.loc[:, [col for col in columns_to_keep if col in result.columns]]
                result["price_czk"] = pd.to_numeric(result["price_czk"], errors="coerce")
                result_valid_prices = result.dropna(subset=["price_czk"])

                unique_card_count = result["card_name"].nunique()

                if not result_valid_prices.empty:
                    result_sorted = result_valid_prices.sort_values(by="price_czk", ascending=False)
                    top_card = result_sorted.iloc[0]
                    st.markdown(f"Out of the **{unique_card_count}** cards shown, the most expensive card is **{top_card['card_name']}** with a price around **{top_card['price_czk']:.2f} CZK**.")
                else:
                    result_sorted = result
                    st.warning("No valid CZK prices found to determine the most expensive card.")

                # visualisation
                result = result.sort_values(by="price_czk", ascending=False, na_position="last")
                result = result.reset_index(drop=True)  # Reset index
                st.dataframe(result.style.hide(axis="index"))
                csv = result.to_csv(index=False)
                st.download_button("Download CSV", csv, file_name="card_prices.csv")

        elif option == "Option 2: Prices per single set":
            try:
                sets_df = card.fetch_all_mtg_sets()
                set_display_names = [f"{row['name']} ({row['code'].upper()})" for _, row in sets_df.iterrows()]
                selected_set_display = st.selectbox("Choose a set", set_display_names)

                if selected_set_display:
                    selected_set_code = selected_set_display.split("(")[-1].replace(")", "").strip()

                    all_results = []
                    for cardname, count in deck:
                        df = card.get_card_price_for_set(card_name=cardname, set_code=selected_set_code)
                        if df is not None:
                            df["count"] = count
                            df["set_code"] = selected_set_code.upper()
                            all_results.append(df)

                    if all_results:
                        #### adding markdown line for highest price

                        result_df = pd.concat(all_results, ignore_index=True)
                        result_df = result_df.sort_values(by="price_czk", ascending=False,
                                                          na_position="last").reset_index(drop=True)
                        top_card = result_df.iloc[0]
                        unique_card_count = result_df["card_name"].nunique()

                        st.markdown(f"Out of the **{unique_card_count}** cards shown, the most expensive card is **{top_card['card_name']}** with a price around **{top_card['price_czk']:.2f} CZK**.")

                        st.dataframe(result_df.style.hide(axis="index"))
                        csv = result_df.to_csv(index=False)
                        st.download_button("Download CSV", csv, file_name="card_prices_selected_set.csv")
                    else:
                        st.warning("No data found for selected set.")

            except Exception as e:
                st.error(f"Failed to fetch sets or prices: {e}")

        elif option == "Option 3: Prices per card per set":
            set_selections = {}
            all_ready = True

            for idx, (cardname, count) in enumerate(deck):
                dropdown_key = f"set_selection_{idx}_{cardname}"

                if dropdown_key not in st.session_state:
                    sets = card.get_card_set(cardname)
                    if not sets:
                        st.warning(f"No sets found for card: {cardname}")
                        all_ready = False
                        continue
                    st.session_state[dropdown_key + "_options"] = [f"{name} ({code})" for name, code in sets]

                set_option_list = st.session_state.get(dropdown_key + "_options", [])
                if not set_option_list:
                    st.warning(f"Set options not available for {cardname}.")
                    all_ready = False
                    continue

                selected_set_display = st.selectbox(
                    f"Select set for **{cardname}**",
                    set_option_list,
                    key=dropdown_key)

                if selected_set_display:
                    set_code = selected_set_display.split("(")[-1].replace(")", "").strip()
                    set_selections[cardname] = (set_code, count)
                else:
                    all_ready = False

            if all_ready and set_selections:
                st.success("All sets selected. Fetching prices...")

                results = []
                for cardname, (set_code, count) in set_selections.items():
                    df = card.get_card_price_for_set(cardname, set_code)
                    if df is not None:
                        df["count"] = count
                        df["set_code"] = set_code.upper()
                        results.append(df)

                if results:
                    final_df = pd.concat(results, ignore_index=True)
                    final_df = final_df.sort_values(by="price_czk", ascending=False, na_position="last").reset_index(drop=True)
                    top_card = final_df.iloc[0]
                    unique_card_count = final_df["card_name"].nunique()

                    st.markdown(
                        f"Out of the **{unique_card_count}** cards shown, the most expensive card is **{top_card['card_name']}** with a price around **{top_card['price_czk']:.2f} CZK**.")

                    st.dataframe(final_df.style.hide(axis="index"))
                    csv = final_df.to_csv(index=False)
                    st.download_button("Download CSV", csv, file_name="card_prices_custom_sets.csv")
                else:
                    st.warning("No prices found for selected cards and sets.")
            elif not set_selections:
                st.info("No cards available for set selection.")
            else:
                st.info("Please make selections for all cards.")


        else:
            st.info("Please select an option to proceed.")
# KEEP_ALIVE_TIMESTAMP: 2025-05-28T01:14:26Z

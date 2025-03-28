import streamlit as st
from PIL import Image
import pandas as pd
from class_cardfinder import CardFinder

st.title("Trend Setter")

uploaded_file = st.file_uploader("Upload a photo of your cards", type=["jpg", "jpeg", "png"])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded image", use_column_width=True)
    st.info("Processing...")

    image_path = "temp_uploaded_image.jpg"
    image.save(image_path)

    card = CardFinder()
    deck = card.recognize_card(file_path=image_path)

    if not deck:
        st.error("No cards recognized. Try another image.")
    else:
        # Select option after OCR
        option = st.selectbox(
            "Choose what to do next:",
            ["Select an option", "Option 1: Show average price", "Option 2"]
        )

        if option == "Option 1: Show average price":
            all_dfs = []
            for cardname, count in deck:
                df = card.download_daily_price_per_card(cardname=cardname)
                if df is not None:
                    df["count"] = count
                    all_dfs.append(df)

            if all_dfs:
                result = pd.concat(all_dfs, ignore_index=True)
                columns_to_keep = ['card_name', 'price_usd', 'price_usd_foil', 'price_eur',
                                   'price_eur_foil', 'price_czk', 'price_czk_foil', 'tix']
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

        elif option == "Option 2":
            """
            Place to insert code. The code should:
            - take the extracted card's name 
            - create a function in class_cardfinder.py extracts all the possible sets which were released so far
            - create a button which would have all these options available 
            - prepare a script which would find a price for the chosen set + card name using get_card_price_for_set()
            """
            st.write("Option 2 selected: This is just a placeholder action for now.")
        elif option == "Option 3":
            """
            Place to insert code. The code should:
            - take the extracted card's name
            - for each card name create a button with a list of sets where the card was released in (use get_card_set() function)
            - prepare a script which would take each card name + the chosen set, run using get_card_price_for_set() for each combination
            - append results for each combination into dataframe
            """
            st.write("Option 3 selected: This is just a placeholder action for now.")

        else:
            st.info("Please select an option to proceed.")

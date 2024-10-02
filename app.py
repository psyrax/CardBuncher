import streamlit as st
from sqlalchemy import text
import requests
import json

headers = {
    'X-Api-Key': st.secrets["api_keys"]["tcgapi"],
}

st.set_page_config(layout="wide")
conn = st.connection('cards_db', type='sql', ttl=1)

@st.cache_data
def get_cards():
    cards = conn.query('SELECT * FROM cards')
    return cards

if "current_card" not in st.session_state:
    st.session_state.current_card = False

def set_current_card():
    st.session_state.current_card = st.session_state.card_number_input
    current_expansion_set = st.session_state.expansion_set_input
    card_number = st.session_state.card_number_input
    card_url = "https://api.pokemontcg.io/v2/cards?q=set.id:{} number:{}".format(current_expansion_set, card_number)
    card_response = requests.get(card_url, headers=headers)
    st.session_state.current_card = card_response.json()['data'][0]
    
    

with conn.session as s:
    s.execute(text('CREATE TABLE IF NOT EXISTS cards (expansion TEXT, number TEXT, language TEXT, api_expansion TEXT, api_id TEXT, normal INT, holo INT, reverse_holo INT, api_data TEXT, league INT);'))
    s.commit()


with open('legal_sets.json', 'r') as file:
    legal_sets = json.load(file)
    
expansion_sets = [expansion_set['apiCode'] for expansion_set in legal_sets]

def expansion_format(api_code):
    for legal_set in legal_sets:
        if legal_set['apiCode'] == api_code:
            return '{} - {}'.format(legal_set['ptcgoCode'], legal_set['name'])


def get_expansion_code(api_code):
    for legal_set in legal_sets:
        if legal_set['apiCode'] == api_code:
            return legal_set['ptcgoCode']

col1, col2 = st.columns(2)

with col1:
    st.write("Add Card")
    form_col1, form_col2 = st.columns(2)
    
    with form_col1:
        select_set = st.selectbox("Expansion set", expansion_sets, format_func=expansion_format, key="expansion_set_input")
        card_number = st.text_input("Card number", key="card_number_input", on_change=set_current_card)
        card_type = st.radio("Card type",
            [
                "Normal",
                "Holo",
                "Reverse Holo"
            ])
        card_language = st.radio("Language", [
            "en",
            "es"
        ])
        card_league = st.checkbox("League card")
    with form_col2:
        if st.session_state.current_card:
            current_card = st.session_state.current_card
            st.image(current_card['images']['small'])
            try:
                for price in current_card['tcgplayer']['prices']:
                    st.write('{}: ${}'.format(price, current_card['tcgplayer']['prices'][price]['market']))
            except:
                pass
            card_data = {
                'expansion': get_expansion_code(select_set),
                'number': card_number,
                'language': card_language,
                'api_expansion': current_card['set']['id'],
                'api_id': current_card['id'],
                'normal': 0,
                'holo': 0,
                'reverse_holo': 0,
                'api_data': json.dumps(current_card),
                'league': 0
            }
            if card_type == "Normal":
                card_data['normal'] = 1
            elif card_type == "Holo":
                card_data['holo'] = 1
            elif card_type == "Reverse Holo":
                card_data['reverse_holo'] = 1
            if card_league:
                card_data['league'] = 1
        if st.button("Save"):
            st.cache_data.clear()
            with conn.session as s:
                s.execute(
                    text('INSERT INTO cards (expansion, number, language, api_expansion, api_id, normal, holo, reverse_holo, api_data, league) VALUES (:expansion, :number, :language, :api_expansion, :api_id, :normal, :holo, :reverse_holo, :api_data, :league)'),
                    params = card_data
                )
                s.commit()
                st.write("Saved")

with col2:
    st.write('DB')
    st.dataframe(get_cards())
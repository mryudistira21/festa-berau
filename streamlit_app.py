import streamlit as st
from datetime import date, datetime
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import json

# Initialize session state to store the DataFrame
if 'scraped_df' not in st.session_state:
    st.session_state.scraped_df = None

# Page config
st.set_page_config(page_title="Festa Berau", layout="wide")
st.header('Fenomena Statistik Kabupaten Berau')

# Helper functions
def get_date_range(start_date, end_date):
    """Generate a list of date strings between start_date and end_date."""
    return pd.date_range(start=start_date, end=end_date).strftime('%Y/%m/%d').tolist()

def fetch_page(url, retries=3, delay=2):
    """Fetch a webpage with retry logic."""
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            time.sleep(delay)
    return None

def scrape_berau_terkini(dates_to_scrape):
    """Scrape Berita Berau Terkini ."""
    scraped_data = []
    for date_input in dates_to_scrape:
        current_page = 1
        while True:
            url = f"https://berauterkini.co.id/indeks/page/{current_page}/?category=all&date={date_input}"
            response = fetch_page(url)
            if not response:
                break

            soup = BeautifulSoup(response.content, "html.parser")
            articles = soup.find_all(class_="indeks-item media")

            if not articles:
                break

            for article in articles:
                scraped_data.append({
                    "title": article.find("a", class_="media-title").text.strip(),
                    "category": article.find("div", class_="indeks-category").text.strip(),
                    "date": article.find("div", class_="indeks-date").text.strip(),
                    "URL": article.find("a")["href"],
                    "source": "Berau Terkini"
                })
            current_page += 1
    return scraped_data

def scrape_detik(start_date, end_date):
    """Scrape Berita Detik based on query parameters."""
    scraped_data = []
    current_page = 1

    while True:
        # URL format with query parameters
        url = (
            f"https://www.detik.com/search/searchall?query=berau"
            f"&page={current_page}&result_type=latest"
            f"&fromdatex={start_date}&todatex={end_date}"
        )
        response = fetch_page(url)
        if not response:
            break

        soup = BeautifulSoup(response.content, "html.parser")
        articles = soup.find_all("article", class_="list-content__item")

        if not articles:
            break

        for article in articles:
            scraped_data.append({
                "title": article.find("h3", class_="media__title").text.strip(),
                "category": article.find("h2", class_="media__subtitle").text.strip(),
                "date": article.find("div", class_="media__date").text.strip(),
                "URL": article.find("a")["href"],
                "source": "Detik"
            })
        
        # Check for the presence of a "next page" button
        next_page = soup.find("a", class_="pagination__next")
        if next_page:
            current_page += 1
        else:
            break

    return scraped_data

# Unified scrape function
def scrape_news(start_date, end_date, selected_sources):
    all_data = []
    if "Berau Terkini" in selected_sources:
        dates_to_scrape = get_date_range(start_date, end_date)
        all_data.extend(scrape_berau_terkini(dates_to_scrape))
    if "Detik" in selected_sources:
        all_data.extend(scrape_detik(start_date.strftime('%d/%m/%Y'), end_date.strftime('%d/%m/%Y')))
    return all_data


# Sidebar for user inputs
with st.sidebar:
    st.header('Settings')
    start_date = st.date_input("Tanggal Awal", date(2022, 1, 1))
    end_date = st.date_input("Tanggal Akhir", date.today())
    news_sources = st.multiselect("Sumber Berita", ["Berau Terkini", "Detik"], default=["Berau Terkini"])

    if st.button("Scrape"):
        with st.spinner("Scraping news..."):
            scraped_data = scrape_news(start_date, end_date, news_sources)
            if scraped_data:
                st.success(f"Scraped {len(scraped_data)} news successfully!")
                st.session_state.scraped_df = pd.DataFrame(scraped_data)
            else:
                st.warning("No news found.")


# Display results
if st.session_state.scraped_df is not None:
    df = st.session_state.scraped_df

    # Make URLs clickable
    def make_clickable(url):
        return f'<a href="{url}" target="_blank">{url}</a>'

    df["URL"] = df["URL"].apply(make_clickable)
    st.write(df.to_html(escape=False, index=False), unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV", csv, "news_articles.csv", "text/csv")

    with col2:
        json_str = df.to_json(orient="records", indent=4)
        st.download_button("Download JSON", json_str, "news_articles.json", "application/json")

# Usage instructions
with st.expander("Cara Penggunaan"):
    st.write("""
    1. Pilih rentang tanggal yang diinginkan
    2. Pilih Media Online yang diinginkan
    3. Klik tombol 'Scrape' untuk memulai pengambilan data
    4. Hasil dapat diunduh dalam format CSV atau JSON
    5. Proses scraping mungkin memerlukan waktu beberapa menit tergantung jumlah artikel
    """)

#Copyright
st.caption('Copyright (c) 2024 BPS Kabupaten Berau')

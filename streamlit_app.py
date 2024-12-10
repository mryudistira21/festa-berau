import streamlit as st
from datetime import date, datetime
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re


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
        except requests.exceptions.RequestException:
            time.sleep(delay)
    return None

# Mapping Indonesian to English day and month names
def translate_date(raw_date):
    day_mapping = {
        "Senin": "Monday", "Selasa": "Tuesday", "Rabu": "Wednesday",
        "Kamis": "Thursday", "Jumat": "Friday", "Sabtu": "Saturday",
        "Minggu": "Sunday"
    }
    month_mapping = {
        "Januari": "January", "Februari": "February", "Maret": "March",
        "April": "April", "Mei": "May", "Juni": "June",
        "Juli": "July", "Agustus": "August", "September": "September",
        "Oktober": "October", "November": "November", "Desember": "December"
    }
    
    for indo_day, eng_day in day_mapping.items():
        raw_date = raw_date.replace(indo_day, eng_day)
    for indo_month, eng_month in month_mapping.items():
        raw_date = raw_date.replace(indo_month, eng_month)
    return raw_date

def scrape_berau_terkini(dates_to_scrape):
    """Scrape Berita Berau Terkini."""
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

def scrape_benuanta(start_date, end_date, max_pages=10):
    """Scrape Berita Benuanta with performance optimizations."""
    scraped_data = []
    current_page = 1

    # Convert start_date and end_date to datetime.datetime
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())

    while current_page <= max_pages:
        url = f"https://benuanta.co.id/index.php/page/{current_page}/?s=Berau"
        response = fetch_page(url)
        if not response:
            break

        soup = BeautifulSoup(response.content, 'html.parser')
        articles = soup.find_all('article')

        if not articles:
            print("No more articles found.")
            break

        for article in articles:
            date_tag = article.find('time')
            if date_tag:
                date_str = date_tag.get('datetime')
                article_date = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S%z').replace(tzinfo=None)

                if start_datetime <= article_date <= end_datetime:
                    title_tag = article.find('h2')
                    category_tag = article.find('span', class_="gmr-meta-topic")
                    link_tag = article.find('a')

                    if title_tag and category_tag and link_tag:
                        scraped_data.append({
                            "title": title_tag.text.strip(),
                            "category": category_tag.text.strip(),
                            "date": article_date.strftime('%Y-%m-%d'),
                            "URL": link_tag['href'],
                            "source": "Benuanta"
                        })

        next_page = soup.find("a", class_="next page-numbers")
        if not next_page:
            break

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

def scrape_prokal(start_date, end_date, max_pages=10):
    """Scrape Prokal articles with performance optimizations."""
    scraped_data = []
    base_url = "https://www.prokal.co/search?q=berau&sort=latest&page="
    current_page = 1

    # Convert start_date and end_date to datetime objects with time
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())

    while current_page <= max_pages:
        url = f"{base_url}{current_page}"
        response = requests.get(url)

        if response.status_code != 200:
            print(f"Failed to retrieve page {current_page}: {response.status_code}")
            break

        soup = BeautifulSoup(response.content, "html.parser")
        articles = soup.find_all("div", class_="latest__item")

        if not articles:
            print("No more articles found.")
            break

        for article in articles:
            try:
                title = article.find("h2").text.strip()
                category = article.find("h4").text.strip()
                url = article.find("a")["href"].strip()
                raw_date = article.find("date", class_="latest__date").text.strip().split("|")[0]

                # Clean the date string
                clean_date = re.sub(r'citation_\d+', '', raw_date).strip()

                # Translate and parse the date
                translated_date = translate_date(clean_date)
                article_date = datetime.strptime(translated_date, "%A, %d %B %Y")

                # Filter by date range
                if start_datetime <= article_date <= end_datetime:
                    scraped_data.append({
                        "title": title,
                        "category": category,
                        "date": clean_date,
                        "URL": url,
                        "source": "Prokal"
                    })

            except Exception as e:
                print(f"Error parsing an article: {e}")

        next_page = soup.find("a", class_="next")
        if not next_page:
            break

        current_page += 1

    return scraped_data


# Unified scrape function
def scrape_news(start_date, end_date, selected_sources):
    all_data = []
    if "Berau Terkini" in selected_sources:
        dates_to_scrape = get_date_range(start_date, end_date)
        all_data.extend(scrape_berau_terkini(dates_to_scrape))
    if "Benuanta" in selected_sources:
        all_data.extend(scrape_benuanta(start_date, end_date))
    if "Detik" in selected_sources:
        all_data.extend(scrape_detik(start_date.strftime('%d/%m/%Y'), end_date.strftime('%d/%m/%Y')))
    if "Prokal" in selected_sources:
        all_data.extend(scrape_prokal(start_date, end_date))
    return all_data

# Sidebar for user inputs
with st.sidebar:
    st.header('Settings')
    start_date = st.date_input("Tanggal Awal", date(2022, 1, 1))
    end_date = st.date_input("Tanggal Akhir", date.today())
    news_sources = st.multiselect("Sumber Berita", ["Berau Terkini", "Benuanta", "Detik", "Prokal"], default=["Berau Terkini"])

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

# Copyright
st.caption('Copyright (c) 2024 BPS Kabupaten Berau')

# Opportunate

A free platform to help students discover internships based on their career interests or personal skills using web scraping and Google Gemini AI.

## Setup

1. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

2. **Add your API key**

   ```bash
   cp .env.example .env
   ```

   Edit `.env` and set `GEMINI_API_KEY` from [Google AI Studio](https://aistudio.google.com/apikey).

3. **Run the app**

   ```bash
   python app.py
   ```

   Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

## Features

- Scrapes top internships from Internshala
- Uses Google Gemini to suggest skills and free resources
- Download results as PDF

## Required API keys

| Key | Where to get it | Required? |
|-----|-----------------|-----------|
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/apikey) | Yes |

No other third-party API keys are needed. The Flask backend runs locally on your machine.

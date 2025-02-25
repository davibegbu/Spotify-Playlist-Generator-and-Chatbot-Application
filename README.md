# README - Spotify Playlist Generator & Music Insights App

## 📌 Overview
This repository contains a **Flask web application** that integrates **Spotify API** and **OpenAI API** to provide personalized music insights and generate playlists based on user preferences. Users can log in with their **Spotify account**, explore their top songs and artists, and generate custom playlists using AI-powered recommendations.

## 📁 Project Structure

### 🔹 **Main Application**
- **app.py** → Flask backend that handles user authentication, Spotify API interactions, and OpenAI-based recommendations.

### 🔹 **Configuration Files**
- **config.py** → Stores API keys for Spotify and OpenAI.

### 🔹 **Templates (HTML Files for UI)**
- **login.html** → Login page with a Spotify authentication link.
- **base.html** → Main UI displaying prompts and chatbot interactions.
- **top_songs.html** → Shows the user's top Spotify tracks.
- **top_artists.html** → Displays the user's most played artists.
- **most_played_genres.html** → Summarizes the user's most played genres.
- **recommended_playlist.html** → Displays AI-generated playlist recommendations.

## 🛠️ How It Works
1. **User Authentication:**
   - Users log in via **Spotify OAuth**.
   - The app requests **read access** to top tracks, saved songs, and playlists.

2. **Music Insights & Chatbot:**
   - Users can ask AI-driven music-related queries.
   - Example prompts: *“What’s my most played genre?”*, *“Who is my favorite artist?”*, *“Can you recommend a song based on my listening history?”*
   - AI generates responses using **OpenAI GPT-3.5**.

3. **Playlist Generation:**
   - Users can input **a mood or genre**, and the app creates a **personalized playlist** using **Spotify’s track search API**.
   - The AI model selects **20 relevant songs** based on the user’s top listening preferences.

4. **Top Tracks & Artists:**
   - The app fetches and displays the user's **most played songs and artists**.

## 📌 Key Functions
- **get_sp()** → Retrieves a valid **Spotify authentication token**.
- **home_post()** → Processes user queries, fetches listening history, and provides AI-powered recommendations.
- **recommend()** → Generates a **Spotify playlist** based on AI recommendations.
- **top_songs()** → Fetches and displays **user's top songs**.
- **top_artists()** → Fetches and displays **user's top artists**.
- **most_played_genres()** → Computes the **most played genres** based on the user’s top tracks.

## 🔗 Dependencies
- **Python Libraries:** Flask, Spotipy (Spotify API wrapper), OpenAI, Requests, JSON, re (Regex)
- **External APIs:** Spotify Web API, OpenAI API

## 🚀 How to Run Locally

### 🔹 **1. Install Dependencies**
```bash
pip install flask spotipy openai requests ratelimit
```

### 🔹 **2. Set Up API Keys**
Create a **config.py** file and add the following:
```python
SPOTIFY_CLIENT_ID = "your_spotify_client_id"
SPOTIFY_CLIENT_SECRET = "your_spotify_client_secret"
SPOTIFY_REDIRECT_URI = "http://localhost:8080/callback"
OPENAI_API_KEY = "your_openai_api_key"
```

### 🔹 **3. Run the Application**
```bash
python app.py
```

### 🔹 **4. Access the Web App**
Open your browser and go to:
```bash
http://localhost:8080
```

## 📊 Example Queries & Outputs
```
User: What's my most played genre?
AI: Based on your Spotify listening history, your most played genre is Hip-Hop.

User: Can you generate a playlist with a chill mood?
AI: Here's a curated Spotify playlist based on a chill vibe.

User: Who is my most played artist?
AI: Your top artist is Drake.
```

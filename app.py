import spotipy
import config
import openai
import json
from flask import Flask, redirect, url_for, session, request, render_template
from spotipy.oauth2 import SpotifyOAuth
import time
import re
import ratelimit

app = Flask(__name__)
app.secret_key = 'YOUR_SECRET_KEY'
app.config['SESSION_COOKIE_NAME'] = 'spotify-login-session'

openai.api_key = config.OPENAI_API_KEY

# Force the login dialog to show every time by setting show_dialog=True
sp_oauth = SpotifyOAuth(
    client_id=config.SPOTIFY_CLIENT_ID,
    client_secret=config.SPOTIFY_CLIENT_SECRET,
    redirect_uri=config.SPOTIFY_REDIRECT_URI,
    scope="user-top-read playlist-modify-private user-library-read",
    show_dialog=True  # This forces the Spotify login page to appear every time
)

def get_sp():
    token_info = session.get('token_info', None)
    if not token_info:
        print("No token info found in session.")
        return None  # User is not authenticated

    now = int(time.time())
    is_token_expired = token_info['expires_at'] - now < 60

    if is_token_expired:
        try:
            token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
            session['token_info'] = token_info  # Update the session with the new token info
            print("Token refreshed and updated in session.")
        except Exception as e:
            print(f"Error refreshing access token: {e}")
            return None  # Redirect to login in case of failure

    sp = spotipy.Spotify(auth=token_info['access_token'])
    print(f"Returning Spotify object with token: {token_info['access_token']}")
    return sp

@app.route('/')
def login():
    # Only clear session if user explicitly logs out, not during navigation
    if 'logged_in' in session:
        return redirect(url_for('home'))
    auth_url = sp_oauth.get_authorize_url()
    return render_template('login.html', auth_url=auth_url)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    try:
        token_info = sp_oauth.get_access_token(code)
        session['token_info'] = token_info
        session['logged_in'] = True  # Mark the user as logged in
        print(f"New token info stored in session: {token_info}")
        return redirect(url_for('home'))
    except Exception as e:
        print(f"Error obtaining access token: {e}")
        return f"Error obtaining access token: {e}", 400

@app.route('/logout')
def logout():
    session.clear()  # Clear the session
    print("Session cleared on logout.")
    return redirect(url_for('login'))

@app.route('/home')
def home():
    logged_in = session.get('logged_in', False)
    if not logged_in:
        return redirect(url_for('login'))
    sp = get_sp()
    if not sp:
        return redirect(url_for('login'))
    return render_template('base.html', prompts=[
        "What's my most played genre?",
        "What's my favorite artist?",
        "What's the average duration of my top tracks?",
        "What's the most popular song in my top tracks?",
        "Can you recommend a new artist based on my listening history?"
    ])

@app.route('/home', methods=['POST'])
@ratelimit.limits(calls=50, period=60)  # 50 calls per 60 seconds
def home_post():
    sp = get_sp()
    if not sp:
        return redirect(url_for('login'))

    # Get the user prompt from the form submission
    prompt = request.form['prompt'].lower()

    # Extract the main noun/mood/genre from the user's prompt
    noun_match = re.search(r'create a (\w+) playlist', prompt)
    keyword = noun_match.group(1) if noun_match else None

    # Fetch all user's saved tracks by paginating the requests
    saved_songs = []
    try:
        offset = 0
        limit = 50
        while True:
            saved_tracks = sp.current_user_saved_tracks(limit=limit, offset=offset)
            saved_songs.extend([{
                "song": track["track"]["name"],
                "artist": track["track"]["artists"][0]["name"]
            } for track in saved_tracks['items']])

            if len(saved_tracks['items']) < limit:
                break
            offset += limit
    except Exception as e:
        print(f"Error fetching user's saved tracks: {e}")
        return "Error fetching user's saved tracks", 500

    # If the prompt contains "playlist" and a keyword is found, generate a playlist
    playlist = []
    response_message = ""
    if "playlist" in prompt and keyword:
        results = sp.search(q=f'{keyword}', type='track', limit=20)
        playlist = [{"song": track["name"], "artist": track["artists"][0]["name"], "album_cover": track["album"]["images"][0]["url"]} for track in results['tracks']['items']]
        response_message = f"Here's a playlist based on the {keyword} mood:"
    
    # If the prompt asks about "most popular artist", handle it
    elif "most popular artist" in prompt:
        artist_frequency = {}
        for track in saved_songs:
            artist = track["artist"]
            artist_frequency[artist] = artist_frequency.get(artist, 0) + 1
        most_popular_artist = max(artist_frequency, key=artist_frequency.get)
        response_message = f"Your most popular artist is {most_popular_artist}, based on your saved tracks."

    # General OpenAI API prompt handling for other queries
    else:
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a Spotify data assistant that analyzes the user's listening history and answers any questions from the user based on their data."},
                    {"role": "user", "content": f"Here is some of the user's favorite data: {saved_songs[:10]}. Now answer the following question based on this data: {prompt}"}
                ]
            )
            content = response.choices[0].message.content
            response_message = content
        except Exception as e:
            print(f"Error calling OpenAI API: {e}")
            response_message = "Error processing your request."

    # Render the homepage with the chatbot's response and the playlist if it exists
    return render_template('base.html', response=response_message, prompts=[
        "What's my most played genre?",
        "What's my favorite artist?",
        "What's the average duration of my top tracks?",
        "What's the most popular song in my top tracks?",
        "Can you recommend a new artist based on my listening history?"
    ], playlist=playlist)

@app.route('/recommended_playlist')
def recommend():
    sp = get_sp()
    if not sp:
        return redirect(url_for('login'))

    # Fetch user's top tracks
    top_tracks = sp.current_user_top_tracks(limit=5)
    top_songs = [{"song": track["name"], "artist": track["artists"][0]["name"]} for track in top_tracks['items']]

    # Fetch user's liked songs
    liked_tracks = sp.current_user_saved_tracks(limit=50)
    liked_songs = set(track["track"]["id"] for track in liked_tracks["items"])

    # Prompt for OpenAI
    prompt = f"Generate a playlist of 20 songs that are similar to the following songs but by different artists in the same genre: {json.dumps(top_songs)}"

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a playlist generating assistant."},
                {"role": "user", "content": prompt}
            ]
        )
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return "Error calling OpenAI API", 500

    try:
        content = response.choices[0].message.content
        print(f"Response content: {content}")  # Log the content for debugging

        # Parse the plain text response to extract songs and artists
        recommended_playlist = []
        lines = content.split('\n')
        for line in lines:
            match = re.match(r'\d+\.\s*"([^"]+)"\s+by\s+(.+)', line)
            if match:
                song = match.group(1)
                artist = match.group(2)
                recommended_playlist.append({"song": song, "artist": artist})

    except json.JSONDecodeError as json_err:
        print(f"JSON decode error: {json_err}")
        return f"Error decoding JSON: {json_err}", 400

    track_ids = []
    final_playlist = []
    for item in recommended_playlist:
        query = f"{item['song']} {item['artist']}"
        search_results = sp.search(q=query, type='track', limit=1)
        if search_results['tracks']['items']:
            track = search_results['tracks']['items'][0]
            if track['id'] not in liked_songs:  # Ensure the song is not in liked songs
                track_ids.append(track['id'])
                final_playlist.append({
                    "song": track['name'],
                    "artist": track['artists'][0]['name'],
                    "album": track['album']['name'],
                    "duration": time.strftime("%M:%S", time.gmtime(track['duration_ms'] // 1000)),
                    "cover_url": track['album']['images'][0]['url'] if track['album']['images'] else None
                })
            if len(track_ids) == 20:
                break

    if track_ids:
        user_id = sp.current_user()['id']
        playlist = sp.user_playlist_create(user_id, name='Recommended Playlist', public=False)
        sp.user_playlist_add_tracks(user_id, playlist['id'], track_ids)
        return render_template('recommended_playlist.html', top_songs=top_songs, recommended_playlist=final_playlist, playlist_url=f"https://open.spotify.com/playlist/{playlist['id']}")
    else:
        print("No track IDs were found.")
        return render_template('recommended_playlist.html', top_songs=top_songs, recommended_playlist=final_playlist, playlist_url="#", enumerate=enumerate, error="No valid tracks found for the playlist.")

@app.route('/top_songs')
def top_songs():
    sp = get_sp()
    if not sp:
        return redirect(url_for('login'))
    top_tracks = sp.current_user_top_tracks(limit=25)
    top_songs = [{
        "song": track["name"],
        "artist": track["artists"][0]["name"],
        "album": track["album"]["name"],
        "duration": time.strftime("%M:%S", time.gmtime(track["duration_ms"] // 1000)),
        "cover_url": track["album"]["images"][0]["url"] if track["album"]["images"] else None
    } for track in top_tracks["items"]]
    return render_template('top_songs.html', top_songs=top_songs)

@app.route('/top_artists')
def top_artists():
    sp = get_sp()
    if not sp:
        return redirect(url_for('login'))
    top_artists = sp.current_user_top_artists(limit=25)
    top_artists_list = [{
        "name": artist["name"],
        "genres": artist["genres"],
        "popularity": artist["popularity"],
        "image_url": artist["images"][0]["url"] if artist["images"] else None
    } for artist in top_artists["items"]]
    return render_template('top_artists.html', top_artists=top_artists_list)

@app.route('/most_played_genres')
def most_played_genres():
    sp = get_sp()
    if not sp:
        return redirect(url_for('login'))
    top_tracks = sp.current_user_top_tracks(limit=50)
    genres = {}
    for track in top_tracks['items']:
        for artist in track['artists']:
            artist_info = sp.artist(artist['id'])
            for genre in artist_info['genres']:
                if genre in genres:
                    genres[genre] += 1
                else:
                    genres[genre] = 1
    sorted_genres = sorted(genres.items(), key=lambda item: item[1], reverse=True)
    return render_template('most_played_genres.html', genres=sorted_genres)

# Fetch top artists based on time range
def get_top_artists(sp, time_range='long_term'):
    return sp.current_user_top_artists(limit=25, time_range=time_range)

def fetch_all_liked_songs(sp):
    liked_songs = []
    limit = 50
    offset = 0
    while True:
        results = sp.current_user_saved_tracks(limit=limit, offset=offset)
        liked_songs.extend([{
            "song": item['track']['name'],
            "artist": item['track']['artists'][0]['name'],
            "album_cover": item['track']['album']['images'][0]['url'] if item['track']['album']['images'] else None
        } for item in results['items']])
        if results['next'] is None:
            break
        offset += limit
    return liked_songs


# Fetch top tracks based on time range
def get_top_tracks(sp, time_range='long_term'):
    return sp.current_user_top_tracks(limit=25, time_range=time_range)

# Fetch recently played tracks (for daily listening queries)
def get_recently_played(sp):
    return sp.current_user_recently_played(limit=50)

@app.context_processor
def utility_processor():
    return dict(enumerate=enumerate)

if __name__ == '__main__':
    app.run(debug=True, port=8080)

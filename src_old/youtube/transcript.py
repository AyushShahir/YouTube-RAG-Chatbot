import re
import urllib.parse as urlparse
import urllib.request
import json
from youtube_transcript_api import YouTubeTranscriptApi

def extract_video_id(url: str) -> str:
    """
    Extract the 11-character video ID from a YouTube URL.
    Supports watch URLs, shared URLs (youtu.be), embed URLs, shorts, and live URLs.
    """
    if not url:
        raise ValueError("URL cannot be empty.")
    
    # Regex to handle various youtube formats and extract the 11-character video ID
    pattern = r'(?:https?://)?(?:www\.)?(?:youtube\.com/(?:watch\?v=|embed/|v/|shorts/|live/)|youtu\.be/)([a-zA-Z0-9_-]{11})'
    match = re.search(pattern, url)
    if match:
        return match.group(1)
        
    parsed = urlparse.urlparse(url)
    if parsed.hostname in ('www.youtube.com', 'youtube.com'):
        query = urlparse.parse_qs(parsed.query)
        if 'v' in query:
            return query['v'][0]
            
    raise ValueError("Could not extract a valid YouTube video ID. Please check the URL format.")

def fetch_transcript(url: str) -> list[dict]:
    """
    Fetch the transcript of the YouTube video at the given URL.
    Returns a list of transcript snippets with text, start, and duration keys.
    """
    video_id = extract_video_id(url)
    
    api = YouTubeTranscriptApi()
    transcript = api.fetch(video_id)
    
    transcript_data = []
    for snippet in transcript:
        if isinstance(snippet, dict):
            transcript_data.append({
                "text": snippet.get("text", ""),
                "start": snippet.get("start", 0),
                "duration": snippet.get("duration", 0)
            })
        else:
            transcript_data.append({
                "text": getattr(snippet, "text", str(snippet)),
                "start": getattr(snippet, "start", 0),
                "duration": getattr(snippet, "duration", 0)
            })
        
    return transcript_data

def fetch_video_metadata(url: str) -> dict:
    """
    Fetch basic video metadata (title, channel, views, duration, published) 
    by parsing the YouTube HTML page.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9'
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8', errors='replace')
    except Exception as e:
        return {
            "title": "YouTube Video",
            "channel": "Unknown Channel",
            "views": "N/A",
            "duration": "N/A",
            "published": "N/A"
        }
        
    # Try parsing ytInitialPlayerResponse
    pattern = r'ytInitialPlayerResponse\s*=\s*(\{.+?\});'
    match = re.search(pattern, html)
    if not match:
        pattern = r'window\["ytInitialPlayerResponse"\]\s*=\s*(\{.+?\});'
        match = re.search(pattern, html)
        
    if match:
        try:
            player_response = json.loads(match.group(1))
            video_details = player_response.get("videoDetails", {})
            microformat = player_response.get("microformat", {}).get("playerMicroformatRenderer", {})
            
            # Format view count nicely
            views = video_details.get("viewCount", "0")
            try:
                views_formatted = f"{int(views):,}"
            except ValueError:
                views_formatted = views
                
            # Format duration (seconds -> MM:SS or HH:MM:SS)
            length_seconds = int(video_details.get("lengthSeconds", 0))
            hours = length_seconds // 3600
            minutes = (length_seconds % 3600) // 60
            seconds = length_seconds % 60
            if hours > 0:
                duration_formatted = f"{hours}:{minutes:02d}:{seconds:02d}"
            else:
                duration_formatted = f"{minutes}:{seconds:02d}"
                
            # Format publication date to YYYY-MM-DD
            raw_publish_date = microformat.get("publishDate", "N/A")
            published_formatted = raw_publish_date[:10] if len(raw_publish_date) >= 10 else raw_publish_date
            
            return {
                "title": video_details.get("title", "YouTube Video"),
                "channel": video_details.get("author", "Unknown Channel"),
                "views": views_formatted,
                "duration": duration_formatted,
                "published": published_formatted
            }
        except Exception:
            pass
            
    # Fallback to simple title extraction via html scraping
    metadata = {
        "title": "YouTube Video",
        "channel": "Unknown Channel",
        "views": "N/A",
        "duration": "N/A",
        "published": "N/A"
    }
    
    title_match = re.search(r'<meta name="title" content="([^"]+)">', html)
    if title_match:
        metadata["title"] = title_match.group(1)
        
    return metadata

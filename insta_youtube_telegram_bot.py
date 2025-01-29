import os
import re
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from instaloader import Instaloader, Post
import yt_dlp
import io

# Initialize Instaloader
L = Instaloader()

# Telegram Bot Token
TOKEN = "7768481988:AAET5OQtoMOqh4_rPhOgz_-y4mN8JVGzG-Q"

# Configure yt-dlp
ydl_opts = {
    'format': 'best[filesize<50M]',  # Best quality under 50MB (Telegram limit)
    'quiet': True,
    'no_warnings': True,
    'extract_flat': False,
    'socket_timeout': 120,  # Increase timeout limit to 120 seconds
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    await update.message.reply_text('Hi! Send me an Instagram or YouTube link (including Shorts), and I\'ll download it for you!')

def extract_shortcode(url):
    """Extract the shortcode from an Instagram URL."""
    pattern = r'(?:instagram.com/(?:p|reel|stories)/)([\w-]+)'
    match = re.search(pattern, url)
    return match.group(1) if match else None

def is_youtube_url(url):
    """Check if the URL is from YouTube."""
    youtube_patterns = [
        r'(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)([^&\n?]+)'
    ]
    for pattern in youtube_patterns:
        match = re.search(pattern, url)
        if match:
            return True, match.group(1)
    return False, None

async def download_youtube_video(url, update):
    """Download YouTube video and send to user."""
    try:
        # Send buffering message
        buffering_msg = await update.message.reply_text('Buffering video... Please wait.')
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Get video info
            info = ydl.extract_info(url, download=False)
            
            # Get the video URL
            video_url = info['url']
            
            # Download video content
            video_response = requests.get(video_url, stream=True, timeout=120)  # Increase timeout to 120 seconds
            video_bytes = io.BytesIO(video_response.content)
            
            # Send video to user
            await update.message.reply_video(
                video_bytes,
                caption=f"📝 Title: {info.get('title', 'Unknown')}\n"
                       f"👁 Views: {info.get('view_count', 0):,}\n"
                       f"⏱ Duration: {info.get('duration', 0)} seconds\n\n"
                       f"🔗 {url}"
            )
        
        # Delete buffering message once video is sent
        await buffering_msg.delete()
        
    except Exception as e:
        # If file is too large, try with a smaller format
        if "File too large" in str(e):
            try:
                ydl_opts['format'] = 'worst'  # Try with lowest quality
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    video_url = info['url']
                    video_response = requests.get(video_url, stream=True, timeout=120)  # Increased timeout
                    video_bytes = io.BytesIO(video_response.content)
                    
                    await update.message.reply_video(
                        video_bytes,
                        caption=f"📝 Title: {info.get('title', 'Unknown')}\n"
                               f"(Lower quality due to size limitations)\n\n"
                               f"🔗 {url}"
                    )
            except Exception as e2:
                await update.message.reply_text(f"Error downloading YouTube video: {str(e2)} or Look at sometime")
        else:
            await update.message.reply_text(f"Error downloading YouTube video: {str(e)} or Look at sometime")

async def download_instagram_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Download Instagram content when a valid link is received."""
    url = update.message.text
    
    try:
        # Send processing message
        processing_msg = await update.message.reply_text('Processing your request...')
        
        # Check if it's a YouTube URL
        is_youtube, video_id = is_youtube_url(url)
        if is_youtube:
            await download_youtube_video(url, update)
            await processing_msg.delete()
            return
        
        # Handle Instagram content
        shortcode = extract_shortcode(url)
        if not shortcode:
            await update.message.reply_text('Please send a valid Instagram or YouTube link.')
            return
        
        # Get post information
        post = Post.from_shortcode(L.context, shortcode)
        
        try:
            if post.is_video:
                # Get video URL
                video_url = post.video_url
                # Stream video content
                video_response = requests.get(video_url, stream=True, timeout=120)  # Increased timeout
                video_bytes = io.BytesIO(video_response.content)
                
                # Send video directly to user
                await update.message.reply_video(
                    video_bytes,
                    caption=f"Downloaded from: {url}"
                )
            else:
                # Get photo URL
                photo_url = post.url
                # Stream photo content
                photo_response = requests.get(photo_url, stream=True, timeout=120)  # Increased timeout
                photo_bytes = io.BytesIO(photo_response.content)
                
                # Send photo directly to user
                await update.message.reply_photo(
                    photo_bytes,
                    caption=f"Downloaded from: {url}"
                )
            
        except Exception as e:
            await update.message.reply_text(f"Error processing media: {str(e)}")
        
        # Delete processing message
        await processing_msg.delete()
        
    except Exception as e:
        await update.message.reply_text(f'Sorry, an error occurred: {str(e)}')

def main():
    """Start the bot."""
    # Create the Application and pass it your bot's token
    application = Application.builder().token(TOKEN).build()

    # Commands
    application.add_handler(CommandHandler("start", start))

    # Message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_instagram_content))

    # Start the Bot using run_polling() method
    print("Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
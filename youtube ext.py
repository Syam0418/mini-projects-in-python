'''import os
import yt_dlp

# -----------------------------------------
# 1. OUTPUT FOLDER
# -----------------------------------------

OUTPUT_FOLDER = r"D:\YouTube MP3\downloads"

# Create folder automatically if it does not exist
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# -----------------------------------------
# 2. GET PLAYLIST URL
# -----------------------------------------

print("=" * 55)
print("   ULTRA-FAST YOUTUBE PLAYLIST DOWNLOADER (ARIA2C)")
print("=" * 55)

playlist_url = input("\nEnter YouTube Playlist URL: ").strip()

if not playlist_url:
    print("Error: Playlist URL cannot be empty.")

else:

    # -----------------------------------------
    # 3. REMASTERED & OPTIMIZED DOWNLOAD SETTINGS
    # -----------------------------------------

    options = {
        # Best native audio format (no FFmpeg needed)
        'format': 'bestaudio/best',
        
        # Save files organized by playlist index and title
        'outtmpl': os.path.join(
            OUTPUT_FOLDER,
            '%(playlist_index)03d - %(title)s.%(ext)s'
        ),

        # --- MAXIMUM SPEED VIA ARIA2C ---
        # Uses aria2c to multi-thread fragment downloads and shatter throttling
        'external_downloader': 'aria2c',
        'external_downloader_args': {
            'aria2c': [
                '--max-connection-per-server=16',
                '--split=16',
                '--min-split-size=1M',
                '--summary-interval=0'
            ]
        },
        # -------------------------------

        # Robust error and retry handling
        'retries': 15,
        'fragment_retries': 15,
        'ignoreerrors': True,
        'noplaylist': False,
        'overwrites': False,
        'windowsfilenames': True,

        # Clean progress hooks
        'progress_hooks': [
            lambda data: print(
                f"\nDownload completed: {data.get('filename', '')}"
                if data.get('status') == 'finished'
                else "",
                end=""
            )
        ],

        'quiet': False
    }

    # -----------------------------------------
    # 4. START DOWNLOADING
    # -----------------------------------------

    try:

        print("\nStarting high-speed multi-threaded download...")
        print("Output folder:", OUTPUT_FOLDER)
        print("Downloader engine: aria2c (Max Speed Mode)")

        with yt_dlp.YoutubeDL(options) as downloader:
            downloader.download([playlist_url])

        print("\n" + "=" * 55)
        print("PLAYLIST PROCESSING COMPLETED")
        print("=" * 55)

        print("\nFiles saved successfully where available:")
        print(OUTPUT_FOLDER)

    except Exception as error:

        print("\nDownload failed!")
        print("Error:", error)

# -----------------------------------------
# 5. END OF PROGRAM
# -----------------------------------------
'''
import os
import shutil
import yt_dlp

# -----------------------------------------
# 1. OUTPUT FOLDER & DEPENDENCY CHECK
# -----------------------------------------

OUTPUT_FOLDER = r"D:\YouTube MP3\downloads"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

has_aria2c = shutil.which("aria2c") is not None

# -----------------------------------------
# 2. GET MULTIPLE URLS INPUT
# -----------------------------------------

print("=" * 55)
print("   ULTRA-FAST MULTI-URL YOUTUBE DOWNLOADER")
print("=" * 55)

urls_input = input("\nEnter YouTube URLs (separate multiple URLs with commas):\n> ").strip()

if not urls_input:
    print("Error: URLs cannot be empty.")
else:
    # Split the input string by commas and clean up whitespace
    urls_list = [url.strip() for url in urls_input.split(",") if url.strip()]

    if not urls_list:
        print("Error: No valid URLs provided.")
    else:

        # -----------------------------------------
        # 3. DOWNLOAD SETTINGS
        # -----------------------------------------

        options = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(
                OUTPUT_FOLDER,
                '%(playlist_index)s - %(title)s.%(ext)s' if '%(playlist_index' in '%(playlist_index)s' else '%(title)s.%(ext)s'
            ),
        }

        # Fix outtmpl to handle individual videos vs playlists gracefully
        options['outtmpl'] = os.path.join(
            OUTPUT_FOLDER,
            '%(playlist_title)s/%(playlist_index)03d - %(title)s.%(ext)s'
        )

        # Conditionally enable aria2c if available, otherwise use multi-threaded fragments
        if has_aria2c:
            options['external_downloader'] = 'aria2c'
            options['external_downloader_args'] = {
                'aria2c': [
                    '--max-connection-per-server=16',
                    '--split=16',
                    '--min-split-size=1M',
                    '--summary-interval=0'
                ]
            }
            downloader_mode = "aria2c (Max Speed Multi-threaded)"
        else:
            options['concurrent_fragment_downloads'] = 16
            downloader_mode = "Built-in Concurrent Fragments (aria2c not found)"

        options.update({
            'retries': 15,
            'fragment_retries': 15,
            'ignoreerrors': True,
            'noplaylist': False,
            'overwrites': False,
            'windowsfilenames': True,
            'progress_hooks': [
                lambda data: print(
                    f"\nDownload completed: {data.get('filename', '')}"
                    if data.get('status') == 'finished'
                    else "",
                    end=""
                )
            ],
            'quiet': False
        })

        # -----------------------------------------
        # 4. START DOWNLOADING MULTIPLE URLS
        # -----------------------------------------

        print(f"\nFound {len(urls_list)} URL(s) to process.")
        print("Output folder:", OUTPUT_FOLDER)
        print("Engine Mode:", downloader_mode)
        print("=" * 55)

        try:
            with yt_dlp.YoutubeDL(options) as downloader:
                for idx, url in enumerate(urls_list, start=1):
                    print(f"\n--- Processing URL [{idx}/{len(urls_list)}] ---")
                    print(f"Target: {url}")
                    downloader.download([url])

            print("\n" + "=" * 55)
            print("ALL URLS PROCESSED SUCCESSFULLY")
            print("=" * 55)
            print("Saved in:", OUTPUT_FOLDER)

        except Exception as error:
            print("\nAn error occurred during batch processing!")
            print("Error:", error)

# -----------------------------------------
# 5. END OF PROGRAM
# -----------------------------------------

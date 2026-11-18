import os
import shutil
import yt_dlp

# -----------------------------------------
# 1. OUTPUT FOLDER & FILE PATHS
# -----------------------------------------

OUTPUT_FOLDER = r"D:\YouTube MP3\downloads"
LINKS_FILE = r"D:\YouTube MP3\links.txt"

os.makedirs(OUTPUT_FOLDER, exist_ok=True)
has_aria2c = shutil.which("aria2c") is not None

# -----------------------------------------
# 2. USER MENU: FORMAT SELECTION
# -----------------------------------------

print("=" * 60)
print("     ULTRA-FAST YOUTUBE BATCH DOWNLOADER")
print("=" * 60)

print("\nSelect Output Format:")
print("  [1] Audio Only (Best Quality Native Audio)")
print("  [2] Video Only (Best Quality Video + Audio)")
format_choice = input("\nEnter your choice (1 or 2, default is 1): ").strip()

if format_choice == "2":
    format_selector = "bestvideo+bestaudio/best"
    mode_desc = "High-Quality Video Mode"
else:
    format_selector = "bestaudio/best"
    mode_desc = "High-Quality Audio Mode"

print(f"-> Selected Format: {mode_desc}")

# -----------------------------------------
# 3. USER MENU: URL INPUT SOURCE SELECTION
# -----------------------------------------

print("\nSelect URL Input Method:")
print("  [1] Enter URLs manually via prompt (comma-separated)")
print("  [2] Read URLs automatically from text file (links.txt)")
input_choice = input("\nEnter your choice (1 or 2, default is 2): ").strip()

urls_list = []

if input_choice == "1":
    urls_input = input("\nEnter YouTube URLs (separate multiple URLs with commas):\n> ").strip()
    if urls_input:
        urls_list = [url.strip() for url in urls_input.split(",") if url.strip()]
else:
    # Check if links.txt exists; if not, create a template file automatically
    if not os.path.exists(LINKS_FILE):
        os.makedirs(os.path.dirname(LINKS_FILE), exist_ok=True)
        with open(LINKS_FILE, "w", encoding="utf-8") as f:
            f.write("# Paste your YouTube playlist or video URLs below (one per line)\n")
            f.write("# https://www.youtube.com/watch?v=...\n")
        print(f"\n[Info] Created template links file at: {LINKS_FILE}")
        print("Please add your YouTube URLs to that file and run the script again.")
    else:
        with open(LINKS_FILE, "r", encoding="utf-8") as f:
            # Read lines, strip whitespace, and ignore comments/empty lines
            urls_list = [
                line.strip() 
                for line in f 
                if line.strip() and not line.strip().startswith("#")
            ]
        print(f"\nSuccessfully loaded {len(urls_list)} URL(s) from '{LINKS_FILE}'.")

if not urls_list:
    print("\nError: No valid URLs provided or found. Exiting program.")
else:

    # -----------------------------------------
    # 4. DOWNLOAD SETTINGS & SPEED OPTIMIZATIONS
    # -----------------------------------------

    options = {
        'format': format_selector,
        'outtmpl': os.path.join(
            OUTPUT_FOLDER,
            '%(playlist_title)s/%(playlist_index)03d - %(title)s.%(ext)s'
        ),
    }

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
    # 5. START DOWNLOADING PROCESS
    # -----------------------------------------

    print(f"\nStarting batch process for {len(urls_list)} URL(s)...")
    print("Output folder:", OUTPUT_FOLDER)
    print("Engine Mode:", downloader_mode)
    print("=" * 60)

    try:
        with yt_dlp.YoutubeDL(options) as downloader:
            for idx, url in enumerate(urls_list, start=1):
                print(f"\n--- Processing URL [{idx}/{len(urls_list)}] ---")
                print(f"Target: {url}")
                downloader.download([url])

        print("\n" + "=" * 60)
        print("ALL URLS PROCESSED SUCCESSFULLY")
        print("=" * 60)
        print("Saved in:", OUTPUT_FOLDER)

    except Exception as error:
        print("\nAn error occurred during batch processing!")
        print("Error:", error)

# -----------------------------------------
# 6. END OF PROGRAM
# -----------------------------------------



#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import vlc
import time
import os
import sys

# --- Configuration ---
# Adjust this path if your project structure is different
MEDIA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media')
VIDEO_FILE = 'AF_Materna_Video1_Abertura_LB.mp4' # The video file inside the DIR(media) to play

# ---------------------

print("--- VLC Basic Playback Test ---")

video_path = os.path.join(MEDIA_DIR, VIDEO_FILE)

# Check if the video file exists
if not os.path.exists(video_path):
    print(f"[ERROR] Video file not found at: {video_path}")
    print("Please ensure the video file exists in the 'media' subdirectory.")
    sys.exit(1) # Exit the script if the file is missing

print(f"Attempting to play: {video_path}")

# --- VLC Initialization ---
try:
    # Create a VLC instance
    # Add options if needed, e.g., '--no-xlib' for headless, though fullscreen usually works
    instance = vlc.Instance() #vlc.Instance('--no-video-title-show') # Example option

    # Create a MediaPlayer object
    player = instance.media_player_new()

    # Create a Media object from the file path
    media = instance.media_new(video_path)

    # Set the media for the player
    player.set_media(media)

    # --- Playback Control ---
    # Set fullscreen (important for kiosk-style display)
    player.set_fullscreen(True)

    # Start playing
    print("Starting playback...")
    play_success = player.play() # Returns 0 on success, -1 on error

    if play_success == -1:
        print("[ERROR] Failed to start playback. Check VLC logs or video file.")
        sys.exit(1)

    # --- Wait for playback to almost finish ---
    # We need to keep the script running while VLC plays in the background.
    # This is a simple way; later we'll use event handling.

    print("Playback started. Waiting for video to load and play...")
    print("Press Ctrl+C to stop early.")

    # Initial wait for video to potentially load
    time.sleep(2)

    while True:
        state = player.get_state()
        # Possible states: NothingSpecial, Opening, Buffering, Playing, Paused, Stopped, Ended, Error
        print(f"Current player state: {state}")

        if state == vlc.State.Ended or state == vlc.State.Stopped or state == vlc.State.Error:
            print(f"Playback finished or stopped/errored (State: {state}).")
            break

        # Check playback position (optional, just for info)
        # position = player.get_position() # Returns float 0.0 to 1.0
        # print(f"Position: {position:.2f}")

        # Prevent busy-waiting
        time.sleep(1) # Check state every second


except NameError as e:
    if 'vlc' in str(e).lower():
        print("[ERROR] Failed to import VLC. Is 'python-vlc' installed correctly?")
        print("  Try: 'pip3 install python-vlc' or 'sudo apt install python3-vlc'")
    else:
        print(f"[ERROR] A NameError occurred: {e}")
    sys.exit(1)
except Exception as e:
    print(f"[ERROR] An unexpected error occurred: {e}")
    sys.exit(1)
except KeyboardInterrupt:
    print("\n[INFO] Ctrl+C detected. Stopping playback.")
finally:
    # --- Cleanup ---
    # Ensure the player is stopped before exiting
    if 'player' in locals() and player.is_playing():
        print("Stopping player...")
        player.stop()
    print("--- Test script finished ---")
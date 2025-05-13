import cv2
import numpy as np
import os
import time

# --- Configuration ---
MEDIA_FOLDER = "media/"
VIDEO_FILES = [
    "AF_Materna_Video1_Abertura_LB.mp4",  # This will be treated as the first in the sequence
    "AF_Materna_Video2_Pre_LB.mp4",
    "AF_Materna_Video3_VitaminasMinerais_LB.mp4",
    "AF_Materna_Video4_Omega3_LB.mp4",
    "AF_Materna_Video5_Multivitaminico_LB.mp4",
    "AF_Materna_Video6_Nause_LB.mp4",
    "AF_Materna_Video7_Opti-Lac_LB.mp4",
]

FADE_DURATION_SECONDS = 2.0
WINDOW_NAME = "RFID Video Kiosk - Sequential Play"

def load_video_properties(capture_object):
    """Helper function to get video properties."""
    if not capture_object or not capture_object.isOpened():
        return None, 0, 0, 0
    
    fps = capture_object.get(cv2.CAP_PROP_FPS)
    if fps == 0:
        print("Warning: Could not determine video FPS. Using default 25 FPS.")
        fps = 25
    width = int(capture_object.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture_object.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(capture_object.get(cv2.CAP_PROP_FRAME_COUNT))
    return fps, width, height, total_frames

def main():
    # 1. Validate video files
    valid_video_paths = []
    for video_file in VIDEO_FILES:
        path = os.path.join(MEDIA_FOLDER, video_file)
        if os.path.exists(path):
            valid_video_paths.append(path)
        else:
            print(f"Warning: Video file not found and will be skipped: {path}")
    
    if not valid_video_paths:
        print("Error: No valid video files found in the list. Exiting.")
        return

    # 2. Create a named window and set it to fullscreen
    cv2.namedWindow(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN)
    cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    current_video_index = 0
    cap = None
    
    # Initialize properties for the first video (these will be updated per video)
    # We need to open the first video to get its dimensions for the black_frame
    # This is a bit of a chicken-and-egg, so we'll load first video outside the loop initially
    
    first_video_path = valid_video_paths[current_video_index]
    cap = cv2.VideoCapture(first_video_path)
    if not cap.isOpened():
        print(f"Error: Could not open initial video: {first_video_path}. Exiting.")
        return
        
    fps, frame_width, frame_height, _ = load_video_properties(cap)
    if frame_width == 0 or frame_height == 0: # Check if load_video_properties failed
        print(f"Error: Could not get properties for initial video: {first_video_path}. Exiting.")
        cap.release()
        cv2.destroyAllWindows()
        return

    print(f"Starting with: {os.path.basename(first_video_path)} ({frame_width}x{frame_height} @ {fps:.2f} FPS)")
    
    black_frame = np.zeros((frame_height, frame_height, 3), dtype=np.uint8)
    fade_in_frames = int(FADE_DURATION_SECONDS * fps)
    current_playback_frame_count = 0
    
    running = True
    try:
        while running:
            if not cap or not cap.isOpened():
                # This case should ideally be handled by the video switching logic
                # but as a fallback if 'cap' becomes invalid unexpectedly.
                print("Error: VideoCapture is not open. Attempting to load next video.")
                # Release if it exists but is not open
                if cap: cap.release()
                
                current_video_index = (current_video_index + 1) % len(valid_video_paths)
                next_video_path = valid_video_paths[current_video_index]
                print(f"Switching to video: {os.path.basename(next_video_path)}")
                cap = cv2.VideoCapture(next_video_path)
                
                if not cap.isOpened():
                    print(f"Error: Failed to open {next_video_path}. Skipping or exiting if list exhausted.")
                    # Add more robust skipping logic if needed, for now, we might get stuck or error out
                    # For simplicity, if a video fails to load here, we might exit the loop.
                    # A better approach would be to try the *next* one in valid_video_paths.
                    # Let's assume valid_video_paths only contains truly openable files for now.
                    # Or, the outer loop will try again.
                    running = False # Or break
                    continue

                fps, new_width, new_height, _ = load_video_properties(cap)
                if new_width == 0 or new_height == 0:
                    print(f"Error: Could not get properties for {os.path.basename(next_video_path)}. Exiting.")
                    running = False
                    continue
                
                # Update resolution-dependent elements if they changed
                if new_width != frame_width or new_height != frame_height:
                    frame_width, frame_height = new_width, new_height
                    # Recreate black_frame ONLY IF resolution changes.
                    # Note: The provided black_frame uses (frame_height, frame_height, 3)
                    # This seems like a typo and should be (frame_height, frame_width, 3)
                    black_frame = np.zeros((frame_height, frame_width, 3), dtype=np.uint8)

                fade_in_frames = int(FADE_DURATION_SECONDS * fps)
                current_playback_frame_count = 0 # Reset for fade-in


            ret, frame = cap.read()

            if not ret:
                print(f"Finished video: {os.path.basename(valid_video_paths[current_video_index])}")
                cap.release() # Release the finished video

                current_video_index = (current_video_index + 1) % len(valid_video_paths)
                next_video_path = valid_video_paths[current_video_index]
                
                print(f"Loading next video: {os.path.basename(next_video_path)}")
                cap = cv2.VideoCapture(next_video_path)

                if not cap.isOpened():
                    print(f"Fatal Error: Could not open next video: {next_video_path}. Exiting.")
                    # This is a critical failure if a pre-validated path can't be opened.
                    running = False 
                    continue 
                
                new_fps, new_width, new_height, _ = load_video_properties(cap)
                if new_width == 0 or new_height == 0:
                    print(f"Fatal Error: Could not get properties for {os.path.basename(next_video_path)}. Exiting.")
                    running = False
                    continue

                # Update properties if they changed for the new video
                fps = new_fps
                if new_width != frame_width or new_height != frame_height:
                    frame_width, frame_height = new_width, new_height
                    black_frame = np.zeros((frame_height, frame_width, 3), dtype=np.uint8)
                
                fade_in_frames = int(FADE_DURATION_SECONDS * fps)
                current_playback_frame_count = 0 # Reset for fade-in for the new video
                
                # Read the first frame of the new video
                ret, frame = cap.read()
                if not ret:
                    print(f"Fatal Error: Could not read first frame of {os.path.basename(next_video_path)}. Exiting.")
                    running = False
                    continue # Exit loop

            # If frame is still None after trying to read (should be caught by 'not ret' above)
            if frame is None:
                print("Error: Frame is None, cannot proceed. Attempting to load next video.")
                # This is an unexpected state, try to recover by advancing video
                if cap: cap.release()
                current_video_index = (current_video_index + 1) % len(valid_video_paths)
                # Trigger reload in the next iteration by ensuring cap is None
                cap = None 
                continue


            current_playback_frame_count += 1
            display_frame = frame.copy()

            # --- Fade-in logic ---
            if current_playback_frame_count <= fade_in_frames:
                alpha = current_playback_frame_count / fade_in_frames
                alpha = min(alpha, 1.0)
                # Ensure black_frame matches current frame dimensions before blending
                if black_frame.shape[0] != frame.shape[0] or black_frame.shape[1] != frame.shape[1]:
                     black_frame = np.zeros_like(frame) # Make it match current frame if somehow mismatched
                display_frame = cv2.addWeighted(frame, alpha, black_frame, 1 - alpha, 0)
            
            cv2.imshow(WINDOW_NAME, display_frame)

            key = cv2.waitKey(max(1, int(1000 / fps))) & 0xFF # Ensure waitKey delay is at least 1ms
            if key == ord('q') or key == 27: # 'q' or ESC
                print("Exit key pressed.")
                running = False
                
    except KeyboardInterrupt:
        print("Ctrl+C pressed, exiting.")
    finally:
        if cap:
            cap.release()
        cv2.destroyAllWindows()
        print("Resources released.")

if __name__ == "__main__":
    # Check if MEDIA_FOLDER exists
    if not os.path.isdir(MEDIA_FOLDER):
        print(f"Error: Media folder '{MEDIA_FOLDER}' not found.")
        print("Please create it and add your MP4 video files.")
        # Create dummy videos if media folder is missing, for basic script run
        print(f"Attempting to create dummy '{MEDIA_FOLDER}' and dummy videos for testing...")
        try:
            os.makedirs(MEDIA_FOLDER, exist_ok=True)
            for i, fname_template in enumerate([
                "AF_Materna_Video1_Abertura_LB.mp4",
                "AF_Materna_Video2_Pre_LB.mp4" # Create at least two for sequence test
            ]):
                dummy_path = os.path.join(MEDIA_FOLDER, fname_template)
                if not os.path.exists(dummy_path):
                    print(f"Creating dummy video: {dummy_path}")
                    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                    # Make dummy videos short for quick testing of sequence
                    out_dummy = cv2.VideoWriter(dummy_path, fourcc, 25.0, (320, 240)) 
                    for j in range(50): # 2 seconds
                        img = np.zeros((240, 320, 3), dtype=np.uint8)
                        cv2.putText(img, f'Video {i+1} F:{j+1}', (20, 120), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, int(j*5)), 2)
                        out_dummy.write(img)
                    out_dummy.release()
            print("Dummy files created (if they weren't already present).")
        except Exception as e:
            print(f"Could not create dummy media folder/files: {e}")


    main()
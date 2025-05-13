import cv2
import numpy as np
import time # We might use this for a slight pause before looping, if desired
import os

# --- Configuration ---
VIDEO_PATH = "media/AF_Materna_Video1_Abertura_LB.mp4"  # Replace with your video file
FADE_DURATION_SECONDS = 2.0   # How long the fade-in should last
WINDOW_NAME = "RFID Video Kiosk - Looping"

def main():
    # 1. Check if video file exists
    if not os.path.exists(VIDEO_PATH):
        print(f"Error: Video file not found at {VIDEO_PATH}")
        return

    # 2. Open the video file
    cap = cv2.VideoCapture(VIDEO_PATH)
    if not cap.isOpened():
        print(f"Error: Could not open video file {VIDEO_PATH}")
        return

    # 3. Get video properties
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps == 0:
        print("Warning: Could not determine video FPS. Using default 25 FPS for delay calculation.")
        fps = 25
        
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames_in_video = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    print(f"Video: {VIDEO_PATH}")
    print(f"Resolution: {frame_width}x{frame_height}, FPS: {fps:.2f}, Total Frames: {total_frames_in_video}")

    # 4. Create a named window and set it to fullscreen
    cv2.namedWindow(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN)
    cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    
    black_frame = np.zeros((frame_height, frame_width, 3), dtype=np.uint8)
    fade_in_frames = int(FADE_DURATION_SECONDS * fps)
    
    # current_frame_count will now track frames *within the current loop iteration*
    # for the fade effect, not the absolute frame number in the video file.
    current_playback_frame_count = 0 

    try:
        running = True
        while running:
            ret, frame = cap.read()

            if not ret:
                # End of video, so reset to the beginning
                print("Video ended. Looping...")
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0) # Rewind video
                current_playback_frame_count = 0    # Reset frame counter for fade-in
                # Optional: Brief pause before restarting
                # time.sleep(0.1) # 100ms pause
                ret, frame = cap.read() # Read the first frame again
                if not ret:
                    print("Error: Could not read frame after attempting to loop. Exiting.")
                    break # Exit if we can't even read the first frame after reset

            current_playback_frame_count += 1
            display_frame = frame.copy()

            # --- Fade-in logic ---
            if current_playback_frame_count <= fade_in_frames:
                alpha = current_playback_frame_count / fade_in_frames
                alpha = min(alpha, 1.0) 
                display_frame = cv2.addWeighted(frame, alpha, black_frame, 1 - alpha, 0)
            
            cv2.imshow(WINDOW_NAME, display_frame)

            key = cv2.waitKey(int(1000 / fps)) & 0xFF
            if key == ord('q') or key == 27: # 'q' or ESC
                print("Exit key pressed.")
                running = False
                
    except KeyboardInterrupt:
        print("Ctrl+C pressed, exiting.")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("Resources released.")

if __name__ == "__main__":
    # Create a dummy video file if it doesn't exist, for quick testing
    if not os.path.exists(VIDEO_PATH):
        print(f"Creating a dummy video '{VIDEO_PATH}' for testing...")
        fourcc = cv2.VideoWriter_fourcc(*'mp4v') 
        out_dummy = cv2.VideoWriter(VIDEO_PATH, fourcc, 25.0, (640, 480))
        for i in range(75): # 3 seconds at 25 fps for a shorter loop test
            img = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(img, f'Loop Frame: {i+1}', (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 
                        1, (0, 255, int(i*3.4)), 2, cv2.LINE_AA)
            cv2.circle(img, (320 + int(100*np.sin(i/5.0)), 240 + int(100*np.cos(i/5.0))), 30, (int(i*3.4),0,0), -1)
            out_dummy.write(img)
        out_dummy.release()
        print(f"Dummy video '{VIDEO_PATH}' created.")

    main()
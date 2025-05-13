import cv2
import numpy as np
import os
import time
import threading
import queue
import logging
import configparser
import serial # For serial.SerialException
import pygame # Added for audio playback

# --- Initialize Logger ---
# Basic config here, will be updated after config file is read if LogLevel is specified
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Attempt to import the RDM6300 library ---
# This block needs to be BEFORE classes that inherit from it are defined.
try:
    from rdm6300 import BaseReader, CardData # Assumes rdm6300 library is in project dir
    RDM6300_IMPORTED = True
    logger.info("Successfully imported rdm6300 library.")
except ImportError:
    logger.error("CRITICAL: Could not import rdm6300 library. Ensure it's in a 'rdm6300' subdirectory or installed.")
    RDM6300_IMPORTED = False
    # Define dummy classes if import fails so the rest of the code doesn't break immediately,
    # though RFID functionality will be disabled.
    class BaseReader: pass
    class CardData: pass
    # If RFID is absolutely essential, you might want to exit here:
    # logger.critical("Exiting because rdm6300 library is missing.")
    # exit(1)


# --- Configuration Loading Function ---
def load_configuration(config_file="config.ini"):
    config = configparser.ConfigParser()
    default_config = {
        "MEDIA_FOLDER": "media/",
        "IDLE_VIDEO_FILENAME": "AF_Materna_Video1_Abertura_LB.mp4", # Default idle video
        "TAG_VIDEO_MAP": {}, # Default empty map
        "RFID_SERIAL_PORT": "/dev/serial0",
        "RFID_HEARTBEAT_INTERVAL": 0.5,
        "FADE_DURATION_SECONDS": 1.5,
        "LOG_LEVEL_STR": "INFO",
        "WINDOW_NAME": "Interactive Kiosk Default",
        "ALLOW_NO_RFID": "False", # New: Allow running without RFID if True
        "SOUNDTRACK_FILE": "soundtrack.mp3" # Default soundtrack filename
    }

    if not os.path.exists(config_file):
        logger.error(f"Configuration file '{config_file}' not found. Using default values.")
        return default_config # Return all defaults

    config.read(config_file)
    app_config = {}

    try:
        # General Settings
        app_config["MEDIA_FOLDER"] = config.get('GeneralSettings', 'MediaFolder', fallback=default_config["MEDIA_FOLDER"])
        app_config["RFID_SERIAL_PORT"] = config.get('GeneralSettings', 'SerialPort', fallback=default_config["RFID_SERIAL_PORT"])
        app_config["LOG_LEVEL_STR"] = config.get('GeneralSettings', 'LogLevel', fallback=default_config["LOG_LEVEL_STR"]).upper()
        app_config["FADE_DURATION_SECONDS"] = config.getfloat('GeneralSettings', 'FadeDurationSeconds', fallback=default_config["FADE_DURATION_SECONDS"])
        app_config["RFID_HEARTBEAT_INTERVAL"] = config.getfloat('GeneralSettings', 'RfidHeartbeatInterval', fallback=default_config["RFID_HEARTBEAT_INTERVAL"])
        app_config["WINDOW_NAME"] = config.get('GeneralSettings', 'WindowName', fallback=default_config["WINDOW_NAME"])
        app_config["ALLOW_NO_RFID"] = config.getboolean('GeneralSettings', 'AllowNoRfid', fallback=default_config["ALLOW_NO_RFID"] == "True")
        app_config["SOUNDTRACK_FILE"] = config.get('GeneralSettings', 'SoundtrackFile', fallback=default_config["SOUNDTRACK_FILE"])


        # Video Mapping
        app_config["IDLE_VIDEO_FILENAME"] = config.get('VideoMapping', 'IDLE_VIDEO', fallback=default_config["IDLE_VIDEO_FILENAME"])
        
        tag_video_map_int_keys = {}
        if 'VideoMapping' in config:
            for key_hex_str, value_video_file in config.items('VideoMapping'):
                if key_hex_str.lower() == 'idle_video': # Skip the idle_video key itself
                    continue
                try:
                    # Convert the HEXADECIMAL string key from config.ini to an INTEGER
                    tag_id_int = int(key_hex_str, 16) 
                    tag_video_map_int_keys[tag_id_int] = value_video_file
                    # This debug log will be visible if LogLevel in config is DEBUG
                    logger.debug(f"Config: Mapped hex key '{key_hex_str}' (int: {tag_id_int}) to '{value_video_file}'")
                except ValueError:
                    logger.warning(f"Invalid hexadecimal tag ID '{key_hex_str}' in config.ini [VideoMapping]. Skipping.")
        app_config["TAG_VIDEO_MAP"] = tag_video_map_int_keys

        logger.info(f"Configuration loaded from '{config_file}'")

    except (configparser.NoSectionError, configparser.NoOptionError) as e:
        logger.error(f"Error reading configuration file '{config_file}': {e}. Some defaults may be used.")
        # Fill missing keys with defaults if specific sections/options are missing
        for key, val in default_config.items():
            if key not in app_config:
                app_config[key] = val
    except ValueError as e:
        logger.error(f"Error converting configuration value in '{config_file}': {e}. Check number formats. Some defaults may be used.")
        for key, val in default_config.items():
            if key not in app_config:
                app_config[key] = val
    return app_config

# --- Load Configuration ---
APP_CONFIG = load_configuration()

# --- Setup Logging based on Config (Re-configure if level changed) ---
LOG_LEVEL_MAP = {
    "DEBUG": logging.DEBUG, "INFO": logging.INFO,
    "WARNING": logging.WARNING, "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}
effective_log_level = LOG_LEVEL_MAP.get(APP_CONFIG.get("LOG_LEVEL_STR", "INFO"), logging.INFO)
# Reconfigure root logger
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
logging.basicConfig(level=effective_log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__) # Already defined, will pick up new level

# --- Constants from Config ---
MEDIA_FOLDER = APP_CONFIG["MEDIA_FOLDER"]
IDLE_VIDEO_FILENAME = APP_CONFIG["IDLE_VIDEO_FILENAME"]
TAG_VIDEO_MAP = APP_CONFIG["TAG_VIDEO_MAP"] # This map has INTEGER keys
RFID_SERIAL_PORT = APP_CONFIG["RFID_SERIAL_PORT"]
RFID_HEARTBEAT_INTERVAL = APP_CONFIG["RFID_HEARTBEAT_INTERVAL"]
FADE_DURATION_SECONDS = APP_CONFIG["FADE_DURATION_SECONDS"]
WINDOW_NAME = APP_CONFIG["WINDOW_NAME"]
ALLOW_NO_RFID = APP_CONFIG["ALLOW_NO_RFID"]
SOUNDTRACK_FILE = APP_CONFIG["SOUNDTRACK_FILE"] # Added from config

# --- Pygame Mixer Initialization ---
pygame_mixer_initialized = False
soundtrack = None
soundtrack_channel = None
# SOUNDTRACK_FILE = "soundtrack.mp3" # REMOVED - Now from APP_CONFIG
SOUNDTRACK_DURATION_SEC = 19.0 # Known duration, will try to update
TARGET_SOUNDTRACK_VOLUME = 0.7 # Or 1.0

try:
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
    soundtrack_path = os.path.join(MEDIA_FOLDER, SOUNDTRACK_FILE)
    if os.path.exists(soundtrack_path):
        soundtrack = pygame.mixer.Sound(soundtrack_path)
        try:
            SOUNDTRACK_DURATION_SEC = soundtrack.get_length()
            logger.info(f"Soundtrack '{soundtrack_path}' loaded successfully. Duration: {SOUNDTRACK_DURATION_SEC:.2f}s.")
        except pygame.error: # Some environments might not get length easily before play
            logger.warning(f"Soundtrack '{soundtrack_path}' loaded, but couldn't get length. Using assumed {SOUNDTRACK_DURATION_SEC}s.")
    else:
        logger.warning(f"Soundtrack file not found: {soundtrack_path}. Audio will not play.")
    pygame_mixer_initialized = True
except pygame.error as e:
    logger.error(f"Failed to initialize pygame.mixer or load soundtrack: {e}. Audio will not play.")
except Exception as e:
    logger.error(f"An unexpected error occurred during pygame.mixer setup: {e}. Audio will not play.")

# --- Audio State Global Variables ---
audio_playback_start_time = 0.0 # When audio (and video) playback started - potentially less needed
current_video_duration_sec = 0.0 # Duration of the currently playing content video
audio_fade_state = "NONE" # "NONE", "FADE_IN", "PLAYING", "FADE_OUT"

# --- Global variables for state management ---
rfid_event_queue = queue.Queue()
stop_rfid_thread = threading.Event()
previous_video_was_content = False # Initialize to False

# --- RFID Handler Class (Defined AFTER BaseReader is known) ---
class RfidVideoHandler(BaseReader):
    def __init__(self, port, event_queue, heartbeat_interval):
        if not RDM6300_IMPORTED:
            logger.error("RfidVideoHandler cannot be initialized: rdm6300 library failed to import.")
            raise ImportError("rdm6300 library not available for RfidVideoHandler")

        logger.info(f"RfidVideoHandler: Initializing with port={port}, heartbeat={heartbeat_interval}")
        try:
            super().__init__(port=port, heartbeat_interval=heartbeat_interval)
            self.event_queue = event_queue
            logger.info(f"RfidVideoHandler: Successfully initialized serial port {self.serial.name if self.serial and hasattr(self.serial, 'name') else 'N/A'}.")
            if self.serial and self.serial.is_open:
                logger.info(f"RfidVideoHandler: Serial port {self.serial.name} is open.")
            else:
                port_name_for_log = self.serial.name if self.serial and hasattr(self.serial, 'name') else port
                logger.warning(f"RfidVideoHandler: Serial port {port_name_for_log} IS NOT OPEN after init (or serial object invalid).")
        except serial.SerialException as e:
            logger.error(f"RfidVideoHandler: CRITICAL - Failed to open serial port {port} during super().__init__(): {e}")
            raise
        except Exception as e:
            logger.error(f"RfidVideoHandler: CRITICAL - Unexpected error during __init__: {e}", exc_info=True)
            raise

    def card_inserted(self, card: CardData):
        logger.debug(f"RfidVideoHandler.card_inserted: Raw card data: {card}")
        if card.is_valid:
            tag_id_to_check = card.value # card.value is an integer
            logger.info(f"RfidVideoHandler: Valid Tag Inserted: ID(int)={tag_id_to_check}")
            self.event_queue.put(("TAG_INSERTED", tag_id_to_check))
            logger.debug(f"RfidVideoHandler: Event TAG_INSERTED for {tag_id_to_check} put on queue.")
        else:
            logger.warning(f"RfidVideoHandler: Tag Inserted (Invalid Checksum): ID={card.value}")
            self.event_queue.put(("TAG_INVALID", card.value))

    def card_removed(self, card: CardData):
        logger.info(f"RFID Tag Removed: ID={card.value} (event ignored for video control)")

    def invalid_card(self, card: CardData):
        logger.warning(f"RFID Invalid Card Data Detected: {card}")
        self.event_queue.put(("TAG_INVALID", card.value))

    def tick(self):
        if stop_rfid_thread.is_set():
            logger.info("RfidVideoHandler.tick: stop_rfid_thread is set, calling self.stop()")
            self.stop()

# --- RFID Reader Thread Function ---
def rfid_reader_thread_func(port, event_queue, heartbeat_interval):
    if not RDM6300_IMPORTED:
        logger.error("RFID thread cannot start: rdm6300 library failed to import.")
        return

    rfid_handler = None
    logger.info("RFID Thread: Starting.")
    try:
        rfid_handler = RfidVideoHandler(port, event_queue, heartbeat_interval)
        logger.info("RFID Thread: RfidVideoHandler instantiated. Calling rfid_handler.start().")
        rfid_handler.start() # This is a blocking call
        logger.info("RFID Thread: rfid_handler.start() returned (reader loop ended).")
    except ImportError:
        logger.error("RFID Thread: Failed to initialize RfidVideoHandler due to missing rdm6300 library (ImportError).")
    except serial.SerialException as se:
        logger.error(f"RFID Thread: SerialException, possibly port {port} not available or permission issue: {se}")
    except Exception as e:
        logger.error(f"RFID Thread: Unhandled exception: {e}", exc_info=True)
    finally:
        if rfid_handler:
            logger.info("RFID Thread: Closing rfid_handler.")
            rfid_handler.close()
        logger.info("RFID Thread: Stopped and cleaned up.")

# --- Helper Functions ---
def get_video_properties(capture_object):
    if not capture_object or not capture_object.isOpened():
        return 0, 0, 0, 0 # fps, width, height, total_frames (fps=0 indicates error)
    fps = capture_object.get(cv2.CAP_PROP_FPS)
    if fps == 0: fps = 25 # Default FPS if detection fails
    width = int(capture_object.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture_object.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(capture_object.get(cv2.CAP_PROP_FRAME_COUNT)) # Get total frames
    return fps, width, height, total_frames

def start_soundtrack_for_video(video_total_frames, video_fps):
    global pygame_mixer_initialized, soundtrack, soundtrack_channel
    global audio_playback_start_time, current_video_duration_sec, audio_fade_state

    if not (pygame_mixer_initialized and soundtrack):
        logger.debug("Cannot start soundtrack: Pygame mixer not init or soundtrack not loaded.")
        audio_fade_state = "NONE"
        return

    # Stop any currently playing sound on the channel immediately
    if soundtrack_channel and soundtrack_channel.get_busy():
        soundtrack_channel.stop()
        logger.debug("Stopped previous soundtrack instance.")

    current_video_duration_sec = video_total_frames / video_fps if video_fps > 0 else 0
    logger.info(f"Starting soundtrack for video (duration: {current_video_duration_sec:.2f}s).")
    
    soundtrack_channel = soundtrack.play(loops=0) # Play ONCE
    if soundtrack_channel:
        soundtrack_channel.set_volume(0.0)
        audio_playback_start_time = time.time() # Mark start for potential reference, though video time is primary
        audio_fade_state = "FADE_IN"
        logger.debug(f"Soundtrack playing. State: FADE_IN. Video duration: {current_video_duration_sec:.2f}s")
    else:
        logger.error("Failed to play soundtrack (channel is None).")
        audio_fade_state = "NONE"

def manage_soundtrack_volume(video_current_time_sec, fade_duration_config_sec):
    global pygame_mixer_initialized, soundtrack_channel, audio_fade_state
    global current_video_duration_sec, TARGET_SOUNDTRACK_VOLUME

    if not (pygame_mixer_initialized and soundtrack_channel and soundtrack_channel.get_busy()):
        if audio_fade_state != "NONE": # If it was supposed to be playing
             logger.debug(f"Soundtrack channel not busy or None. Current state: {audio_fade_state}. Setting to NONE.")
        audio_fade_state = "NONE" # Ensure state is reset if channel stops unexpectedly
        return

    # --- FADE-IN ---
    if audio_fade_state == "FADE_IN":
        if video_current_time_sec < fade_duration_config_sec:
            volume = (video_current_time_sec / fade_duration_config_sec) * TARGET_SOUNDTRACK_VOLUME
            soundtrack_channel.set_volume(min(volume, TARGET_SOUNDTRACK_VOLUME))
        else:
            soundtrack_channel.set_volume(TARGET_SOUNDTRACK_VOLUME)
            audio_fade_state = "PLAYING"
            logger.debug("Soundtrack state: PLAYING (fade-in complete).")
    
    # --- CHECK FOR FADE-OUT START ---
    # Start fading out `fade_duration_config_sec` before the video ends.
    fade_out_start_time_video = current_video_duration_sec - fade_duration_config_sec
    
    if audio_fade_state == "PLAYING" and video_current_time_sec >= fade_out_start_time_video and current_video_duration_sec > 0:
        # Ensure current_video_duration_sec is positive to avoid issues if video duration is 0
        audio_fade_state = "FADE_OUT"
        logger.debug(f"Soundtrack state: FADE_OUT. Video current: {video_current_time_sec:.2f}s, Fade starts at: {fade_out_start_time_video:.2f}s.")
        # No volume change here, FADE_OUT logic below will handle it from current volume

    # --- FADE-OUT ---
    if audio_fade_state == "FADE_OUT":
        # Time into the designated fade-out period
        time_into_fade_out_period = video_current_time_sec - fade_out_start_time_video
        
        if time_into_fade_out_period < 0:
            # This means we are before the fade_out_start_time_video, so keep target volume
            # This case should ideally be caught by the PLAYING state check above, but as a safeguard:
            if soundtrack_channel.get_volume() < TARGET_SOUNDTRACK_VOLUME : # Only set if not already at target
                 soundtrack_channel.set_volume(TARGET_SOUNDTRACK_VOLUME)
        elif time_into_fade_out_period < fade_duration_config_sec:
            # Volume decreases from TARGET_SOUNDTRACK_VOLUME to 0 over fade_duration_config_sec
            fadeOutProgress = time_into_fade_out_period / fade_duration_config_sec
            volume = TARGET_SOUNDTRACK_VOLUME * (1.0 - fadeOutProgress)
            soundtrack_channel.set_volume(max(0.0, volume)) # Ensure volume doesn't go negative
        else: # Fade-out duration has passed (or video is beyond its expected end for fade)
            soundtrack_channel.set_volume(0.0)
            logger.debug("Soundtrack fade-out complete (volume at 0).")
            # audio_fade_state = "NONE" # Let video end logic handle full stop

def stop_soundtrack_immediately():
    global pygame_mixer_initialized, soundtrack_channel, audio_fade_state
    if pygame_mixer_initialized and soundtrack_channel and soundtrack_channel.get_busy():
        soundtrack_channel.stop()
        logger.info("Soundtrack stopped immediately.")
    audio_fade_state = "NONE"

# --- Main Application Logic ---
def main():
    global previous_video_was_content # Declare global at the start of the function
    logger.info("Kiosk application starting...")
    logger.info(f"Effective Log Level: {logging.getLevelName(logger.getEffectiveLevel())}")
    logger.info(f"Using Idle Video: {IDLE_VIDEO_FILENAME}")
    logger.info(f"Tag to Video Map (Int_key : Video_file): {TAG_VIDEO_MAP}")

    idle_video_full_path = os.path.join(MEDIA_FOLDER, IDLE_VIDEO_FILENAME)
    if not os.path.exists(idle_video_full_path):
        logger.error(f"Idle video not found: {idle_video_full_path}. Exiting.")
        return

    # valid_tag_video_map will store integer_tag_id -> full_video_path
    valid_tag_video_map = {}
    for tag_id_int, video_filename in TAG_VIDEO_MAP.items(): 
        path = os.path.join(MEDIA_FOLDER, video_filename)
        if os.path.exists(path):
            valid_tag_video_map[tag_id_int] = path
        else:
            logger.warning(f"Video for tag ID(int) {tag_id_int} ('{video_filename}') not found at {path}. This tag will be ignored.")
    
    rfid_thread = None
    rfid_active = False
    if RDM6300_IMPORTED:
        logger.info("Main: Preparing to start RFID thread.")
        try:
            rfid_thread = threading.Thread(target=rfid_reader_thread_func,
                                           args=(RFID_SERIAL_PORT, rfid_event_queue, RFID_HEARTBEAT_INTERVAL),
                                           daemon=True)
            rfid_thread.start()
            if rfid_thread.is_alive():
                 logger.info(f"Main: RFID reader thread initiated successfully.")
                 rfid_active = True
            else: # Thread might fail to start for other reasons not caught by exception
                 logger.error(f"Main: RFID reader thread failed to start or exited immediately.")
        except Exception as e: # Catch broader exceptions if thread creation itself fails
            logger.error(f"Main: Failed to start RFID thread: {e}. Running without RFID functionality.", exc_info=True)
    elif ALLOW_NO_RFID:
        logger.warning("Main: rdm6300 library not imported, but AllowNoRfid is True. RFID functionality disabled.")
    else:
        logger.error("Main: rdm6300 library not imported and AllowNoRfid is False. Cannot proceed without RFID. Exiting.")
        return


    cv2.namedWindow(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN)
    cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    
    cap = None
    active_tag_id = None # Stores the INTEGER ID of the currently active tag video
    current_video_path_playing = ""
    target_video_path = idle_video_full_path
    target_is_idle = True

    # Initialize with placeholder values, will be updated by first video loaded
    fps, frame_width, frame_height = 30, 1920, 1080 
    black_frame = np.zeros((frame_height, frame_width, 3), dtype=np.uint8)
    fade_in_frames = int(FADE_DURATION_SECONDS * fps)
    current_playback_frame_count = 0

    running = True
    try:
        while running:
            # --- 1. Process RFID Events ---
            if rfid_active: # Only try to get from queue if RFID thread is supposed to be active
                try:
                    event_type, event_data_int = rfid_event_queue.get_nowait() # event_data_int is card.value (integer)
                    if event_type == "TAG_INSERTED":
                        new_tag_id_int = event_data_int 
                        logger.debug(f"Main: Received TAG_INSERTED event for tag ID(int): {new_tag_id_int}")

                        if new_tag_id_int != active_tag_id: # Check against current active integer tag ID
                            if new_tag_id_int in valid_tag_video_map:
                                logger.info(f"Switching to video for tag ID(int): {new_tag_id_int} -> {valid_tag_video_map[new_tag_id_int]}")
                                target_video_path = valid_tag_video_map[new_tag_id_int]
                                target_is_idle = False
                            else:
                                logger.info(f"Tag ID(int) {new_tag_id_int} detected but not in map or video file missing.")
                        # If same tag is re-scanned while its video is playing, do nothing.
                    elif event_type == "TAG_INVALID":
                        logger.warning(f"Invalid tag data received for ID (approx int): {event_data_int}")
                except queue.Empty:
                    pass # No new RFID events

            # --- 2. Manage Video Transitions & Loading ---
            if current_video_path_playing != target_video_path or not cap or not cap.isOpened():
                if cap:
                    cap.release() # Release previous video capture
                
                logger.info(f"Loading video: {target_video_path}")
                cap = cv2.VideoCapture(target_video_path)
                
                # global previous_video_was_content # Removed: Declared at the start of main()

                if not cap.isOpened():
                    logger.error(f"Failed to open video: {target_video_path}. Reverting to idle.")
                    # If reverting to idle due to error, previous was likely content or attempted content
                    if current_video_path_playing != idle_video_full_path and current_video_path_playing != "":
                         previous_video_was_content = True
                    else: # e.g. idle video itself failed on first load or after looping
                         previous_video_was_content = False
                    target_video_path = idle_video_full_path # Fallback to idle
                    target_is_idle = True
                    active_tag_id = None
                    current_video_path_playing = "" # Force reload attempt of idle
                    time.sleep(1) # Avoid rapid error loops if idle video also fails
                    continue
                
                # Successfully opened video, now get properties and decide on fade
                new_fps, new_width, new_height, new_total_frames = get_video_properties(cap)
                
                # Default fade_in_frames based on new_fps, or current fps if new_fps is invalid
                # This ensures fade_in_frames is always defined before use
                effective_fps_for_fade = new_fps if new_fps > 0 else fps
                fade_in_frames = int(FADE_DURATION_SECONDS * effective_fps_for_fade)

                is_loading_idle_video = (target_video_path == idle_video_full_path)
                
                if is_loading_idle_video:
                    if previous_video_was_content:
                        logger.info("Transitioning from content to idle: Will fade in idle video.")
                        current_playback_frame_count = 0 # Reset for fade-in
                    else:
                        logger.info("Loading idle video (not from content video): Starting immediately.")
                        current_playback_frame_count = fade_in_frames + 1 # Bypass fade-in
                    previous_video_was_content = False # Reset flag after deciding for idle video
                else: # It's a content video
                    logger.info("Loading content video: Will fade in.")
                    current_playback_frame_count = 0 # Content videos always fade in
                    previous_video_was_content = True # Mark that content video is now active
                
                current_video_path_playing = target_video_path
                
                if target_is_idle: # This should align with is_loading_idle_video
                    active_tag_id = None
                    if not is_loading_idle_video: # Should not happen if logic is correct
                         logger.warning("State inconsistency: target_is_idle but not loading idle video path.")
                    stop_soundtrack_immediately()
                else: # Content video
                    found_tag_id = None
                    for int_id, path_val in valid_tag_video_map.items():
                        if path_val == target_video_path:
                            found_tag_id = int_id
                            break
                    active_tag_id = found_tag_id

                if new_fps > 0 and new_width > 0 and new_height > 0:
                    if fps != new_fps or frame_width != new_width or frame_height != new_height:
                        fps, frame_width, frame_height = new_fps, new_width, new_height
                        black_frame = np.zeros((frame_height, frame_width, 3), dtype=np.uint8)
                        logger.info(f"Video properties updated: {frame_width}x{frame_height} @ {fps:.2f} FPS, Total Frames: {new_total_frames}")
                    # fade_in_frames was already calculated above using effective_fps_for_fade
                    
                    if not target_is_idle: # Content video
                        start_soundtrack_for_video(new_total_frames, new_fps)
                else: # Failed to get valid video properties
                    logger.error(f"Failed to get valid properties for {target_video_path}. FPS: {new_fps}")
                    stop_soundtrack_immediately()
                    # If loading a content video failed, ensure previous_video_was_content is true
                    # so that the subsequent automatic switch to idle video fades in.
                    if not is_loading_idle_video: # if it was an attempt to load a content video
                        previous_video_was_content = True

            # --- 3. Read and Display Frame ---
            if cap and cap.isOpened():
                ret, frame = cap.read()

                if not ret: # End of video or read error
                    logger.info(f"Video ended or read error: {current_video_path_playing}")
                    cap.release()
                    stop_soundtrack_immediately()
                    # global previous_video_was_content # Removed: Declared at the start of main()

                    # Determine if the video that JUST ENDED was a content video
                    if active_tag_id is not None: # This implies it was a content video
                        previous_video_was_content = True
                        logger.debug("Content video just ended, setting previous_video_was_content=True for next idle load.")
                    else: # Idle video just ended (looped)
                        previous_video_was_content = False
                        logger.debug("Idle video just ended/looped, setting previous_video_was_content=False.")
                    
                    target_video_path = idle_video_full_path
                    target_is_idle = True
                    active_tag_id = None
                    continue

                current_playback_frame_count += 1
                
                if not target_is_idle and fps > 0: # Only manage volume if it's a content video and fps is valid
                    video_time_elapsed_sec = current_playback_frame_count / fps
                    manage_soundtrack_volume(video_time_elapsed_sec, FADE_DURATION_SECONDS)

                display_frame = frame.copy()

                # Video Fade-in logic
                if current_playback_frame_count <= fade_in_frames:
                    alpha = min(current_playback_frame_count / fade_in_frames, 1.0)
                    # Ensure black_frame matches current frame dimensions before blending
                    if black_frame.shape[0] != frame.shape[0] or black_frame.shape[1] != frame.shape[1]:
                         black_frame = np.zeros_like(frame) # Make it match current frame if somehow mismatched
                    display_frame = cv2.addWeighted(frame, alpha, black_frame, 1 - alpha, 0)
                
                cv2.imshow(WINDOW_NAME, display_frame)

                # --- 4. Handle Input & Delay ---
                key = cv2.waitKey(max(1, int(1000 / fps))) & 0xFF # Ensure waitKey delay is at least 1ms
                if key == ord('q') or key == 27: # 'q' or ESC
                    logger.info("Exit key pressed.")
                    running = False
            else:
                # cap is not opened, likely waiting for it to load or in an error state after failing to load idle
                logger.debug("Main loop: cap not ready, waiting...")
                cv2.waitKey(100) # Wait 100ms to prevent tight loop

    except KeyboardInterrupt:
        logger.info("Ctrl+C pressed, exiting.")
    except Exception as e: # Catch any other unexpected errors in the main loop
        logger.error(f"An unexpected error occurred in the main loop: {e}", exc_info=True)
    finally:
        running = False # Ensure loop terminates
        if rfid_active and rfid_thread and rfid_thread.is_alive():
            logger.info("Stopping RFID thread...")
            stop_rfid_thread.set() 
            rfid_thread.join(timeout=2.0) # Wait for RFID thread to finish
            if rfid_thread.is_alive():
                logger.warning("RFID thread did not stop in time.")
        
        if cap:
            cap.release()
        
        stop_soundtrack_immediately() # Ensure sound is stopped on exit
        if pygame_mixer_initialized:
            logger.info("Stopping Pygame mixer.")
            pygame.mixer.quit()

        cv2.destroyAllWindows()
        logger.info("Resources released. Kiosk application stopped.")

# --- Script Entry Point ---
if __name__ == "__main__":
    # Initial checks before starting main logic
    if not RDM6300_IMPORTED and not ALLOW_NO_RFID:
        logger.critical("RFID library (rdm6300) failed to import and AllowNoRfid is False in config. Exiting.")
        exit(1)
    
    if not os.path.isdir(MEDIA_FOLDER): 
        logger.critical(f"Media folder '{MEDIA_FOLDER}' (from config or default) not found. Please create it and add videos. Exiting.")
        exit(1)
    
    main()
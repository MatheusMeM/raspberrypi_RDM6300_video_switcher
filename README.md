# Interactive RFID-Triggered Video Kiosk

## 1. Objective

This project implements an interactive kiosk system where video playback, accompanied by a synchronized soundtrack for content videos, is controlled by RFID tag detection. The primary objective is to provide a seamless user experience, displaying an idle/attract-loop video by default (without a soundtrack), and switching to specific content videos with an accompanying one-shot soundtrack when a corresponding RFID tag is presented. The system is designed for robustness, ease of configuration, and a polished user experience, suitable for embedded applications.

## 2. System Overview

The system operates on a host platform (e.g., Raspberry Pi) connected to an RDM6300 RFID reader and a display. The core application, written in Python, continuously monitors the RFID reader. Upon detection of a valid, mapped RFID tag, the application transitions from the silent idle video to the tag-specific content video.

**Video & Audio Playback:**
*   **Content Videos:** Play with a dedicated soundtrack (e.g., `soundtrack.mp3`) that plays once per video. Both video and audio fade in synchronously. The audio is engineered to fade out and reach zero volume precisely when the content video finishes.
*   **Idle Video:** Plays silently. It starts immediately without a fade-in when the application first launches or when the idle video loops. It only performs a fade-in when transitioning from a content video back to the idle state.
*   **Transitions:** Video transitions are managed using OpenCV, while audio playback and fade effects are handled by Pygame Mixer.

All operational parameters, video mappings, hardware configurations, and the soundtrack filename are externalized to a [`config.ini`](config.ini:1) file for straightforward customization.

## 3. Features

*   RFID-triggered video playback.
*   Configurable mapping of RFID tags to specific video files.
*   Default idle video when no tag is active.
*   Synchronized one-shot soundtrack playback for content videos.
*   Configurable soundtrack file.
*   Smooth fade-in transitions for content videos and their soundtracks.
*   Precisely timed fade-out for soundtracks to end with their content video.
*   Conditional fade-in for the idle video (only when transitioning from a content video).
*   Fullscreen video display.
*   Configuration via an external `config.ini` file.
*   Robust logging for diagnostics.
*   Support for running without an RFID reader for testing video playback (via `AllowNoRfid` config).

## 4. Hardware Requirements

*   **Host Platform:** A single-board computer (SBC) capable of running Python, OpenCV, and Pygame. A Raspberry Pi (3B+ or newer recommended) is a typical choice.
*   **RFID Reader:** RDM6300 125kHz EM4100 RFID card reader module.
*   **RFID Tags:** Compatible 125kHz EM4100 RFID tags/cards.
*   **Display:** Any monitor/screen compatible with the host platform's video output (e.g., HDMI display for Raspberry Pi).
*   **Audio Output:** Speakers or headphones connected to the host platform's audio output.
*   **Power Supply:** Adequate power supply for the host platform and connected peripherals.

## 5. Pinout (RDM6300 to Host Platform - Example: Raspberry Pi)

The RDM6300 module communicates via a serial (UART) interface.

| RDM6300 Pin | Raspberry Pi Pin (GPIO) | Function        | Notes                                   |
| :---------- | :---------------------- | :-------------- | :-------------------------------------- |
| VCC         | 5V Pin                  | Power           | 5V Supply                               |
| GND         | GND Pin                 | Ground          | Common Ground                           |
| TX          | GPIO15 (RXD0)           | Data Transmit   | RDM6300 TX to Pi RX                     |
| RX          | GPIO14 (TXD0)           | Data Receive    | RDM6300 RX to Pi TX (Often not needed for basic reading) |
| ANT1, ANT2  | -                       | Antenna Coil    | Connect to the RFID antenna coil        |

**Note:** Ensure the Raspberry Pi's serial port (`/dev/serial0` or `/dev/ttyS0` typically) is enabled and configured correctly (e.g., serial console disabled if using primary UART). The `RFID_SERIAL_PORT` in [`config.ini`](config.ini:1) must match the connected port.

## 6. Software Dependencies & Setup

The system relies on several Python libraries.

**Prerequisites:**
*   Python 3.x
*   `pip` (Python package installer)

**Installation:**
1.  Clone this repository to your host platform.
2.  Navigate to the project directory.
3.  Install the required Python libraries using the [`requirements.txt`](requirements.txt:1) file:
    ```bash
    pip install -r requirements.txt
    ```

**Key Libraries:**
*   **OpenCV (`opencv-python`):** For video decoding, processing, and display.
*   **Pygame:** For audio playback and management (`pygame.mixer`).
*   **pyserial:** For serial communication with the RDM6300 RFID reader.
*   **NumPy:** Dependency for OpenCV, used for numerical operations.
*   **configparser:** For reading the [`config.ini`](config.ini:1) file (standard library).
*   **rdm6300 (local library):** Custom library located in the `rdm6300/` directory for interfacing with the RDM6300 reader. This handles card reading, validation, and event generation.

## 7. Project Structure

```
.
├── config.ini             # Main configuration file
├── main.py                # Core application logic
├── requirements.txt       # Python dependencies
├── media/                 # Directory for video and audio files
│   ├── idle_video.mp4     # Example idle video
│   ├── content_video1.mp4 # Example content video for a tag
│   ├── soundtrack.mp3     # Example soundtrack file
│   └── ...                # Other media files
├── rdm6300/               # RDM6300 reader library
│   ├── __init__.py
│   ├── reader.py          # Base reader logic
│   └── test_reader.py     # Test script for the reader
├── tests/                 # Directory for various test scripts (if any)
│   └── ...
├── README.md              # This file
└── log.txt                # Application log file (generated at runtime)
```
*(Ensure your actual media filenames in `media/` match those specified in `config.ini`)*

## 8. Configuration (`config.ini`)

The [`config.ini`](config.ini:1) file centralizes all tunable parameters. Create this file in the root of the project directory.

*   **[GeneralSettings]**
    *   `MediaFolder`: Path to the directory containing video and audio files (e.g., `media/`).
    *   `SerialPort`: The serial port connected to the RDM6300 reader (e.g., `/dev/serial0` on Raspberry Pi, `COM3` on Windows).
    *   `LogLevel`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    *   `FadeDurationSeconds`: Duration (in seconds) of the fade-in effect for videos and soundtracks, and the basis for soundtrack fade-out duration.
    *   `RfidHeartbeatInterval`: Heartbeat interval (in seconds) for the RDM6300 reader communication.
    *   `WindowName`: Title of the OpenCV display window.
    *   `AllowNoRfid`: If `True`, allows the application to run (playing idle video) even if the RFID reader fails to initialize. Defaults to `False`.
    *   `SoundtrackFile`: Filename of the MP3 soundtrack located in the `MediaFolder` to be played with content videos (e.g., `soundtrack.mp3`).

*   **[VideoMapping]**
    *   `IDLE_VIDEO`: Filename of the video to play when no tag is active (e.g., `idle_video.mp4`). This video plays silently.
    *   `<TAG_ID_HEX>`: Filename of the video associated with a specific RFID tag. The tag ID must be provided in **hexadecimal format** (e.g., `0A1B2C3D4E = content_video1.mp4`). These videos will play with the configured soundtrack.

**Example `config.ini`:**
```ini
[GeneralSettings]
MediaFolder = media/
SerialPort = /dev/serial0
LogLevel = INFO
FadeDurationSeconds = 1.5
RfidHeartbeatInterval = 0.5
WindowName = Interactive Kiosk Display
AllowNoRfid = False
SoundtrackFile = soundtrack.mp3

[VideoMapping]
IDLE_VIDEO = idle_video.mp4
0102030405 = content_video1.mp4
AABBCCDDEE = content_video2.mp4
```

## 9. Operational Strategy

1.  **Initialization:**
    *   The [`main.py`](main.py:1) script starts by loading settings from [`config.ini`](config.ini:1), including media paths, serial port, fade durations, and the `SoundtrackFile`.
    *   Logging is configured based on the `LogLevel`.
    *   Pygame Mixer is initialized, and the specified `SoundtrackFile` is loaded. If the soundtrack cannot be loaded, an error is logged, and the application continues with video-only playback for content.
    *   The RDM6300 RFID reader interface is initialized in a separate thread. If `AllowNoRfid` is `False` and the reader cannot be initialized, the application will exit.
2.  **RFID Detection Thread:**
    *   The `RfidVideoHandler` class continuously polls the serial port for data from the RDM6300.
    *   Upon receiving valid card data, it places a `("TAG_INSERTED", tag_id_int)` event onto a shared queue.
3.  **Main Video & Audio Loop:**
    *   The main loop checks the event queue for RFID events.
    *   If a `TAG_INSERTED` event is detected for a new tag, the `target_video_path` is updated to the corresponding content video.
    *   **Video & Audio Transition Logic:**
        *   When loading a **new content video**:
            *   Any currently playing soundtrack is stopped.
            *   The new content video is loaded via OpenCV.
            *   The configured soundtrack (e.g., `soundtrack.mp3`) starts playing once (no loop).
            *   Both the video and its soundtrack fade in synchronously over `FadeDurationSeconds`.
            *   The system calculates when the soundtrack needs to start fading out to reach zero volume precisely as the video ends.
        *   When loading the **idle video**:
            *   Any currently playing soundtrack is stopped immediately.
            *   The idle video is loaded.
            *   **Conditional Fade-In for Idle Video:**
                *   If transitioning from a content video, the idle video fades in.
                *   If the application is starting or the idle video is looping, it starts immediately without a fade.
    *   **Playback Management:**
        *   During content video playback, `manage_soundtrack_volume` is called continuously to adjust the soundtrack's volume for fade-in and the precisely timed fade-out.
        *   Video frames are read and displayed in a fullscreen OpenCV window.
    *   **End of Video / Idle State:**
        *   When a content video finishes, its soundtrack will have already faded out. The system transitions to the idle video (which will fade in).
        *   When the idle video finishes, it loops back to itself (starting immediately, no fade).
        *   If any video fails to load, the system attempts to revert to the idle video (which will fade in if the failed video was content).
    *   The loop continues until 'q' or ESC is pressed.
4.  **Cleanup:**
    *   Upon exit, the RFID thread is signaled to stop, any playing soundtrack is stopped, Pygame Mixer is quit, the video capture is released, and OpenCV windows are destroyed.

## 10. Running the Application

1.  Ensure all hardware is connected correctly.
2.  Verify your [`config.ini`](config.ini:1) is set up with correct paths, serial port, and media filenames.
3.  Place your video files and the soundtrack MP3 in the `MediaFolder` specified in `config.ini`.
4.  Run the main script from the project's root directory:
    ```bash
    python main.py
    ```
5.  Press 'q' or 'ESC' to exit the application.

## 11. Logging

The application maintains a log file ([`log.txt`](log.txt:1)) in the project's root directory. The verbosity of logging is controlled by the `LogLevel` setting in [`config.ini`](config.ini:1). This log is crucial for diagnostics and troubleshooting.

## 12. Potential Enhancements & Considerations

*   **Error Resilience:** More sophisticated error handling for video file corruption or unexpected hardware disconnects during playback.
*   **Dynamic Configuration Reload:** Ability to reload `config.ini` without restarting the application (e.g., for updating video mappings on the fly).
*   **Remote Management/Monitoring:** Adding a simple web interface or network API for status checks, basic control, or log viewing.
*   **Advanced Audio Features:**
    *   Support for different soundtracks per content video.
    *   Configurable target volume for the soundtrack.
*   **Alternative Media Backends:** For more complex playback requirements (e.g., playlists, different video/audio formats not well supported by OpenCV/Pygame), libraries like `python-vlc` or GStreamer could be explored. The `tests/vlc_test.py` suggests `python-vlc` was considered.
*   **Hardware Watchdog:** For long-running kiosk applications, implementing a hardware watchdog can improve system reliability on platforms like Raspberry Pi.
*   **GUI for Configuration:** A simple graphical user interface for managing tag-to-video mappings.

## 13. Troubleshooting

*   **No video / "Failed to open video" errors:**
    *   Check `MediaFolder` path in `config.ini`.
    *   Ensure video filenames in `config.ini` (for `IDLE_VIDEO` and tag mappings) exactly match the files in the media folder.
    *   Verify video files are in a format OpenCV can read (e.g., .mp4 with H.264 codec).
*   **RFID reader not working:**
    *   Check `SerialPort` in `config.ini`.
    *   Ensure the RDM6300 is correctly wired and powered.
    *   On Linux, check serial port permissions and ensure the serial console is not conflicting if using `/dev/serial0`.
    *   Set `LogLevel` to `DEBUG` in `config.ini` for more detailed RFID logs.
*   **No audio / Soundtrack issues:**
    *   Check `SoundtrackFile` in `config.ini` and ensure the file exists in `MediaFolder`.
    *   Verify the MP3 file is not corrupted.
    *   Ensure audio output is working on the host system and speakers are connected/unmuted.
    *   Check `log.txt` for Pygame Mixer initialization errors or soundtrack loading errors.
*   **Application exits immediately:** Check `log.txt` for critical errors, often related to missing libraries, incorrect configurations, or hardware initialization failures.

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs, feature requests, or improvements.

---

*This README provides a comprehensive guide to setting up, configuring, and running the Interactive RFID-Triggered Video Kiosk.*
import time
import argparse
import sys
import math
import threading
import queue
from src import screen
from src import fft
from src import animation_utils
from src import audio_source
from src import tcp_server
from collections import deque

# Passed in the command line arguments
ANIMATION_FRAMERATE = None
FFT_SAMPLING_RATE = None

fft_queue = queue.Queue()
stop_event = threading.Event()
pixels_queue = deque()
args = None

last_fft = 0
last_levels = None


def audio_worker():
    fft.init(fft_queue, not args.disable_emma, args.emma_alpha)

    source = None
    source_type = None
    
    if args.file:
        source = args.file
        source_type = 'wav'
    elif args.input_id:
        source = args.input_id
        source_type = 'stream'
        
    if source is None:
        print("No audio source provided")
        raise RuntimeError("No audio source provided")

    # Open the audio source
    samples_count, framerate, sample_width, channels, wav_generator = audio_source.open_audio(source, source_type, FFT_SAMPLING_RATE)
    print("Audio framerate (hz):", framerate)
    
    if channels > 1:
        print(f"Audio channels: {channels}. Audio will be converted to mono")
    else:
        print("Mono audio")
        

    print("Samples count (bytes):", samples_count)
    print("Sample width (bits):", sample_width * 8)
    
    print("Started audio worker")
    # Read data
    for data in wav_generator:
        fft.analyze(data, samples_count, framerate, sample_width, channels)
        if stop_event.is_set():
            wav_generator.close()
            break
        
def interpolate(a, b, t):
    return (1 - t) * a + t * b
        
def main(frames_queue = None):
    global last_fft, last_levels

    values = None
    
    try:
        values = fft_queue.get_nowait()
        
        if not args.disable_server:
            tcp_server.data_queue.put(values)
    except queue.Empty:
        return
    except:
        print("No more audio. Exiting!")
        sys.exit(0)
        
    if args.disable_animation:
        time.sleep(1 / FFT_SAMPLING_RATE)
        return

    if last_levels is None:
        last_levels = [-1] * len(values)
    
    current_levels = []
    for max_amp in values:
        current_levels.append(animation_utils.get_level(max_amp))
        
    num_frames = ANIMATION_FRAMERATE // FFT_SAMPLING_RATE
    
    if num_frames == 1:
        pixels = []
        for max_amp in values:
            level = animation_utils.get_level(max_amp)
            frame = animation_utils.level_to_pixels(level)
            pixels.append(frame)
            
        frames_queue.appendleft(pixels) 
    else: 
        frames = []
        for i in range(num_frames):
            t = i / (num_frames - 1)
            interpolated_frame = [interpolate(last_levels[i], current_levels[i], t) for i in range(len(last_levels))] 
            frames.append(interpolated_frame)
            
        last_levels = current_levels
            
        for frame in frames:
            pixels = []
            for level in frame:
                pixels.append(animation_utils.level_to_pixels(round(level)))
                
            frames_queue.appendleft(pixels)
        
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='''
Analyze audio and stream FFT results over TCP while displaying an animation on the screen.
Provide either --input-id or --file to specify the audio source. If both are provided --file will be used.
''')
    parser.add_argument('--sample-rate', default=20, type=int, help='FFT sampling rate. Defaults to 20 (FFT analysis every 20ms)')
    parser.add_argument('--host', default='0.0.0.0', type=str, help='The host to bind the TCP server. Defaults to "0.0.0.0"')
    parser.add_argument('--port', default=12345, type=int, help='The port to bind the TCP server. Defaults to 12345')
    parser.add_argument('--file', type=str, help='Path to the audio wav file')
    parser.add_argument('--input-id', type=str, help='The id of the input device to capture. Use --list-inputs to list all available input devices')
    parser.add_argument('--list-inputs', action='store_true', help='List all available input devices')
    parser.add_argument('--fps', type=int, default=60, help="Animation framerate in frames per second. Defaults to 60")
    parser.add_argument('--emma-alpha', type=float, default=0.5, help="The alpha value for the exponential moving average. Defaults to 0.5")
    parser.add_argument('--disable-server', action='store_true', help="Disable streaming FFT results over TCP. By default, the server is enabled")
    parser.add_argument('--disable-animation', action='store_true', help="Disable the built-in animation, run only the TCP server")
    parser.add_argument('--disable-emma', action='store_true', help="Disable the exponential moving average for the FFT results")
    
    if len(sys.argv) == 1:
        parser.print_help()
        exit(1)
        
    args = parser.parse_args()
    
    if args.list_inputs:
        audio_source.list_audio_input_devices()
        exit(0)

    if not (args.input_id or args.file):
        parser.error("Provide either --input-id or --file")
    
    
    if args.sample_rate < 1:
        parser.error("Sample rate must be greater than 0")
        
    if args.fps < args.sample_rate:
        parser.error("Animation framerate must be greater than or equal to the FFT sampling rate")

    FFT_SAMPLING_RATE = args.sample_rate
    ANIMATION_FRAMERATE = args.fps

    print(f'FFT sampling rate (rate/s): {FFT_SAMPLING_RATE}')
    if not args.disable_animation:
        print(f'Animation framerate (fps): {ANIMATION_FRAMERATE}')

    thread = threading.Thread(target=audio_worker)
    thread.start()
    
    if not args.disable_server:
        tcp_server.start(FFT_SAMPLING_RATE, len(fft.frequency_bands), args.host, args.port)
        
    if args.disable_animation and args.disable_server:
        parser.error("Nothing to do if both the TCP server and the animations are disabled")
        
    try:
        if args.disable_animation:
            while True:
                main()
        else:
            screen.init(ANIMATION_FRAMERATE)
            screen.mainloop(main)
    except KeyboardInterrupt:
        exit(0)
    finally:
        stop_event.set()
        if not args.disable_server:
            tcp_server.stop()

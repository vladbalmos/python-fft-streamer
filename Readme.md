# FFT Audio Analysis and Streaming

This is a Python demo used to understand the concepts of FFT (Fast Fourier Transform), animation, and how they all tie together. The script performs FFT analysis on either WAV files or captured audio input, converts the FFT results to amplitudes, and streams the data over TCP. The application creates a TCP server that listens for clients and transmits the data to each client. Additionally, it includes a demo animation that changes according to the analyzed audio data.

The server feature can be used to make custom IoT RGB lights react to sound / music.

## Features

- Perform FFT analysis on WAV files or live audio input
- Stream FFT analysis results over TCP to multiple clients
- Real-time demo animation that responds to audio data

## Dependencies

- `pygame`
- `pyaudio`
- `numpy`

## Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/vladbalmos/python-fft-streamer.git
    cd python-fft-streamer
    ```

2. Install the dependencies:
    ```sh
    pip install --user -r requirements.txt
    ```

## Usage

To see all available options, run:
```sh
python main.py
```

## Example commands

- To perform FFT analysis on a WAV file and stream the data:
    ```sh
    python main.py --file input.wav
    ```
    
- To capture live audio input:
    ```sh
    python main.py --list-inputs
    python main.pu --input-id [id of input source from the output of the previous command]
    ```
    
- By default the TCP server is bound to 0.0.0.0:12345, to change that:
    ```sh
    python main.py --host 127.0.0.1 --port 1024 --file input.wav
    ```
    
- To change the FFT sample rate & animation framerate:
    ```sh
    python main.py --sample-rate 20 --animation-fps 30
    ```
    

## Demo Animation

The demo animation visualizes the FFT analysis results in real-time. It provides a visual representation of the audio data, showing how the amplitudes change with the audio input.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgments

This project was inspired by the need to understand the concepts of FFT, animation, and their integration. Special thanks to the authors of the `pygame`, `pyaudio`, and `numpy` libraries for their invaluable tools.

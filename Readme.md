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
    
## FFT stream

When a client connects it will first receive a two byte configuration message where the first byte contains the FFT sample rate and the second is the number of frequency bands for each subsequent FFT analysis. Ex:

Configuration message (16 bit) |  Sample rate | Frequencies count |
-------------------------------|--------------|-------------------|
            0x140xa            |     20       |       10          |

After the config message the client will receive the amplitudes in dBFS encoded as a 32 bit float bytearray having a length defined by the frequency band count received in the configuration message. The frequency of each amplitudes set is defined by the sample rate value from the first configuration message. Ex:

    Given a sample rate of 20 samples/s and a frequency count of 10, a client will receive 40 bytes of data every 50ms. Each amplitude value corresponds to one of the frequency band defined in `src/fft.py`. After each set of amplitudes the client must respond back with 1 byte of arbitrary data.
    
See the `fft_client.py` as an example implementation.
        

## Demo Animation

The demo animation visualizes the FFT analysis results in real-time. It provides a visual representation of the audio data, showing how the amplitudes change with the audio input.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgments

This project was inspired by the need to understand the concepts of FFT, animation, and their integration. Special thanks to the authors of the `pygame`, `pyaudio`, and `numpy` libraries for their invaluable tools.

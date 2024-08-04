import pprint
import sys
import time
import struct
import asyncio
import argparse

CONFIG_MSG_SIZE = 2

class FFTClient:

    def __init__(self, reader, writer):
        self._reader = reader
        self._writer = writer

        self.last_read_duration_ms = 0
        self.last_sample_time_ms = 0
        self.last_sample_tstamp = 0

        self.config = {}
        
    async def _acknowledge(self):
        '''
        Acknowledge the receipt of data
        Send a single byte back so that the ACK packet is sent as quickly as possible
        to prevent delaying the next data message
        '''
        self._writer.write(b'1')    
        await self._writer.drain()

    async def init_config(self):
        data = await self._read_data(CONFIG_MSG_SIZE)
        await self._acknowledge()
        
        sample_rate = struct.unpack("!b", data[0:1])[0]
        frequency_bands_count = struct.unpack("!b", data[1:2])[0]

        frames_count = 1
        buffer_size = frames_count * frequency_bands_count * struct.calcsize('!f')

        config = {}
        config['samplerate'] = sample_rate # FFT sample rate in samples/s
        config['frames_count'] = frames_count # Hardcoded to 1
        config['frequency_bands_count'] = frequency_bands_count # Number of frequency bands. For the range see src/fft.py
        config['buffer_size'] = buffer_size # The size of each subsequent data message
        config['period_ms'] = 1000 // sample_rate # The period of each data message in ms
        config['fft_unpack_fmt'] = f"!{frequency_bands_count}f" # The format for unpacking the binary data 
        config['buffer_length_ms'] = frames_count * config['period_ms'] # The length of each audio sampled analized in ms
        
        self.config = config
        
    async def _read_data(self, data_len):
        now = time.time()
        data = await self._reader.readexactly(data_len)
        self.last_read_duration_ms = (time.time() - now) * 1000
        return data
        
    async def read_fft_data(self):
        now = time.time()

        if self.last_sample_tstamp > 0:
            self.last_sample_time_ms = (now - self.last_sample_tstamp) * 1000
            
        self.last_sample_tstamp = now
        fft_data = None

        # Read the raw data from the server
        data = await asyncio.wait_for(self._read_data(self.config['buffer_size']), timeout=0.05)
        await self._acknowledge()
        
        # Convert the binary data to a list of floats representing the amplitudes
        fft_data = struct.unpack(self.config["fft_unpack_fmt"], data)

        self.last_read_duration_ms = (time.time() - now) * 1000
        return fft_data

    async def close(self):
        try:
            self.config = {}
            self._reader = None
            self._writer.close()
            await self._writer.wait_closed()
            self._writer = None
        except:
            pass


async def main(args):
    # Connect to the FFT server
    try:
        reader, writer = await asyncio.open_connection(args.host, args.port)
    except ConnectionError as e:
        print(e)
        return

    client = FFTClient(reader, writer)
    
    try:
        # Read the config from the server
        await asyncio.wait_for(client.init_config(), timeout=1)
        print('Received config from server:\n', pprint.pformat(client.config))
    except (ConnectionError, asyncio.TimeoutError) as e:
        print(e)
        return
    
    # If the client is reading data faster than this,
    # it means it has fallen behind and we should skip some frames
    skip_frames_threshold = client.config['period_ms'] // 5
    last_output_ms = 0
    
    receive_periods = []
    received_samples = 0
    
    now = time.time()

    # Start receiving samples
    while True:
        now = time.time()
        
        if client.last_sample_tstamp > 0:
            receive_periods.append(client.last_sample_time_ms)

        if ((time.time() - last_output_ms) * 1000) >= 1000 and len(receive_periods):
            print(f"Average receive period: {sum(receive_periods) / len(receive_periods):.2f}ms. Received samples: {received_samples}")
            receive_periods = []
            last_output_ms = now

        # Read the data from server
        try:
            amplitudes = await client.read_fft_data()
            received_samples += 1
        except asyncio.TimeoutError:
            continue
        except Exception as e:
            print(e)
            break
        
        if skip_frames_threshold > 0 and (client.last_sample_time_ms < skip_frames_threshold):
            print(f"Client read to data too fast, skipping frames. Read time {client.last_sample_time_ms}ms. Threshold {skip_frames_threshold}ms")
            continue
        
        # Do something with the amplitudes
        # print(amplitudes)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='''
FFT client implementation
''')
    parser.add_argument('--host', default='127.0.0.1', type=str, help='FFT server host. Defaults to "127.0.0.1"')
    parser.add_argument('--port', default=12345, type=int, help='FFT server port. Defaults to 12345')

    args = parser.parse_args()
    
    try:
        asyncio.run(main(args))
    except KeyboardInterrupt:
        exit(0)
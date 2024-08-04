import time
import threading
import asyncio
import queue
import struct

data_queue = queue.Queue()
stop_event = threading.Event()

_asyncio_loop = None
_thread = None
_server = None
_clients = []
_sample_rate = None
_frequency_bands_count = None

async def disconnect_clients(clients):
    for client in clients:
        try:
            client[1].close()
            await asyncio.wait_for(client[1].wait_closed(), timeout=0.005)
        except:
            pass
        _clients.remove(client)
        
async def discard_client_responses():
    '''We don't care about client responses. The only reason for expecting them
    is to make sure the client doesn't delay sending the ACK packet after receiving data
    which in turn would delay the next FFT data packet'''
    while True:
        for client in _clients:
            try:
                now = time.time()
                await asyncio.wait_for(client[0].readexactly(1), timeout=0.01)
                read_duration_ms = (time.time() - now) * 1000
                if read_duration_ms > 1:
                    print('Client response read duration:', read_duration_ms)
            except asyncio.TimeoutError:
                print("Caught timeout error while waiting for client response")
            except Exception as e:
                print("Client disconnected", e)
                await disconnect_clients([client])
        await asyncio.sleep(1)

async def broadcast_fft_data():
    try:
        last_ms = 0
        last_output_ms = time.time()
        sent_samples = 0
        while True:
            try:
                data = data_queue.get(block=True, timeout=0.001)
            except queue.Empty:
                data = None
                
            if data is None:
                await asyncio.sleep(0.001)
                continue

            if len(_clients) > 0:
                sent_samples += 1

            data = struct.pack(f'!{len(data)}f', *data.tolist())
            disconnected_clients = []

            for client in _clients:
                try:
                    client[1].write(data)
                    await client[1].drain()

                    now = time.time()
                    if last_ms > 0:
                        diff = (now - last_ms) * 1000
                        
                        if time.time() - last_output_ms >= 1:
                            print(f'Sending interval: {diff}ms. Sent FFT results: {sent_samples}')
                            last_output_ms = now

                    last_ms = now
                except asyncio.TimeoutError as e:
                    print("Timeout error", e)
                    continue
                except Exception as e:
                    disconnected_clients.append(client)
                    print("Client disconnected", e)
                    
            # remove any disconnected clients
            if len(disconnected_clients):
                await disconnect_clients(disconnected_clients)

    except asyncio.CancelledError:
        await disconnect_clients(_clients)

async def handle_client(reader, writer):
    print(_sample_rate, _frequency_bands_count)
    try:
        writer.write(struct.pack('!bb', _sample_rate, _frequency_bands_count))
        await writer.drain()
    except:
        print("Error while sending config to client")
        return

    try:
        await asyncio.wait_for(reader.readexactly(1), timeout=1)
    except asyncio.TimeoutError:
        print("Timeout while waiting for client response after connection")
        return

    print("Client connected")
    _clients.append([reader, writer])

async def main(host, port):
    global _server
    _server = await asyncio.start_server(handle_client, host, port)
    broadcast_task = asyncio.create_task(broadcast_fft_data())
    discard_client_responses_task = asyncio.create_task(discard_client_responses())
    tasks = asyncio.gather(broadcast_task, discard_client_responses_task, _server.serve_forever())
    while True:
        if stop_event.is_set():
            tasks.cancel()
            try:
                await tasks
            except asyncio.CancelledError:
                pass
            await _server.wait_closed()
            asyncio.get_event_loop().stop()
            break
        await asyncio.sleep(1)


def run(asyncio_loop, sample_rate, frequency_bands_count, host, port):
    global _sample_rate, _frequency_bands_count
    _sample_rate = sample_rate
    _frequency_bands_count = frequency_bands_count

    asyncio.set_event_loop(asyncio_loop)
    try:
        asyncio_loop.run_until_complete(main(host, port))
    finally:
        asyncio_loop.run_until_complete(asyncio_loop.shutdown_asyncgens())
        asyncio_loop.close()
    
def start(framerate, frequency_bands_count, host, port):
    global _asyncio_loop, _thread
    loop = asyncio.new_event_loop()
    _asyncio_loop = loop
    print(f"Started TCP server on {host}:{port}")
    _thread = threading.Thread(target=run, args=(loop, framerate, frequency_bands_count, host, port))
    _thread.start()

def join():
    _thread.join()

def stop():
    stop_event.set()
    _thread.join()
    

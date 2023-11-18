import asyncio
from bleak import BleakClient
import struct

# Replace the following variables with your actual device and characteristic details
device_address = "4B:63:04:4D:61:10"  # Replace with your device's address
characteristic_uuid = 'ca73b3ba-39f6-4ab3-91ae-186dc9577d99'  # Replace with your characteristic's UUID

async def read_characteristic(address, uuid):
    async with BleakClient(address) as client:
        # Check if the device is connected
        if not client.is_connected:
            print(f"Connecting to {address}...")
            await client.connect()

        try:
            previous_data = 0
            while True:
                # Read the value from the characteristic
                received_data = await client.read_gatt_char(uuid)
                if received_data == previous_data:
                    continue
                uint16_values = struct.unpack('<' + 'H' * (len(received_data) // 2), received_data)
                print(f"Received value: {uint16_values}")
                previous_data = received_data

        except KeyboardInterrupt:
            pass

        finally:
            print("Disconnecting...")
            await client.disconnect()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(read_characteristic(device_address, characteristic_uuid))
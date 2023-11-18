import asyncio
import sys
from bleak import BleakClient
import struct

UUID = 'ca73b3ba-39f6-4ab3-91ae-186dc9577d99'

async def main(address):
  async with BleakClient(address) as client:
    if (not client.is_connected):
      raise "client not connected"

    services = await client.get_services()

    received_data = await client.read_gatt_char(UUID)
    # name = bytearray.decode(name_bytes)

    # Convert the byte array to uint16
    uint16_values = struct.unpack('<' + 'H' * (len(received_data) // 2), received_data)
    print(received_data)
    print(uint16_values)

if __name__ == "__main__":
  address = "4B:63:04:4D:61:10"
  print('address:', address)
  asyncio.run(main(address))
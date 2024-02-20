import serial
import sys
import platform
import serial.tools.list_ports


def connect_to_arduino(baudrate):
    arduino_ports = list(serial.tools.list_ports.comports())
    for p in arduino_ports:
        print(p[1])
        if "XIAO" in p[1]:
            arduino_port = p[0]
            print("Connecting to Arduino on port:", arduino_port)
            ser = serial.Serial(arduino_port, baudrate=baudrate, timeout=1)
            return ser      
    print("Couldn't find Arduino port.")
    sys.exit(1)


# Configure the serial port
port = connect_to_arduino(115200)

# Create a buffer to store the received data
buffer_size = 512
buffer = bytearray(buffer_size)

# Read and store the data in the buffer
while True:
    # Read data from the serial port
    data = port.read(buffer_size)
    
    # Store the data in the buffer
    buffer[:len(data)] = data
    
    # Process the received data
    # ...

    # Print the received data
    print(buffer[:len(data)])

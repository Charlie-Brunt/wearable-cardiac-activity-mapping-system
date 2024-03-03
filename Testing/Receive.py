import serial
import sys
import platform
import serial.tools.list_ports
import time

def connect_to_board(baudrate):
    board_ports = list(serial.tools.list_ports.comports())
    if platform.system() == "Darwin":
        for p in board_ports:
            print(p[1])
            if "XIAO" in p[1]:
                board_port = p[0]
                print("Connecting to board on port:", board_port)
                ser = serial.Serial(board_port, baudrate, timeout=1)
                return ser
        print("Couldn't find board port.")
        sys.exit(1)
    elif platform.system() == "Windows":
        for p in board_ports:
            print(p[2])
            if "2886" in p[2]:
                board_port = p[0]
                print("Connecting to board on port:", board_port)
                ser = serial.Serial(board_port, baudrate, timeout=1)
                return ser
        print("Couldn't find board port.")
        sys.exit(1)
    else:
        print("Unsupported platform")
        sys.exit(1)


# Configure the serial port
port = connect_to_board(1000000)

# Create a buffer to store the received data
buffer_size = 128
buffer = bytearray(buffer_size)

# Read and store the data in the buffer
while True:
    # Read data from the serial port, blocks until 
    data = port.read(buffer_size)
    
    # Store the data in the buffer
    # buffer[:len(data)] = data
    
    # Process the received data
    # ...
    decoded_buffer = list(data)


    # Print the received data
    print(decoded_buffer)
    time.sleep(0.01)

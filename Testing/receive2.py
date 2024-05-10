import serial
import sys
import serial.tools.list_ports
import time
import platform
import pandas as pd

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

def save_to_csv(dataframe):
    """Save data to a CSV file."""
    filename = "test.csv"
    if filename:
        dataframe.to_csv(filename, index=False)


# Configure the serial port
port = connect_to_board(115200)

dataframe = pd.DataFrame(columns=['data'])
count = 0

# Read and store the data in the buffer
while True:
    count += 1
    # Read data from the serial port, blocks until 
    data = port.readline().decode().strip()
    
    # Store the data in the buffer
    # buffer[:len(data)] = data
    
    # Process the received data
    # ...

    # Print the received data
    print(data)
    dataframe = dataframe.append({'data': data}, ignore_index=True)
    time.sleep(0.01)
    if count == 1000:
        save_to_csv(dataframe)
        break

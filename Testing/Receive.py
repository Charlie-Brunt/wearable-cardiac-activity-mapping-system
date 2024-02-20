import serial
import sys
import platform

def find_arduino_port():
    if platform.system() == 'Darwin':  # macOS
        arduino_ports = ["/dev/tty.usbserial", "/dev/ttyUSB", "/dev/ttyACM"]
    elif platform.system() == 'Windows':
        arduino_ports = ["COM" + str(i + 1) for i in range(256)]
    else:
        print("Unsupported platform")
        sys.exit(1)

    for port in arduino_ports:
        try:
            ser = serial.Serial(port)
            ser.close()
            return port
        except serial.SerialException:
            pass
    print("Couldn't find Arduino port.")
    sys.exit(1)

def connect_to_arduino():
    arduino_port = find_arduino_port()
    print("Connecting to Arduino on port:", arduino_port)
    ser = serial.Serial(arduino_port, baudrate=9600, timeout=1)
    return ser


# Configure the serial port
port = serial.Serial('COM6', 115200)  # Replace 'COM1' with the appropriate serial port

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

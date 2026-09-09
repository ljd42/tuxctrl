# Tux Controller Demo 

This demo has been showcased at the Embedded World 2026.

I wanted to learn about IMU, object orientation, sensor fusion, quaternion 
and the drawback of using Euler's angles (gimbal lock among other).

## Setup 

### Setting manifest repository

1. Using `west`, clone the tuxctrl manifest repository:
   ```
   west init -m https://github/ljd42/tuxctrl demo
   ```
2. Install the Zephyr's dependencies needed to build the firmware:
   ```
   cd demo
   west update
   ```
3. Setup virtual environment for the tuxviewer
   ```
   cd tuxctrl/host
   python -m venv .venv
   .venv/bin/activate    # activate venv, script depends on your shell
   ```
4. Install dependencies required for tuxviewer
   ```
   pip install -r requirements.txt
   ```

### Building and flashing the firmware

1. Building the firmware:
   ```
   west build -b arduino_nano_33_ble_rev2/nrf52840/sense tuxctrl/app
   ```
2. Flashing is described [here](https://docs.zephyrproject.org/latest/boards/arduino/nano_33_ble/doc/index.html#programming-and-debugging).
   You will need to install the arduino's variant of bossac. The commands below
   assumes that the bossac tools has been build from
   [source](https://github.com/arduino/BOSSA) in `$HOME/tools`
   <br/>

3. Connect your board to your host machine. Double tap reset to switch to boatloader mode.
   You should see a pulsing orange LED near the USB port.
   <br/>

4. Flash the firmware:
   ```
   west flash --bossac="$HOME/tools/BOSSA/bin/bossac"
   ```

## Running the Demo 

### Using tuxviewer

1. Start the tux viewer, assuming the board is connected to /dev/ttyACM0
   ```
   python tux.py -w 1280x1024 -v 
   ```
2. connect the board to the computer using USB.
   Use `-p` option to change the serial port.

3. Rotate the board, tux should rotate accordingly. 
   reset the board to set the initial board position.

### More on tuxviewer 
```
python tux.py -w 1024x768             # use a window of size 1024x768
python tux.py -w 1024x768 -p COM1     # use serial port COM1
python tux.py -w 1024x768 -p COM1 -v  # verbose (debug message)
python tux.py -h                      # show usage
```

## Technically...

- Use Arduino Nano 33 BLE Sense, rev2.
  Board uses a nRF52 / cortex-M4 with FPU.
- Custom board support for rev2, as only rev1 is supported in tree as of now
- Use of USB Next Gen stack with CDC/ACM ("Serial over USB")
- Use sensor APIs to read acceleration/gyro from the Bosch BMI270
- Use zscilib ("Zephyr Scientific Library") for sensor fusion algorithm
- Use AQUA (algebraic quaternion) algorithm for the orientation computation
- Convertion to Euler's angle: roll, pitch, yaw 
- Send periodically (at ~25Hz) the update value to the "USB serial" port using
CDC/ACM.

### Zephyr features 

- west application 
- custom board
- external module
- hardware abstraction (sensors)


## Further Works 

This demo is biased toward the Nano Sense 33 BLE rev2. Make the application
more generic use magnetic field.

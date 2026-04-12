#=============================================================================
# Tux Controller - Show 3D wireframe tux
#
# Inspired by tsoding 
# see: https://github.com/tsoding/formula
#
# When started in test mode (--test), arrow key can be used to change angles:
# LEFT, RIGHT: roll angle 
#   UP, DOWN : pitch 
#
# Otherwise it is assumed that the roll,pitch and yaw angles are coming from
# an board with an IMU connected to a serial line
# message structure (one measurement)
# HAMI|roll:pitch:yaw|IMHA\r\n 
#
# roll,pitch,yaw angles are given in degree 
# 
# The demo uses an arduino nano 33 sense rev2 BLE (based on a Nordic nRF52840)
# running Zephyr main / USB NEXT / CDC ACM / BMI270 driver 
# 
# The angles are estimated using the AQUA algorithm (Algebraic Quarternion)
# available in zscilib. The computed quaternion is converted to Euler angle and
# sent to this program over USB using the CDC/ACM protocol ("USB serial").
# 
# This demo illustrates some of the drawbacks of using Euler angles.
#
# (c) Loic Domaigne
#
#-----------------------------------------------------------------------------
# usage: tux.py [-h] [-p PORT] [-b BAUD] [-t] [-w foo]
#
# Tux Controller
#
# Options:
#  -h, --help            show this help message and exit
#  -p PORT, --port PORT  Serial port (default: /dev/ttyACM0)
#  -b BAUD, --baud BAUD  Baud rate (default: 115200)
#  -t, --test            Test mode, use keyboard
#  -w foo, --winsize foo
#                        window size HxW for display (default: 800x600)
# Examples: 
# python tux.py --winsize 1024x768 --port COM11  # listen on COM11, use 1024x768 window size
# python tux.py --winsize 1024x768 --test        # same but in test mode (use arrow key)
#
#-----------------------------------------------------------------------------

import argparse
import math
import pygame
import serial
import sys
import threading
import time 

import penger
from graphic3d import *

class EulerAngle:
    """ Simple Thread-safe class to encode Euler Angle"""
    def __init__(self, roll: float = 0, pitch: float = 0, yaw: float = 0) -> None:
        self._roll = roll
        self._pitch = pitch
        self._yaw = yaw 
        self._lock = threading.Lock()

    def get_angle(self) -> tuple[float,float,float]:
        with self._lock:
            return (self._roll, self._pitch, self._yaw)

    def set_angle(self, roll: float, pitch: float, yaw: float ) -> None:
        with self._lock:
            self._roll, self._pitch, self._yaw = roll, pitch, yaw

    def get_screen_angle(self) -> tuple[float,float,float]:
        """
        get roll, pitch, yaw but in the screen coordinate:

        Object Orientation         Screen
        (roll, pitch, yaw)         (pitch, yaw, roll)
          ▲ z                        ▲ y
          ┃                          ┃
          • ━━━▶ y                   • ━━━▶ x
        x                           z  
        """
        return (self._pitch, self._yaw, self._roll)

    def __str__(self):
        return f"{math.degrees(self._roll):7.2f}  {math.degrees(self._pitch):7.2f}  {math.degrees(self._yaw):7.2f}"


position = EulerAngle()

class FetchAnglesFromSerial:

    def __init__(self, port: str, baud_rate: int) -> None:
        self.port = port
        self.baud_rate = baud_rate
        self.ser = None

    def parse_rpy(self):
        while True:
            try:
                data = self.ser.readline()
            except serial.SerialException as exc:
                break
            if not data.startswith(b"HAMI|"):
                continue
            if not data.endswith(b"|IMAH\r\n"):
                continue
            yield (math.radians(float(v)) for v in data[5:-7].split(b":"))


    def fetch_angles(self):
        while True:
            print(f"Connect to serial device {self.port}", end='', flush=True)

            self.ser = None
            while self.ser is None:
                try:
                    self.ser = serial.Serial(self.port, self.baud_rate, timeout=1)
                except serial.SerialException:
                    time.sleep(1)
                    dbg(".", end="", flush=True)
            print("\n--> Connection etablished")

            angle_values = self.parse_rpy()
            while True:
                try:
                    roll, pitch, yaw = next(angle_values)
                    position.set_angle(roll, pitch, yaw)
                    dbg(position)
                except ValueError:
                    continue;
                except StopIteration:
                    print(">>> line disconnected\n")
                    break

    def run(self) -> None:
        t = threading.Thread(target=self.fetch_angles, daemon=True)
        t.start()

        

class Scene: 
    BLACK = (0, 0, 0)
    WHITE = (255, 255, 255)
    BLUE = (100, 150, 255)
    GREEN = (0, 255, 0)

    dW = math.radians(2.5) 

    def __init__(self, width: int, height: int, test_mode: bool) -> None:
        self.width = width
        self.height = height
        self.test_mode = test_mode
        pygame.init()
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("3D Rotating Penguin Wireframe")
        self.clock = pygame.time.Clock()
            

    def loop(self) -> None:
        running = True
        
        # Main loop
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_r:
                        position.set_angle(0,0,0) # reset row,pitch,yaw to 0,0,0
            
            if (self.test_mode):
                r, p, y = position.get_angle()
                keys = pygame.key.get_pressed()
                if keys[pygame.K_LEFT]:  position.set_angle(r-Scene.dW,p,y)
                if keys[pygame.K_RIGHT]: position.set_angle(r+Scene.dW,p,y)
                if keys[pygame.K_UP]:    position.set_angle(r,p-Scene.dW,y)
                if keys[pygame.K_DOWN]:  position.set_angle(r,p+Scene.dW,y)
                dbg(position)

            angle_x, angle_y, angle_z = position.get_screen_angle()
            rotated_points = [
                rotate_x(rotate_y(rotate_z(v, angle_z),angle_y),angle_x) 
                for v in penger.vs
            ]
            self.screen.fill(Scene.BLACK)
            for f in penger.fs:
                f_len = len(f)
                for i in range(f_len):
                    a = rotated_points[f[i]]
                    b = rotated_points[f[(i+1)%f_len]]
                    pygame.draw.line(self.screen, Scene.GREEN, project_3d_to_2d(a, self.width, self.height), project_3d_to_2d(b, self.width, self.height))

            # Instructions
            font = pygame.font.SysFont(None, int(3*self.width/100))
            text = font.render("Arrow keys: manual rotate | R: reset | ESC: quit", True, Scene.WHITE)
            self.screen.blit(text, (10, 10))
            
            pygame.display.flip()
            self.clock.tick(60)
                

def winsize(res: str) -> tuple[int,int]:
    try:
        w,h = res.lower().split('x')
        return int(w),int(h)
    except ValueError:
        raise argparse.ArgumentTypeError("Excepted 'WidthxHeight', like 1024x720")

def main():
    parser = argparse.ArgumentParser(description="Tux Controller")
    parser.add_argument("-p", "--port", default = "/dev/ttyACM0", help="Serial port (default: /dev/ttyACM0)")
    parser.add_argument("-b", "--baud", type=int, default=115200, help="Baud rate (default: 115200)")
    parser.add_argument("-t", "--test", action="store_true", help="Test mode, use keyboard" )
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose mode" )
    parser.add_argument("-w", "--winsize", type=winsize, default=(800,600), metavar="size", help="window size HxW for display (default: 800x600)")
    args = parser.parse_args()

    global dbg
    dbg = print if args.verbose else lambda *args, **kwargs: None 

    if not args.test:
        data_fetcher = FetchAnglesFromSerial(args.port, args.baud)
        data_fetcher.run()
    
    scene = Scene(*args.winsize, args.test)
    scene.loop()


if __name__ == "__main__":
    main()

import time
import board
import displayio
import digitalio
from adafruit_bitmap_font import bitmap_font
import busio
import adafruit_ili9341
from adafruit_display_text import label
try:
    from fourwire import FourWire
except ImportError:
    from displayio import FourWire

# Replace with your actual button pins
btn_oct_up = digitalio.DigitalInOut(board.D2)
btn_oct_up.switch_to_input(pull=digitalio.Pull.DOWN)

btn_oct_down = digitalio.DigitalInOut(board.D3)
btn_oct_down.switch_to_input(pull=digitalio.Pull.DOWN)

btn_cw = digitalio.DigitalInOut(board.D4)
btn_cw.switch_to_input(pull=digitalio.Pull.DOWN)

btn_ccw = digitalio.DigitalInOut(board.D5)
btn_ccw.switch_to_input(pull=digitalio.Pull.DOWN)


def check_buttons():
    """Poll buttons and trigger scene/patch changes."""
    if btn_oct_up.value:
        scene_change("octaveUp")

    if btn_oct_down.value:
        scene_change("octaveDown")

    if btn_cw.value:
        patch_change("cw")

    if btn_ccw.value:
        patch_change("ccw")


# --- Initialisations ---

displayio.release_displays()
spi = busio.SPI(clock=board.D13, MISO=board.D12, MOSI=board.D11)
cs = board.D10
dc = board.D9
reset = board.D8

display_bus = FourWire(spi, command=dc, chip_select=cs, reset=reset)
display = adafruit_ili9341.ILI9341(display_bus, width=320, height=240)

splash = displayio.Group()
display.root_group = splash

bg = displayio.TileGrid(
    displayio.Bitmap(display.width, display.height, 1),
    pixel_shader=displayio.Palette(1)
)
bg.pixel_shader[0] = 0x09082B
splash.insert(0, bg)





#while True:
    #check_buttons()     # handle button presses
    #handle_scenes()     # handle encoders for active scene
    #draw_display()    # (future) update GUI here
    
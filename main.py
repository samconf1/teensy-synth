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
    
import uihandler

#input init
oct_up = digitalio.DigitalInOut(board.D2)
oct_up.switch_to_input(pull=digitalio.Pull.DOWN)
oct_up_state = oct_up.value

oct_down = digitalio.DigitalInOut(board.D3)
oct_down.switch_to_input(pull=digitalio.Pull.DOWN)
oct_down_state = oct_down.value

control = rotaryio.IncrementalEncoder(board.D10, board.D9)
control_lastpos = control.positiondef check_buttons():

check_buttons():
    if oct_up.value and not oct_up_state:
        uihandler.scene_change("octaveUp")
        oct_up_state = True

    if oct_down.value and not oct_down_state:
        uihandler.scene_change("octaveDown")
        oct_down_state = True
        
    if not oct_up.value and oct_up_state:
        oct_up_state = False
        
    if not oct_down.value and oct_down_state:
        oct_down_state = False
        
    if control_lastpos != control.position:
        control_change = control.position - control_lastpos
        if abs(control_change) == control_change: #if positive
            uihandler.patch_change("cw")
        else:
            uihandler.patch_change("ccw")


uihandler.init_uihandler()

while True:
    check_buttons()
    uihandler.handle_scenes()
    
    chordbuilder.handle_keys()
    
    
    if note_is_on(): #and space in buffer
        send_to_dma(generate_block())

        
    
    
    
    
    

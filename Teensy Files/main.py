import traceback
import board
import displayio
import busio
import shared_resources
import digitalio
import adafruit_ili9341
from fourwire import FourWire
import rotaryio


displayio.release_displays() #define display pins
spi = busio.SPI(clock=board.D13, MISO=board.D12, MOSI=board.D11)
cs = board.D10
dc = board.D9
reset = board.D8


display_bus = FourWire(spi, command=dc, chip_select=cs, reset=reset) #initalise display bus
display = adafruit_ili9341.ILI9341(display_bus, width=320, height=240) #intialise display
display.rotation = 180

splash = displayio.Group()
display.root_group = shared_resources.splash

layer0 = displayio.Group() #background colour
shared_resources.layer1 = displayio.Group() #arc backgrounds
shared_resources.layer2 = displayio.Group() #arcs + text
shared_resources.layer3 = displayio.Group() #graphs

shared_resources.splash.append(layer0)
shared_resources.splash.append(shared_resources.layer1)
shared_resources.splash.append(shared_resources.layer2)
shared_resources.splash.append(shared_resources.layer3)


bg = displayio.TileGrid( #create background object
    displayio.Bitmap(display.width, display.height, 1),
    pixel_shader=displayio.Palette(1)
)
bg.pixel_shader[0] = 0x09082B
layer0.append(bg) #append background

import uihandler
import chordbuilder
from audio_driver import set_buffer_length, start_audio, buffer_has_space, stop_audio, get_underrun_count, get_callback_count, update_params, c_generate_block, c_note_on, c_note_off, c_is_note_on


sample_rate = 48000
block_length = 256

#intialise inputs
shared_resources.octaveUp = digitalio.DigitalInOut(board.D22)
shared_resources.octaveUp.switch_to_input(pull=digitalio.Pull.DOWN)
shared_resources.CurStateOctaveUp = False

shared_resources.octaveDown = digitalio.DigitalInOut(board.D23)
shared_resources.octaveDown.switch_to_input(pull=digitalio.Pull.DOWN)
shared_resources.CurStateOctaveDown = False

shared_resources.control = rotaryio.IncrementalEncoder(board.D41, board.D14)
shared_resources.control_lastpos = shared_resources.control.position

shared_resources.shift = digitalio.DigitalInOut(board.D21)
shared_resources.shift.switch_to_input(pull=digitalio.Pull.DOWN)
shared_resources.CurStateShift = False

#define callbacks for chordbuilder.py to call generate block in c. Converts lists into bytearrays for C first.
def note_on_callback(midi_values, velocity_values):
    midi_buf = bytearray(midi_values)
    vel_buf = bytearray(velocity_values)
    c_note_on(midi_buf, vel_buf)
    c_generate_block()

def note_off_callback(midi_values):
    midi_buf = bytearray(midi_values)
    c_note_off(midi_buf)
    c_generate_block()  

uihandler.init_uihandler()
uihandler.patch_text.text = "Midi or Synth"

#let user choose midi mode or synth mode. Initialise the chosen one.
while True:
    if shared_resources.octaveDown.value:
        mode = "midi"
        uihandler.patch_text.text = "Midi"
        shared_resources.layer2.remove(uihandler.left)
        shared_resources.layer2.remove(uihandler.right)
        shared_resources.layer2.remove(uihandler.left_text)
        shared_resources.layer2.remove(uihandler.right_text)
        shared_resources.layer2.remove(uihandler.title1_text)
        shared_resources.layer2.remove(uihandler.title2_text)
        
        break
    if shared_resources.octaveUp.value:
        uihandler.patch_text.text = "P0"
        mode = "synth"
        break

chordbuilder.init_chordbuilder(note_on_callback, note_off_callback, mode)



#called inside the main loop. Checks each button and calls respective functions on a button press/button release event.
def check_buttons(up, up_state, down, down_state, control, control_state):
    if shared_resources.shift.value and not shared_resources.CurStateShift:
        shared_resources.CurStateShift = True
        
    if not shared_resources.shift.value and shared_resources.CurStateShift:
        shared_resources.CurStateShift = False
        
    if up and not up_state:
        if shared_resources.CurStateShift:
            chordbuilder.octave_up()
        else:
            uihandler.scene_change("octaveUp")
        shared_resources.CurStateOctaveUp = True

    if down and not down_state:
        if shared_resources.CurStateShift:
            chordbuilder.octave_down()
        else:
            uihandler.scene_change("octaveDown")
        shared_resources.CurStateOctaveDown = True
        
    if not up and up_state:
        shared_resources.CurStateOctaveUp = False
        
    if not down and down_state:
        shared_resources.CurStateOctaveDown = False
        
    if shared_resources.CurStateOctaveUp and shared_resources.CurStateOctaveDown:
        uihandler.save_patch()
        shared_resources.CurStateOctaveUp = False
        shared_resources.CurStateOctaveDown = False  
        
    if control_state != control:
        control_change = control - control_state
        shared_resources.control_lastpos = control
        if abs(control_change) == control_change: #if positive
            uihandler.patch_change("cw")
        else: #if negative
            uihandler.patch_change("ccw")
      

if mode == "synth": #initialise all synth mode dependencies
    uihandler.handle_scenes()
    set_buffer_length(block_length, 8, sample_rate)
    update_params(uihandler.parameters)
    start_audio()


    chordbuilder.handle_keys(mode)
    while True: #start synth loop.
        try:
            buffer_space = buffer_has_space()
            if buffer_space >= 1 and c_is_note_on(): #audio priority.
                c_generate_block()

            if buffer_space > 1:
                check_buttons(shared_resources.octaveUp.value, shared_resources.CurStateOctaveUp, shared_resources.octaveDown.value, shared_resources.CurStateOctaveDown, shared_resources.control.position, shared_resources.control_lastpos)
                uihandler.handle_scenes()
        
            if uihandler.parameters["dirty"]: #update c parameters only if python parameters have changed. 
                update_params(uihandler.parameters)
                uihandler.parameters["dirty"] = False
            
            chordbuilder.handle_keys(mode)
    
        except Exception as e:
            print("Exception occurred:")
            print("Python: Stopping Audio")
            traceback.print_exception(e)

            stop_audio()
            break
    
    print(f"Underruns: {get_underrun_count()}")
    stop_audio()
        


if mode == "midi":
    while True: #midi mode loop
        chordbuilder.handle_keys(mode)



import time
import board
import displayio
import busio
import shared_resources

displayio.release_displays()
spi = busio.SPI(clock=board.D13, MISO=board.D12, MOSI=board.D11)
cs = board.D10
dc = board.D9
reset = board.D8

import digitalio
from adafruit_bitmap_font import bitmap_font
import adafruit_ili9341

from adafruit_display_text import label
try:
    from fourwire import FourWire
except ImportError:
    from displayio import FourWire

display_bus = FourWire(spi, command=dc, chip_select=cs, reset=reset)
display = adafruit_ili9341.ILI9341(display_bus, width=320, height=240)
display.rotation = 180

splash = displayio.Group()
display.root_group = splash

layer0 = displayio.Group()  # background colour
shared_resources.layer1 = displayio.Group()  # arc backgrounds
shared_resources.layer2 = displayio.Group()
shared_resources.layer3 = displayio.Group()

splash.append(layer0)  # index 0
splash.append(shared_resources.layer1)  # index 1
splash.append(shared_resources.layer2)
splash.append(shared_resources.layer3)


bg = displayio.TileGrid(
    displayio.Bitmap(display.width, display.height, 1),
    pixel_shader=displayio.Palette(1)
)
bg.pixel_shader[0] = 0x09082B
layer0.append(bg)

import uihandler
import rotaryio
import synth
import chordbuilder

from audio_driver import set_buffer_length, start_audio, buffer_has_space, send_to_buffer, send_filter_values 

block_queue = []

#input init
shared_resources.octaveUp = digitalio.DigitalInOut(board.D22)
shared_resources.octaveUp.switch_to_input(pull=digitalio.Pull.DOWN)
shared_resources.CurStateOctaveUp = False

shared_resources.octaveDown = digitalio.DigitalInOut(board.D23)
shared_resources.octaveDown.switch_to_input(pull=digitalio.Pull.DOWN)
shared_resources.CurStateOctaveDown = False

shared_resources.control = rotaryio.IncrementalEncoder(board.D41, board.D14)
shared_resources.control_lastpos = shared_resources.control.position

def check_buttons(up, up_state, down, down_state, control, control_state):
    if up and not up_state:
        uihandler.scene_change("octaveUp")
        shared_resources.CurStateOctaveUp = True

    if down and not down_state:
        uihandler.scene_change("octaveDown")
        shared_resources.CurStateOctaveDown = True
        
    if not up and up_state:
        shared_resources.CurStateOctaveUp = False
        
    if not down and down_state:
        shared_resources.CurStateOctaveDown = False
        
    if control_state != control:
        control_change = control - control_state
        control_lastpos = control.position
        if abs(control_change) == control_change: #if positive
            uihandler.patch_change("cw")
        else:
            uihandler.patch_change("ccw")


uihandler.init_uihandler()
uihandler.handle_scenes()

def queue_block():
    global block_queue

    params = uihandler.parameters
    block_queue.append(synth.generate_block(params))

def note_on_callback(midi_values, velocity_values):
    synth.NoteOn(midi_values, velocity_values, uihandler.parameters)

def note_off_callback(midi_values):
    synth.NoteOff(midi_values, uihandler.parameters)
    
chordbuilder.init_chordbuilder(note_on_callback, note_off_callback)


set_buffer_length(synth.block_length, 8, synth.sample_rate)
start_audio()

send_filter_values(uihandler.parameters["filter_cutoff"], uihandler.parameters["filter_resonance"])
cutoff = uihandler.parameters["filter_cutoff"]
resonance = uihandler.parameters["filter_resonance"]

while True:
    if len(block_queue) < 8 and synth.note_is_on():
        queue_block()

    if len(block_queue) >= 1 and buffer_has_space(): #make note is on function
        send_to_buffer(block_queue.pop(0))

    if len(block_queue) > 4: #only handle ui when safe. 
        check_buttons(shared_resources.octaveUp.value, shared_resources.CurStateOctaveUp, shared_resources.octaveDown.value, shared_resources.CurStateOctaveDown, shared_resources.control.value, shared_resources.control_lastpos)
        uihandler.handle_scenes()
        if cutoff != uihandler.parameters["filter_cutoff"] or resonance != uihandler.parameters["filter_resonance"]:
            send_filter_values(uihandler.parameters["filter_cutoff"], uihandler.parameters["filter_resonance"])
            cutoff = uihandler.parameters["filter_cutoff"]
            resonance = uihandler.parameters["filter_resonance"]


    chordbuilder.handle_keys()

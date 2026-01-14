import board
import digitalio
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import label
from adafruit_display_shapes.roundrect import RoundRect
import shared_resources

import adafruit_midi
from adafruit_midi.control_change import ControlChange
from adafruit_midi.note_on import NoteOn
from adafruit_midi.note_off import NoteOff
import usb_midi

#intialise chordbuilder keys
btnI = digitalio.DigitalInOut(board.D2)
btnII = digitalio.DigitalInOut(board.D3)
btnIII = digitalio.DigitalInOut(board.D5)
btnIV = digitalio.DigitalInOut(board.D24)
btnV = digitalio.DigitalInOut(board.D28)
btnVI = digitalio.DigitalInOut(board.D30)
btnVII = digitalio.DigitalInOut(board.D32)
btn7th = digitalio.DigitalInOut(board.D25)
btn9th = digitalio.DigitalInOut(board.D29)
btnsus2 = digitalio.DigitalInOut(board.D20)
btnsus4 = digitalio.DigitalInOut(board.D4)
btnAsharp = digitalio.DigitalInOut(board.D31)

btnI.switch_to_input(pull=digitalio.Pull.DOWN)
btnII.switch_to_input(pull=digitalio.Pull.DOWN)
btnIII.switch_to_input(pull=digitalio.Pull.DOWN)
btnIV.switch_to_input(pull=digitalio.Pull.DOWN)
btnV.switch_to_input(pull=digitalio.Pull.DOWN)
btnVI.switch_to_input(pull=digitalio.Pull.DOWN)
btnVII.switch_to_input(pull=digitalio.Pull.DOWN)
btn7th.switch_to_input(pull=digitalio.Pull.DOWN)
btn9th.switch_to_input(pull=digitalio.Pull.DOWN)
btnsus2.switch_to_input(pull=digitalio.Pull.DOWN)
btnsus4.switch_to_input(pull=digitalio.Pull.DOWN)
btnAsharp.switch_to_input(pull=digitalio.Pull.DOWN)

#software setup

#chord interval arrays
majorArray = [[0,4,7,11,14],
[2,5,9,12,15],
[4,7,11,14,18],
[5,9,12,16,19],
[7,11,14,18,21],
[9,12,16,19,23],
[11,14,17,21]]


minorArray = [[0,3,7,10,14],
[2,5,8,11],
[3,7,10,14,17],
[5,8,12,15,19],
[7,10,14,17,21],
[8,12,15,19,22],
[10,14,17,20,24]]

arrays = [majorArray, minorArray]

majorInKey = [["", "maj7", "maj9", "add9", "sus2", "sus4"],
              ["", "m7", "m9", "sus4"],
              ["", "m7", "m9"],
              ["","maj7", "add9", "sus2", "sus4"],
              ["", "7", "add9", "sus2", "sus4"],
              ["", "m7", "m9"],
              ["", "m7b5"]]

minorInKey = [["", "m7", "m9", "madd9", "sus2", "sus4"],
              ["", "m7b5" ],
              ["", "maj7", "sus2", "sus4"],
              ["", "m7", "sus2"],
              ["", "7", "sus4"],
              ["", "sus2"],
              ["", "sus2", "sus4"]]


roots = [48,49,50,51,52,53,54,55,56,57,58,59]
notes = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]

major_chord_qualities = ["", "m", "m", "", "", "m", "dim"]
minor_chord_qualities = ["m", "dim", "", "m", "m", "", ""]


array = majorArray #default is major
current_mode = 1 #1 for major, 2 for minor

midi = None
midi_in = None

activeObj = None
ThirdNoteVelocity = 120
btn7Velocity = 0
btn9Velocity = 0
SuspendedNote = 0
SuspendedVelocity = 0
octaveNumber = 0
SuspendedVelocity = 0
ASharpVelocity = 0

note_on_fn = None
note_off_fn = None
    

noteValue = 52 #default root midi value - C3

#display intiialisations
key_text1 = label.Label(font = bitmap_font.load_font("/helvr08.bdf"), text="KEY: ", color=0x575756, anchored_position=(14,186), anchor_point=(0.0,1.0), scale=1)
key_text2 = label.Label(font = bitmap_font.load_font("/helvr08.bdf"), text="C Major", color=0xFFFFFF, anchored_position=(41,188), anchor_point=(0.0,1.0), scale=1)
octave_text1 = label.Label(font = bitmap_font.load_font("/helvr08.bdf"), text="OCTAVE: ", color=0x575756, anchored_position=(86,186), anchor_point=(0.0,1.0), scale=1)
octave_text2 = label.Label(font = bitmap_font.load_font("/helvr08.bdf"), text="0", color=0xFFFFFF, anchored_position=(134,185), anchor_point=(0.0,1.0), scale=1)
chord_text1 = label.Label(font = bitmap_font.load_font("/helvr08.bdf"), text="CHORD: ", color=0x575756, anchored_position=(154,186), anchor_point=(0.0,1.0), scale=1)
chord_text2 = label.Label(font = bitmap_font.load_font("/helvb14.bdf"), text="", color=0xFF0000, anchored_position=(199,186), anchor_point=(0.0,1.0), scale=1)
chord1 = RoundRect(x=12, y=193, width=38, height=38, r=7, outline=0x575756, stroke=1)
chord1_text = label.Label(font = bitmap_font.load_font("/helvb12.bdf"), text="", color=0xFFFFFF, anchored_position=(31,212), anchor_point=(0.5,0.5), scale=1, line_spacing=0.5)
chord2 = RoundRect(x=56, y=193, width=38, height=38, r=7, outline=0x575756, stroke=1)
chord2_text = label.Label(font = bitmap_font.load_font("/helvb12.bdf"), text="", color=0xFFFFFF, anchored_position=(75,212), anchor_point=(0.5,0.5), scale=1)
chord3 = RoundRect(x=100, y=193, width=38, height=38, r=7, outline=0x575756, stroke=1)
chord3_text = label.Label(font = bitmap_font.load_font("/helvb12.bdf"), text="", color=0xFFFFFF, anchored_position=(119,212), anchor_point=(0.5,0.5), scale=1)
chord4 = RoundRect(x=144, y=193, width=38, height=38, r=7, outline=0x575756, stroke=1)
chord4_text = label.Label(font = bitmap_font.load_font("/helvb12.bdf"), text="", color=0xFFFFFF, anchored_position=(163,212), anchor_point=(0.5,0.5), scale=1)
chord5 = RoundRect(x=188, y=193, width=38, height=38, r=7, outline=0x575756, stroke=1)
chord5_text = label.Label(font = bitmap_font.load_font("/helvb12.bdf"), text="", color=0xFFFFFF, anchored_position=(206,212), anchor_point=(0.5,0.5), scale=1)
chord6 = RoundRect(x=232, y=193, width=38, height=38, r=7, outline=0x575756, stroke=1)
chord6_text = label.Label(font = bitmap_font.load_font("/helvb12.bdf"), text="", color=0xFFFFFF, anchored_position=(251,212), anchor_point=(0.5,0.5), scale=1)
chord7 = RoundRect(x=276, y=193, width=38, height=38, r=7, outline=0x575756, stroke=1)
chord7_text = label.Label(font = bitmap_font.load_font("/helvb12.bdf"), text="", color=0xFFFFFF, anchored_position=(295,212), anchor_point=(0.5,0.5), scale=1, line_spacing=0.5)

shared_resources.layer2.append(key_text1)
shared_resources.layer2.append(key_text2)
shared_resources.layer2.append(octave_text1)
shared_resources.layer2.append(octave_text2)
shared_resources.layer2.append(chord_text1)
shared_resources.layer2.append(chord_text2)
shared_resources.layer2.append(chord1)
shared_resources.layer2.append(chord1_text)
shared_resources.layer2.append(chord2)
shared_resources.layer2.append(chord2_text)
shared_resources.layer2.append(chord3)
shared_resources.layer2.append(chord3_text)
shared_resources.layer2.append(chord4)
shared_resources.layer2.append(chord4_text)
shared_resources.layer2.append(chord5)
shared_resources.layer2.append(chord5_text)
shared_resources.layer2.append(chord6)
shared_resources.layer2.append(chord6_text)
shared_resources.layer2.append(chord7)
shared_resources.layer2.append(chord7_text)


def sendOn(arrayrow, btn_obj, mode):
    if btn_obj not in buttons: #validation first 
        print(f"Invalid button: {btn_obj}")
        return
    
    midi_values = []
    velocity_values = []
    
    if arrayrow >= len(array) and (black_buttons[btn_obj]["column"] == 3 or black_buttons[btn_obj]["column"] == 4):  #single black note. 
        midi_values.append(arrayrow)
        velocity_values.append(120)
        if mode == "midi":
            midi.send(NoteOn(midi_values[0], velocity_values[0]))
        else:
            note_on_fn(midi_values, velocity_values)
        return
    
    
    #build note arrays 
    buttons[btn_obj]["chord_active"] = True
    chord_text2.text = get_current_chord(arrayrow)
    
    midi_values.append(noteValue + array[arrayrow][0]) #root
    velocity_values.append(120)
    
    midi_values.append(noteValue + array[arrayrow][1]) #third
    velocity_values.append(ThirdNoteVelocity)
    
    midi_values.append(noteValue + array[arrayrow][2]) #fifth
    velocity_values.append(120)
    
    midi_values.append(noteValue + array[arrayrow][3]) #7th
    velocity_values.append(int(btn7Velocity))
    
    if len(array[arrayrow]) == 5: #9th with validation
        midi_values.append(noteValue + array[arrayrow][4])
        velocity_values.append(int(btn9Velocity))
        
    if SuspendedVelocity == 120: #suspended
        midi_values.append(noteValue + array[arrayrow][0] + SuspendedNote)
        velocity_values.append(int(SuspendedVelocity))
    
    
    
    #update display
    globals()["chord" + str(arrayrow+1)].outline = 0xff0000
    globals()["chord" + str(arrayrow+1)].stroke = 2
    chord_text2.text = get_current_chord(arrayrow)
    
    #send to midi host or synth engine.
    if mode == "synth":
        note_on_fn(midi_values, velocity_values)
    else:
        for i in range(len(midi_values)):
            midi.send(NoteOn(midi_values[i], velocity_values[i]))
            

    
    print("Note On")
  
def sendOff(arrayrow, btn_obj, mode):
    #update display
    globals()["chord" + str(arrayrow+1)].stroke = 1
    globals()["chord" + str(arrayrow+1)].outline = 0x575756
    globals()["chord" + str(arrayrow+1)].fill = None
    chord_text2.text = ""
    
    #midi note off message 
    if mode == "midi":
        midi.send(ControlChange(123, 0))
        return
    
    #build note arrays
    midi_values = []
    buttons[btn_obj]["chord_active"] = False
    chord_text2.text = ""
    midi_values.append(noteValue + array[arrayrow][0]) #root
    midi_values.append(noteValue + array[arrayrow][1]) #third
    midi_values.append(noteValue + array[arrayrow][2]) #fifth
    midi_values.append(noteValue + array[arrayrow][3]) #7th
    
    if len(array[arrayrow]) == 5:
        midi_values.append(noteValue + array[arrayrow][4]) #9th
    
    if SuspendedVelocity == 120:
        midi_values.append(noteValue + array[arrayrow][0] + SuspendedNote) #suspended
        
    chord_text2.text = ""
    
    if mode == "midi":
        for i in range(len(midi_values)):
            midi.send(NoteOff(midi_values[i], 0))
            return
    
    note_off_fn(midi_values)
    
    
def get_chords(root): #get chords based on key
    chords = []
    adjusted_root = root + (octaveNumber * -12)
    if adjusted_root not in roots:
        print(f"Invalid root note: {root}")
        return chords
    
    root_index = roots.index(root+(octaveNumber*-12))
    
    
    if array == arrays[0]:
        qualities = major_chord_qualities
    else:
        qualities = minor_chord_qualities
    
    for j in range(7):
        absolute_index = array[j][0] + root_index
        if absolute_index > 11:
            absolute_index -= 12
        
        chords.append(str(notes[absolute_index] + qualities[j]))
    return chords


def key_change(newRootIndex):
    print("key_change")
    if newRootIndex < 0 or newRootIndex >= len(roots): #validate 
        print(f"Invalid root index: {newRootIndex}")
        return
    
    global noteValue
    global octaveNumber
    octaveNumber = 0 #reset octaveNumber to zero
    octave_text2.text = "0"

    noteValue = roots[newRootIndex]
    chords = get_chords(noteValue)

    #calculate available chords
    if chords[1][-3:] == "dim":
        chords[1] = chords[1][0] + "\n" + chords[1][1:]
    elif chords[5][-3:] == "dim":
        chords[5] = chords[5][0] + "\n" + chords[5][1:]
    for i in range(7):
        globals()["chord" + str(i+1) + "_text"].text = chords[i]
        
    #update available chords on display
    if current_mode == 1:
        key_text2.text = str(chords[0]) + "Major"
    else:
        
        key_text2.text = str(chords[0][0]) + "Minor"
        

def get_current_chord(arrayrow): #used for current chord on display. 
    global inKey

    base = get_chords(noteValue)[arrayrow]
    variation = ""

    is_minor = base.endswith("m") and not base.endswith("dim")
    is_dim = base.endswith("dim")

    if btn7Velocity == 120 and btn9Velocity == 120:
        if is_minor:
            variation = "m9"
        elif not is_dim:
            variation = "9"

    elif btn7Velocity == 120:
        if is_dim:
            base = base[:-3]        
            variation = "m7b5"

        elif is_minor:
            variation = "m7"

        else:
            if arrayrow == 5 and array[2][0] == 4:
                variation = "7"
            else:
                variation = "maj7"

    elif btn9Velocity == 120:
        variation = "add9"

    if not ThirdNoteVelocity:
        if is_minor:
            base = base[:-1]

        if SuspendedVelocity == 120:
            if SuspendedNote == 2:
                variation += "sus2"
            elif SuspendedNote == 5:
                variation += "sus4"

    inKey = False
    for allowed in majorInKey[arrayrow]:
        if variation == allowed:
            inKey = True
            break

    if not inKey and variation != "":
        chord_text2.text += " !"

    return base + variation

def octave_down(): #octave down, update display, update octaveNumber
    global noteValue, octaveNumber, octave_text2
    if noteValue > 24: #bounds check first 
        noteValue -= 12 #edit root
        octaveNumber -= 1
        octave_text2.text = str(octaveNumber)
        
def octave_up(): #octave up, update dsplay, update octavenumber
    global noteValue, octaveNumber, octave_text2
    if noteValue < 100: #bounds check first 
            noteValue += 12 #edit root 
            octaveNumber += 1
            octave_text2.text = str(octaveNumber)
            
def init_chordbuilder(note_on_callback, note_off_callback, mode):
    global note_on_fn, note_off_fn
    note_on_fn = note_on_callback
    note_off_fn = note_off_callback
    key_change(0) #default key is index 0 which is C Major 
    
    if mode == "midi": #intialise midi device 
        global midi, midi_in
        midi = adafruit_midi.MIDI(midi_in=usb_midi.ports[1], in_channel=0, midi_out=usb_midi.ports[1], out_channel=0)
    


#button dictionaries 

buttons = {
    "btnI": {"key_value": 0, "row": 0, "state": False, "chord_active": False},
    "btnII": {"key_value": 2, "row": 1, "state": False, "chord_active": False},
    "btnIII": {"key_value": 4, "row": 2, "state": False, "chord_active": False},
    "btnIV": {"key_value": 5, "row": 3, "state": False, "chord_active": False},
    "btnV": {"key_value": 7, "row": 4, "state": False, "chord_active": False},
    "btnVI": {"key_value": 9, "row": 5, "state": False, "chord_active": False},
    "btnVII": {"key_value": 11, "row": 6, "state": False, "chord_active": False}
    
}


black_buttons = {
    "btn7th": {"state": False, "velocity": "btn7Velocity", "key_value": 6, "column" : 3},
    "btn9th": {"state": False, "velocity": "btn9Velocity", "key_value": 8, "column": 4},
    "btnsus2": {"state": False, "velocity": "SuspendedVelocity", "key_value": 1, "susNote": 2},
    "btnsus4": {"state": False, "velocity": "SuspendedVelocity", "key_value": 3, "susNote": 5},
    "btnAsharp": {"state": False, "velocity": "ASharpVelocity", "key_value": 10}
    }


def handle_keys(mode):
    #WHITE KEYS
    global noteValue, octaveNumber, ThirdNoteVelocity, SuspendedNote
    for button_obj, button_values in buttons.items(): #iterate through all white keys.
        if globals()[button_obj].value and not button_values["state"]: #check button value, update state to true if needed 
            button_values["state"] = True
            if shared_resources.CurStateShift:
                key_change(button_values["key_value"]) #if shift held, call key change
            else: 
                sendOn(button_values["row"], button_obj, mode) #else send chord
        
        if not globals()[button_obj].value and button_values["state"]: #check button value, update state to false if needed
            button_values["state"] = False
            sendOff(button_values["row"], button_obj, mode) #send chord off 
        
    global current_mode, array
    for button_obj, button_values in black_buttons.items(): #iterate through all black keys 
        activeObj = None
        if globals()[button_obj].value and not button_values["state"]: #if button pressed
            button_values["state"] = True
            if shared_resources.CurStateShift:
                key_change(button_values["key_value"]) #call key change is shift pressed
            else:
                for obj, values in buttons.items(): #else iterate through white keys to check if chord is active
                    if values["chord_active"] == True:
                        activeObj = obj
                
                #if no chord active, set button velocity. This code gets ready for a white key to be pressed. If black key down and white key pressed
                #suspension/extension is already added. 
                if activeObj == None: 
                    globals()[button_values["velocity"]] = 120 #Does for every black key
                    if button_obj == "btnsus2" or button_obj == "btnsus4": # Does only for sus keys
                        ThirdNoteVelocity = 0
                        SuspendedNote = button_values["susNote"]
                        
                if activeObj is not None: #if there is an active chord 
                    if len(array[buttons[activeObj]["row"]]) == 5: #No extensions available for diminished chord. 
                        sendOn(noteValue + array[buttons[activeObj]["row"]][button_values["column"]], button_obj, mode) #sends 7th or 9th of the active chord alone

                        
                    
                
        if not globals()[button_obj].value and button_values["state"]: #check for black button release
            button_values["state"] = False
            globals()[button_values["velocity"]] = 0
            if button_obj == "btnsus2" or button_obj == "btnsus4":
                ThirdNoteVelocity = 120
                SuspendedNote = button_values["susNote"]
                
    if black_buttons["btnsus2"]["state"] and black_buttons["btnsus4"]["state"]: #if C# and D# pressed together, change key to major
        current_mode = 3 - current_mode #switches back and forth from 1 to 2
    
        array = arrays[current_mode-1]
        key_change(roots.index(noteValue))
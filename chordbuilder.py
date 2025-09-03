import board
import synth
import digitalio
import analogio
from math import floor
import displayio
from adafruit_bitmap_font import bitmap_font
import busio
import adafruit_ili9341
from adafruit_display_text import label
from adafruit_midi import control_change
from adafruit_display_shapes.roundrect import RoundRect
try:
    from fourwire import FourWire
except ImportError:
    from displayio import FourWire
import uihandler


btnI, btnII, btnIII, btnIV, btnV, btnVI, btnVII, btn7th, btn9th, btnsus2, btnsus4, btnAsharp, shift, octaveUp, octaveDown = digitalio.DigitalInOut(board.GP1), digitalio.DigitalInOut(board.GP2),digitalio.DigitalInOut(board.GP3),digitalio.DigitalInOut(board.GP4),digitalio.DigitalInOut(board.GP5),digitalio.DigitalInOut(board.GP6),digitalio.DigitalInOut(board.GP7),digitalio.DigitalInOut(board.GP8),digitalio.DigitalInOut(board.GP9),digitalio.DigitalInOut(board.GP10),digitalio.DigitalInOut(board.GP11),digitalio.DigitalInOut(board.GP12),digitalio.DigitalInOut(board.GP13),digitalio.DigitalInOut(board.GP20),digitalio.DigitalInOut(board.GP21),digitalio.DigitalInOut(board.GP22)


btnI.switch_to_input(pull=digitalio.Pull.DOWN) # GP1
btnII.switch_to_input(pull=digitalio.Pull.DOWN) # GP2
btnIII.switch_to_input(pull=digitalio.Pull.DOWN) # GP3
btnIV.switch_to_input(pull=digitalio.Pull.DOWN) # GP4
btnV.switch_to_input(pull=digitalio.Pull.DOWN) # GP5
btnVI.switch_to_input(pull=digitalio.Pull.DOWN) # GP6
btnVII.switch_to_input(pull=digitalio.Pull.DOWN) # GP7
btn7th.switch_to_input(pull=digitalio.Pull.DOWN) # GP8
btn9th.switch_to_input(pull=digitalio.Pull.DOWN) # GP9
btnsus2.switch_to_input(pull=digitalio.Pull.DOWN) # GP10
btnsus4.switch_to_input(pull=digitalio.Pull.DOWN) # GP11
btnAsharp.switch_to_input(pull=digitalio.Pull.DOWN) # GP12
shift.switch_to_input(pull=digitalio.Pull.DOWN) # GP13
octaveUp.switch_to_input(pull=digitalio.Pull.DOWN) # GP20
octaveDown.switch_to_input(pull=digitalio.Pull.DOWN) # GP21

print("GPIO Pins Initialised")


#SOFTWARE SETUP

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


#still need a way for major/minor
array= majorArray



activeObj = None
CurStateShift = False
CurStateOctaveUp = False
CurStateOctaveDown = False
ThirdNoteVelocity = 0
btn7Velocity = 0
btn9Velocity = 0
SuspendedNote = 0
SuspendedVelocity = 0
AnalogInDebounce = 7
arrayrowGlobal = 0
octaveNumber = 0
SuspendedVelocity = 0
ASharpVelocity = 0


noteValue = 52

print("Variables Defined")


#DEFINING FUNCTIONS

def init_chordbuilder(): #add all inits like starting octave and starting key and  
    #display object init
    key_text1 = label.Label(font = bitmap_font.load_font("/helvr08.bdf"), text="KEY: ", color=0x575756, anchored_position=(14,186), anchor_point=(0.0,1.0), scale=1)
    key_text2 = label.Label(font = bitmap_font.load_font("/helvr08.bdf"), text="C Major", color=0xFFFFFF, anchored_position=(41,188), anchor_point=(0.0,1.0), scale=1)
    octave_text1 = label.Label(font = bitmap_font.load_font("/helvr08.bdf"), text="OCTAVE: ", color=0x575756, anchored_position=(86,186), anchor_point=(0.0,1.0), scale=1)
    octave_text2 = label.Label(font = bitmap_font.load_font("/helvr08.bdf"), text="0", color=0xFFFFFF, anchored_position=(134,185), anchor_point=(0.0,1.0), scale=1)
    chord_text1 = label.Label(font = bitmap_font.load_font("/helvr08.bdf"), text="CHORD: ", color=0x575756, anchored_position=(154,186), anchor_point=(0.0,1.0), scale=1)
    chord_text2 = label.Label(font = bitmap_font.load_font("/helvb14.bdf"), text="", color=0xFF0000, anchored_position=(199,186), anchor_point=(0.0,1.0), scale=1)

    chord1 = RoundRect(x=12, y=193, width=38, height=38, r=7, outline=0x575756, stroke=1)
    chord1_text = label.Label(font = bitmap_font.load_font("/helvb12.bdf"), text="", color=0xFFFFFF, anchored_position=(31,212), anchor_point=(0.5,0.5), scale=1)
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
    
    
    layer2.append(key_text1)
    layer2.append(key_text2)
    layer2.append(octave_text1)
    layer2.append(octave_text2)
    layer2.append(chord_text1)
    layer2.append(chord_text2)
    layer2.append(chord1)
    layer2.append(chord1_text)
    layer2.append(chord2)
    layer2.append(chord2_text)
    layer2.append(chord3)
    layer2.append(chord3_text)
    layer2.append(chord4)
    layer2.append(chord4_text)
    layer2.append(chord5)
    layer2.append(chord5_text)
    layer2.append(chord6)
    layer2.append(chord6_text)
    layer2.append(chord7)
    layer2.append(chord7_text)
    

def sendOn(arrayrow, btn_obj):
    midi_values = []
    velocity_values = []
    buttons[btn_obj]["chord_active"] = True
    chord_text2.text = get_current_chord(arrayrow)
    
    midi_values.append(noteValue + array[arrayrow][0]) #root
    velocity_values.append(120)
    
    midi_values.append(noteValue + array[arrayrow][1]) #third
    velocity_values.append(ThirdNoteVelocity)
    
    midi_values.append(noteValue + array[arrayrow][2]) #fifth
    velocity_values.append(120)
    
    midi_values.append(noteValue + array[arrayrow][3]) #7th
    velocity_values.append(btn7Velocity)
    
    if len(array[arrayrow]) == 5: #9th
        midi_values.append(noteValue + array[arrayrow][4])
        velocity_values.append(btn9Velocity)
        
    if SuspendedVelocity == 120: #sus2
        midi_values.append(noteValue + array[arrayrow][0] + SuspendedNote)
        
    velocity_values.append(SuspendedVelocity)
    synth.NoteOn(midi_values, velocity_values)
    
    
    globals()["chord" + str(arrayrow+1)].outline = 1.5
    globals()["chord" + str(arrayrow+1)].stroke = 0xff0000
    chord_text2.text = get_current_chord()

    
    print("Note On")
  
def sendOff(arrayrow, btn_obj):
    midi_values = []
    buttons[btn_obj]["chord_active"] = False
    chord_text2.text = ""
    midi_values.append(NoteOff(noteValue + array[arrayrow][0])) #root
    midi_values.append(NoteOff(noteValue + array[arrayrow][1])) #third
    midi_values.append(NoteOff(noteValue + array[arrayrow][2])) #fifth
    midi_values.append(NoteOff(noteValue + array[arrayrow][3])) #7th
    
    if len(array[arrayrow]) == 5:
        midi_values.append(NoteOff(noteValue + array[arrayrow][4])) #9th
    
    if SuspendedVelocity == 120:
        midi_values.append(NoteOff(noteValue + array[arrayrow][0] + SuspendedNote)) #suspended
        
    synth.NoteOff(midi_values)
    
    globals()["chord" + str(arrayrow+1)].outline = 1
    globals()["chord" + str(arrayrow+1)].stroke = 0x575756
    chord_text2.text = ""
    
    
def get_chords(root):
    chords = []
    root_index = roots.index(root+(octaveNumber*-12))
    
    
    if array[2][0] == 4:
        qualities = major_chord_qualities
    else:
        qualities = minor_chord_qualities
    
    for j in range(7):
        s = array[j][0] + root_index
        if s > 11:
            s = s-12
        
        chords.append(str(notes[s] + qualities[j]))
    return chords



def key_change(newRootIndex):
    global noteValue
    global octaveNumber
    octaveNumber = 0
    noteValue = roots[newRootIndex]
    chords = get_chords(noteValue)
    if chords[1][-3:] == "dim":
        chords[1] = chords[1][0] + "\n" + chords[1][1:]
    elif chords[5][-3:] == "dim":
        chords[5] = chords[5][0] + "\n" + chords[5][1:]
    for i in range(7):
        globals()["chord" + str(i+1) + "_text"].text = chords[i]
        
    if len(chords[1]) != 1:
        chords[1] = chords[1][0]
        key_text2.text = str(chords[1]) + "Minor"
    else:
        key_text2.text = str(chords[1]) + "Major"
        


def get_current_chord(arrayrow):
    global inKey
    current_chord = get_chords(noteValue)[arrayrow]
    variation = ""
       
    if btn9Velocity == 120 and btn7Velocity == 120:
        if current_chord[-1] != "m":
            variation += "maj9"

        
    elif btn7Velocity == 120:
        if current_chord[-1] != "m" and arrayrow !=5 and array[2][0] != 4:
            variation +=  "maj7"
        
        if arrayrow == 5 and array[2][0] == 4:
            variation += "7"
        
        
        if current_chord[-2] == "i":
            current_chord = current_chord[:-3]
            variation += "m7b5"
            
        else:
            variation += "7" #for minor 7
        
        
        
    elif btn9Velocity == 120:
        variation += "add9"
        
    if ThirdNoteVelocity == 0:
        if current_chord[-1] == "m" and current_chord[-2] != "i":
            current_chord = current_chord[:-1]
            
        
        if SuspendedNote == 2 and SuspendedVelocity == 120:
            variation += "sus2"
            
        if SuspendedNote == 5 and SuspendedVelocity == 120:
            variation += "sus4"
            
    inKey = False
    
    for i in majorInKey[arrayrow]:
        if variation == i:
            inKey = True

    if not inKey:
        chord_text2.text = chord_text2.text + " !"
    
    
    return current_chord + variation


print("Functions Defined")

print("Display Splashed")

buttons = {
    "btnI": {"key_value": 0, "row": 0, "state": False, "chord_active": False},
    "btnII": {"key_value": 2, "row": 1, "state": False, "chord_active": False},
    "btnIII": {"key_value": 4, "row": 2, "state": False, "chord_active": False},
    "btnIV": {"key_value": 5, "row": 3, "state": False, "chord_active": False},
    "btnV": {"key_value": 7, "row": 4, "state": False, "chord_active": False},
    "btnVI": {"key_value": 9, "row": 5, "state": False, "chord_active": False},
    "btnVII": {"key_value": 11, "row": 6, "state": False, "chord_active": False}
    
}




black_buttons = { #buttons need a state, velocity and key value
    "btn7th": {"state": False, "velocity": "btn7Velocity", "key_value": 1, "column" : 3},
    "btn9th": {"state": False, "velocity": "btn9Velocity", "key_value": 3, "column": 4},
    "btnsus2": {"state": False, "velocity": "SuspendedVelocity", "key_value": 6, "susNote": 2},
    "btnsus4": {"state": False, "velocity": "SuspendedVelocity", "key_value": 8, "susNote": 5},
    "btnAsharp": {"state": False, "velocity": "ASharpVelocity", "key_value": 10}
    }

print("Button objects created")
print("Loop Starting...")

def handle_keys():
    #WHITE KEYS
    
    for button_obj, button_values in buttons.items():
        if globals()[button_obj].value and not button_values["state"]:
            button_values["state"] = True
            if CurStateShift:
                key_change(button_values["key_value"])
            else:
                sendOn(button_values["row"], button_obj)
        
        if not globals()[button_obj].value and button_values["state"]:
            button_values["state"] = False
            sendOff(button_values["row"], button_obj)
        
        
    for button_obj, button_values in black_buttons.items():
        activeObj = None
        if globals()[button_obj].value and not button_values["state"]: #button press
            button_values["state"] = True
            if CurStateShift:
                key_change(button_values["key_value"])
            else:
                for obj, values in buttons.items():
                    if values["chord_active"] == False:
                        activeObj = obj
                
                if activeObj == None:
                    globals()[button_values["velocity"]] = 120 #Does for every black key
                    if button_obj == "btnsus2" or button_obj == "btnsus4": # Does only for sus keys
                        ThirdNoteVelocity = 0
                        SuspendedNote = button_values["susNote"]
                        
                if activeObj is not  None:
                    if len(array[buttons[activeObj]["row"]]) == 5: #So doesn't work for diminshed chord
                        synth.SendOn(NoteOn(noteValue + array[buttons[activeObj]["row"]][button_values["column"]], 120)) #sends 7th or 9th of the active chord alone
                        
                    
                
        if not globals()[button_obj].value and button_values["state"]: #button release
            button_values["state"] = False
            globals()[button_values["velocity"]] = 0
            if button_obj == "btnsus2" or button_obj == "btnsus4":
                ThirdNoteVelocity = 120
                SuspendedNote = button_values["susNote"]
                
                
                

    

    if shift.value and not CurStateShift: #Shift
        CurStateShift = True
    if not shift.value and CurStateShift:
        CurStateShift = False
        
    if octaveUp.value and not CurStateOctaveUp: #Octave Up
        if noteValue < 100:
            noteValue += 12
            octaveNumber += 1
        CurStateOctaveUp = True
    if not octaveUp.value and CurStateOctaveUp:
        CurStateOctaveUp = False
        
    if octaveDown.value and not CurStateOctaveDown: #Octave Down
        CurStateOctaveDown = True
        if noteValue > 24:
            noteValue -= 12
            octaveNumber -= 1
    if not octaveDown.value and CurStateOctaveDown:
        CurStateOctaveDown = False

    
    
    
#Make the major/minor switcher. Something should come up on the screen as well.
#Do octave switcher and shift button handler
    
    
    
        
    
      
      
    




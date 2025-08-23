import board
import digitalio
import analogio
from math import floor
import displayio
from adafruit_bitmap_font import bitmap_font
import busio
import adafruit_ili9341
from adafruit_display_text import label
from adafruit_midi import control_change

try:
    from fourwire import FourWire
except ImportError:
    from displayio import FourWire




btnI, btnII, btnIII, btnIV, btnV, btnVI, btnVII, btn7th, btn9th, btnsus2, btnsus4, btnAsharp, shift, octaveUp, octaveDown, bass = digitalio.DigitalInOut(board.GP1), digitalio.DigitalInOut(board.GP2),digitalio.DigitalInOut(board.GP3),digitalio.DigitalInOut(board.GP4),digitalio.DigitalInOut(board.GP5),digitalio.DigitalInOut(board.GP6),digitalio.DigitalInOut(board.GP7),digitalio.DigitalInOut(board.GP8),digitalio.DigitalInOut(board.GP9),digitalio.DigitalInOut(board.GP10),digitalio.DigitalInOut(board.GP11),digitalio.DigitalInOut(board.GP12),digitalio.DigitalInOut(board.GP13),digitalio.DigitalInOut(board.GP20),digitalio.DigitalInOut(board.GP21),digitalio.DigitalInOut(board.GP22)


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
bass.switch_to_input(pull=digitalio.Pull.DOWN) # GP22

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



array= majorArray
#for i in range(25):
#    if shift.value:
 #       array = minorArray
 #       break

  #  time.sleep(0.2)


activeObj = None
CurStateShift = False
CurStateOctaveUp = False
CurStateOctaveDown = False
CurStateBass = False
CurStateBass2 = False
autoBass = True
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

def noteOn(arrayrow, btn_obj):
    buttons[btn_obj]["chord_active"] = True
    current_text_area.text = get_current_chord(arrayrow)
    midi.send(NoteOn(noteValue + array[arrayrow][0], 120))
    midi.send(NoteOn(noteValue + array[arrayrow][1], ThirdNoteVelocity))
    midi.send(NoteOn(noteValue + array[arrayrow][2], 120))
    midi.send(NoteOn(noteValue + array[arrayrow][3], btn7Velocity)) #7th
    if len(array[arrayrow]) == 5:
        midi.send(NoteOn(noteValue + array[arrayrow][4], btn9Velocity)) #9th
        current_text_area.color = 0xFFFFFF
    else:
        current_text_area.color = 0xFF0000
    if SuspendedVelocity == 120:
        midi.send(NoteOn(noteValue + array[arrayrow][0] + SuspendedNote, SuspendedVelocity)) #sus2
    if autoBass:
        bassmidi.send(NoteOn(noteValue + array[arrayrow][0], 120))
    
    print("Note On")
  
def noteOff(arrayrow, btn_obj):
    buttons[btn_obj]["chord_active"] = False
    current_text_area.text = ""
    midi.send(NoteOff(noteValue + array[arrayrow][0], 120))
    midi.send(NoteOff(noteValue + array[arrayrow][1], 120))
    midi.send(NoteOff(noteValue + array[arrayrow][2], 120))
    midi.send(NoteOff(noteValue + array[arrayrow][3], 120)) #7th
    
    if len(array[arrayrow]) == 5:
        midi.send(NoteOff(noteValue + array[arrayrow][4], 120)) #9th
    
    if SuspendedVelocity == 120:
        midi.send(NoteOff(noteValue + array[arrayrow][0] + SuspendedNote, 120)) #suspended
    bassmidi.send(NoteOff(noteValue + array[arrayrow][0], 120))
    
    
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


def get_current_chord(arrayrow):
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
        current_text_area.color = 0xFF0000
    
    if inKey:
        current_text_area.color = 0xFFFFFF
    
    return current_chord + variation




    


print("Functions Defined")



        
chord_text_area.text = "Chords:\n" + "   ".join(get_chords(noteValue))
octave_text_area.text = "Octave: " + str(octaveNumber)
autobass_text_area.text = "AutoBass Enabled"
key_text_area.text = "Key: Major"

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

while True:
    #WHITE KEYS
    
    for button_obj, button_values in buttons.items():
        if globals()[button_obj].value and not button_values["state"]:
            button_values["state"] = True
            if CurStateShift:
                key_change(button_values["key_value"])
            else:
                noteOn(button_values["row"], button_obj)
        
        if not globals()[button_obj].value and button_values["state"]:
            button_values["state"] = False
            noteOff(button_values["row"], button_obj)
        
        
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
                        midi.send(NoteOn(noteValue + array[buttons[activeObj]["row"]][button_values["column"]], 120)) #sends 7th or 9th of the active chord alone
                        
                    
                
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
            update_display(noteValue)
        CurStateOctaveUp = True
    if not octaveUp.value and CurStateOctaveUp:
        CurStateOctaveUp = False
        
    if octaveDown.value and not CurStateOctaveDown: #Octave Down
        CurStateOctaveDown = True
        if noteValue > 24:
            noteValue -= 12
            octaveNumber -= 1
            update_display(noteValue)
    if not octaveDown.value and CurStateOctaveDown:
        CurStateOctaveDown = False

    if bass.value and not CurStateBass: #Bass
        CurStateBass = True
        if shift.value and autoBass:
            autoBass = False
            autobass_text_area.text = ""
        elif shift.value and not autoBass:
            autoBass = True
            autobass_text_area.text = "AutoBass Enabled"
            
        else:
            if not autoBass:
                bassmidi.send(NoteOn(noteValue + array[arrayrowGlobal][0] - 24, 120))
        
    if not bass.value and CurStateBass:
        CurStateBass = False
        if not autoBass:
            bassmidi.send(NoteOff(noteValue + array[arrayrowGlobal][0], 120))
        
    
    
    
    if AnalogInDebounce == 20:
        digitalSynthFilter = floor(int(analogSynthFilter.value)/516)
        digitalSynthVol = floor(int(analogSynthVol.value)/516)
    
        midi.send(control_change.ControlChange(74, digitalSynthFilter, channel=0))
        midi.send(control_change.ControlChange(2, digitalSynthVol, channel=0))
        AnalogInDebounce = 0
    AnalogInDebounce += 1
    
    
    
#Make the major/minor switcher. Something should come up on the screen as well.
#
    
    
    
        
    
      
      
    



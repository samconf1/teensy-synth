import uihandler
import math
import ulab as ul



active_notes1 = {}
active_notes2 = {}
release_notes1 = {}
release_notes2 = {}

last_note = []


sample_rate = 44100
table_length = 2048
block_length = 256

filter_start = True
x1,x2,y1,y2 = 0,0,0,0

sine = [math.sin(2 * math.pi * i / table_length) for i in range(table_length)]
saw = [2.0 * (i / table_length) - 1.0 for i in range(table_length)]
square = [1.0 if i < table_length // 2 else -1.0 for i in range(table_length)]
triangle = []
for i in range(table_length):
    phase = i / table_length
    if phase < 0.25:               
        triangle.append(-1.0 + 4.0 * phase)
    elif phase < 0.75:              
        triangle.append(1.0 - 4.0 * (phase - 0.25))
    else:                           
        triangle.append(-1.0 + 4.0 * (phase - 0.75))
        
        
def calculate_cents(unison, detune):
    if unison == 1:
        return [0]
    
    offsets = []
    step = (detune * 2) / (unison - 1)   # spacing in cents
    half = (unison - 1) // 2                   # how many voices on each side

    for i in range(-half, half+1):
        offsets.append(i * step)
    return offsets
    
        
        


def precomp_osc(note_data, number_of_notes, note_number):
    block = ul.zeros(block_length, dtype=ul.float)
    
    #unison
    unison_cents = calculate_cents(note_data["unison"], note_data["detune"])
    freq_array = note_data["frequency"] * (2 ** (ul.array(unison_cents) / 1200))
    note_data["inc"] = freq_array * table_length / sample_rate
    
    for i in range(len(unison_cents)):
        phase_indices = (note_data["phase"][i] + note_data["inc"][i] * ul.arange(block_length)).astype(int) % table_length

        block += note_data["table"][phase_indices] / note_data["unison"] / number_of_notes
        
        note_data["phase"][i] += note_data["inc"][i] * block_length
        note_data["phase"][i] %= table_length 

    return block
                    

def osc1_envelope():
    global sample_rate
    attack = uihandler.parameters["osc1_attack"]
    decay = uihandler.parameters["osc1_decay"]
    sustain = uihandler.parameters["osc1_sustain"]
    envelope_value = 0.0
    
    #attack
    attack_inc = 1000 / (sample_rate * attack)
    attack_steps = int((1 - envelope_value) / attack_inc)
    attack_array = ul.arange(envelope_value + attack_inc, 1 + attack_inc, attack_inc)

    if attack_array[-1] != 1.0:
        attack_array = ul.concatenate((attack_array, ul.array([1.0])))

    
    #decay
    decay_inc = 1000 * (1 - sustain) / (sample_rate * decay)
    decay_steps = int((1 - sustain) / decay_inc)
    decay_array = ul.arange(1 - decay_inc, sustain - decay_inc, -decay_inc)

    if decay_array[-1] != sustain:
        decay_array = ul.concatenate((decay_array, ul.array([sustain])))
        
    envelope = ul.concatenate((attack_array, decay_array))
    
    return envelope

def osc2_envelope():
    global sample_rate
    attack = uihandler.parameters["osc2_attack"]
    decay = uihandler.parameters["osc2_decay"]
    sustain = uihandler.parameters["osc2_sustain"]
    envelope_value = 0.0
    
    #attack
    attack_inc = 1000 / (sample_rate * attack)
    attack_array = ul.arange(envelope_value + attack_inc, 1 + attack_inc, attack_inc)

    if attack_array[-1] != 1.0:
        attack_array = ul.concatenate((attack_array, ul.array([1.0])))

    
    #decay
    decay_inc = 1000 * (1 - sustain) / (sample_rate * decay)
    decay_array = ul.arange(1 - decay_inc, sustain - decay_inc, -decay_inc)

    if decay_array[-1] != sustain:
        decay_array = ul.concatenate((decay_array, ul.array([sustain])))
        
    envelope = ul.concatenate((attack_array, decay_array))
    
    return envelope
    

    
def osc1_release():
    global sample_rate
    release = uihandler.parameters["osc1_release"]
    sustain = uihandler.parameters["osc1_sustain"]
    
    
    release_inc = 1000 * sustain / (release * sample_rate)
    release_array = ul.arange(sustain - release_inc, -release_inc, -release_inc)

    if release_array[-1] != 0.0:
        release_array = ul.concatenate((release_array, ul.array([0.0])))

    return release_array

def osc2_release():
    global sample_rate
    release = uihandler.parameters["osc2_release"]
    sustain = uihandler.parameters["osc2_sustain"]
    
    
    release_inc = 1000 * sustain / (release * sample_rate)
    release_array = ul.arange(sustain - release_inc, -release_inc, -release_inc)

    if release_array[-1] != 0.0:
        release_array = ul.concatenate((release_array, ul.array([0.0])))

    return release_array



def calculate_coefficients(cutoff, resonance):
    angular_f = 2 * math.pi * (cutoff / sample_rate)
    k = math.tan(angular_f / 2)
    W = k**2
    alpha = 1 + k / resonance + W  
    a0 = W / alpha
    a1 = 2 * W / alpha
    a2 = a0
    b1 = 2 * (W - 1) / alpha
    b2 = (1 - k/resonance + W) / alpha
    if a2 >=1:
        a2 = 0.95
    if a2 <= -1:
        a2 = -0.95
        
    return [a0, a1, a2, b1, b2]


def apply_filter(initial_block):
    global x1,x2,y1,y2
    
    
    filtered_block = ul.zeros(block_length, dtype=ul.float)
    coefficients = calculate_coefficients(uihandler.parameters["filter_cutoff"], uihandler.parameters["filter_resonance"])
    
    for i in range(len(initial_block)):
        y0 = coefficients[0]*initial_block[i] + coefficients[1]*x1 + coefficients[2]*x2 - coefficients[3]*y1- coefficients[4]*y2
        filtered_block[i] = y0

        y2 = y1
        y1 = y0
        x2 = x1
        x1 = initial_block[i]
        
        
    return filtered_block
    
    
    


def generate_block():
    global active_notes1, active_notes2
    number_of_notes = len(active_notes1)
    final_block = ul.zeros(block_length, dtype=ul.float)
    
    for note_number, note_data in active_notes1.items(): #osc1
        block = precomp_osc(note_data, number_of_notes, note_number)
        envelope = note_data["envelope"]
        sustain = envelope[-1]
        block_number = note_data["block_number"]
        
        if len(envelope) - block_number*block_length >= block_length:
            block *= envelope[block_number*block_length:(block_number+1)*block_length]
        
        elif note_data["envelope_end"]:
            block *= ul.ones(block_length, dtype=ul.float) * sustain
            
        else:
            remaining = envelope[block_number*block_length:]
            padding = ul.ones(block_length - len(remaining), dtype=ul.float) * sustain
            block *= ul.concatenate((remaining, padding))
            note_data["envelope_end"] = True
            
        
        final_block += block
        note_data["block_number"] += 1
        
        
    for note_number, note_data in active_notes2.items(): #osc2
        block = precomp_osc(note_data, number_of_notes, note_number)
        envelope = note_data["envelope"]
        sustain = envelope[-1]
        block_number = note_data["block_number"]
        
            
        if len(envelope) - block_number*block_length >= block_length:
            block *= envelope[block_number*block_length:(block_number+1)*block_length]
        
        elif note_data["envelope_end"]:
            block *= ul.ones(block_length, dtype=ul.float) * sustain
            
        else:
            remaining = envelope[block_number*block_length:]
            padding = ul.ones(block_length - len(remaining), dtype=ul.float) * sustain
            block *= ul.concatenate((remaining, padding))
            note_data["envelope_end"] = True
            
        
        final_block += block
        note_data["block_number"] += 1
        
    final_block /= 2
    
    notes_to_delete = []
    for note_number, note_data in release_notes1.items():
        block = precomp_osc(note_data, number_of_notes, note_number)
        envelope = note_data["envelope"]
        block_number = note_data["block_number"]
        
        if len(envelope) - block_number*block_length >= block_length:
            block *= envelope[block_number*block_length:(block_number+1)*block_length]
            
        elif note_data["envelope_end"]:
            notes_to_delete.append(note_number)
            
        else:
            remaining = envelope[block_number*block_length:]
            padding = ul.zeros(block_length - len(remaining), dtype=ul.float)
            block *= ul.concatenate((remaining, padding))
            note_data["envelope_end"] = True
            
        final_block += block
        note_data["block_number"] += 1
            
            
    for note_number, note_data in release_notes2.items():
        block = precomp_osc(note_data, number_of_notes, note_number)
        envelope = note_data["envelope"]
        block_number = note_data["block_number"]
        
        if len(envelope) - block_number*block_length >= block_length:
            block *= envelope[block_number*block_length:(block_number+1)*block_length]

        
        else:
            remaining = envelope[block_number*block_length:]
            padding = ul.zeros(block_length - len(remaining), dtype=ul.float)
            block *= ul.concatenate((remaining, padding))
            note_data["envelope_end"] = True
            
        final_block += block
        note_data["block_number"] += 1
        
    for i in notes_to_delete:
        del release_notes1[i]
        del release_notes2[i]
            
        
        
    
    final_block = apply_filter(final_block)
    
    return final_block
        
    
        
        
    
    
    
     
def NoteOn(midi_values, velocity_values):
    global last_note
    envelope1 = osc1_envelope()
    envelope2 = osc2_envelope()
     
    for n in midi_values:
        if velocity_values[midi_values.index(n)] != 0:
            unison_temp = uihandler.parameters["osc1_unison"]
            active_notes1[n] = {"frequency" : 440*2**((n-69)/12),
                                "unison" : unison_temp,
                                "detune" : uihandler.parameters["osc1_detune"],
                                "phase" : ul.zeros(unison_temp),
                                "inc" : ul.zeros(unison_temp),
                                "envelope" : envelope1,
                                "envelope_end" : False,
                                "table" : globals()[uihandler.parameters["osc1_wave"]],
                                "block_number" : 0}
            
            last_note.append(n)
        
            unison_temp = uihandler.parameters["osc2_unison"]
            active_notes2[n] = {"frequency" : 440*2**((n-69)/12),
                                "unison" : unison_temp,
                                "detune" : uihandler.parameters["osc2_detune"],
                                "phase" : ul.zeros(unison_temp),
                                "inc" : ul.zeros(unison_temp),
                                "envelope" : envelope2,
                                "envelope_end" : False,
                                "table" : globals()[uihandler.parameters["osc2_wave"]],
                                "block_number" : 0}
            
            if len(midi_values) == 1:
                active_notes1[n]["block_number"] = active_notes1[last_note[-2]]["block_number"]
                active_notes2[n]["block_number"] = active_notes2[last_note[-2]]["block_number"]
            
            

    
            
            
            
def NoteOff(midi_values):
    global last_note
    for n in midi_values:
        release_notes1[n] = active_notes1[n]
        release_notes2[n] = active_notes2[n]
        del active_notes1[n]
        del active_notes2[n]
        
        release_notes1[n]["envelope"] = osc1_release()
        release_notes2[n]["envelope"] = osc2_release()
        release_notes1[n]["block_number"] = 0
        release_notes2[n]["block_number"] = 0
        release_notes1[n]["envelope_end"] = False
        release_notes2[n]["envelope_end"] = False
    
    last_note = last_note[-2:]
        
        
        
        
        
        
        
        
        
    
    
        
        
    
    

        
        

        

        
        
        
        


        

        
    

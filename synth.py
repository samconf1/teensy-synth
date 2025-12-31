import math
import ulab as ul



active_notes1 = {}
active_notes2 = {}
release_notes1 = {}
release_notes2 = {}

last_note = []

def note_is_on():
    active_count = len(active_notes1) + len(active_notes2)
    release_count = len(release_notes1) + len(release_notes2)
    return active_count > 0 or release_count > 0

sample_rate = 44100
table_length = 2048
block_length = 256


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
                    

def osc1_envelope(params):
    global sample_rate
    attack = params["env1_attack"]
    decay = params["env1_decay"]
    sustain = params["env1_sustain"]
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

def osc2_envelope(params):
    global sample_rate
    attack = params["env2_attack"]
    decay = params["env2_decay"]
    sustain = params["env2_sustain"]
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
    

    
def osc1_release(params):
    global sample_rate
    release = params["env1_release"]
    sustain = params["env1_sustain"]
    
    
    release_inc = 1000 * sustain / (release * sample_rate)
    release_array = ul.arange(sustain - release_inc, -release_inc, -release_inc)

    if release_array[-1] != 0.0:
        release_array = ul.concatenate((release_array, ul.array([0.0])))

    return release_array

def osc2_release(params):
    global sample_rate
    release = params["env2_release"]
    sustain = params["env2_sustain"]
    
    
    release_inc = 1000 * sustain / (release * sample_rate)
    release_array = ul.arange(sustain - release_inc, -release_inc, -release_inc)

    if release_array[-1] != 0.0:
        release_array = ul.concatenate((release_array, ul.array([0.0])))

    return release_array
    
    
def generate_block(params):
    global active_notes1, active_notes2
    number_of_notes = len(active_notes1)
    if number_of_notes == 0:
        number_of_notes = 1 #prevent division by zero

    final_block = ul.zeros(block_length, dtype=ul.float)
    
    if params["osc1_level"] > 0:
        for note_number, note_data in active_notes1.items(): #generate osc1 block
            block = precomp_osc(note_data, number_of_notes, note_number)
            envelope = note_data["envelope"]
            sustain = envelope[-1]
            block_number = note_data["block_number"]

            #if in attack or decay
            if len(envelope) - block_number*block_length >= block_length:
                block *= envelope[block_number*block_length:(block_number+1)*block_length]

            elif note_data["envelope_end"]: #if in sustain
                block *= ul.ones(block_length, dtype=ul.float) * sustain

            else: #if entering sustain this block
                remaining = envelope[block_number*block_length:]
                padding = ul.ones(block_length - len(remaining), dtype=ul.float) * sustain
                block *= ul.concatenate((remaining, padding))
                note_data["envelope_end"] = True


            final_block += block
            note_data["block_number"] += 1
        
    if params["osc2_level"] > 0: 
        for note_number, note_data in active_notes2.items(): #generate osc2 block
            block = precomp_osc(note_data, number_of_notes, note_number)
            envelope = note_data["envelope"]
            sustain = envelope[-1]
            block_number = note_data["block_number"]

            #if in attack or decay 
            if len(envelope) - block_number*block_length >= block_length:
                block *= envelope[block_number*block_length:(block_number+1)*block_length]

            #if in sustain
            elif note_data["envelope_end"]:
                block *= ul.ones(block_length, dtype=ul.float) * sustain

            else: #if entering sustain this block
                remaining = envelope[block_number*block_length:]
                padding = ul.ones(block_length - len(remaining), dtype=ul.float) * sustain
                block *= ul.concatenate((remaining, padding))
                note_data["envelope_end"] = True


            final_block += block
            note_data["block_number"] += 1

    total_level = params["osc1_level"] + params["osc2_level"] #clipping
    if total_level > 1:
        final_block *= total_level
            

    notes_to_delete = []
    for note_number, note_data in release_notes1.items(): #generate osc1 release block
        block = precomp_osc(note_data, number_of_notes, note_number)
        envelope = note_data["envelope"]
        block_number = note_data["block_number"]
        
        #if in release
        if len(envelope) - block_number*block_length >= block_length:
            block *= envelope[block_number*block_length:(block_number+1)*block_length]
            
        #if release ended
        elif note_data["envelope_end"]:
            notes_to_delete.append(note_number)
            
        else: #if release finished this block 
            remaining = envelope[block_number*block_length:]
            padding = ul.zeros(block_length - len(remaining), dtype=ul.float)
            block *= ul.concatenate((remaining, padding))
            note_data["envelope_end"] = True
            
        final_block += block
        note_data["block_number"] += 1

        for i in notes_to_delete:
            del release_notes1[i]
        notes_to_delete = []
            
            
    for note_number, note_data in release_notes2.items(): #same for osc2 release block
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
        
    for i in notes_to_delete:
        del release_notes2[i]
            
    return final_block
        
    
def NoteOn(midi_values, velocity_values, params):
    if not midi_values or not velocity_values: #validate inputs
        return
    
    if len(midi_values) != len(velocity_values):
        print("Warning: midi_values and velocity_values length mismatch") #check for length mismatch
        return
    
    global last_note, active_notes1, active_notes2, release_notes1, release_notes2
    envelope1 = osc1_envelope(params)
    envelope2 = osc2_envelope(params)
     
    for n in midi_values:
        if velocity_values[midi_values.index(n)] != 0:
            unison_temp = params["osc1_unison"]
            active_notes1[n] = {"frequency" : 440*2**((n-69)/12),
                                "unison" : unison_temp,
                                "detune" : params["osc1_detune"],
                                "phase" : ul.zeros(unison_temp),
                                "inc" : ul.zeros(unison_temp),
                                "envelope" : envelope1,
                                "envelope_end" : False,
                                "table" : globals()[params["osc1_wave"]],
                                "block_number" : 0}
            
            last_note.append(n)
        
            unison_temp = params["osc2_unison"]
            active_notes2[n] = {"frequency" : 440*2**((n-69)/12),
                                "unison" : unison_temp,
                                "detune" : params["osc2_detune"],
                                "phase" : ul.zeros(unison_temp),
                                "inc" : ul.zeros(unison_temp),
                                "envelope" : envelope2,
                                "envelope_end" : False,
                                "table" : globals()[params["osc2_wave"]],
                                "block_number" : 0}
            
            if len(midi_values) == 1: #won't fail because midi values only equals 1 if key is pressed i.e. active_notes is not empty. last_note[-2] will always exist if this code is run.
                active_notes1[n]["block_number"] = active_notes1[last_note[-2]]["block_number"]
                active_notes2[n]["block_number"] = active_notes2[last_note[-2]]["block_number"]
            
            
def NoteOff(midi_values, params):
    global last_note
    
    for n in midi_values: 
        if n not in active_notes1 or n not in active_notes2: #check if note exists first
            continue

        release_notes1[n] = active_notes1[n]
        release_notes2[n] = active_notes2[n]
        
        del active_notes1[n]
        del active_notes2[n]
        
        release_notes1[n]["envelope"] = osc1_release(params)
        release_notes2[n]["envelope"] = osc2_release(params)
        release_notes1[n]["block_number"] = 0
        release_notes2[n]["block_number"] = 0
        release_notes1[n]["envelope_end"] = False
        release_notes2[n]["envelope_end"] = False
    
    last_note = last_note[-2:]
        
        
        
        


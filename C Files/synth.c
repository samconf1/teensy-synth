#include "shared-bindings/audio_driver/__init__.h"
#include "shared-module/audio_driver/audio_driver.h"
#include "shared-module/audio_driver/synth.h"
#include "py/obj.h"
#include "py/objlist.h"
#include "py/runtime.h"
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <string.h>
#include <math.h>
#include <stddef.h>

#define TABLE_LENGTH 2048
#define pi M_PI
#define MAX_NOTES 20

//define note pool
static note_node_t note_pool[MAX_NOTES];
static uint8_t note_used[MAX_NOTES] = {0};


static note_node_t* alloc_note(void) { //allocated note to note pool
    for (int i = 0; i < MAX_NOTES; i++) {
        if (!note_used[i]) {
            note_used[i] = 1;
            memset(&note_pool[i], 0, sizeof(note_node_t));
            return &note_pool[i];
        }
    }
    return NULL;
}

static void free_note(note_node_t* note) { //frees not from note pool
    for (int i = 0; i < MAX_NOTES; i++) {
        if (&note_pool[i] == note) {
            note_used[i] = 0;
            return;
        }
    }
}

//declare and allocate wavetable arrays
__attribute__((section(".bss")))
static float sine[TABLE_LENGTH];

__attribute__((section(".bss")))
static float saw[TABLE_LENGTH];

__attribute__((section(".bss")))
static float square[TABLE_LENGTH];

__attribute__((section(".bss")))
static float triangle[TABLE_LENGTH];

//declare and allocate envelope arrays 
static float env1_array[7500];
static float env2_array[7500];
static float release1_array[5500];
static float release2_array[5500];

note_node_t *active_notes1 = NULL;
note_node_t *active_notes2 = NULL;
note_node_t *release_notes1 = NULL;
note_node_t *release_notes2 = NULL;

float coeffs[5];

static float x1 = 0;
static float x2 = 0;
static float _y1 = 0; //y1 is already a defined variable in the math.h lib so _y1
static float y2 = 0;

uint8_t is_note_on = 0;

synth_params_t current_params;

static note_node_t *last_note1 = NULL; //pointer to last note - not including 7th or 9th, osc1
static note_node_t *last_note2 = NULL; //pointer to last note - not including 7th or 9th, osc2

void print_sp(void) { //print_sp, used for checking for stack overflow.
    void* sp; 
    asm("mov %0, sp" : "=r"(sp));
    printf("SP=%p\n", sp);
}


void synth_init(void) {
    for (int i = 0; i < TABLE_LENGTH; i++) {
        sine[i] = sinf(2.0f * M_PI * (float)i / (float)TABLE_LENGTH);

        saw[i] = 2.0f * ((float)i / (float)TABLE_LENGTH) - 1.0f;

        square[i] = (i < (TABLE_LENGTH / 2)) ? 1.0f : -1.0f;

        if (i < TABLE_LENGTH / 2) {
            triangle[i] = 4.0f * ((float)i / (float)TABLE_LENGTH) - 1.0f;
        } else {
            triangle[i] = 3.0f - 4.0f * ((float)i / (float)TABLE_LENGTH);
        }
    }
    calculate_coefficients(current_params.filter_cutoff, current_params.filter_resonance);
    srand(0xC0FFEE);
    print_sp();
}

bool synth_is_note_on(void) { //called by c bindings. is_note_on is a condition in the main python loop to generate the next block.
    return (active_notes1 || active_notes2 || release_notes1 || release_notes2);
}

static void calculate_cents(int16_t unison, float detune, float *offsets) { //returns an array of frequency offsets from the main osc frequency for unison 
    if (unison == 1) {
        offsets[0] = 0.0f;
        return;
    }

    float step = detune*2 / (float)(unison - 1);
    int half = (unison - 1) / 2;

    for (int i = -half; i <= half; i++) {
        offsets[i + half] = i * step;
    }
}

int count_notes(note_node_t *list_head) { //counts number of notes in linked list
    int count = 0;
    note_node_t *current = list_head;
    
    while (current != NULL) {
        count++;
        current = current->next;
    }
    
    return count;
}

static uint16_t comp_envelope(int8_t osc_number) { //comp envelope - runs twice per note on, one per osc. 1Khz envelope
    float attack, decay, sustain;
    float *envelope = NULL;

    if (osc_number == 1) { //for osc1
        attack = (float)current_params.env1_attack;
        decay = (float)current_params.env1_decay;
        sustain = current_params.env1_sustain;
        memset(env1_array, 0, sizeof(env1_array));
        envelope = env1_array;
    } else if (osc_number == 2) { //for osc2
        attack = (float)current_params.env2_attack;
        decay = (float)current_params.env2_decay;
        sustain = current_params.env2_sustain;
        memset(env2_array, 0, sizeof(env2_array));
        envelope = env2_array;
    }
    

    uint16_t index = 0;

    //ATTACK COMP
    float attack_inc = 1.0f / attack;
    float env = 0.0f;

    for (int i = 0; i < attack; i++) {
        env += attack_inc;
        if (env > 1.0f) env = 1.0f;
        envelope[index++] = env; 
    }
    if (fabsf(envelope[index-1] - 1.0f) > 0.001f) envelope[index-1] = 1.0f;


    //DECAY COMP
    float decay_inc = (1.0f - sustain) / decay;
    float env_decay = 1.0f;

    for (uint16_t i = 0; i < decay; i++) {
            env_decay -= decay_inc;
            if (env_decay < sustain) env_decay = sustain;
            envelope[index++] = env_decay;
        }
    
    if (fabsf(envelope[index - 1] - sustain) > 0.001f) {
        envelope[index++] = sustain;
    }

    return index;  // return length of envelope
    
}

static void apply_envelope(note_node_t *current_note, float *block) { //applies envelope to block. Location in envelope found based on block_number in note node.
    if (!current_note->envelope || current_note->envelope_length == 0) {
        return; // or skip envelope entirely
    }

    float *envelope = current_note->envelope;
    uint32_t envelope_length = current_note->envelope_length;
    float sustain = current_note->envelope[current_note->envelope_length - 1];

    if (current_note->envelope_end && fabsf(sustain - 1.0f) < 0.001f) { //skip if in sustain and sustain is max
        return;
    }
    
    
    float samples_per_env_step = sample_rate * 0.001f;
    uint32_t env_start = (current_note->block_number * block_length/2) / (int)samples_per_env_step;
    uint32_t env_end   = ((current_note->block_number + 1) * block_length/2) / (int)samples_per_env_step; 

    //if already in sustain phase
    if (current_note->envelope_end) { 
        for (int i = 0; i < 256; i++) {
            block[i] *= sustain;
        }
        return;
    }
    //if entire block within attack/decay
    if ((uint32_t)env_end < envelope_length) {
        int sample = 0;
        for (uint32_t e = env_start; e < env_end; e++) {
            float env = envelope[e];

            for (int s = 0; s < samples_per_env_step && sample < block_length/2; s++) {
                block[sample++] *= env;
            }
        }
        //in case rounding mismatch
        while (sample < block_length/2) {
            block[sample] *= envelope[env_end - 1];
            sample++;
        }
        current_note->block_number++;
        return;
    }
    //if entering sustain this block 
    int sample = 0; 
    for (uint32_t e = env_start; e < envelope_length; e++) {
        float env = envelope[e];

        for (int s = 0; s < samples_per_env_step && sample < block_length/2; s++) {
            block[sample++] *= env;
        }
    }   

    while (sample < block_length/2) { // pad rest of block with sustain
        block[sample++] *= sustain;
    }

    // mark sustain reached
    current_note->envelope_end = true;
    current_note->block_number++;

}

static uint16_t comp_release_envelope(int8_t osc_number) { //comps release part of the envelope. Also 1Khz, runs twice per note on, one per osc
    float release;
    uint16_t index = 0;
    float sustain;
    float *envelope = NULL;

    if (osc_number == 1) {
        release = (float)current_params.env1_release;
        sustain = (float)current_params.env1_sustain;
        memset(release1_array, 0, sizeof(release1_array));
        envelope = release1_array;
    } else if (osc_number == 2) {
        release = (float)current_params.env2_release;
        sustain = (float)current_params.env2_sustain;
        memset(release2_array, 0, sizeof(release2_array));
        envelope = release2_array;
    } 

    float release_inc = sustain / release;
    float env = sustain;

    for (int i = 0; i < (int)release; i++) {
        env -= release_inc;
        if (env < 0.0f) env = 0.0f;
        envelope[index++] = env;
    }

    if (index > 0) {
        envelope[index - 1] = 0.0f;
    }

    return index; // return length of release envelope
}

static void apply_release_envelope(note_node_t *note, float *block) { //applies release envelope to block. block_number should be reset, so 0 = first 256 in array.
    if (!note->envelope || note->envelope_length == 0) {
        return; 
    }
    float *envelope = note->envelope;   
    uint32_t envelope_length = note->envelope_length;
    uint32_t block_num = note->block_number;
    uint32_t sample_index = 0;                     
    float samples_per_env_step = sample_rate * 0.001f; 

    uint32_t env_start = (uint32_t)((block_num * block_length/2) / samples_per_env_step);
    uint32_t env_end   = (uint32_t)(((block_num + 1) * block_length/2) / samples_per_env_step);

    //if release already ended
    if (note->envelope_end) {
        for (int i = 0; i < block_length/2; i++) {
            block[i] = 0.0f;
        }
        return;
    }

    //if in release
    for (uint32_t e = env_start; e < env_end && e < envelope_length; e++) {
        float env_value = envelope[e];

        for (uint32_t s = 0; s < samples_per_env_step && sample_index < block_length/2; s++) {
            block[sample_index++] *= env_value;
        }
    }


    while (sample_index < block_length/2) { //pad remaining samples with zero 
        block[sample_index++] = 0.0f;
    }


    if (env_end >= envelope_length) { //mark note as finished
        note->envelope_end = true;
    }

    note->block_number++; 

}

void calculate_coefficients(float cutoff, float resonance) { //calculates new filter coefficients
    float angular_f = 2 * pi * (cutoff / (float)sample_rate);
    float k = tanf(angular_f / 2.0f);
    float W = k * k;
    float alpha = 1 + k / resonance + W;
    float a0 = W / alpha;
    float a1 = 2 * W / alpha;
    float a2 = a0;
    float b1 = 2 * (W - 1) / alpha;
    float b2 = (1 - k/resonance + W) / alpha;
    
    if (a2 >=1) {
        a2 = 0.95;
    }
    if (a2 <= -1) {
        a2 = -0.95;
    }

    coeffs[0] = a0;
    coeffs[1] = a1;
    coeffs[2] = a2;
    coeffs[3] = b1;
    coeffs[4] = b2;

}

void apply_filter(float *block) { //applies biquad filter to block 
    static float y0;
    for (int i = 0; i < block_length/2; i++) {
        y0 = coeffs[0]*block[i] + coeffs[1]*x1 + coeffs[2]*x2 - coeffs[3]*_y1 - coeffs[4]*y2;

        // Update delay elements
        y2 = _y1;
        _y1 = y0;
        x2 = x1;
        x1 = block[i];

        block[i] = y0;


    }
}

static void precomp_osc(note_node_t *note, float *block) { //fills passed in block array with samples.
    memset(block, 0, sizeof(float) * 256);  
    

    float scale = 1.0f /sqrtf((float)(note->unison));  //scale each voice by sqrt number of voices
    
    for (int i = 0; i < note->unison; i++) { //per voice - create wave and add to block 
        float phase = note->phase[i];
        float inc = note->inc[i];
        float *table = note->wavetable;

        
        for (int n = 0; n < 256; n++) { //per sample - find and add to block at index n
            if (phase >= TABLE_LENGTH) {
                phase -= TABLE_LENGTH;
            }
            int index = (int)phase;
            block[n] += table[index] * scale; //table lookup
            phase += inc;
        }
        
        while (phase >= TABLE_LENGTH) {
            phase -= TABLE_LENGTH;
        }

        note->phase[i] = phase; //update phase in note node.

        
    }
    
}

void generate_block(void) { //called by python under 2 conditions. Note is on, and buffer_has_space returns > 1
    if (active_notes1 == NULL && active_notes2 == NULL && release_notes1 == NULL && release_notes2 == NULL) { //return if no notes active 
        return;
    }
    
    float osc1_level = current_params.osc1_level;
    float osc2_level = current_params.osc2_level;
    float final_block[256];
    memset(final_block, 0, sizeof(final_block));

    

    int8_t number_of_notes;

    fflush(stdout);
    //active notes
    if (osc1_level > 0.0f) { //only calculate if level above 0
        number_of_notes += count_notes(active_notes1); + count_notes(release_notes1);
        note_node_t *current_note = active_notes1;
        while (current_note != NULL) { //per active note node, comp osc, and apply envelope
            float block[256];
            precomp_osc(current_note, block);
            apply_envelope(current_note, block);
            
            for (int i = 0; i < block_length/2; i++) {
                final_block[i] += block[i] * osc1_level;
            }
            current_note = current_note->next;
        }
    }
    
    if (osc2_level > 0.0f) { //only calcualte if level above 0
        number_of_notes += count_notes(active_notes2); + count_notes(release_notes2);
        note_node_t *current_note = active_notes2;
        while (current_note != NULL) {
            float block[256];
            precomp_osc(current_note, block);
            apply_envelope(current_note, block);
            
            for (int i = 0; i < block_length/2; i++) {
                final_block[i] += block[i] * osc2_level;
            }
            current_note = current_note->next;
        }
    }


    //releas_notes

    if (osc1_level > 0.0f) {
        note_node_t *current_note = release_notes1;
        while (current_note != NULL) { //per release note node, comp osc and apply envelope 
            float block[256];
            precomp_osc(current_note, block);
            apply_release_envelope(current_note, block);
            
            for (int i = 0; i < block_length/2; i++) {
                final_block[i] += block[i] * osc1_level;
            }
            current_note = current_note->next;
        }
    }

    if (osc2_level > 0.0f) {
        note_node_t *current_note = release_notes2;
        while (current_note != NULL) {
            float block[256];
            precomp_osc(current_note, block);
            apply_release_envelope(current_note, block);
            
            for (int i = 0; i < block_length/2; i++) {
                final_block[i] += block[i] * osc2_level;
            
            }
            current_note = current_note->next;
        }   
    }


    //freeing notes that have finished release.
    if (release_notes1 != NULL && release_notes1->envelope_end) { //free release notes1 if they have ended 
        note_node_t *current = release_notes1;
        note_node_t *tmp;

        while (current != NULL) {
            tmp = current;
            current = current->next;
            free_note(tmp);
        }
        release_notes1 = NULL;
        last_note1 = NULL;
    }

    
    if (release_notes2 != NULL && release_notes2->envelope_end) { //free release notes2 if theyve ended
        note_node_t *current = release_notes2;
        note_node_t *tmp;

        while (current != NULL) {
            tmp = current;
            current = current->next;
            free_note(tmp);
        }
        release_notes2 = NULL;
        last_note2 = NULL;
    }

    if (number_of_notes == 0) { //kill divide by zero possibility
        number_of_notes = 1;
    }   

    for (int i = 0; i < block_length/2; i++) {
        final_block[i] *= 1.0f / (float)number_of_notes;
    }
    //normalizing final block if total level > 1.0
    float total_level = current_params.total_level;
    if (total_level > 1.0f) {
        float scale = 1.0f / total_level;
        for (int i = 0; i < block_length/2; i++) {
            final_block[i] *= scale;
        }
    }



    apply_filter(final_block);
    send_to_buffer(final_block);
}

void synth_note_on(uint8_t* midi_values, uint8_t* velocity_values, uint8_t len) { //called by c bindings. 
    printf("C_NOTE ON CALLED\n");
    if (len > 1 && (active_notes1 != NULL || active_notes2 != NULL)) {
        printf("Chord already playing\n");
        return;
    }
    
    //comp both envelopes, save their lengths. 
    uint16_t env1_length = comp_envelope(1); 
    uint16_t env2_length = comp_envelope(2);

    for (uint8_t i = 0; i < len; i++) {
        if (velocity_values[i] != 0) {
            //OSC1
            note_node_t *new_note1 = alloc_note();
            if (!new_note1) { //per note - create note node. 
                // handle allocation failure
                printf("Error: Out of memory for new note\n");
                return;
            }

            new_note1->midi_value = midi_values[i];
            new_note1->frequency = 440.0f * powf(2.0f, (midi_values[i] - 69) / 12.0f);
            new_note1->unison = current_params.osc1_unison;
            new_note1->detune = current_params.osc1_detune; 
            
            if (current_params.osc1_wave == 0) {
                new_note1->wavetable = sine;
            } else if (current_params.osc1_wave == 1) {
                new_note1->wavetable = saw;
            } else if (current_params.osc1_wave == 2) {
                new_note1->wavetable = square;
            } else if (current_params.osc1_wave == 3) {
                new_note1->wavetable = triangle;
            } else {
                new_note1->wavetable = sine; // default                       
            }

            //add envelope to note node
            new_note1->envelope_length = env1_length;
            new_note1->envelope = env1_array;

            new_note1->envelope_end = false;
            new_note1->block_number = 0;

            float cents[7];
            calculate_cents(new_note1->unison, new_note1->detune, cents);

            for (int u = 0; u < new_note1->unison; u++) { //calculate the inc and each notes slightly detuned frequency
                float freq = new_note1->frequency * powf(2.0f, cents[u]/1200.0f);
                new_note1->inc[u] = freq * TABLE_LENGTH / sample_rate;
                new_note1->phase[u] = (float)(rand() % TABLE_LENGTH); //randomise phase for beating 
            }      

            new_note1->next = active_notes1;
            active_notes1 = new_note1;

            
            // OSC2

            fflush(stdout);
            note_node_t *new_note2 = alloc_note();
                if (!new_note2) {
                    // handle allocation failure
                    printf("Error: Out of memory for new note\n");
                    return;
                }
                new_note2->midi_value = midi_values[i];
                new_note2->frequency = 440.0f * powf(2.0f, (midi_values[i] - 69) / 12.0f); 
                new_note2->unison = current_params.osc2_unison;
                new_note2->detune = current_params.osc2_detune; 
                
                if (current_params.osc2_wave == 0) {
                    new_note2->wavetable = sine;
                } else if (current_params.osc2_wave == 1) {
                    new_note2->wavetable = saw;
                } else if (current_params.osc2_wave == 2) {
                    new_note2->wavetable = square;
                } else if (current_params.osc2_wave == 3) {
                    new_note2->wavetable = triangle;
                } else {
                    new_note2->wavetable = sine; // default                       
                }


                new_note2->envelope_length = env2_length;
                new_note2->envelope = env2_array;                         
                new_note2->envelope_end = false;
                new_note2->block_number = 0;

                calculate_cents(new_note2->unison, new_note2->detune, cents);

                for (int u = 0; u < new_note2->unison; u++) {
                    float freq = new_note2->frequency * powf(2.0f, cents[u]/1200.0f);
                    new_note2->inc[u] = freq * TABLE_LENGTH / sample_rate;
                    new_note2->phase[u] = (float)(rand() % TABLE_LENGTH); //randomise phase for beating 
                }  

            new_note2->next = active_notes2;
            active_notes2 = new_note2;
            

            //handle black notes. if only one note pressed, its a chord extension.
            if (last_note1 == NULL) {
                last_note1 = new_note1;
                last_note2 = new_note2;
            
            } else if (len == 1) {
                new_note1->block_number = last_note1->block_number; //add the last notes block number onto it so envelope is read in the right place. 
                new_note2->block_number = last_note2->block_number;
            } else {
                last_note1 = new_note1;
                last_note2 = new_note2;
            }
        }
    }
    fflush(stdout);
}




void synth_note_off(uint8_t *midi_values, uint8_t len) {
    printf("C_NOTE OFF CALLED\n");
    if (active_notes1 == NULL && active_notes2 == NULL) {
        printf("Nothing to release\n");
        return; // nothing to release
    }
    uint16_t release1_length = comp_release_envelope(1);
    uint16_t release2_length = comp_release_envelope(2);

    
    note_node_t *tmp;
    while (release_notes1 != NULL) {
        tmp = release_notes1;
        release_notes1 = release_notes1->next;
        free_note(tmp);
    }
    while (release_notes2 != NULL) {
        tmp = release_notes2;
        release_notes2 = release_notes2->next;
        free_note(tmp);
    }

    note_node_t *current, *next;

    //move active note to release
    current = active_notes1;
    while (current != NULL) {
        next = current->next;

        current->envelope_end = false;

        current->envelope = release1_array;
        current->envelope_length = release1_length;

        current->block_number = 0;

        current->next = release_notes1;
        release_notes1 = current;

        current = next;
    }
    active_notes1 = NULL;

    //move active note to relase
    current = active_notes2;
    while (current != NULL) {
        next = current->next;

        current->envelope_end = false;

        current->envelope = release2_array;
        current->envelope_length = release2_length;

        current->block_number = 0;

        current->next = release_notes2;
        release_notes2 = current;

        current = next;
    }
    active_notes2 = NULL;
}


void send_to_buffer(float *block) {
    uint16_t read_ptr, write_ptr;
    get_buffer_ptrs(&read_ptr, &write_ptr);

    for (int i = 0; i < block_length/2; i++) {
        block[i] = block[i] * 32767.0f; //expand to 16 bit integer.
        block[i] = fmaxf(fminf(block[i], 32767.0f), -32768.0f); //prevent clipping

        ring_buffer[write_ptr] = (int16_t)block[i];
        write_ptr = (write_ptr + 1) % buffer_size; // left

        ring_buffer[write_ptr] = (int16_t)block[i];
        write_ptr = (write_ptr + 1) % buffer_size; // right
    }
    

    set_write_ptr(write_ptr);
}

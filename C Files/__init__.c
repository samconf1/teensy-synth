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
#include "MIMXRT1062.h"
#include <math.h>
#include "fsl_cache.h"
#include "fsl_sai.h"
#define pi 3.14159265358979323846f
#include "MIMXRT1062_features.h"
#include "fsl_common.h"
#include "fsl_edma.h"


//defaults
static uint16_t buffer_multiplier = 8;
uint16_t block_length = 512;
uint16_t buffer_size = 256*8*2;
uint16_t sample_rate = 48000;
volatile bool audio_running = false;


//STORED IN DTCM SO RING BUFFER IS NEVER CACHED.
__attribute__((section(".dtcm_bss"), aligned(32)))
static int16_t ring_buffer_storage[256 * 8 * 2];
int16_t *ring_buffer = ring_buffer_storage;

volatile uint32_t buffer_ptrs = 0; //lower 16 bits = write_ptr, upper 16 bits = read_ptr


static mp_obj_t get_callback_count(void) {
    return mp_obj_new_int(dma_callback_count);
}

void get_buffer_ptrs(uint16_t *read_ptr, uint16_t *write_ptr) { //read buffer ptrs into 2 seperate variables
    uint32_t ptrs = buffer_ptrs;
    __DMB();
    
    *read_ptr = (uint16_t)(ptrs >> 16);
    *write_ptr = (uint16_t)(ptrs & 0xFFFF);
}


void set_read_ptr(uint16_t read) { //atomic set to prevent race conditions
    uint32_t old_val;
    uint32_t new_val;
    
    do {
        old_val = __LDREXW(&buffer_ptrs); // load exclusive
        new_val = (old_val & 0x0000FFFF) | ((uint32_t)read << 16);

    } while (__STREXW(new_val, &buffer_ptrs)); // store exclusive
    __DMB();
}

void set_write_ptr(uint16_t write) { //atomic write to prevent race conditions
    uint32_t old_val;
    uint32_t new_val;
    
    do {
        old_val = __LDREXW(&buffer_ptrs);  
        new_val = (old_val & 0xFFFF0000) | (uint32_t)write;

    } while (__STREXW(new_val, &buffer_ptrs)); 
    __DMB();
}


static mp_obj_t start_audio(void) { //Initialisas the full audio pipelines. Called by python.
    dma_callback_count = 0;
    underrun_count = 0;
    enable_system_clocks();
    synth_init();
    sai_init();
    dma_init();
    return mp_const_none;
}


static mp_obj_t set_buffer_length(mp_obj_t py_block_length, mp_obj_t py_buffer_multiplier, mp_obj_t py_sample_rate) { //called by python - set block length, buffer multiplier and sample rate
    block_length = mp_obj_get_int(py_block_length) * 2;
    buffer_multiplier = mp_obj_get_int(py_buffer_multiplier);
    sample_rate = mp_obj_get_int(py_sample_rate); // get values from python
    buffer_ptrs = 0;
    buffer_size = block_length * buffer_multiplier; //define buffer size x2 for stereo

    return mp_const_none;

}

static mp_obj_t c_generate_block(void) { //links python to synth.c 
    generate_block();
    return mp_const_none;
}

static uint8_t wave_name_to_index(const char *name) { //get index from wave name
    if (strcmp(name, "sine") == 0) return 0;
    if (strcmp(name, "saw") == 0) return 1;
    if (strcmp(name, "square") == 0) return 2;
    if (strcmp(name, "triangle") == 0) return 3;
    return 0;
}


static mp_obj_t update_params(mp_obj_t py_params) { //called by python - updates all parameters in C struct to new values. 
    mp_obj_t val;
    //OSC 1 PARAMS
    val = mp_obj_dict_get(py_params, MP_OBJ_NEW_QSTR(MP_QSTR_osc1_wave));
    const char *wave_str = mp_obj_str_get_str(val);
    current_params.osc1_wave = wave_name_to_index(wave_str);
    
    val = mp_obj_dict_get(py_params, MP_OBJ_NEW_QSTR(MP_QSTR_osc1_level));
    current_params.osc1_level = mp_obj_get_float(val);
    
    val = mp_obj_dict_get(py_params, MP_OBJ_NEW_QSTR(MP_QSTR_osc1_unison));
    current_params.osc1_unison = mp_obj_get_int(val);
    
    val = mp_obj_dict_get(py_params, MP_OBJ_NEW_QSTR(MP_QSTR_osc1_detune));
    current_params.osc1_detune = mp_obj_get_float(val);
    
    // OSC2 PARAMS
    val = mp_obj_dict_get(py_params, MP_OBJ_NEW_QSTR(MP_QSTR_osc2_wave));
    wave_str = mp_obj_str_get_str(val);
    current_params.osc2_wave = wave_name_to_index(wave_str);
    
    val = mp_obj_dict_get(py_params, MP_OBJ_NEW_QSTR(MP_QSTR_osc2_level));
    current_params.osc2_level = mp_obj_get_float(val);
    
    val = mp_obj_dict_get(py_params, MP_OBJ_NEW_QSTR(MP_QSTR_osc2_unison));
    current_params.osc2_unison = mp_obj_get_int(val);
    
    val = mp_obj_dict_get(py_params, MP_OBJ_NEW_QSTR(MP_QSTR_osc2_detune));
    current_params.osc2_detune = mp_obj_get_float(val);
    
    // ENV2 PARAMS
    val = mp_obj_dict_get(py_params, MP_OBJ_NEW_QSTR(MP_QSTR_env1_attack));
    current_params.env1_attack = mp_obj_get_int(val);
    
    val = mp_obj_dict_get(py_params, MP_OBJ_NEW_QSTR(MP_QSTR_env1_decay));
    current_params.env1_decay = mp_obj_get_int(val);
    
    val = mp_obj_dict_get(py_params, MP_OBJ_NEW_QSTR(MP_QSTR_env1_sustain));
    current_params.env1_sustain = mp_obj_get_float(val);
    
    val = mp_obj_dict_get(py_params, MP_OBJ_NEW_QSTR(MP_QSTR_env1_release));
    current_params.env1_release = mp_obj_get_int(val);
    
    // ENV2 PARAMS
    val = mp_obj_dict_get(py_params, MP_OBJ_NEW_QSTR(MP_QSTR_env2_attack));
    current_params.env2_attack = mp_obj_get_int(val);
    
    val = mp_obj_dict_get(py_params, MP_OBJ_NEW_QSTR(MP_QSTR_env2_decay));
    current_params.env2_decay = mp_obj_get_int(val);
    
    val = mp_obj_dict_get(py_params, MP_OBJ_NEW_QSTR(MP_QSTR_env2_sustain));
    current_params.env2_sustain = mp_obj_get_float(val);
    
    val = mp_obj_dict_get(py_params, MP_OBJ_NEW_QSTR(MP_QSTR_env2_release));
    current_params.env2_release = mp_obj_get_int(val);
    
    // FILTER
    val = mp_obj_dict_get(py_params, MP_OBJ_NEW_QSTR(MP_QSTR_filter_cutoff));
    float old_cutoff = current_params.filter_cutoff;
    current_params.filter_cutoff = mp_obj_get_float(val);

    if (fabsf(old_cutoff - current_params.filter_cutoff) > 0.001f) {
        calculate_coefficients(current_params.filter_cutoff, current_params.filter_resonance); //call automatically if filter params change
    }
    
    val = mp_obj_dict_get(py_params, MP_OBJ_NEW_QSTR(MP_QSTR_filter_resonance));
    float old_resonance = current_params.filter_resonance;
    current_params.filter_resonance = mp_obj_get_float(val);

    if (fabsf(old_resonance - current_params.filter_resonance) > 0.001f) {
        calculate_coefficients(current_params.filter_cutoff, current_params.filter_resonance); //call automatically if filter params change
    }

    current_params.total_level = current_params.osc1_level + current_params.osc2_level;
    current_params.dirty = 1;

    
    return mp_const_none;
}

//Called by python. Converts bytearrays from python into C types and forwards them to the synth. Also gets length.
static mp_obj_t c_note_on(mp_obj_t py_midi_values, mp_obj_t py_velocity_values) {
    mp_buffer_info_t midi_buf;
    mp_get_buffer_raise(py_midi_values, &midi_buf, MP_BUFFER_READ);
    uint8_t *midi_array = (uint8_t*)midi_buf.buf;
    size_t len_midi = midi_buf.len;
    
    mp_buffer_info_t vel_buf;
    mp_get_buffer_raise(py_velocity_values, &vel_buf, MP_BUFFER_READ);
    uint8_t *vel_array = (uint8_t*)vel_buf.buf;
    size_t len_vel = vel_buf.len;

    if (len_midi != len_vel) {
        mp_raise_msg(&mp_type_ValueError, MP_ERROR_TEXT("Length mismatch")); //raise value error on length mismatch
    }

    synth_note_on(midi_array, vel_array, len_midi);
    return mp_const_none;
}

//Called by Python. Converts bytearrays from python into C types and forwards them to the synth.
static mp_obj_t c_note_off(mp_obj_t py_midi_values) {
    mp_buffer_info_t midi_buf;
    mp_get_buffer_raise(py_midi_values, &midi_buf, MP_BUFFER_READ);
    uint8_t *midi_array = (uint8_t*)midi_buf.buf;
    size_t len_midi = midi_buf.len;

    synth_note_off(midi_array, len_midi);
    return mp_const_none;
}

//Returns an integer of the number of blocks that can fit in the ring buffer. Called by python
static mp_obj_t buffer_has_space(void) {
    uint16_t read_ptr, write_ptr;
    get_buffer_ptrs(&read_ptr, &write_ptr);

    uint16_t free_space;

    if (write_ptr >= read_ptr) {
        free_space = buffer_size - (write_ptr - read_ptr) - 1; // reserve 1 slot
    } else {
        free_space = read_ptr - write_ptr - 1;  // reserve 1 slot
    }
    return mp_obj_new_int(floorf(free_space/block_length));
}



static mp_obj_t get_underrun_count(void) {
    return mp_obj_new_int(underrun_count);
}

//Links python to synth.c
static mp_obj_t c_is_note_on(void) {
    bool is_note_on = synth_is_note_on();
    return mp_obj_new_bool(is_note_on);

}

//called by python, immediately disables all audio. 
static mp_obj_t stop_audio(void) {
    audio_running = false;
    NVIC_DisableIRQ(DMA4_DMA20_IRQn);

    for (volatile int i = 0; i < 50000; i++) {
        __NOP();
    }

    SAI_TxEnableDMA(SAI1, kSAI_FIFORequestDMAEnable, false);
    SAI_TxEnable(SAI1, false);
    DMA0->CERQ = 20; //disable dma channel
    DMA0->CINT = 20; //clear any pending interrupts

    SAI1->TCSR &= ~I2S_TCSR_TE_MASK;   // disable transmitter
    SAI1->TCSR &= ~I2S_TCSR_FRDE_MASK; // disable fifo request DMA
    SAI1->TCSR |= I2S_TCSR_SR_MASK;  

    //reset tcd values to 0 so they aren't random on reinit.
    DMA0->TCD[20].DLAST_SGA = 0; 
    DMA0->TCD[20].CITER_ELINKNO = 0;
    DMA0->TCD[20].BITER_ELINKNO = 0;

    printf("C: Audio system stopped\n\n");
    return mp_const_none;

}


//define all the python functions
MP_DEFINE_CONST_FUN_OBJ_3(set_buffer_length_obj, set_buffer_length);
MP_DEFINE_CONST_FUN_OBJ_0(buffer_has_space_obj, buffer_has_space);
MP_DEFINE_CONST_FUN_OBJ_0(start_audio_obj, start_audio);
MP_DEFINE_CONST_FUN_OBJ_0(get_callback_count_obj, get_callback_count);
MP_DEFINE_CONST_FUN_OBJ_0(get_underrun_count_obj, get_underrun_count);
MP_DEFINE_CONST_FUN_OBJ_0(stop_audio_obj, stop_audio);
MP_DEFINE_CONST_FUN_OBJ_1(update_params_obj, update_params);
MP_DEFINE_CONST_FUN_OBJ_2(c_note_on_obj, c_note_on);
MP_DEFINE_CONST_FUN_OBJ_1(c_note_off_obj, c_note_off);
MP_DEFINE_CONST_FUN_OBJ_0(c_is_note_on_obj, c_is_note_on);
MP_DEFINE_CONST_FUN_OBJ_0(c_generate_block_obj, c_generate_block);



//define the module
static const mp_rom_map_elem_t audio_driver_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_audio_driver) },
    { MP_ROM_QSTR(MP_QSTR_set_buffer_length), MP_ROM_PTR(&set_buffer_length_obj) },
    { MP_ROM_QSTR(MP_QSTR_start_audio), MP_ROM_PTR(&start_audio_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_callback_count), MP_ROM_PTR(&get_callback_count_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_underrun_count), MP_ROM_PTR(&get_underrun_count_obj) },
    { MP_ROM_QSTR(MP_QSTR_update_params), MP_ROM_PTR(&update_params_obj) },
    { MP_ROM_QSTR(MP_QSTR_c_note_on), MP_ROM_PTR(&c_note_on_obj) },
    { MP_ROM_QSTR(MP_QSTR_c_note_off), MP_ROM_PTR(&c_note_off_obj) },
    { MP_ROM_QSTR(MP_QSTR_c_generate_block), MP_ROM_PTR(&c_generate_block_obj) },
    { MP_ROM_QSTR(MP_QSTR_buffer_has_space), MP_ROM_PTR(&buffer_has_space_obj) },
    { MP_ROM_QSTR(MP_QSTR_c_is_note_on), MP_ROM_PTR(&c_is_note_on_obj) },
    { MP_ROM_QSTR(MP_QSTR_stop_audio), MP_ROM_PTR(&stop_audio_obj) }

};
MP_DEFINE_CONST_DICT(audio_driver_module_globals, audio_driver_module_globals_table);


const mp_obj_module_t audio_driver_module = {
    .base    = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&audio_driver_module_globals,
};

//expose the module to python
MP_REGISTER_MODULE(MP_QSTR_audio_driver, audio_driver_module);









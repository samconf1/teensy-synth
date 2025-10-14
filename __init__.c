#include "shared-bindings/audio_driver/__init__.h"
#include "shared-module/audio_driver/audio_driver.h"
#include "py/obj.h"
#include "py/objlist.h"
#include "py/runtime.h"
#include <stdint.h>
#include <stdlib.h>
#include <stdbool.h>
#include <string.h>
#include "MIMXRT1062.h"
#include <math.h>
#include "fsl_cache.h"
#define pi 3.14159265358979323846f

static uint16_t buffer_multiplier = 8;
uint16_t block_length = 512;
int16_t* ring_buffer = NULL;
uint16_t buffer_size = 256*8*2;
uint16_t sample_rate = 44100;
volatile uint32_t buffer_ptrs = 0; //lower 16 bits = write_ptr, upper 16 bits = read_ptr
float coeffs[5];

float cutoff = 20000.0f;
float resonance = 0.5f;

static float x1 = 0;
static float x2 = 0;
static float _y1 = 0; //y1 is already a defined variable in the math.h lib
static float y2 = 0;

static mp_obj_t py_get_pointers(void) {

    uint16_t read_ptr, write_ptr;
    get_buffer_ptrs(&read_ptr, &write_ptr);

    mp_obj_t list[2];
    list[0] = mp_obj_new_int(read_ptr);
    list[1] = mp_obj_new_int(write_ptr);

    // Convert C array into Python list
    return mp_obj_new_list(2, list);
}

static mp_obj_t get_callback_count(void) {
    return mp_obj_new_int(dma_callback_count);
}

void get_buffer_ptrs(uint16_t *read_ptr, uint16_t *write_ptr) {
    uint32_t ptrs;
    
    do {
        ptrs = __LDREXW(&buffer_ptrs);
    } while (__STREXW(ptrs, &buffer_ptrs));  // Re-store to clear exclusive monitor
    
    __DMB();
    
    *read_ptr = (uint16_t)(ptrs >> 16);
    *write_ptr = (uint16_t)(ptrs & 0xFFFF);

}

void set_read_ptr(uint16_t read) {
    uint32_t old_val;
    uint32_t new_val;
    
    do {
        old_val = __LDREXW(&buffer_ptrs); // load exclusive
        new_val = (old_val & 0x0000FFFF) | ((uint32_t)read << 16);

    } while (__STREXW(new_val, &buffer_ptrs)); // store exclusive
    __DMB();
}

void set_write_ptr(uint16_t write) {
    uint32_t old_val;
    uint32_t new_val;
    
    do {
        old_val = __LDREXW(&buffer_ptrs);  
        new_val = (old_val & 0xFFFF0000) | (uint32_t)write;

    } while (__STREXW(new_val, &buffer_ptrs)); 
    __DMB();
}


static mp_obj_t start_audio(void) {
    dma_callback_count = 0;
    enable_system_clocks();
    sai_init();
    dma_init();
    return mp_const_none;
}


static mp_obj_t set_buffer_length(mp_obj_t py_block_length, mp_obj_t py_buffer_multiplier, mp_obj_t py_sample_rate) {
    block_length = mp_obj_get_int(py_block_length) * 2;
    buffer_multiplier = mp_obj_get_int(py_buffer_multiplier);
    sample_rate = mp_obj_get_int(py_sample_rate); // get values from python
    buffer_ptrs = 0;

    buffer_size = block_length * buffer_multiplier; //define buffer size x2 for stereo
    ring_buffer = (int16_t *)aligned_alloc(32, buffer_size * sizeof(int16_t)); //create ring buffer
    return mp_const_none;

}

void calculate_coefficients(void) {
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

static mp_obj_t send_filter_values(mp_obj_t py_cutoff, mp_obj_t py_resonance) {
    cutoff = (float)mp_obj_get_float(py_cutoff);
    resonance = (float)mp_obj_get_float(py_resonance);

    calculate_coefficients();
    return mp_const_none;
}


static mp_obj_t buffer_has_space(void) {
    uint16_t read_ptr, write_ptr;
    get_buffer_ptrs(&read_ptr, &write_ptr);

    uint16_t free_space;

    if (write_ptr >= read_ptr) {
        free_space = buffer_size - (write_ptr - read_ptr) - 1; // reserve 1 slot
    } else {
        free_space = read_ptr - write_ptr - 1;  // reserve 1 slot
    }

    if (free_space >= block_length) {   // enough space for a full block
        return mp_const_true;
    } else {
        return mp_const_false;
    }
}


static mp_obj_t send_to_buffer(mp_obj_t py_block) {
    uint16_t read_ptr, write_ptr;
    get_buffer_ptrs(&read_ptr, &write_ptr);
    mp_buffer_info_t bufinfo;
    mp_get_buffer_raise(py_block, &bufinfo, MP_BUFFER_READ); //get block from python
    
    int16_t block_start = write_ptr;

    static float y0;

    for (size_t i = 0; i < block_length/2; i++) { 
        y0 = coeffs[0]*((float*)bufinfo.buf)[i] + coeffs[1]*x1 + coeffs[2]*x2 - coeffs[3]*_y1 - coeffs[4]*y2;

        y2 = _y1;
        _y1 = y0;
        x2 = x1;
        x1 = ((float*)bufinfo.buf)[i];

        y0 = y0 * 32767.0f;

        if (y0 > 32767) {
            y0 = 32767;
        }
        if (y0 < -32768) {
            y0 = -32768;
        }
        
        ring_buffer[write_ptr] = (int16_t)y0;
        write_ptr = (write_ptr + 1) % buffer_size; // left

        ring_buffer[write_ptr] = (int16_t)y0;
        write_ptr = (write_ptr + 1) % buffer_size; // right
    }

    //this cleans the cache which moves the buffer into memory so dma can actually see it.

if (block_start + block_length <= buffer_size) {
        DCACHE_CleanByRange((uint32_t)&ring_buffer[block_start],block_length * sizeof(int16_t)); //no wraparound of buffer
    } else {
        //with wraparound
        uint32_t first_part = buffer_size - block_start;
        uint32_t second_part = block_length - first_part;

        DCACHE_CleanByRange((uint32_t)&ring_buffer[block_start],first_part * sizeof(int16_t));

        DCACHE_CleanByRange((uint32_t)&ring_buffer[0],second_part * sizeof(int16_t));
   }



    set_write_ptr(write_ptr);// update write pointer
    return mp_const_none;
}



//define all the python functions
MP_DEFINE_CONST_FUN_OBJ_1(send_to_buffer_obj, send_to_buffer);
MP_DEFINE_CONST_FUN_OBJ_3(set_buffer_length_obj, set_buffer_length);
MP_DEFINE_CONST_FUN_OBJ_0(buffer_has_space_obj, buffer_has_space);
MP_DEFINE_CONST_FUN_OBJ_0(start_audio_obj, start_audio);
MP_DEFINE_CONST_FUN_OBJ_2(send_filter_values_obj, send_filter_values);
MP_DEFINE_CONST_FUN_OBJ_0(py_get_pointers_obj, py_get_pointers);
MP_DEFINE_CONST_FUN_OBJ_0(get_callback_count_obj, get_callback_count);


//define the module
static const mp_rom_map_elem_t audio_driver_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_audio_driver) },
    { MP_ROM_QSTR(MP_QSTR_set_buffer_length), MP_ROM_PTR(&set_buffer_length_obj) },
    { MP_ROM_QSTR(MP_QSTR_buffer_has_space), MP_ROM_PTR(&buffer_has_space_obj) },
    { MP_ROM_QSTR(MP_QSTR_send_to_buffer), MP_ROM_PTR(&send_to_buffer_obj) },
    { MP_ROM_QSTR(MP_QSTR_start_audio), MP_ROM_PTR(&start_audio_obj) },
    { MP_ROM_QSTR(MP_QSTR_send_filter_values), MP_ROM_PTR(&send_filter_values_obj) },
    { MP_ROM_QSTR(MP_QSTR_py_get_pointers), MP_ROM_PTR(&py_get_pointers_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_callback_count), MP_ROM_PTR(&get_callback_count_obj) }
};
MP_DEFINE_CONST_DICT(audio_driver_module_globals, audio_driver_module_globals_table);


const mp_obj_module_t audio_driver_module = {
    .base    = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&audio_driver_module_globals,
};

// Register module to make it exposed to python
MP_REGISTER_MODULE(MP_QSTR_audio_driver, audio_driver_module);









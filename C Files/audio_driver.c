#include "shared-module/audio_driver/audio_driver.h"
#include "shared-bindings/audio_driver/__init__.h"
#include <stdlib.h>
#include "fsl_edma.h"
#include "fsl_device_registers.h"
#include "fsl_dmamux.h"
#include "fsl_common.h"
#include "MIMXRT1062.h"
#include "MIMXRT1062_features.h"
#include "fsl_sai_edma.h"
#include <stdio.h>

#include "fsl_sai.h"
#include "fsl_clock.h"
#include "fsl_iomuxc.h"
#include "fsl_gpio.h"
#include "fsl_cache.h"

static int16_t* zero_block = NULL; //empty block, for buffer underrun
volatile uint32_t dma_callback_count = 0;

void enable_system_clocks(void) {
    // mcu clocks

    const clock_audio_pll_config_t audioPllConfig = {
        .loopDivider = 32,      // PLL loop divider
        .postDivider = 1,       // Post divider
        .numerator = 77,        // Numerator for fractional part
        .denominator = 100,     // Denominator for fractional part
        .src = kCLOCK_PllClkSrc24M  // Use 24 MHz crystal
    };
    
    CLOCK_InitAudioPll(&audioPllConfig);
    
    // Now configure SAI to use Audio PLL
    CLOCK_SetMux(kCLOCK_Sai1Mux, 2);      // ✓ CHANGED: 2 = Audio PLL
    CLOCK_SetDiv(kCLOCK_Sai1PreDiv, 3);   // Divide by 4
    CLOCK_SetDiv(kCLOCK_Sai1Div, 15);     // ✓ CHANGED: Divide by 16
    CLOCK_EnableClock(kCLOCK_Sai1);

    CLOCK_EnableClock(kCLOCK_Iomuxc);
    CLOCK_EnableClock(kCLOCK_IomuxcSnvs);
    CLOCK_EnableClock(kCLOCK_Dma);
    for (volatile int i = 0; i < 1000; i++); // small delay to ensure clocks are stable
}
 
void sai_init(void) {
    zero_block = (int16_t *)aligned_alloc(32, block_length * sizeof(int16_t));
    if (zero_block == NULL) {
        printf("ERROR: Failed to allocate zero_block!\n");
        return;
    }
    memset(zero_block, 0, block_length * sizeof(int16_t));
    DCACHE_CleanByRange((uint32_t)zero_block, block_length * sizeof(int16_t));

    // Get MCLK frequency (already configured in enable_system_clocks)
    uint32_t sai1_mclk = CLOCK_GetClockRootFreq(kCLOCK_Sai1ClkRoot);
    printf("\n=== SAI Configuration ===\n");
    printf("MCLK: %lu Hz\n", sai1_mclk);

    // Pin muxing
    IOMUXC_SetPinMux(IOMUXC_GPIO_AD_B1_14_SAI1_TX_BCLK, 0);  // Pin 26 
    IOMUXC_SetPinMux(IOMUXC_GPIO_AD_B1_15_SAI1_TX_SYNC, 0);  // Pin 27 
    IOMUXC_SetPinMux(IOMUXC_GPIO_B1_01_SAI1_TX_DATA00, 0);   // Pin 7 
    
    // ✓ STEP 1: Initialize SAI (this must come FIRST)
    SAI_Init(SAI1);
    SAI_TxReset(SAI1);

    // ✓ STEP 2: Configure transceiver structure
    sai_transceiver_t tx_config;
    
    // Bit clock
    tx_config.bitClock.bclkPolarity = kSAI_PolarityActiveHigh;
    tx_config.bitClock.bclkSource   = kSAI_BclkSourceMclkDiv;
    
    // Frame sync
    tx_config.frameSync.frameSyncPolarity = kSAI_PolarityActiveHigh;
    tx_config.frameSync.frameSyncEarly    = false;
    
    // Data format
    tx_config.serialData.dataWordLength = kSAI_WordWidth16bits;
    tx_config.serialData.dataWordNum   = 2;  // stereo
    
    // Master/slave
    tx_config.masterSlave = kSAI_Master;
    tx_config.syncMode    = kSAI_ModeAsync;
    
    // Channels
    tx_config.startChannel = 0;
    tx_config.endChannel   = 1;
    tx_config.channelNums  = 2;
    tx_config.channelMask  = 0x03;
    
    // ✓ STEP 3: Apply configuration
    SAI_TxSetConfig(SAI1, &tx_config);
    
    // ✓ STEP 4: Configure FIFO
    sai_fifo_t fifo_config = {
        .fifoWatermark = 1
    };
    SAI_TxSetFifoConfig(SAI1, &fifo_config);
    
    // ✓ STEP 5: Set bit clock rate (AFTER SAI_TxSetConfig)
    SAI_TxSetBitClockRate(SAI1, sai1_mclk, sample_rate, 16, 2);
    
    // ✓ STEP 6: Verify what was actually configured
    uint32_t tcr2 = SAI1->TCR2;
    uint32_t div = (tcr2 & I2S_TCR2_DIV_MASK) >> I2S_TCR2_DIV_SHIFT;
    uint32_t actual_bclk = sai1_mclk / ((div + 1) * 2);
    uint32_t actual_fs = actual_bclk / 32;
    
    printf("Divider: %lu\n", div);
    printf("Actual BCLK: %lu Hz\n", actual_bclk);
    printf("Actual sample rate: %lu Hz (target: %u Hz)\n", actual_fs, sample_rate);
    
    // ✓ If sample rate is wrong, try manual configuration
    if (actual_fs < (sample_rate * 0.98) || actual_fs > (sample_rate * 1.02)) {
        printf("WARNING: Sample rate out of tolerance, setting manually...\n");
        
        uint32_t target_bclk = sample_rate * 32;
        uint32_t manual_div = (sai1_mclk / target_bclk / 2) - 1;
        
        printf("Manual divider: %lu\n", manual_div);
        SAI1->TCR2 = (SAI1->TCR2 & ~I2S_TCR2_DIV_MASK) | I2S_TCR2_DIV(manual_div);
        
        // Verify manual setting
        div = (SAI1->TCR2 & I2S_TCR2_DIV_MASK) >> I2S_TCR2_DIV_SHIFT;
        actual_bclk = sai1_mclk / ((div + 1) * 2);
        actual_fs = actual_bclk / 32;
        printf("After manual: Div=%lu, BCLK=%lu Hz, Fs=%lu Hz\n", div, actual_bclk, actual_fs);
    }
    
    printf("========================\n\n");
    
    // ✓ STEP 7: Enable DMA requests
    SAI_TxEnableDMA(SAI1, kSAI_FIFORequestDMAEnable, true);
}


//static volatile bool dma_running = false;

//DMA initialisation

static edma_handle_t dma_handle;

#define dma_channel 20

void dma_init(void) {
    printf("\n=== DMA Configuration ===\n");
    
    // 1. Initialize DMAMUX
    DMAMUX_Init(DMAMUX);
    DMAMUX_SetSource(DMAMUX, dma_channel, kDmaRequestMuxSai1Tx);
    DMAMUX_EnableChannel(DMAMUX, dma_channel);
    
    printf("DMAMUX source: %d (SAI1 TX)\n", kDmaRequestMuxSai1Tx);

    // 2. Initialize eDMA
    edma_config_t edma_config;
    EDMA_GetDefaultConfig(&edma_config);
    EDMA_Init(DMA0, &edma_config);
    
    // 3. Create handle
    EDMA_CreateHandle(&dma_handle, DMA0, dma_channel);
    EDMA_SetCallback(&dma_handle, dma_callback, NULL);

    // 4. Enable interrupts
    EDMA_EnableChannelInterrupts(DMA0, dma_channel, kEDMA_MajorInterruptEnable);
    NVIC_SetPriority(DMA4_DMA20_IRQn, 2);
    NVIC_EnableIRQ(DMA4_DMA20_IRQn);

    // 5. ✓ CRITICAL: Prepare transfer with proper settings
    edma_transfer_config_t edma_transfer_config;
    EDMA_PrepareTransfer(&edma_transfer_config,
                     zero_block,                                     // Source
                     sizeof(int16_t),                                // Source width
                     (void *)SAI_TxGetDataRegisterAddress(SAI1, 0), // Destination
                     sizeof(int16_t),                                // Dest width
                     sizeof(int16_t),                                // Bytes per minor loop
                     block_length * sizeof(int16_t),                 // Total bytes
                     kEDMA_MemoryToPeripheral);

    // ✓ CRITICAL: Manually configure for peripheral-paced transfer
    // The EDMA_PrepareTransfer sets up basic params, but we need to ensure
    // it's truly peripheral-paced
    
    EDMA_SubmitTransfer(&dma_handle, &edma_transfer_config);
    
    // ✓ ADD: Disable DMA request (don't start yet!)
    EDMA_DisableChannelRequest(DMA0, dma_channel);
    
    
    // ✓ Now enable SAI FIRST (so it can generate requests)
    SAI_TxEnable(SAI1, true);
    printf("SAI TX enabled\n");
    
    // Small delay to let SAI stabilize
    for (volatile int i = 0; i < 10000; i++);
    
    // ✓ Check if SAI is generating FIFO requests
    uint32_t tcsr = SAI1->TCSR;
    printf("SAI TCSR: 0x%08lX\n", tcsr);
    printf("SAI FIFO Request Flag: %s\n", (tcsr & I2S_TCSR_FRF_MASK) ? "YES" : "NO");
    printf("SAI FIFO Warning Flag: %s\n", (tcsr & I2S_TCSR_FWF_MASK) ? "YES" : "NO");
    
    // ✓ NOW enable DMA request
    EDMA_EnableChannelRequest(DMA0, dma_channel);
    printf("DMA request enabled\n");
    
    // ✓ Start the DMA transfer
    EDMA_StartTransfer(&dma_handle);
    printf("DMA started\n");
    
    // Verify DMA is now active
}


void DMA4_DMA20_IRQHandler(void) {
    dma_callback_count ++;
    EDMA_HandleIRQ(&dma_handle); //handle iqr SHOULD clear the interrupt flag
}

//dma callback
void dma_callback(edma_handle_t *handle, void *userData, bool transferDone, uint32_t tcds) {
    if (!transferDone) {
        return; //skip rest of function if transfer not done
    }
    uint16_t read_ptr, write_ptr;
    get_buffer_ptrs(&read_ptr, &write_ptr);
    edma_transfer_config_t next_transfer_config;
    
    int16_t *src_ptr;
    
    int16_t available = 0;
    
    if (write_ptr >= read_ptr) {
        available = write_ptr - read_ptr;
    } else {
        available = buffer_size - read_ptr + write_ptr;
    }
    if (available >= block_length) {
        
        src_ptr = &ring_buffer[read_ptr];
        DCACHE_CleanByRange((uint32_t)src_ptr, block_length * sizeof(int16_t));
        set_read_ptr((read_ptr + block_length) % buffer_size); // update read pointer
        
    } else {
        src_ptr = zero_block; // underrun
        DCACHE_CleanByRange((uint32_t)src_ptr, block_length * sizeof(int16_t));
    }
    
    
    // Prepare the next transfer
    EDMA_PrepareTransfer(&next_transfer_config,
                 src_ptr,                        // src address
                 sizeof(int16_t),                    // src width (2 bytes)
                 (void *)SAI_TxGetDataRegisterAddress(SAI1, 0), // dest address
                 sizeof(int16_t),                    // dest width (2 bytes)  
                 sizeof(int16_t),                    // minor loop
                 block_length * sizeof(int16_t),     // major loop 
                 kEDMA_MemoryToPeripheral); 
    // Submit it again
    EDMA_SubmitTransfer(handle, &next_transfer_config);
    EDMA_StartTransfer(handle);
    
}
//in technical solution, if you have a diary of something - like oh i had this problem and had to stop becauas this didnt work so i did mroe resarch and design and then built it again 

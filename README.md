# teensy-synth

git clone https://github.com/adafruit/circuitpython.git
Make fetch-all-submodules

Install arm-none-eabi-gcc
(macos only) export PATH=~/tools/arm-gnu-toolchain-14.3.rel1-darwin-arm64-arm-none-eabi/bin:$PATH

mkdir /shared-bindings/audio_driver/
mdkir /shared-modules/audio_driver/

cp /teensy-synth/"C files"/audio_driver.c /shared-bindings/audio_driver/
cp /teensy-synth/"C files"/audio_driver.h /shared-bindings/audio_driver/
cp /teensy-synth/"C files"/synth.c /shared-bindings/audio_driver/
cp /teensy-synth/"C files"/synth.h /shared-bindings/audio_driver/

cp /teensy-synth/"C files"/__init.c /shared-modules/audio_driver/
cp /teensy-synth/"C files"/__init.h /shared-modules/audio_driver/





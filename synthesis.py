#!/usr/bin/env python

"""
synthesis.py -- lightweight toy synthesizer

"""

import wave
import struct

###############################################################################
## Notes
##

# Once again, I have no idea of what it is that I am doing. So here are some
# notes to arrange my thoughts a little bit.
#
#  - Write to wave files.
#  - Use iterators to procure samples for the wave files
#  - Initialize iterators with sampling rates
#  - Generators produce waveforms, filters transform and limit waveforms.
#
# For now, we will hardcode a bunch of stuff to make life easier.
#  - 44,100 kHz
#  - 1 channel
#
# From what I recall from getting sound working on Gentoo, I think linear
# increase is not a useful model here. In any case decibels are logarithmic.
# For now, a scale that works using a direct multiplication might work. A more
# realistic implementation would facotr in the logarithmic thing.
#

SAMPLING_RATE = 44100

###############################################################################
## Basic generators
##

# Generators are iterators that return floating point amplitude values between
# -1 and 1.

def rectangular_wave(frequency, duty_cycle, minimum=0.0, maximum=1.0):
    """
    A rectangular waveform that alternates between `minimum` and `maximum`.
    `frequency` is specified in Hertz.

    """
    # First, use the frequency to figure out how many samples each oscillation
    # will occupy.
    num_samples = round(SAMPLING_RATE / frequency)

    # Use the duty cycle to figure out how many samples need to be on and off.
    # TODO<susmits>: This is extremely nearest-neighbour, and as a result will
    # sound more and more off as frequency approaches SAMPLING_RATE.
    assert(0.0 <= duty_cycle <= 1.0)
    max_count = round(duty_cycle * num_samples)
    min_count = num_samples - max_count

    min, max = float(minimum), float(maximum)
    while True:
        for i in range(max_count):
            yield max

        for i in range(min_count):
            yield min


###############################################################################
## Filters
##

def time_limiter(generator, num_seconds):
    """
    Yields samples from the given generator for `num_seconds`.

    """
    # TODO<susmits>: SAMPLING_RATE * num_seconds can be truly big. Do something.
    num_samples = round(num_seconds * SAMPLING_RATE)
    for i in range(num_samples):
        yield next(generator)


def scale(generator, factor):
    """
    Scales the value of the generator iterations by `factor`.

    """
    for value in generator:
        yield value * factor


###############################################################################
## Wave writer
##

def pipe_to_wave(generator, out_filename):
    """
    Pipes samples from `generator` into `out_file`, which is a file-like object.

    Please make sure `generator` is limited if you value your hard drive.

    """
    with wave.open(out_filename, "w") as wav:
        # Monophonic
        wav.setnchannels(1)

        # Sampling frequency
        wav.setframerate(SAMPLING_RATE)

        # Let's make each sample 16-bit wide.
        wav.setsampwidth(2)

        # For two bytes, the range is [-32767, 32767]
        # TODO<susmits>: Most likely -32768 is illegal; be good to verify.
        scaler = 32767
        for sample in generator:
            data = struct.pack('<h', round(scaler * sample))
            wav.writeframesraw(data)


###############################################################################
## Test!
##

if __name__ == "__main__":
    pipe_to_wave(
        # One second only
        time_limiter(
            # Not too loud
            scale(
                # Middle C
                rectangular_wave(261.63, 0.25),
                0.2),
            1.0), "test.wav")

###############################################################################

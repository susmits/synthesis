#!/usr/bin/env python

"""
synthesis.py -- lightweight toy synthesizer

"""

import wave

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

SAMPLING_RATE = 44100

###############################################################################
## Basic generators
##

# Generators are iterators that return floating point amplitude values between
# -1 and 1.

def rectangular_wave(duty_cycle, minimum=0.0, maximum=1.0):
    """
    A rectangular waveform that alternates between `minimum` and `maximum`.

    """
    # Use the duty cycle to figure out how many samples need to be on and off.
    assert(0.0 <= duty_cycle <= 1.0)
    max_count = round(duty_cycle * SAMPLING_RATE)
    min_count = SAMPLING_RATE - max_count

    min, max = float(minimum), float(maximum)
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


###############################################################################
## Wave writer
##

# tbd


###############################################################################

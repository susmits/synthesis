#!/usr/bin/env python
"""synthesis.py -- lightweight toy synthesizer"""

from enum import Enum
import math
import re
import struct
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
# From what I recall from getting sound working on Gentoo, I think linear
# increase is not a useful model here. In any case decibels are logarithmic.
# For now, a scale that works using a direct multiplication might work. A more
# realistic implementation would facotr in the logarithmic thing.
#

SAMPLING_RATE = 44100

TEMPO = 80  # Quarter Notes Per Minute

NOTE_REGEX = "([ABCDEFG][#b]?)([1-9]?)"

A4_FREQ = 440.0  # Reference frequency for all tuning.

SEMITONAL_OFFSET_MAP = {
    "C": -9,
    "C#": -8,
    "Db": -8,
    "D": -7,
    "D#": -6,
    "Eb": -6,
    "E": -5,
    "F": -4,
    "F#": -3,
    "Gb": -3,
    "G": -2,
    "G#": -1,
    "Ab": -1,
    "A": 0,
    "A#": 1,
    "Bb": 1,
    "B": 2,
}


class NoteDuration(Enum):
  FULL = 1
  HALF = 2
  QUARTER = 3
  EIGHTH = 4
  SIXTEENTH = 5
  THIRTYSECOND = 6
  DOTTED_FULL = 7
  DOTTED_HALF = 8
  DOTTED_QUARTER = 9
  DOTTED_EIGHTH = 10
  DOTTED_SIXTEENTH = 11
  DOTTED_THIRTYSECOND = 12


NOTE_DURATION_RATIO_MAP = {
    NoteDuration.FULL: 4.0,
    NoteDuration.HALF: 2.0,
    NoteDuration.QUARTER: 1.0,
    NoteDuration.EIGHTH: 0.5,
    NoteDuration.SIXTEENTH: 0.25,
    NoteDuration.THIRTYSECOND: 0.125,
    NoteDuration.DOTTED_FULL: 4.0 * 1.5,
    NoteDuration.DOTTED_HALF: 2.0 * 1.5,
    NoteDuration.DOTTED_QUARTER: 1.0 * 1.5,
    NoteDuration.DOTTED_EIGHTH: 0.5 * 1.5,
    NoteDuration.DOTTED_SIXTEENTH: 0.25 * 1.5,
    NoteDuration.DOTTED_THIRTYSECOND: 0.125 * 1.5
}


###############################################################################
## Utility functions
##
def note_duration_to_sec(note_duration):
  return NOTE_DURATION_RATIO_MAP[note_duration] * 60.0 / TEMPO


def note_to_freq(note_name):
  """
    Function to convert the name of a note to its frequency.
    Acceptable inputs:
      A5
      A#5: A Sharp 5
      Ab5: A Flat 5
      A: A4 (Default octave is 4)
    TODO(antb): Add error checking for bad note names.
    """

  match = re.match(NOTE_REGEX, note_name)

  if match.group(2):
    octave = int(match.group(2))
  else:
    octave = 4

  return A4_FREQ * math.pow(
      2, SEMITONAL_OFFSET_MAP[match.group(1)] / 12.0) * math.pow(2, octave - 4)


###############################################################################
## Basic generators
##

# Generators are iterators that return floating point amplitude values between
# -1 and 1.


def hold(level):
  """
    An infinite generator that holds at level. DO NOT pipe this to audio,
    or you will damage your output equipment. This is only good for envelopes.
    """
  while True:
    yield level


def silence():
  """
    An infinite generator that supplies silence.
    """
  return hold(0.0)


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
  assert (0.0 <= duty_cycle <= 1.0)
  max_count = round(duty_cycle * num_samples)
  min_count = num_samples - max_count

  min, max = float(minimum), float(maximum)
  while True:
    for i in range(max_count):
      yield max

    for i in range(min_count):
      yield min


def sine_wave(frequency):
  """
    A sinusoidal wave that goes from -1.0 to 1.0.
    """
  # First, determine the number of samples for one cycle.
  num_samples = round(SAMPLING_RATE / frequency)

  while True:
    for i in range(num_samples):
      phase = i * math.pi * 2 / num_samples
      yield math.sin(phase)


def linear_change(duration, start, end):
  """
    A linear rise or fall over a given period of time.
    """
  # First, figure out the number of samples
  num_samples = round(duration * SAMPLING_RATE)

  slope = (end - start) / float(num_samples)
  for i in range(num_samples):
    yield start + i * slope


def triangle_wave(frequency):
  """
    A triangular waveform that linearly rises from 0 to 1, falls from 1 to -1,
    and rises from -1 to 0 over one wave train.
    """
  # What's the duration for one cycle?
  time_period = 1.0 / frequency

  while True:
    for sample in linear_change(time_period / 4, 0, 1):
      yield sample
    for sample in linear_change(time_period / 2, 1, -1):
      yield sample
    for sample in linear_change(time_period / 4, -1, 0):
      yield sample


def sawtooth_wave(frequency):
  """
    A sawtooth waveform that linearly rises from -1 to 1, and then sharply
    falls to -1 again.
    """
  # What's the duration for one cycle?
  time_period = 1.0 / frequency

  while True:
    for sample in linear_change(time_period, -1, 1):
      yield sample


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


def scale(generator, factor_generator):
  """
    Scales the value of the generator iterations by `factor_generator`.
    """
  for sample, factor in zip(generator, factor_generator):
    yield sample * factor


def concatenate(*kwargs):
  """
    Concatenates every supplied generator.
    """
  for generator in kwargs:
    for sample in generator:
      yield sample


###############################################################################
## Envelope generators
##


def linear_adsr(attack_duration, decay_duration, sustain_duration,
                release_duration, sustain_level):
  r"""

    Produces a linear ADSR envelope which looks so:
    1      /\
          /  \___ (sustain_level)
         /       \
    0   /         \
         a d   s r
         d d   d d

    All increases are linear in time.
     - rise from 0 to 1 over attack_duration
     - fall from 1 to sustain_level over decay_duration
     - hold at sustain_level over sustain_duration
     - fall from sustain_level to 0 over release_duration
    """
  return concatenate(
      linear_change(attack_duration, 0.0, 1.0),
      linear_change(decay_duration, 1.0, sustain_level),
      time_limiter(hold(sustain_level), sustain_duration),
      linear_change(release_duration, sustain_level, 0.0))


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
    i = 0
    ss, sm = 0, 0
    try:
      for sample in generator:
        i += 1
        ss, sm = scaler, sample
        data = struct.pack("<h", round(scaler * sample))
        wav.writeframesraw(data)
    except:
      print(i, ss, sm)


###############################################################################
## Test!
##

if __name__ == "__main__":
  notes = list(
      map(
          lambda x: (note_to_freq(x[0]), x[1]),
          [
              ("B4", NoteDuration.EIGHTH),
              ("E5", NoteDuration.DOTTED_EIGHTH),
              ("G5", NoteDuration.SIXTEENTH),
              ("F#5", NoteDuration.EIGHTH),
              ("E5", NoteDuration.QUARTER),
              ("B5", NoteDuration.EIGHTH),
              ("A5", NoteDuration.DOTTED_QUARTER),
              ("F#5", NoteDuration.DOTTED_QUARTER),
              #
              ("E5", NoteDuration.DOTTED_EIGHTH),
              ("G5", NoteDuration.SIXTEENTH),
              ("F#5", NoteDuration.EIGHTH),
              ("D#5", NoteDuration.QUARTER),
              ("F5", NoteDuration.EIGHTH),
              ("B4", NoteDuration.DOTTED_QUARTER),
              ("G4", NoteDuration.QUARTER),
              #
              ("B4", NoteDuration.EIGHTH),
              ("E5", NoteDuration.DOTTED_EIGHTH),
              ("G5", NoteDuration.SIXTEENTH),
              ("F#5", NoteDuration.EIGHTH),
              ("E5", NoteDuration.QUARTER),
              ("B5", NoteDuration.EIGHTH),
              ("D6", NoteDuration.QUARTER),
              ("C#6", NoteDuration.EIGHTH),
              ("C6", NoteDuration.QUARTER),
              ("A#5", NoteDuration.EIGHTH),
              ("C6", NoteDuration.DOTTED_EIGHTH),
              ("B5", NoteDuration.SIXTEENTH),
              ("A#5", NoteDuration.EIGHTH),
              ("A#4", NoteDuration.QUARTER),
              ("G5", NoteDuration.EIGHTH),
              ("E5", NoteDuration.DOTTED_QUARTER),
              ("E5", NoteDuration.QUARTER),
              #
              ("G5", NoteDuration.EIGHTH),
              ("B5", NoteDuration.QUARTER),
              ("G5", NoteDuration.EIGHTH),
              ("B5", NoteDuration.QUARTER),
              ("G5", NoteDuration.EIGHTH),
              ("C6", NoteDuration.QUARTER),
              ("B5", NoteDuration.EIGHTH),
              ("A#5", NoteDuration.QUARTER),
              #
              ("F#5", NoteDuration.EIGHTH),
              ("G5", NoteDuration.DOTTED_EIGHTH),
              ("B5", NoteDuration.SIXTEENTH),
              ("A#5", NoteDuration.EIGHTH),
              ("A#4", NoteDuration.QUARTER),
              ("B4", NoteDuration.EIGHTH),
              ("B5", NoteDuration.DOTTED_QUARTER),
              ("G5", NoteDuration.QUARTER),
              #
              ("G5", NoteDuration.EIGHTH),
              ("B5", NoteDuration.QUARTER),
              ("G5", NoteDuration.EIGHTH),
              ("B5", NoteDuration.QUARTER),
              ("G5", NoteDuration.EIGHTH),
              ("D6", NoteDuration.QUARTER),
              ("C#6", NoteDuration.EIGHTH),
              ("C6", NoteDuration.QUARTER),
              ("A#5", NoteDuration.EIGHTH),
              ("C6", NoteDuration.DOTTED_EIGHTH),
              ("B5", NoteDuration.SIXTEENTH),
              ("A#5", NoteDuration.EIGHTH),
              ("A#4", NoteDuration.QUARTER),
              ("G5", NoteDuration.EIGHTH),
              ("E5", NoteDuration.DOTTED_QUARTER),
          ]))
  octave = [
      scale(
          sine_wave(frequency),
          scale(
              linear_adsr(
                  attack_duration=0.02,
                  decay_duration=0.02,
                  sustain_duration=note_duration_to_sec(duration),
                  release_duration=0.02,
                  sustain_level=0.8), hold(1))) for frequency, duration in notes
  ]

  pipe_to_wave(
      concatenate(*octave), "test.wav"
  )

###############################################################################

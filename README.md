SoxBindings
==============

Python bindings for SoX. An attempt to bind a subset of the capabilities of
the SoX command line utility but in Python via bindings for speed. This 
avoids costly exec calls when using augmentations in SoX. This is a
work in progress! Help welcome.

Installation from source
------------------------

soxbindings only supports Unix systems (Linux and OSX), due to how
one builds sox. A related library (torchaudio) has similar problems:
https://github.com/pytorch/audio/issues/425.

**On Unix (Linux, OS X) using Anaconda**

 - clone this repository
 - Make a conda environment
 - `conda install -c conda-forge sox`
 - If on Linux: `conda install gcc_linux-64 gxx_linux-64`
 - `pip install -e .`

Run the tests to make sure everything works:

```
python -m pytest .
```

The tests run a large variety of commands, all pulled from the pysox test 
cases. SoxBindings output is then compared with pysox output.

Usage
------

SoxBindings is built to be a drop-in replacement for the sox command
line tool, avoiding a costly exec call. Specifically, the way it works
is to provide an alternative backend to the excellent library that wraps
the command line tool [pysox](https://github.com/rabitt/pysox). SoxBindings
simply re-implements the `build` function in pysox `Transformer` classes. 

Note that `Combiner` classes in pysox are NOT supported.

If you have a script that works with pysox, like so:

```
import sox
# create transformer
tfm = sox.Transformer()
# trim the audio between 5 and 10.5 seconds.
tfm.trim(5, 10.5)
# apply compression
tfm.compand()
# apply a fade in and fade out
tfm.fade(fade_in_len=1.0, fade_out_len=0.5)
# create an output file.
tfm.build_file('path/to/input_audio.wav', 'path/to/output/audio.aiff')
# or equivalently using the legacy API
tfm.build('path/to/input_audio.wav', 'path/to/output/audio.aiff')
# get the output in-memory as a numpy array
# by default the sample rate will be the same as the input file
array_out = tfm.build_array(input_filepath='path/to/input_audio.wav')
# see the applied effects
tfm.effects_log
> ['trim', 'compand', 'fade']
```

Then, all you have to do is change the import:

```
import soxbindings as sox
```

and everything should work, but be faster because of the direct bindings
to libsox!

Deploying to PyPI
-----------------

The Github action workflow "Build wheels" gets run every time there is a commit
to master. When it's done, the wheels for OSX and Linux are created and place in
an artifact. For example:

https://github.com/pseeth/soxbindings/actions/runs/169544837

Download the artifact zip, then do the following steps:

```
unzip [/path/to/artifact.zip] 
```

License
-------

soxbindings is under an MIT license.


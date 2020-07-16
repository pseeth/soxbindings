SoxBindings
==============

[![Downloads](https://pepy.tech/badge/soxbindings)](https://pepy.tech/project/soxbindings)
![Tests](https://github.com/pseeth/soxbindings/workflows/Run%20tests/badge.svg)
![Wheels built](https://github.com/pseeth/soxbindings/workflows/Build%20wheels/badge.svg)

Python bindings for SoX. An attempt to bind a subset of the capabilities of
the SoX command line utility but in Python via bindings for speed. This 
avoids costly exec calls when using augmentations in SoX. This is a
work in progress! Help welcome.

soxbindings only supports Unix systems (Linux and OSX), due to how
one builds sox. A related library (torchaudio) has similar problems:
https://github.com/pytorch/audio/issues/425.

Install from pip
----------------

If on MacOS or Linux, just do:

`pip install soxbindings`

If on Windows, it's not supported but you *could* install sox from source, 
and then link libsox and get everything working possibly. If you do and figure
out an automated way to do it using `cibuildwheel`, please put in a PR adding
Windows support!

Installation from source
------------------------

**On Unix (Linux, OS X) using Anaconda**

 - clone this repository
 - Make a conda environment
 - `conda install -c conda-forge sox`
 - If on Linux: 
    - Option 1: `conda install gcc_linux-64 gxx_linux-64`
    - Option 2: `sudo apt-get install sox libsox-dev`
    - Option 3: build and install sox from source (e.g. as in `.github/workflows/build_install_sox_centos.sh`).
 - `pip install -e .`

Run the tests to make sure everything works:

```bash
pip install -r extra_requirements.txt
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

```python
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

```python
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

Download the artifact zip, then do the following steps from the root of the
soxbindings repo:

```bash
unzip [/path/to/artifact.zip]
# clear out dist
rm -rf dist/
# create source distribution
python setup.py sdist
cp -r [/path/to/artifact]/* dist/
```

The dist folder should look something like:

```
dist
├── soxbindings-0.0.1-cp35-cp35m-macosx_10_9_x86_64.whl
├── soxbindings-0.0.1-cp35-cp35m-manylinux2010_i686.whl
├── soxbindings-0.0.1-cp35-cp35m-manylinux2010_x86_64.whl
├── soxbindings-0.0.1-cp36-cp36m-macosx_10_9_x86_64.whl
├── soxbindings-0.0.1-cp36-cp36m-manylinux2010_i686.whl
├── soxbindings-0.0.1-cp36-cp36m-manylinux2010_x86_64.whl
├── soxbindings-0.0.1-cp37-cp37m-macosx_10_9_x86_64.whl
├── soxbindings-0.0.1-cp37-cp37m-manylinux2010_i686.whl
├── soxbindings-0.0.1-cp37-cp37m-manylinux2010_x86_64.whl
├── soxbindings-0.0.1-cp38-cp38-macosx_10_9_x86_64.whl
├── soxbindings-0.0.1-cp38-cp38-manylinux2010_i686.whl
├── soxbindings-0.0.1-cp38-cp38-manylinux2010_x86_64.whl
├── soxbindings-0.0.1-pp27-pypy_73-macosx_10_9_x86_64.whl
├── soxbindings-0.0.1-pp27-pypy_73-manylinux2010_x86_64.whl
├── soxbindings-0.0.1-pp36-pypy36_pp73-macosx_10_9_x86_64.whl
├── soxbindings-0.0.1-pp36-pypy36_pp73-manylinux2010_x86_64.whl
└── soxbindings-0.0.1.tar.gz
```

Upload it to the test server first (requires a version bump):

```
twine upload --repository testpypi dist/*
```

Make sure you can pip install it on both Linux and OSX:

```
pip install -U --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple -U soxbindings
```

Use the demo script included in this repo to try it out. 
Finally, upload it to the regular PyPi server:

```
twine upload dist/*
```


License
-------

soxbindings is under an MIT license.


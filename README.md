SoxBindings
==============

Python bindings for SoX. An attempt to bind a subset of the capabilities of
the SoX command line utility but in Python via bindings for speed. This 
avoids costly exec calls when using augmentations in SoX. This is a
work in progress! Help welcome.

Installation
------------

soxbindings only supports Unix systems (Linux and OSX), due to how
one builds sox. A related library (torchaudio) has similar problems:
https://github.com/pytorch/audio/issues/425.

**On Unix (Linux, OS X) using Anaconda**

 - clone this repository
 - Make a conda environment
 - `conda install -c conda-forge sox`
 - If on Linux: `conda install gcc_linux-64`
 - If on Linux: `conda install gxx_linux-64`
 - `pip install -e .`

Run the tests to make sure everything works:

```
python -m pytest .
```



Building the documentation
--------------------------

Documentation for the example project is generated using Sphinx. Sphinx has the
ability to automatically inspect the signatures and documentation strings in
the extension module to generate beautiful documentation in a variety formats.
The following command generates HTML-based reference documentation; for other
formats please refer to the Sphinx manual:

 - `cd python_example/docs`
 - `make html`

License
-------

soxbindings are under an MIT license.


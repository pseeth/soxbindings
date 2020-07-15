from sox import Transformer as BaseTransformer
from sox import file_info
from sox.transform import ENCODINGS_MAPPING

from sox.log import logger
from .sox_cli import sox
from .audio import get_info
import numpy as np

class Transformer(BaseTransformer):
        def build(self, input_filepath=None, output_filepath=None,
              input_array=None, sample_rate_in=None,
              extra_args=None, return_output=False):
            '''Builds the output file or output numpy array by executing the
            current set of commands. This function returns either the status
            of the command (when output_filepath is specified and return_output
            is False), or it returns a triple of (status, out, err) when
            output_filepath is None or return_output is True.
            Parameters
            ----------
            input_filepath : str or None
                Either path to input audio file or None.
            output_filepath : str or None
                Path to desired output file. If a file already exists at
                the given path, the file will be overwritten.
                If None, the output will be returned as an np.ndarray.
                If '-n', no file is created.
            input_array : np.ndarray or None
                A np.ndarray of an waveform with shape (n_samples, n_channels).
                If this argument is passed, sample_rate_in must also be provided.
                If None, input_filepath must be specified.
            sample_rate_in : int
                Sample rate of input_array.
                This argument is ignored if input_array is None.
            extra_args : list or None, default=None
                If a list is given, these additional arguments are passed to SoX
                at the end of the list of effects.
                Don't use this argument unless you know exactly what you're doing!
            return_output : bool, default=False
                If True, returns the status and information sent to stderr and
                stdout as a tuple (status, stdout, stderr).
                If output_filepath is None, return_output=True by default.
                If False, returns True on success.
            Returns
            -------
            status : bool
                True on success.
            out : str, np.ndarray, or None
                If output_filepath is None returns the output audio as a np.ndarray
                If output_filepath is not None and return_output is True, returns
                the stdout produced by sox.
                Otherwise, this output is not returned.
            err : str, or None
                If output_filepath is None or return_output is True, returns the
                stderr as a string.
                Otherwise, this output is not returned.
            Examples
            --------
            >>> import numpy as np
            >>> import sox
            >>> tfm = sox.Transformer()
            >>> sample_rate = 44100
            >>> y = np.sin(2 * np.pi * 440.0 * np.arange(sample_rate * 1.0) / sample_rate)
            file in, file out - basic usage
            >>> status = tfm.build('path/to/input.wav', 'path/to/output.mp3')
            file in, file out - equivalent usage
            >>> status = tfm.build(
                    input_filepath='path/to/input.wav',
                    output_filepath='path/to/output.mp3'
                )
            file in, array out
            >>> status, array_out, err = tfm.build(input_filepath='path/to/input.wav')
            array in, file out
            >>> status = tfm.build(
                    input_array=y, sample_rate_in=sample_rate,
                    output_filepath='path/to/output.mp3'
                )
            array in, array out
            >>> status, array_out, err = tfm.build(input_array=y, sample_rate_in=sample_rate)
            '''
            if input_filepath is not None and input_array is not None:
                raise ValueError(
                    "Only one of input_filepath and input_array may be specified"
                )

            # set input parameters
            input_format = self.input_format
            encoding = None
            if input_filepath is not None:
                file_info.validate_input_file(input_filepath)
                channels_in = get_info(input_filepath)[0].channels
            elif input_array is not None:
                if not isinstance(input_array, np.ndarray):
                    raise TypeError("input_array must be a numpy array or None")
                if sample_rate_in is None:
                    raise ValueError(
                        "sample_rate_in must be specified if input_array is specified"
                    )
                input_filepath = '-'
                channels_in = (
                    input_array.shape[-1] if len(input_array.shape) > 1 else 1
                )
                encoding = input_array.dtype.type
                input_format = self._input_format_args(
                    ENCODINGS_MAPPING[encoding], sample_rate_in, None,
                    channels_in, None, False
                )
            else:
                raise ValueError(
                    "One of input_filepath or input_array must be specified"
                )

            # set output parameters
            output_format = self.output_format
            if output_filepath is not None:
                if input_filepath == output_filepath:
                    raise ValueError(
                        "input_filepath must be different from output_filepath."
                    )
                file_info.validate_output_file(output_filepath)
                array_output = False
            else:
                ignored_commands = ['rate', 'channels', 'convert']
                if len(list(set(ignored_commands) & set(self.effects_log))) > 0:
                    logger.warning(
                        "When outputting to an array, rate, channels and convert" +
                        " effects may be ignored. Use set_output_format() to " +
                        "specify output formats."
                    )

                output_filepath = '-'
                channels_out = channels_in
                encoding_out = (np.int16 if encoding is None else encoding)
                n_bits = np.dtype(encoding_out).itemsize * 8
                if output_format == []:
                    output_format = self._output_format_args(
                        'raw', sample_rate_in, n_bits,
                        channels_out, None, None, True
                    )
                else:
                    channels_idx = [
                        i for i, f in enumerate(output_format) if f == '-c'
                    ]
                    if len(channels_idx) == 1:
                        channels_out = int(output_format[channels_idx[0] + 1])

                    bits_idx = [
                        i for i, f in enumerate(output_format) if f == '-b'
                    ]
                    if len(bits_idx) == 1:
                        n_bits = int(output_format[bits_idx[0] + 1])
                        if n_bits == 8:
                            encoding_out = np.int8
                        elif n_bits == 16:
                            encoding_out = np.int16
                        elif n_bits == 32:
                            encoding_out = np.float32
                        elif n_bits == 64:
                            encoding_out = np.float64
                        else:
                            raise ValueError("invalid n_bits {}".format(n_bits))

                array_output = True

            args = []
            args.extend(self.globals)
            args.extend(input_format)
            args.append(input_filepath)
            args.extend(output_format)
            args.append(output_filepath)
            args.extend(self.effects)

            if extra_args is not None:
                if not isinstance(extra_args, list):
                    raise ValueError("extra_args must be a list.")
                args.extend(extra_args)

            output_audio, sample_rate_out = sox(args, input_array, sample_rate_in)
            return 0, output_audio, 0

"""
Python equivalent of the `sox` command, using 
libsox bindings instead. Parses command line
args as if you passed it to the traditional
sox command line tool. This is helpful for 
avoiding an exec call when using sox in other
scripts. This is all powered by Python bindings
into libsox.

One important change is that special filenames 
like '-' are done with numpy arrays instead.
"""

import numpy as np
import re


from . import (
    read, 
    write, 
    get_info,
    get_available_effects, 
    initialize_sox, 
    quit_sox,
    SoxEffect,
    build_flow_effects,
)

PIPE_CHAR = '-'
GLOBAL_OPTIONS = [
    '-D',
    '-G',
    '-V0',
    '-V1',
    '-V2',
    '-V3',
]
IGNORED_OPTIONS = [
    '--ignore-length'
]


# single input, single output
def sox(args, input_audio=None, sample_rate_in=None):
    """
    Main entry point into sox. Parses the arguments.
    Only works for single input/single output 
    combination.  Supports numpy arrays that
    already have the samples loaded via some 
    other means (e.g. soxbindings.read, soundfile.read),
    etc. Alternatively, can be read off the command line
    arguments `args`.
    
    Note:
        Does not implement combine operations, only 
        effects chains!

    Args:
        args (str): Command line arguments to sox.
    """
    if isinstance(args, str):
        args = args.split()
    if args[0] == 'sox':
        args.pop(0)
    available_fx = get_available_effects()
    fx_idx = [a in available_fx for a in args]
    if True in fx_idx:
        fx_idx = fx_idx.index(True)
    else:
        fx_idx = len(fx_idx)

    io_args = args[:fx_idx]
    fx_args = args[fx_idx:]
    flags = []
    i = 0
    while (i < len(io_args)):
        io_arg = io_args[i]
        if io_arg != PIPE_CHAR:
            if io_arg.startswith('-'):
                _flag = [io_arg]
                if (
                    i < len(io_args)-1 and 
                    not io_args[i+1].startswith('-')
                    and io_arg not in GLOBAL_OPTIONS
                    and io_arg not in IGNORED_OPTIONS
                ):
                    _flag.append(io_args[i+1])
                    i += 1
                flags.append(tuple(_flag))
            else:
                flags.append(('file', io_arg))
        else:
            flags.append(('file', io_arg))
        i += 1
    
    # check for combine
    if '--combine' in io_args:
        raise NotImplementedError("--combine is not implemented!")
    
    group = []
    groups = []
    for i, flag in enumerate(flags):
        group.append(flag)
        if flag[0] == "file":
            groups.append(group)
            group = []
    
    global_args = []
    group0 = []
    for g in groups[0]:
        if g[-1] in GLOBAL_OPTIONS:
            global_args.append(g[-1])
        else:
            group0.append(g)

    groups[0] = group0
    
    files = [x[-1][-1] for x in groups]
    input_file = files[0]
    output_file = files[-1]

    # figure out how to modify each file according
    # to the flags.
    in_channels = None
    in_precision = 32
    out_channels = None
    sample_rate_out = None
    out_precision = None

    for flag in groups[0]:
        if flag[0] == '-c':
            in_channels = int(flag[1])
        if flag[0] == '-b':
            in_precision = int(flag[1])
        if flag[0] == '-r':
            sample_rate_in = float(flag[1])

    if input_audio is None:
        input_audio, sample_rate_in = read(input_file)
        read_channels = input_audio.shape[-1]
        if in_channels is None:
            in_channels = read_channels
        elif in_channels != read_channels:
            input_audio = input_audio.reshape(-1, in_channels)
    
    sox_effects_chain = []
    add_rate = False

    for flag in groups[1]:
        if flag[0] == '-r':
            sample_rate_out = float(flag[1])
            add_rate = True
        if flag[0] == '-c':
            fx_args.extend(['channels', flag[1]])
            out_channels = int(flag[1])
        if flag[0] == '-b':
            out_precision = int(flag[1])

    fx_group = []
    fx_groups = []
    for i, fx_arg in enumerate(fx_args):
        if fx_arg in available_fx:
            if fx_group:
                fx_groups.append(fx_group)
                fx_group = []
        fx_group.append(fx_arg)
        
    if fx_group:
        fx_groups.append(fx_group)
    current_sample_rate = sample_rate_in

    for fx in fx_groups:
        sox_effect = SoxEffect()
        sox_effect.effect_name = fx[0]
        
        parsed_fx_args = fx[1:]

        if fx[0] == "mcompand":
            parsed_fx_args = ' '.join(parsed_fx_args)
            parsed_fx_args = re.split('(\S+ \S+) (\S+ ) ', parsed_fx_args)[1:]
            parsed_fx_args = [x.rstrip() for x in parsed_fx_args]
                
        sox_effect.effect_args = parsed_fx_args
        if not sox_effect.effect_args:
            sox_effect.effect_args = [""]
        sox_effects_chain.append(sox_effect)

        # if it's pitch, then we need to add rate at the end of the chain
        if fx[0] == "pitch" or fx[0] == "speed":
            add_rate = True
            sample_rate_out = current_sample_rate
        
        if fx[0] == "channels":
            out_channels = int(fx[1])
        if fx[0] == "rate":
            current_sample_rate = float(fx[-1])
            sample_rate_out = current_sample_rate

        if fx[0] == "remix":
            out_channels = len(fx) - 1
        if fx[0] == "reverb":
            # if reverb, add channels effect if out_channels is None
            if out_channels is None:
                sox_effect = SoxEffect()
                sox_effect.effect_name = "channels"
                sox_effect.effect_args = [str(in_channels)]
                sox_effects_chain.append(sox_effect)
    
    if add_rate:
        sox_effect = SoxEffect()
        sox_effect.effect_name = "rate"
        sox_effect.effect_args = [str(sample_rate_out)]
        sox_effects_chain.append(sox_effect)
    
    if len(sox_effects_chain) == 0:
        sox_effect = SoxEffect()
        sox_effect.effect_name = "no_effects"
        sox_effect.effect_args = [""]
        sox_effects_chain.append(sox_effect)  
      
    if out_precision is None:
        out_precision = in_precision
    
    if input_audio is not None:
        output_audio, rate = build_flow_effects(
            input_audio,
            sample_rate_in,
            sox_effects_chain,
            in_channels=in_channels,
            in_precision=in_precision,
            out_channels=out_channels,
            out_precision=out_precision,
            sample_rate_out=sample_rate_out
        )
        if output_file != PIPE_CHAR:
            write(output_file, output_audio, rate, out_precision)
        return output_audio, rate

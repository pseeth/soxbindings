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



def sox(args, input_audio=None, sample_rate_in=None):
    """
    Main entry point into sox. Parses the arguments.

    Args:
        args (str): Command line arguments to sox.
    """
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
    parsed = []

    for i, io_arg in enumerate(io_args):
        if io_arg not in parsed:
            if io_arg != PIPE_CHAR:
                if io_arg.startswith('-'):
                    _flag = [io_arg]
                    if (
                        i < len(io_args)-1 and 
                        not io_args[i+1].startswith('-')
                        and io_arg not in GLOBAL_OPTIONS
                    ):
                        _flag.append(io_args[i+1])
                    parsed.extend(_flag)
                    flags.append(tuple(_flag))
                else:
                    flags.append(('file', io_arg))
            else:
                flags.append(('file', io_arg))
    
    # check for combine
    if '--combine' in io_args:
        return

    # gonna ignore bits etc for now...
    group = []
    groups = []
    for i, flag in enumerate(flags):
        group.append(flag)
        if flag[0] == "file":
            groups.append(group)
            group = []
    
    files = [x[-1][-1] for x in groups]
    input_files = files[:-1]
    output_file = files[-1]

    if input_audio is None:
        input_audio = [read(f) for f in input_files]
    else:
        input_audio = [(input_audio, sample_rate_in)]

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
    sox_effects_chain = []

    for fx in fx_groups:
        sox_effect = SoxEffect()
        sox_effect.effect_name = fx[0]
        
        parsed_fx_args = fx[1:]

        if fx[0] == "mcompand":
            parsed_fx_args = ' '.join(parsed_fx_args)
            parsed_fx_args = re.split('(\S+ \S+) (\S+ )', parsed_fx_args)[1:]
            parsed_fx_args = [x.rstrip() for x in parsed_fx_args]

        sox_effect.effect_args = parsed_fx_args
        if not sox_effect.effect_args:
            sox_effect.effect_args = [""]
        sox_effects_chain.append(sox_effect)

        # if it's pitch, then we need to add rate too
        if fx[0] == "pitch":
            sox_effect = SoxEffect()
            sox_effect.effect_name = "rate"
            sox_effect.effect_args = [str(input_audio[0][1])]
            sox_effects_chain.append(sox_effect)
    
    if len(sox_effects_chain) == 0:
        sox_effect = SoxEffect()
        sox_effect.effect_name = "no_effects"
        sox_effect.effect_args = [""]
        sox_effects_chain.append(sox_effect)
    
    if input_audio:
        output_audio, rate = build_flow_effects(
            input_audio[0][0],
            input_audio[0][1],
            sox_effects_chain,
        )

        if output_file != PIPE_CHAR:
            write(output_file, output_audio, rate)
        return output_audio, rate

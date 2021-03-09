#  Copyright (c) 2021, Greg Michael
#  Licensed under BSD 3-Clause License. See LICENSE.txt for details.

import argparse
import numpy as np
import re

import gm
import craterstats3 as cs3
import demo


class AppendPlotDict(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        s=' '.join(values)
        d = {}
        for kv in re.split(',(?=\w+=)',s): # only split on commas directly preceding keys
            k, v = kv.split("=")
            if k in ('range','offset_age'):
                v=gm.read_textstructure(kv,from_string=True)[k]
            d[k] = v
        list_of_d = getattr(namespace, self.dest)
        list_of_d=[d] if list_of_d is None else list_of_d+[d]
        setattr(namespace, self.dest, list_of_d)

class SpacedString(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, ' '.join(values))


def parse_args(args):
    parser = argparse.ArgumentParser(description='Craterstats: a tool to analyse and plot crater count data for planetary surface dating.')

    parser.add_argument("-lcs", help="list chronology systems", action='store_true')
    #parser.add_argument("-lt", help="list templates", action='store_true')
    parser.add_argument("-lpc", help="list plot symbols and colours", action='store_true')
    parser.add_argument("-about", help="show program details", action='store_true')
    parser.add_argument("-demo", help="run sequence of demonstration commands: output in ./demo", action='store_true')
    parser.add_argument("-src", help="take command line parameters from text file", nargs='+', action=SpacedString)

    parser.add_argument("-t", "--template", help="plot template", nargs='+', action=SpacedString)
    parser.add_argument("-o","--out", help="output filename (omit extension for default)", nargs='+', action=SpacedString)
    parser.add_argument("-as","--autoscale", help="rescale plot axes", action='store_true')
    parser.add_argument("-f", "--format", help="output formats",  nargs='+', choices=['png','jpg','tif','pdf','svg','txt'])
    parser.add_argument("--transparent", help="set transparent background", action='store_true')

    parser.add_argument("-cs", "--chronology_system", help="chronology system index",  type=int)
    parser.add_argument("-ef", "--equilibrium", help="equilibrium function index",  type=int)
    parser.add_argument("-ep", "--epochs", help="epoch system index",  type=int)

    parser.add_argument("-title", help="plot title", nargs='+', action=SpacedString)
    parser.add_argument("-subtitle", help="plot subtitle", nargs='+', action=SpacedString)
    parser.add_argument("-pi","--presentation", choices=range(1,7), metavar="[1-6]", default=2, type=int, dest='presentation_index',
        help="data presentation index: "+(', ').join([str(i+1)+'-'+e for i,e in enumerate(cs3.PRESENTATIONS)]))
    parser.add_argument("-xrange", help="x-axis range, log(min) log(max)", nargs=2)
    parser.add_argument("-yrange", help="y-axis range, log(min) log(max)", nargs=2)
    parser.add_argument("-isochrons", help="comma-separated isochron list in Ga, e.g. 1,3,3.7a,4a (optional combined suffix to modify label: n - suppress; a - above; s - small)")
    parser.add_argument("-show_isochrons", choices=['0', '1'], help="1 - show; 0 - suppress")
    parser.add_argument("-legend", help="any combination of: n - name; a - area; # - number of craters; r - range; N - N(d_ref) value")
    parser.add_argument("-cite_functions", choices=['0','1'], help="1 - show; 0 - suppress")
    parser.add_argument("-mu", choices=['0','1'], help="1 - show; 0 - suppress")
    parser.add_argument("-style", choices=['natural', 'root-2'], help="diameter axis style")
    parser.add_argument("-invert", choices=['0','1'], help="1 - invert to black background; 0 - white background")

    parser.add_argument("-print_dim", help="print dimensions: either single value (cm/decade) or enclosing box (AxB), e.g. 2 or 8x8", nargs=1)
    parser.add_argument("-pt_size", type=float, help="point size for figure text")
    parser.add_argument("-ref_diameter", type=float, help="reference diameter for displayed N(d_ref) values")
    parser.add_argument("-sf","--sig_figs", type=int, choices=[2,3], help="number of significant figures for displayed ages")

    parser.add_argument("-p", "--plot", nargs='+', action=AppendPlotDict, metavar="KEY=VAL,",
                        help="specify overplot. Allowed keys:   \n"
                             "source=txt,"
                             "name=txt,"
                             "range=[min,max],"
                             "type={data,poisson,c-fit,d-fit},"
                             "error_bars={1,0},"
                             "hide={1,0},"
                             "colour={0-31},"
                             "psym={0-14},"
                             "binning={" +','.join(cs3.Cratercount.BINNINGS) + "},"
                             "age_left={1,0},"
                             "display_age={1,0},"
                             "resurf={1,0}, apply resurfacing correction,"
                             "resurf_showall={1,0}, show all data with resurfacing correction,"
                             "isochron={1,0}, show whole fitted isochron,"
                             "offset_age=[x,y], in 1/20ths of decade")

    return parser.parse_args(args)


def construct_cps_dict(args,c,f):
    cpset=c['set']
    if 'presentation_index' in vars(args):
        cpset['presentation']=cs3.PRESENTATIONS[args.presentation_index-1]
    if cpset['presentation'] in ['chronology', 'rate']: #possible to overwrite with user-choice
        cpset['xrange'] = cs3.DEF_XRANGE[args.presentation_index-1]
        cpset['yrange'] = cs3.DEF_YRANGE[args.presentation_index-1]
    cpset['format'] = set(cpset['format']) if 'format' in cpset else {}

    for k,v in vars(args).items():
        if v is not None:
            if k in ('title',
                     'subtitle',
                     'isochrons',
                     'show_isochrons',
                     'legend',
                     'print_dimensions',
                     'pt_size',
                     'ref_diameter',
                     'cite_functions',
                     'sig_figs',
                     'randomness',
                     'mu',
                     'invert',
                     'show_title',
                     'show_subtitle',
                     'style',
                     'xrange', 'yrange',
                     ):
                cpset[k]=v
            if k in ('chronology_system','equilibrium','epochs'):
                d=f[k][np.clip(v-1,0,len(f[k]))]
                cpset[k]=d['name']
            if k == 'out':
                cpset[k] = gm.filename(v, 'pn')
                ext=gm.filename(v, 'e').lstrip('.')
                if ext: cpset['format'].add(ext)
            if k == 'format':
                cpset[k]=set(v)

    cs=next((e for e in f['chronology_system'] if e['name'] == cpset['chronology_system']), None)
    if cs is None: raise ValueError('Chronology system not found:' + cpset['chronology_system'])

    cpset['cf'] = cs3.Chronologyfn(f, cs['cf'])
    cpset['pf'] = cs3.Productionfn(f, cs['pf'])

    if 'equilibrium' in cpset and cpset['equilibrium'] not in (None,''):
        cpset['ef'] = cs3.Productionfn(f, cpset['equilibrium'], equilibrium=True)
    if 'epochs' in cpset and cpset['epochs'] not in (None,''):
        cpset['ep'] = cs3.Epochs(f, cpset['epochs'],cpset['pf'],cpset['cf'])

    if cpset['presentation'] == 'Hartmann':
        if hasattr(cpset['pf'],'xrange'): #not possible to overwrite with user choice
            cpset['xrange'] = cpset['pf'].xrange
            cpset['yrange'] = cpset['pf'].yrange
        else:
            cpset['xrange'] = cs3.DEF_XRANGE[3]
            cpset['yrange'] = cs3.DEF_YRANGE[3]
    if cpset['out'] is None:
        cpset['out']='out' # don't set as default in parse_args: need to detect None in source_cmds
    return cpset


def construct_plot_dicts(args, c):
    plot = c['plot']
    if type(plot) is list: plot=plot[0] #take only first plot entry as template
    cpl = []
    if args.plot is None: return []
    for d in args.plot:
        p=plot.copy()
        if cpl: # for these items: if not given, carry over from previous
            for k in ['source','psym','type','isochron','error_bars','colour','binning']:
                p[k] = cpl[-1][k]
        else:
            if not 'source' in d: raise ValueError('Source not specified')

        for k,v in d.items():
            if k in (
                    'source',
                    'name',
                    'range',
                    'type',
                    'error_bars',
                    'hide',
                    'colour',
                    'psym',
                    'binning',
                    'age_left',
                    'display_age',
                    'resurf',
                    'resurf_showall',
                    'isochron',
                    'offset_age',
                    ):
                p[k]=v
        p['cratercount'] = cs3.Cratercount(p['source'])
        cpl += [p]
    return cpl


def source_cmds(src):
    cmd=gm.read_textfile(src,ignore_blank=True,ignore_hash=True)
    for i,c in enumerate(cmd):
        print(f'\nCommand: {i}\npython craterstats.py '+c)
        a=parse_args(c.split())
        if a.out is None: a.out='{:02d}-out'.format(i)
        main(a)
    print('\nProcessing complete.')

def main(args):
    template="config/default.plt"
    functions="config/functions.txt"

    c = gm.read_textstructure(template if args.template is None else args.template)
    f = gm.read_textstructure(functions)

    if args.lcs:
        print(gm.bright("\nChronology systems:"))
        print('\n'.join(['{0} {1}'.format(i + 1, e['name']) for i, e in enumerate(f['chronology_system'])]))
        print(gm.bright("\nEquilibrium functions:"))
        print('\n'.join(['{0} {1}'.format(i + 1, e['name']) for i, e in enumerate(f['equilibrium'])]))
        print(gm.bright("\nEpoch systems:"))
        print('\n'.join(['{0} {1}'.format(i + 1, e['name']) for i, e in enumerate(f['epochs'])]))
        return

    if args.lpc:
        print(gm.bright("\nPlot symbols:"))
        print('\n'.join(['{0} {1}'.format(i, e[1]) for i, e in enumerate(cs3.MARKERS)]))
        print(gm.bright("\nColours:"))
        print('\n'.join(['{0} {1}'.format(i, e[2]) for i, e in enumerate(cs3.PALETTE)]))
        return

    if args.about:
        print('\n'.join(cs3.ABOUT))
        return

    if args.src:
        source_cmds(args.src)
        return

    if args.demo:
        demo.demo()
        return

    cps_dict = construct_cps_dict(args, c, f)
    cp_dicts = construct_plot_dicts(args, c)
    cpl = [cs3.Craterplot(d) for d in cp_dicts]

    cps=cs3.Craterplotset(cps_dict,craterplot=cpl)

    if args.autoscale or not ('xrange' in cps_dict and 'yrange' in cps_dict):
        cps.autoscale()

    drawn=False
    for f in cps.format:
        if f in {'png','jpg','pdf','svg','tif'}:
            if not drawn:
                cps.draw()
                drawn=True
            cps.fig.savefig(cps_dict['out']+'.'+f, dpi=500, transparent=args.transparent)
        if f in {'txt'}:
            cps.create_summary_file()

if __name__ == '__main__':
    args = parse_args(None)
    main(args)
"""
rasterlinefilter.py - describe

Terry Brown, Terry_N_Brown@yahoo.com, Tue Mar 10 13:07:28 2015
"""

import argparse
import os
import sys

def make_parser():
     
    parser = argparse.ArgumentParser(
        description="""Clasify lines by rasters""",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument("--step-length", type=float, default=10.,
        help="How much line to skip before adding a node, if needed"
    )
    parser.add_argument("--class", type=str, dest="class_", action='append',
        help="Name of an output classification class"
    )
    parser.add_argument("--values", type=str, action='append',
        help="Raster values (classes), space or comma separated, "
             "for preceding output class.  NoData for no data, * for "
             "all remaining values"
    )
    parser.add_argument("--fields", type=str, nargs='+',
        help="Field names, space or , separated, "
             "to copy from `lines` input to output."
    )
    parser.add_argument("--range", type=str, action='append',
        help="Two raster values, space separated, min max, for "
             "preceding output class NOT IMPLEMENTED"
    )
    parser.add_argument("--band", type=int, default=0,
        help="Raster band to use"
    )
    parser.add_argument("lines", type=str,
        help="Path to OGR datasource (shapefile) containing lines"
    )
    parser.add_argument("grid", type=str,
        help="Path to GDAL datasource (grid) containing raster"
    )

    return parser

def main():
    opt = make_parser().parse_args()

    if not validate_options(opt):
        exit(1)

def validate_options(opt):
    
    print("%d classes, %d value lists, %s" % 
          (len(opt.class_), len(opt.values), 
           "ok" if len(opt.class_) == len(opt.values) else
           "ERROR: MUST BE EQUAL NUMBER OF EACH"))
           
    if len(opt.class_) != len(opt.values):
        return False
    
    # split space / comma separated values into lists
    ndint = lambda x: x if x in ('NoData', '*') else int(x)
    opt.values = [[ndint(j) for j in i.replace(',', ' ').split()]
                  for i in opt.values]
    # make wild card containing class(es) last,
    # need to sort values *and* class list
    # http://stackoverflow.com/questions/7851077/how-to-return-index-of-a-sorted-list
    new_order = sorted(range(len(opt.values)), key=lambda k: '*' in opt.values[k])
    opt.values = [opt.values[i] for i in new_order]
    opt.class_ = [opt.class_[i] for i in new_order]
    
    for class_, values in zip(opt.class_, opt.values):
        print(class_)
        print("  %s" % values)
if __name__ == '__main__':
    main()

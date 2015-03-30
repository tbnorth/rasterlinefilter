"""
rasterlinefilter.py - describe

Terry Brown, Terry_N_Brown@yahoo.com, Tue Mar 10 13:07:28 2015
"""

import argparse
import os
import sys

from osgeo import gdal
from osgeo import gdalconst
from osgeo import gdal_array
from osgeo import ogr
from osgeo import osr

import numpy as np
def classify_lines(opt, lines, grid):
    """classify_lines - 

    :param Namespace opt: argparse command line options
    :param OGR layer lines: lines to classify
    :param OGR grid grid: grid for classification

    :return: None
    """

    srs = osr.SpatialReference(grid.GetProjectionRef())
    driver = ogr.GetDriverByName("ESRI Shapefile")
    data_source = driver.CreateDataSource(opt.output)
    output = data_source.CreateLayer(
        os.path.basename(opt.output), srs, ogr.wkbLineString)
    output.CreateField(ogr.FieldDefn("id", ogr.OFTInteger))

    for id_, line in iterate_lines(lines, srs):
        feature = ogr.Feature(output.GetLayerDefn())
        feature.SetField("id", id_)
        linestring = ogr.Geometry(ogr.wkbLineString)
        for point, is_vertex in walk_line(line, opt.step_length, opt.tolerance):
            print(id_, point, is_vertex)
            linestring.AddPoint(point[0], point[1])
        feature.SetGeometry(linestring)
        output.CreateFeature(feature)
        feature.Destroy()
        
    data_source.Destroy()
def get_grid(opt):
    """get_grid - get GDAL grid data source

    :param Namespace opt: argparse command line options
    :return: GRID
    """

    grid = gdal.Open(opt.grid)
    return grid
def get_lines(opt):
    """get_lines - get OGR line data source

    :param Namespace opt: argparse command line options
    :return: OGR layer
    """

    datasource = ogr.Open(opt.lines)
    layer = datasource.GetLayer(0)
    layer._datasource = datasource  # prevent seg. fault
    return layer

def iterate_lines(layer, srs):
    """iterate_lines - Generator yielding line strings with feature id

    :Parameters:
    - `layer`: OGR layer
    - `srs`: transform to this SRS
    """

    for feature in layer:
        id_ = feature.GetFieldAsInteger('id')
        lines = feature.GetGeometryRef()
        lines = lines.Clone()
        lines.TransformTo(srs)
        if lines.GetGeometryName() == 'LINESTRING':
            # otherwise it's a MULTILINESTRING
            lines = [lines]
        for line in lines:
            yield (id_, line)
def make_parser():
     
    parser = argparse.ArgumentParser(
        description="""Clasify lines by rasters""",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument("--step-length", type=float, default=10.,
        help="How much line to skip before adding a node, if needed"
    )
    parser.add_argument("--tolerance", type=float, default=1.,
        help="Increase / decrease step-length this much to get to next vertex"
    )
    parser.add_argument("--min-steps", type=int, default=1,
        help="How many step-length steps in a class are needed to "
             "switch to that class - setting for all classes"
    )
    parser.add_argument("--class-steps", type=int, action='append', default=[],
        help="How many step-length steps in the last class defined are needed to "
             "switch to that class - class specific setting"
    )
    parser.add_argument("--class", type=str, dest="class_", action='append',
        help="Name of an output classification class", default=[]
    )
    parser.add_argument("--values", type=str, action='append',
        help="Raster values (classes), space or comma separated, "
             "for preceding output class.  NoData for no data, * for "
             "all remaining values", default=[]
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
    parser.add_argument("output", type=str,
        help="Basename for output shapefile"
    )

    return parser

def main():

    opt = make_parser().parse_args()

    if not validate_options(opt):
        exit(1)

    lines = get_lines(opt)
    grid = get_grid(opt)

    classify_lines(opt, lines, grid)
def validate_options(opt):
    
    ok = (len(opt.class_) == len(opt.values) and
          (not opt.class_steps or 
           len(opt.class_steps) == len(opt.class_)))
    
    print("%d classes, %d value lists, %d class specific min-steps %s" % 
          (len(opt.class_), len(opt.values), len(opt.class_steps), 
           "ok" if ok else "ERROR: MUST BE EQUAL NUMBER OF EACH"))
    if not ok:
        return False
        
    if not opt.class_steps:
        opt.class_steps = [opt.min_steps] * len(opt.class_)
    
    # split space / comma separated values into lists
    ndint = lambda x: x if x in ('NoData', '*') else int(x)
    opt.values = [[ndint(j) for j in i.replace(',', ' ').split()]
                  for i in opt.values]
    # make wildcard ('*') containing class(es) last, but we
    # need to sort values *and* class and class-steps list
    # http://stackoverflow.com/questions/7851077/how-to-return-index-of-a-sorted-list
    new_order = sorted(range(len(opt.values)), key=lambda k: '*' in opt.values[k])
    opt.values = [opt.values[i] for i in new_order]
    opt.class_ = [opt.class_[i] for i in new_order]
    opt.class_steps = [opt.class_steps[i] for i in new_order]
    
    for class_, values, steps in zip(opt.class_, opt.values, opt.class_steps):
        print("'%s', requires %d step%s in:" % 
              (class_, steps, 's' if steps > 1 else ''))
        print("  %s" % values)
    
    return ok
def walk_line(line, step_length, tolerance):
    """walk_line - generator to return points on a line

    :param OGR LineString line: line to walk
    :param float step_length: step distance
    :param float tolerance: distance to expand / contract step_length if
                            it allows reaching the next vertex on
                            the line
    :yields: OGR Point
    """

    for point in line.GetPoints():
        yield point, True
if __name__ == '__main__':
    main()

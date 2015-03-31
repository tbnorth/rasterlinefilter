"""
rasterlinefilter.py - describe

Terry Brown, Terry_N_Brown@yahoo.com, Tue Mar 10 13:07:28 2015
"""

import argparse
import os
import struct
import sys

from collections import defaultdict
from math import sqrt

from osgeo import gdal
from osgeo import gdalconst
from osgeo import gdal_array
from osgeo import ogr
from osgeo import osr

import numpy as np
class OutOfBounds(Exception):
    pass
class UnknownClass(Exception):
    pass
def classify_lines(opt, lines, grid):
    """classify_lines - 

    :param Namespace opt: argparse command line options
    :param OGR layer lines: lines to classify
    :param OGR grid grid: grid for classification

    :return: None
    """

    srs = osr.SpatialReference(grid.GetProjectionRef())
    
    if opt.get_classes:
        output = None
    else:
        driver = ogr.GetDriverByName("ESRI Shapefile")
        data_source = driver.CreateDataSource(opt.output)
        output = data_source.CreateLayer(
            os.path.basename(opt.output), srs, ogr.wkbLineString)
        layer_def = lines.GetLayerDefn()
        for i in range(layer_def.GetFieldCount()):  # copy field def's
            if layer_def.GetFieldDefn(i).GetName() in opt.fields:
                output.CreateField(layer_def.GetFieldDefn(i))
        output.CreateField(ogr.FieldDefn('lineclass', ogr.OFTString))
            
    class_count = defaultdict(lambda: 0)  # points in each class
    
    raw2reclass = {}
    for n, values in enumerate(opt.values):
        for i in values:
            raw2reclass[i] = n
    
    for value, line in iterate_lines(lines, srs, opt.fields):

        # collect and classify all the points for the line before
        # emitting anything.  'points are' ((x,y), is_vertex)
        points = [i for i in walk_line(line, opt.step_length, opt.stretch)]
        
        class_raw = [get_raw_class(point[0], grid) for point in points]

        for i in class_raw:
            class_count[i] += 1
            
        if not output:
            continue

        reclass = [raw2reclass[i] for i in class_raw]
        
        # make a list of the block sizes for each block, i.e.
        # 0 0 0 0 1 1 1 0 0 1 1 1 1 1 1  <- reclass
        # 4 4 4 4 3 3 3 2 2 6 6 6 6 6 6  <- counts
        counts = [0] * len(reclass)
        start, end = 0, 1
        while end <= len(reclass):
            if end == len(reclass) or reclass[start] != reclass[end]:
                counts[start:end] = [end-start] * (end-start)
                start = end
            end += 1
            
        # start in the middle of the list
        n0 = int(len(reclass) / 2)
        n1 = n0
        # move outwards looking for a block that meets
        # its class_steps threshold
        while True:
            if counts[n0] >= opt.class_steps[reclass[n0]]:
                n = n0
                break
            if counts[n1] >= opt.class_steps[reclass[n1]]:
                n = n1
                break
            if n0 == 0 and n1 == len(reclass)-1:
                n = None
                break
            n0 = max(0, n0-1)
            n1 = min(len(reclass)-1, n1+1)

        final_class = list(reclass)

        # propagate that block outwards to fill deficient blocks
        if n is not None:
            for limit, delta in (0, -1), (len(reclass)-1, +1):
                i = n
                class_ = reclass[i]
                while i != limit:
                    if counts[i] >= opt.class_steps[reclass[i]]:
                        class_ = reclass[i]
                    else:
                        final_class[i] = class_
                    i += delta
        
        cur_class = None
        for n in range(len(points)):
            if cur_class != final_class[n]:
                if cur_class is not None:
                    linestring.AddPoint(points[n][0][0], points[n][0][1])
                    feature.SetGeometry(linestring)
                    output.CreateFeature(feature)
                    feature.Destroy()
                cur_class = final_class[n]
                feature = ogr.Feature(output.GetLayerDefn())
                for field in opt.fields:
                    feature.SetField(field, value[field])
                feature.SetField('lineclass', opt.class_[cur_class])
                linestring = ogr.Geometry(ogr.wkbLineString)
            linestring.AddPoint(points[n][0][0], points[n][0][1])
            
        feature.SetGeometry(linestring)
        output.CreateFeature(feature)
        feature.Destroy()
        
    if output:
        data_source.Destroy()
    
    return class_count
def get_grid(opt):
    """get_grid - get GDAL grid data source

    :param Namespace opt: argparse command line options
    :return: GRID
    """

    grid = gdal.Open(opt.grid)
    
    gt = grid.GetGeoTransform()
    grid._gt_rows = grid.RasterYSize
    grid._gt_cols = grid.RasterXSize
    grid._gt_left = gt[0]
    grid._gt_top = gt[3]
    grid._gt_sizex = gt[1]
    grid._gt_sizey = -gt[5]
    grid._gt_bottom = grid._gt_top - grid._gt_sizey * grid._gt_rows
    grid._gt_right = grid._gt_left + grid._gt_sizex * grid._gt_cols


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
def get_raw_class(point, grid, band_num=1):
    """get_raw_class - get grid value for point

    Assumes same projection (ensured elsewhere)

    :param point point: OGR point
    :param GDAL grid grid: GDAL grid
    :return: grid value at point
    """

    cellx = int( (point[0] - grid._gt_left) / grid._gt_sizex )
    celly = int( (grid._gt_top - point[1]) / grid._gt_sizey )
    
    if (cellx < 0 or celly < 0 or 
        cellx > grid._gt_cols-1 or celly > grid._gt_rows-1):
        raise OutOfBounds
        
    band = grid.GetRasterBand(band_num)
    
    value = band.ReadRaster(cellx, celly, 1, 1, band.DataType)
    
    fmt = {
        gdal.GDT_Byte: 'b',
        gdal.GDT_UInt16: 'h',
    }
    
    value = struct.unpack(fmt[band.DataType], value)[0]
    return value

    
def iterate_lines(layer, srs, fields):
    """iterate_lines - Generator yielding line strings with feature id

    :Parameters:
    - `layer`: OGR layer
    - `srs`: transform to this SRS
    - `fields`: list of field names to copy
    """

    for feature in layer:
        value = {}
        for field in fields:
            value[field] = feature.GetField(field)
        lines = feature.GetGeometryRef()
        lines = lines.Clone()
        lines.TransformTo(srs)
        if lines.GetGeometryName() == 'LINESTRING':
            # otherwise it's a MULTILINESTRING
            lines = [lines]
        for line in lines:
            yield value, line
def make_parser():
     
    parser = argparse.ArgumentParser(
        description="""Clasify lines by rasters""",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument("--step-length", type=float, default=10.,
        help="How much line to skip before adding a node, if needed"
    )
    parser.add_argument("--stretch", type=float, default=1.,
        help="Stretch final step this much to get to next vertex"
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
    parser.add_argument("--get-classes", action='store_true',
        help="Just display a frequency table of classes seen"
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

    classes = classify_lines(opt, lines, grid)

    if opt.get_classes:
        for k, v in classes.items():
            print(k, v)
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
def walk_line(line, step_length, stretch):
    """walk_line - generator to return points on a line

    :param OGR LineString line: line to walk
    :param float step_length: step distance
    :param float stretch: distance to expand / contract step_length if
                            it allows reaching the next vertex on
                            the line
    :yields: OGR Point
    """

    prev_point = None
    
    for point in line.GetPoints():
        
        if prev_point is None:  # must be first vertex
            prev_point = point
            continue
        
        sep = point[0]-prev_point[0], point[1]-prev_point[1]
        
        distance = sqrt(sep[0]*sep[0] + sep[1]*sep[1])
        
        steps = max(1, int(distance / step_length + 0.5))

        dx = sep[0] / steps
        dy = sep[1] / steps
        
        x,y = prev_point
        for n in range(steps):
            yield (x, y), n == 0
            x += dx
            y += dy
            if sqrt(pow(x-point[0], 2) + pow(y-point[1], 2)) <= stretch:
                break  # don't emit a very short step
        
        prev_point = point
        
    yield point, True  # last point on linestring
if __name__ == '__main__':
    main()

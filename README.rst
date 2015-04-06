rasterlinefilter - classify lines by underlying raster
======================================================

.. contents::

Overview
++++++++

``rasterlinefilter.py`` reads lines and samples classes in a raster
under the lines, producing new line segments with the classes from the
raster.  Classes can be lumped without needing to reclassify the raster,
e.g. for a raster with classes A,B,C,D,E,F ``rasterlinefilter`` can
generate class N line segments for raster classes A,B,C and class O line
segments for raster classes D,E,F.

A threshold number of consecutive samples within a (lumped) raster class
before the line classification changes can be specified. This allows
output line segments to bridge over fine scale / noisy raster data and
represent major features in the raster.

Vertices present in the original input line data are always present in the
output, even when they don't represent a class change.  This is necessary to
maintain line shape.  Sampling vertices are only present in the output when
they occur at class change boundaries, i.e. new line segments.

Pictorially::

  original line with vertices

  X--------------------------X----------X--------------------X---------------X

  line with additional sampling vertices

  X----x----x----x----x----x-X----x-----X----x----x----x-----X----x----x-----X

  raw raster classes

  AAECBBEACCAADDBFFEECDDCAAFBBBACBCAEEDEEDDEEEEAEEEABBABDFCFFAAAEBCCDDCEEEABFF

  lumped raster classes (A,B,C = N, D,E,F = O)

  NNONNNONNNNNOONOOOONOONNNONNNNNNNNOOOOOOOOOOONOOONNNNNOONOONNNONNNOONOOONNOO

  output six separate line segments with class

  X---------x---------x------X----x-----X---------x----------X----x----------X
  NNNNNNNNNNNOOOOOOOOOONNNNNNNNNNNNOOOOOOOOOOOOOOOONNNNNNNNNNNNNNNNOOOOOOOOOOO

Usage
+++++

::

    usage: rasterlinefilter.py [-h] [--step-length STEP_LENGTH]
                               [--stretch STRETCH] [--min-steps MIN_STEPS]
                               [--class-steps CLASS_STEPS] [--class CLASS_]
                               [--values VALUES] [--fields FIELDS [FIELDS ...]]
                               [--range RANGE] [--band BAND] [--get-classes]
                               [--progress PROGRESS]
                               lines grid output
    
    Clasify lines by rasters
    
    positional arguments:
      lines                 Path to OGR datasource (shapefile) containing lines
      grid                  Path to GDAL datasource (grid) containing raster
      output                Basename for output shapefile
    
    optional arguments:
      -h, --help            show this help message and exit
      --step-length STEP_LENGTH
                            Spacing of sampling nodes along lines (default: 10.0)
      --stretch STRETCH     Stretch final step this much to get to next vertex
                            (default: 1.0)
      --min-steps MIN_STEPS
                            How many step-length steps in a class are needed to
                            switch to that class - setting for all classes
                            (default: 1)
      --class-steps CLASS_STEPS
                            How many step-length steps in the last class defined
                            are needed to switch to that class - class specific
                            setting (default: [])
      --class CLASS_        Name of an output classification class (default: [])
      --values VALUES       Raster values (classes), space or comma separated, for
                            preceding output class. NoData for no data, * for all
                            remaining values (default: [])
      --fields FIELDS [FIELDS ...]
                            Field names, space or , separated, to copy from
                            `lines` input to output. (default: None)
      --range RANGE         Two raster values, space separated, min max, for
                            preceding output class NOT IMPLEMENTED (default: None)
      --band BAND           Raster band to use (default: 0)
      --get-classes         Just display a frequency table of classes seen
                            (default: False)
      --progress PROGRESS   Report lines proccessed every N lines (default: False)


Example
+++++++

Outputs and output checksums from version 539cc34 Mon Apr 6 10:25:21 2015

    python3 rasterlinefilter.py linestest/linestest.shp lctest/lctest.tif \
      testout --fields id lclass --get-classes

gives (sorted and reformatted)::

    21 164        43 49
    22 20         52 163
    23 28         71 33
    24 5          81 94
    31 43         90 529
    41 537        95 121
    42 50

then::

    python3 rasterlinefilter.py linestest/linestest.shp lctest/lctest.tif \
        testout --fields id lclass \
        --class red --values 21,22,23,24,31,71 --class-steps 4 \
        --class blue --values 41,42,43,52,81,90,95 --class-steps 2

gives::

    2 classes, 2 value lists, 2 class specific min-steps ok
    'red', requires 4 steps in:
      [21, 22, 23, 24, 31, 71]
    'blue', requires 2 steps in:
      [41, 42, 43, 52, 81, 90, 95]
    75bcf5df869025cb211f6384eaa35d99ce79c842  testout/testout.dbf
    f0cfd7b52fbd66c7f8ad7419bd5938137f3931e4  testout/testout.prj
    ab6946d884f20c948a0287b186a9478619222280  testout/testout.shp
    0c1d2d842b7ad48b61f2806166a151118bf31c1a  testout/testout.shx

Notes
+++++

    - A line crossing a road or similar linear feature in a raster may or may
      not change class depending on the angle of intersection.  Crossing at
      right angles will produce far fewer samples in the "road class" than crossing
      at an oblique angle.


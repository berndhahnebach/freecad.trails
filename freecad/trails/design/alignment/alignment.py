# -*- coding: utf-8 -*-
#***********************************************************************
#*                                                                     *
#* Copyright (c) 2019, Joel Graff <monograff76@gmail.com               *
#*                                                                     *
#* This program is free software; you can redistribute it and/or modify*
#* it under the terms of the GNU Lesser General Public License (LGPL)  *
#* as published by the Free Software Foundation; either version 2 of   *
#* the License, or (at your option) any later version.                 *
#* for detail see the LICENCE text file.                               *
#*                                                                     *
#* This program is distributed in the hope that it will be useful,     *
#* but WITHOUT ANY WARRANTY; without even the implied warranty of      *
#* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the       *
#* GNU Library General Public License for more details.                *
#*                                                                     *
#* You should have received a copy of the GNU Library General Public   *
#* License along with this program; if not, write to the Free Software *
#* Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307*
#* USA                                                                 *
#*                                                                     *
#***********************************************************************

"""
Class for managing 2D Horizontal Alignments
"""
from copy import deepcopy

import FreeCAD as App
import Draft

from ..project.support import properties, units
from ..geometry import support
from . import alignment_group, alignment_model

_CLASS_NAME = 'Alignment'
_TYPE = 'Part::Part2DObjectPython'

__title__ = 'alignment.py'
__author__ = 'Joel Graff'
__url__ = "https://www.freecadweb.org"


def create(geometry, object_name='', no_visual=False, zero_reference=False):
    """
    Class construction method
    object_name - Optional. Name of new object.  Defaults to class name.
    no_visual - If true, generates the object without a ViewProvider.
    """

    if not geometry:
        print('No curve geometry supplied')
        return

    _name = _CLASS_NAME

    if object_name:
        _name = object_name

    _obj = None

    if no_visual:
        _obj = App.ActiveDocument.addObject(_TYPE, _name)

    else:
        parent = alignment_group.create()
        _obj = parent.Object.newObject(_TYPE, _name)

    result = Alignment(_obj, _name)
    result.set_geometry(geometry, zero_reference)

    if not no_visual:

        Draft._ViewProviderWire(_obj.ViewObject)

    App.ActiveDocument.recompute()

    return result

class Alignment(Draft._Wire):
    """
    FeaturePython Alignment class
    """

    def __init__(self, obj, label=''):
        """
        Default Constructor
        """

        super(Alignment, self).__init__(obj)

        self.no_execute = True

        obj.Proxy = self

        self.Type = _CLASS_NAME
        self.Object = obj
        self.errors = []

        self.curve_edges = None

        self.model = None
        self.meta = {}
        self.hashes = None

        obj.Label = label
        obj.Closed = False

        if not label:
            obj.Label = obj.Name

        #add class properties

        #metadata
        properties.add(obj, 'String', 'ID', 'ID of alignment', '')
        properties.add(obj, 'String', 'oID', 'Object ID', '')

        properties.add(
            obj, 'Length', 'Length', 'Alignment length', 0.0, is_read_only=True
        )

        properties.add(
            obj, 'String', 'Description', 'Alignment description', ''
        )

        properties.add(
            obj, 'Length', 'Start Station',
            'Starting station of the alignment', 0.0
        )

        obj.addProperty(
            'App::PropertyEnumeration', 'Status', 'Base', 'Alignment status'
        ).Status = ['existing', 'proposed', 'abandoned', 'destroyed']

        properties.add(
            obj, 'Vector', 'Datum', 'Datum value as Northing / Easting',
            App.Vector(0.0, 0.0, 0.0)
        )

        properties.add(
            obj, 'FloatList', 'Hashes', 'Coordiante hashes', []
        )

        #geometry
        properties.add(
            obj, 'VectorList', 'PIs', """
            Discretization of Points of Intersection (PIs) as a list of
            vectors""", []
            )

        properties.add(
            obj, 'Link', 'Parent Alignment',
            'Links to parent alignment object', None
        )

        subdivision_desc = """
            Method of Curve Subdivision\n
            \nTolerance - ensure error between segments and curve is (n)
            \nInterval - Subdivide curve into segments of fixed length
            \nSegment - Subdivide curve into equal-length segments
            """

        obj.addProperty(
            'App::PropertyEnumeration', 'Method', 'Segment', subdivision_desc
        ).Method = ['Tolerance', 'Interval', 'Segment']

        properties.add(obj, 'Float', 'Segment.Seg_Value',
                       'Set the curve segments to control accuracy',
                       int(1000.0 / units.scale_factor()) / 100.0
                      )

        delattr(self, 'no_execute')

    def __getstate__(self):
        return self.Type

    def __setstate__(self, state):
        if state:
            self.Type = state

    def onDocumentRestored(self, obj):
        """
        Restore object references on reload
        """

        self.Object = obj

        self.model = alignment_model.AlignmentModel(
            self.Object.InList[0].Proxy.get_alignment_data(obj.ID)
        )

        self.build_curve_edge_dict()

    def _plot_vectors(self, stations, interval=1.0, is_ortho=True):
        """
        Testing function to plot coordinates and vectors between specified
        stations.

        stations - tuple / list of starting / ending stations
        is_ortho - bool, False plots tangent, True plots orthogonal
        """

        if not stations:
            stations = [
                self.model.data.get('meta').get('StartStation'),
                self.model.data.get('meta').get('StartStation') \
                    + self.model.data.get('meta').get('Length') / 1000.0
            ]

        _pos = stations[0]
        _items = []

        while _pos < stations[1]:

            if is_ortho:
                _items.append(tuple(self.model.get_orthogonal(_pos, 'Left')))

            else:
                _items.append(tuple(self.model.get_tangent(_pos)))

            _pos += interval

        for _v in _items:

            _start = _v[0]
            _end = _start + _v[1] * 100000.0

            _pt = [self.model.data.get('meta').get('Start')]*2
            _pt[0] = _pt[0].add(_start)
            _pt[1] = _pt[1].add(_end)

            line = Draft.makeWire(_pt, closed=False, face=False, support=None)

            Draft.autogroup(line)

        App.ActiveDocument.recompute()


    def build_curve_edge_dict(self):
        """
        Build the dictionary which correlates edges to their corresponding
        curves for quick lookup when curve editing
        """

        curve_dict = {}
        curves = self.model.data.get('geometry')

        #iterate the curves, creating the dictionary for each curve
        #that lists it's wire edges keyed by it's Edge index
        for curve in curves:

            if curve.get('Type') == 'Line':
                continue

            curve_edges = self.Object.Shape.Edges
            curve_pts = [curve.get('Start'), curve.get('End')]
            edge_dict = {}

            #iterate edge list, add edges that fall within curve limits
            for _i, edge in enumerate(curve_edges):

                edge_pts = [edge.Vertexes[0].Point, edge.Vertexes[1].Point]

                #empty list means we haven't found the start yet
                if not edge_dict:

                    if not support.within_tolerance(curve_pts[0], edge_pts[0]):
                        continue

                #still here?  then we're within the geometry
                edge_dict['Edge' + str(_i + 1)] = edge

                #if this edge fits the end, we're done
                if support.within_tolerance(curve_pts[1], edge_pts[1]):
                    break

            #calculate a unique hash based on the curve start and end points
            #and save the edge list to it

            curve_dict[curve['Hash']] = edge_dict

        self.curve_edges = curve_dict

    def get_pi_coords(self):
        """
        Convenience function to get PI coordinates from the model
        """

        return self.model.get_pi_coords()

    def get_edges(self):
        """
        Return the dictionary of curve edges
        """

        return self.curve_edges

    def get_data(self):
        """
        Return the complete dataset for the alignment
        """

        return self.model.data

    def get_data_copy(self):
        """
        Returns a deep copy of the alignment dataset
        """

        return deepcopy(self.model.data)

    def get_length(self):
        """
        Return the alignment length
        """

        return self.model.data.get('meta').get('Length')

    def get_curves(self):
        """
        Return a list of only the curves
        """

        return [_v for _v in self.model.data.get('geometry') \
            if _v.get('Type') != 'Line']

    def get_geometry(self, curve_hash=None):
        """
        Return the geometry of the curve matching the specified hash
        value.  If no match, return all of the geometry
        """

        if not curve_hash:
            return self.model.data.get('geometry')

        for _geo in self.model.data.get('geometry'):

            if _geo['Hash'] == curve_hash:
                return _geo

        return None

    def update_curves(self, curves, pi_list, zero_reference=False):
        """
        Assign updated alignment curves to the model.
        """

        _model = {
            'meta': {
                'Start': pi_list[0],
                'StartStation':
                    self.model.data.get('meta').get('StartStation'),
                'End': pi_list[-1],
            },
            'geometry': curves,
            'station': self.model.data.get('station')
        }

        self.set_geometry(_model, zero_reference)

    def set_geometry(self, geometry, zero_reference=False):
        """
        Assign geometry to the alignment object
        """
        self.model = alignment_model.AlignmentModel(geometry, zero_reference)

        if self.model.errors:
            for _err in self.model.errors:
                print('Error in alignment {0}: {1}'\
                    .format(self.Object.Label, _err)
                     )

            self.model.errors.clear()

        self.assign_meta_data()

        return self.model.errors

    def assign_meta_data(self, model=None):
        """
        Extract the meta data for the alignment from the data set
        Check it for errors
        Assign properties
        """

        obj = self.Object

        meta = self.model.data.get('meta')

        if meta.get('ID'):
            obj.ID = meta.get('ID')

        if meta.get('Description'):
            obj.Description = meta.get('Description')

        if meta.get('ObjectID'):
            obj.ObjectID = meta.get('ObjectID')

        if meta.get('Length'):
            obj.Length = meta.get('Length')

        if meta.get('Status'):
            obj.Status = meta.get('Status')

        if meta.get('StartStation'):
            obj.Start_Station = str(meta.get('StartStation')) + ' ft'

    def onChanged(self, obj, prop):
        """
        Property change callback
        """
        #dodge onChanged calls during initialization
        if hasattr(self, 'no_execute'):
            return

        if prop == "Method":

            _prop = obj.getPropertyByName(prop)

            if _prop == 'Interval':
                self.Object.Seg_Value = int(3000.0 / units.scale_factor())

            elif _prop == 'Segment':
                self.Object.Seg_Value = 200.0

            elif _prop == 'Tolerance':
                self.Object.Seg_Value = \
                    int(1000.0 / units.scale_factor()) / 100.0

    def execute(self, obj):
        """
        Recompute callback
        """
        if hasattr(self, 'no_execute'):
            return

        points = self.model.discretize_geometry(
            [0.0], self.Object.Method, self.Object.Seg_Value
        )

        if not points:
            return

        self.Object.Points = points

        _pl = App.Placement()
        #_pl.Base = self.model.data.get('meta').get('Start')

        self.Object.Placement = _pl

        super(Alignment, self).execute(obj)


class _ViewProviderHorizontalAlignment:

    def __init__(self, obj):
        """
        Initialize the view provider
        """
        obj.Proxy = self
        self.Object = obj

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None

    def attach(self, obj):
        """
        View provider scene graph initialization
        """
        self.Object = obj

    def updateData(self, obj, prop):
        """
        Property update handler
        """
        pass

    def getDisplayMode(self, obj):
        """
        Valid display modes
        """
        return ["Wireframe"]

    def getDefaultDisplayMode(self):
        """
        Return default display mode
        """
        return "Wireframe"

    def setDisplayMode(self, mode):
        """
        Set mode - wireframe only
        """
        return "Wireframe"

    def onChanged(self, vobj, prop):
        """
        Handle individual property changes
        """
        pass

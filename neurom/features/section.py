# Copyright (c) 2020, Ecole Polytechnique Federale de Lausanne, Blue Brain Project
# All rights reserved.
#
# This file is part of NeuroM <https://github.com/BlueBrain/NeuroM>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     1. Redistributions of source code must retain the above copyright
#        notice, this list of conditions and the following disclaimer.
#     2. Redistributions in binary form must reproduce the above copyright
#        notice, this list of conditions and the following disclaimer in the
#        documentation and/or other materials provided with the distribution.
#     3. Neither the name of the copyright holder nor the names of
#        its contributors may be used to endorse or promote products
#        derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""Section functions and functional tools."""

import numpy as np

import neurom.morphmath
from neurom import morphmath as mm
from neurom.core.dataformat import COLS
from neurom.core.morphology import iter_segments
from neurom.core import isection as Section


def section_points(section):
    """Returns the points in the section."""
    return section.points


def section_diameters(section):
    """Returns the diameters of the section."""
    return section.diameters


def section_radii(section):
    """Returns the radii in the section."""
    return 0.5 * section_diameters(section)


def section_path_length(section, stop_node=None):
    """Path length from section to root.

    Args:
        section: Section object.
        stop_node: Node to stop the upstream traversal. If None, it stops when no parent is found.
    """
    return sum(map(section_length, Section.iupstream(section, stop_node=stop_node)))


def segment_lengths(section, prepend_zero=False):
    """Returns the list of segment lengths within the section."""
    return neurom.morphmath.interval_lengths(section_points(section), prepend_zero=prepend_zero)


def section_length(section):
    """Length of a section."""
    return sum(segment_lengths(section))


def segment_areas(section):
    """Returns the list of segment areas within the section."""
    return neurom.morphmath.interval_areas(section_points(section), section_radii(section)).tolist()


def section_area(section):
    """Surface area of a section."""
    return sum(segment_areas(section))


def segment_volumes(section):
    """Returns the list of segment volumes within the section."""
    return neurom.morphmath.interval_volumes(section_points(section), section_radii(section)).tolist()


def section_volume(section):
    """Volume of a section."""
    return sum(segment_volumes(section))


def section_tortuosity(section):
    """Tortuosity of a section.

    The tortuosity is defined as the ratio of the path length of a section
    and the euclidian distnce between its end points.

    The path length is the sum of distances between consecutive points.

    If the section contains less than 2 points, the value 1 is returned.
    """
    pts = section_points(section)
    return 1 if len(pts) < 2 else mm.section_length(pts) / mm.point_dist(pts[-1], pts[0])


def section_end_distance(section):
    """End to end distance of a section.

    The end to end distance of a section is defined as
    the euclidian distnce between its end points.

    If the section contains less than 2 points, the value 0 is returned.
    """
    pts = section_points(section)
    return 0 if len(pts) < 2 else mm.point_dist(pts[-1], pts[0])


def branch_order(section):
    """Branching order of a tree section.

    The branching order is defined as the depth of the tree section.

    Note:
        The first level has branch order 1.
    """
    return sum(1 for _ in Section.iupstream(section)) - 1


def taper_rate(section):
    """Taper rate from fit along a section."""
    pts = section_points(section)
    diameters = section_diameters(section)
    path_distances = np.cumsum(neurom.morphmath.interval_lengths(pts, prepend_zero=True))
    return np.polynomial.polynomial.polyfit(path_distances, diameters, 1)[1]


def number_of_segments(section):
    """Returns the number of segments within a section."""
    return len(section_points(section)) - 1


def segment_mean_radii(section):
    """Returns the list of segment mean radii within the section."""
    radii = section_radii(section)
    return np.divide(np.add(radii[:-1], radii[1:]), 2.0).tolist()


def segment_midpoints(section):
    """Returns the list of segment midpoints within the section."""
    pts = section_points(section)
    return np.divide(np.add(pts[:-1], pts[1:]), 2.0).tolist()


def segment_midpoint_radial_distances(section, origin=None):
    """Returns the list of segment midpoint radial distances to the origin."""
    origin = np.zeros(3, dtype=float) if origin is None else origin
    midpoints = np.array(segment_midpoints(section))
    return np.linalg.norm(midpoints - origin, axis=1).tolist()


def segment_taper_rates(section):
    """Returns the list of segment taper rates within the section."""
    pts = np.column_stack((section_points(section), section_radii(section)))
    diff = np.diff(pts, axis=0)
    distance = np.linalg.norm(diff[:, COLS.XYZ], axis=1)
    return np.divide(2.0 * diff[:, COLS.R], distance).tolist()


def section_radial_distance(section, origin):
    """Return the radial distances of a tree section to a given origin point.

    The radial distance is the euclidian distance between the
    end-point point of the section and the origin point in question.

    Arguments:
        section: neurite section object
        origin: point to which distances are measured. It must have at least 3\
            components. The first 3 components are (x, y, z).
    """
    return mm.point_dist(section_points(section)[-1], origin)


def section_meander_angles(section):
    """Inter-segment opening angles in a section."""
    p = section_points(section)
    return [mm.angle_3points(p[i - 1], p[i - 2], p[i]) for i in range(2, len(p))]


def strahler_order(section):
    """Branching order of a tree section.

    The strahler order is the inverse of the branch order,
    since this is computed from the tips of the tree
    towards the root.

    This implementation is a translation of the three steps described in
    Wikipedia (https://en.wikipedia.org/wiki/Strahler_number):

       - If the node is a leaf (has no children), its Strahler number is one.
       - If the node has one child with Strahler number i, and all other children
         have Strahler numbers less than i, then the Strahler number of the node
         is i again.
       - If the node has two or more children with Strahler number i, and no
         children with greater number, then the Strahler number of the node is
         i + 1.

    No efforts have been invested in making it computationnaly efficient, but
    it computes acceptably fast on tested morphologies (i.e., no waiting time).
    """
    if section.children:
        child_orders = [strahler_order(child) for child in section.children]
        max_so_children = max(child_orders)
        it = iter(co == max_so_children for co in child_orders)
        #  check if there are *two* or more children w/ the max_so_children
        any(it)
        if any(it):
            return max_so_children + 1
        return max_so_children
    return 1


def locate_segment_position(section, fraction):
    """Segment ID / offset corresponding to a given fraction of section length."""
    return mm.path_fraction_id_offset(section_points(section), fraction)


def section_mean_radius(section):
    """Compute the mean radius of a section weighted by segment lengths."""
    radii = section_radii(section)
    points = section_points(section)
    lengths = segment_lengths(section)
    mean_radii = 0.5 * (radii[1:] + radii[:-1])
    return np.sum(mean_radii * lengths) / np.sum(lengths)


def downstream_pathlength(section, iterator_type=Section.ipreorder):
    """Compute the total downstream length starting from a section."""
    return sum(map(section_length, iterator_type(section)))

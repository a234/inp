r"""
Search for difficult graphs in the Independence Number Project.

AUTHORS:

- Patrick Gaskill (2012-09-16): v0.2 refactored into INPGraph class

- Patrick Gaskill (2012-08-21): v0.1 initial version
"""

#*****************************************************************************
#       Copyright (C) 2012 Patrick Gaskill <gaskillpw@vcu.edu>
#       Copyright (C) 2012 Craig Larson <clarson@vcu.edu>
#
#  Distributed under the terms of the GNU General Public License (GPL)
#  as published by the Free Software Foundation; either version 2 of
#  the License, or (at your option) any later version.
#                  http://www.gnu.org/licenses/
#*****************************************************************************

import cvxopt.base
import cvxopt.solvers
import datetime
from string import Template
import operator
import os
import re
import subprocess
import sys
import time

# TODO: Include more functions from survey

from sage.all import Graph, graphs, Integer, Rational, floor, ceil, sqrt, \
                     MixedIntegerLinearProgram
from sage.misc.package import is_package_installed

try:
    from progressbar import Bar, Counter, ETA, Percentage, ProgressBar
    _INPGraph__has_progressbar = True
except ImportError:
    _INPGraph__has_progressbar = False

class INPGraph(Graph):
    _nauty_count_pattern = re.compile(r'>Z (\d+) graphs generated')
    _save_path = os.path.expanduser("~/Dropbox/INP")

    def __init__(self, *args, **kwargs):
        Graph.__init__(self, *args, **kwargs)

    @classmethod
    def survey(cls, func, order):
        # TODO: Write documentation
        # TODO: Is it possible to write tests for this?
        if not is_package_installed("nauty"):
            raise TypeError, "The nauty package is required to survey a bound or property."

        sys.stdout.write("Counting graphs of order {0}... ".format(order))
        sys.stdout.flush()
        num_graphs_to_check = cls.count_viable_graphs(order)
        print num_graphs_to_check

        if __has_progressbar:
            pbar = ProgressBar(widgets=["Testing: ", Counter(), Bar(), ETA()], maxval=num_graphs_to_check, fd=sys.stdout).start()
        else:
            print "Testing..."

        gen = graphs.nauty_geng("-cd3D{0} {1}".format(order-2, order))
        counter = 0
        hits = 0

        is_alpha_property = hasattr(func, '_is_alpha_property') and func._is_alpha_property
        is_bound = (hasattr(func, '_is_lower_bound') and func._is_lower_bound) or \
                   (hasattr(func, '_is_upper_bound') and func._is_upper_bound)

        while True:
            try:
                g = INPGraph(gen.next())

                if is_alpha_property:
                    if func(g):
                        hits += 1
                elif is_bound:
                    if func(g) == g.independence_number():
                        hits += 1

                counter += 1

                if __has_progressbar:
                    pbar.update(counter)
                    sys.stdout.flush()

            except StopIteration:
                if __has_progressbar:
                    pbar.finish()

                if is_alpha_property:
                    print "{0} out of {1} graphs of order {2} satisfied {3}.".format(hits, counter, order, func.__name__)
                elif is_bound:
                    print "{0} out of {1} graphs of order {2} were predicted by {3}.".format(hits, counter, order, func.__name__)
                return

            except KeyboardInterrupt:
                print "\nStopped."
                return

    @classmethod
    def count_viable_graphs(cls, order):
        # TODO: Write documentation
        # TODO: Write tests
        if not is_package_installed("nauty"): 
            raise TypeError, "The nauty package is required to count viable graphs."

        # Graphs with < 6 vertices will have pendant or foldable vertices.
        if order < 6:
            return 0

        output = subprocess.check_output(["{0}/local/bin/nauty-geng".format(SAGE_ROOT),
                                 "-cud3D{0}".format(order-2), str(order)], stderr=subprocess.STDOUT)
        m = cls._nauty_count_pattern.search(output)
        return int(m.group(1))

    @classmethod
    def _next_difficult_graph_of_order(cls, order, verbose=True, save=False):
        if not is_package_installed("nauty"): 
            raise TypeError, "The nauty package is required to find difficult graphs."

        # Graphs with < 6 vertices will have pendant or foldable vertices.
        if order < 6:
            raise ValueError, "There are no difficult graphs with less than 6 vertices."

        if verbose:
            sys.stdout.write("Counting graphs of order {0}... ".format(order))
            sys.stdout.flush()
            num_graphs_to_check = cls.count_viable_graphs(order)
            print num_graphs_to_check

            if __has_progressbar:
                pbar = ProgressBar(widgets=["Testing: ", Counter(), Bar(), ETA()], maxval=num_graphs_to_check, fd=sys.stdout).start()
            else:
                print "Testing..."

        gen = graphs.nauty_geng("-cd3D{0} {1}".format(order-2, order))
        counter = 0

        while True:
            try:
                g = INPGraph(gen.next())

                if g.is_difficult():
                    if verbose:
                        if __has_progressbar:
                            pbar.finish()
                        print "Found a difficult graph: {0}".format(g.graph6_string())

                    if save:
                        g.save_files()

                    return g

                counter += 1

                if verbose and __has_progressbar:
                    pbar.update(counter)
                    sys.stdout.flush()

            except StopIteration:
                if verbose and __has_progressbar:
                    pbar.finish()

                return None
        
    @classmethod
    def next_difficult_graph(cls, order=None, verbose=True, save=False):
        # TODO: Is it possible to write good tests for this?
        r"""
        This function returns the smallest graph considered difficult by INP theory.

        INPUT:

        - ``verbose`` - boolean -- Print progress to the console and save graph
            information as a dossier PDF and a PNG image.

        NOTES:

        The return value of this function may change depending on the functions
        included in the _lower_bounds, _upper_bounds, and _alpha_properties
        settings.
        """
        if not is_package_installed("nauty"): 
            raise TypeError, "The nauty package is not required to find difficult graphs."

        # Graphs with < 6 vertices will have pendant or foldable vertices.

        if order is None:
            n = 6
        else:
            if order < 6:
                raise ValueError, "There are no difficult graphs with less than 6 vertices."

            n = order

        while True:
            try:
                g = cls._next_difficult_graph_of_order(n, verbose, save)
                if g is None:
                    n += 1
                else:
                    return g
            except KeyboardInterrupt:
                if verbose:
                    sys.stdout.flush()
                    print "\nStopped."
                return None

    def is_difficult(self):
        # TODO: Is it possible to write good tests for this?
        r"""
        This function determines if the graph is difficult as described by
        INP theory.

        NOTES:

        The return value of this function may change depending on the functions
        included in the _lower_bounds, _upper_bounds, and _alpha_properties
        settings.
        """
        if self.has_alpha_property():
            return False

        lbound = ceil(self.best_lower_bound())
        ubound = floor(self.best_upper_bound())

        if lbound == ubound:
            return False

        return True

    def best_lower_bound(self):
        # TODO: Is it possible to write good tests for this?
        r"""
        This function computes a lower bound for the independence number of the
        graph.

        NOTES:

        The return value of this function may change depending on the functions
        included in the _lower_bounds setting.
        """
        # The default bound is 1
        lbound = 1

        for func in self._lower_bounds:
            try:
                new_bound = func(self)
                if new_bound > lbound:
                    lbound = new_bound
            except ValueError:
                pass

        return lbound

    def best_upper_bound(self):
        # TODO: Is it possible to write good tests for this?
        r"""
        This function computes an upper bound for the independence number of
        the graph.

        NOTES:

        The return value of this function may change depending on the functions
        included in the _upper_bounds setting.
        """
        # The default upper bound is the number of vertices
        ubound = self.order()

        for func in self._upper_bounds:
            try:
                new_bound = func(self)
                if new_bound < ubound:
                    ubound = new_bound
            except ValueError:
                pass

        return ubound

    def has_alpha_property(self):
        # TODO: Is it possible to write good tests for this?
        r"""
        This function determines if the graph satisifes any of the known
        alpha-properties or alpha-reductions.

        NOTES:

        The return value of this function may change depending on the functions
        included in the _alpha_properties setting.
        """
        for func in self._alpha_properties:
            try:
                if func(self):
                    return True
            except ValueError:
                pass

        return False

    def save_files(self):
        # TODO: Write documentation
        # TODO: Is it possible to write good tests for this?
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        filename = "difficult_graph_{0}".format(timestamp)
        folder_path = "{0}/{1}".format(self._save_path, filename)

        try:
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)
        except IOError:
            "Can't make directory {0}".format(folder_path)

        (saved_plot, saved_pdf) = (False, False)

        try:
            self.plot().save("{0}/{1}.png".format(folder_path, filename))
            #print "Plot saved to {0}{1}.png".format(folder_path, filename)
            saved_plot = True
        except IOError:
            print "Couldn't save {0}/{1}.png".format(folder_path, filename)

        try:
            self._export_pdf(folder_path, filename)
            #print "Dossier saved to {0}{1}.pdf".format(folder_path, filename)
            saved_pdf = True
        except IOError:
            print "Couldn't save {0}/{1}.pdf".format(folder_path, filename)

        if saved_plot or saved_pdf:
            print "Saved graph information to: \n  {0}".format(folder_path)

    def _export_pdf(self, folder_path, filename):
        # TODO: Write documentation
        # TODO: Is it possible to write good tests for this?
        # TODO: Check for tkz style files
        
        # Generate the latex for the alpha properties table
        alphaproperties = {}
        for func in self._alpha_properties:
            name = func.__name__
            value = func(self)
            alphaproperties[name] = value

        alphaproperties_sorted = sorted(alphaproperties.iteritems(), key=operator.itemgetter(1), reverse=True)
        alphaproperties_table = ''

        for (name, value) in alphaproperties_sorted:
            alphaproperties_table += \
                "{0} & {1} \\\\\n".format(self._latex_escape(name), ["\ding{56}", "\ding{51}"][value])

        # Generate the latex for the lower bounds table
        lowerbounds = {}
        for func in self._lower_bounds:
            name = func.__name__
            value = func(self)
            lowerbounds[name] = value

        lowerbounds_sorted = sorted(lowerbounds.iteritems(), key=operator.itemgetter(1))
        lowerbounds_table = ''

        for (name, value) in lowerbounds_sorted:
            try:
                if value in ZZ:
                    lowerbounds_table += \
                        "{0} & {1} \\\\\n".format(self._latex_escape(name), int(Integer(value)))
                else:
                    lowerbounds_table += \
                       "{0} & {1:.3f} \\\\\n".format(self._latex_escape(name), float(value))
                # lowerbounds_table += "{0} & {1} \\\\\n".format(self._latex_escape(name), value)
            except (AttributeError, ValueError):
                print "Can't format", name, value, "for LaTeX output."
                lowerbounds_table += \
                    "{0} & {1} \\\\\n".format(self._latex_escape(name), '?')

        # Generate the latex for the upper bounds table
        upperbounds = {}
        for func in self._upper_bounds:
            name = func.__name__
            value = func(self)
            upperbounds[name] = value

        upperbounds_sorted = sorted(upperbounds.iteritems(), key=operator.itemgetter(1))
        upperbounds_table = ''

        for (name, value) in upperbounds_sorted:
            try:
                if value in ZZ:
                    upperbounds_table += \
                        "{0} & {1} \\\\\n".format(self._latex_escape(name), int(Integer(value)))
                else:
                    upperbounds_table += \
                        "{0} & {1:.3f} \\\\\n".format(self._latex_escape(name), float(value))
            except (AttributeError, ValueError):
                print "Can't format", name, value, "for LaTeX output."
                upperbounds_table += \
                    "{0} & {1} \\\\\n".format(self._latex_escape(name), '?')


        # Insert all the generated latex into the template file
        template_file = open('template.tex', 'r')
        template = template_file.read()
        s = Template(template)

        self.set_pos(self.layout_circular())
        opts = self.latex_options()
        opts.set_option('tkz_style', 'Dijkstra')

        output = s.substitute(name=self._latex_escape(self.graph6_string()),
                              order=self.order(),
                              size=self.size(),
                              alpha=self.independence_number(),
                              alphaproperties=alphaproperties_table,
                              lowerbounds=lowerbounds_table, 
                              upperbounds=upperbounds_table,
                              tikzpicture=latex(self))
        latex_filename = "{0}/{1}.tex".format(folder_path, filename)

        # Write the latex to a file then run pdflatex on it
        # TODO: Handle calling pdflatex and its errors better.
        try:
            latex_file = open(latex_filename, 'w')
            latex_file.write(output)
            latex_file.close()
            with open(os.devnull, 'wb') as devnull:
                subprocess.call(['/usr/texbin/pdflatex', '-output-directory',
                    folder_path, latex_filename],
                    stdout=devnull, stderr=subprocess.STDOUT)
        except:
            pass

    @classmethod
    def _latex_escape(cls, str):
        # TODO: Write documentation
        # TODO: Write tests
        str = str.replace('\\', r'\textbackslash ')

        escape_chars = {
            '#': r'\#',
            '$': r'\$',
            '%': r'\%',
            '&': r'\&',
            '_': r'\_',
            '{': r'\{',
            '}': r'\}',
            '^': r'\textasciicircum ',
            '~': r'\textasciitilde '
        }

        for old, new in escape_chars.iteritems():
            str = str.replace(old, new)
        return str

    @classmethod
    def KillerGraph(cls):
        return cls('EXCO')

    def matching_number(self):
        # TODO: This needs to be updated when Sage 5.3 is released.
        r"""
        Compute the traditional matching number `\mu`.

        EXAMPLES:

        ::
            sage: INPGraph(2).matching_number()
            0

        ::
            sage: INPGraph(graphs.CompleteGraph(3)).matching_number()
            1

        ::
            sage: INPGraph(graphs.PathGraph(3)).matching_number()
            1

        ::
            sage: INPGraph(graphs.StarGraph(3)).matching_number()
            1

        ::
            sage: INPGraph.KillerGraph().matching_number()
            2

        ::
            sage: INPGraph(graphs.CycleGraph(5)).matching_number()
            2

        ::  
            sage: INPGraph(graphs.PetersenGraph()).matching_number()
            5

        WARNINGS:

        Ideally we would set use_edge_labels=False to ignore edge weighting and
        always compute the traditional matching number, but there is a bug
        in Sage 5.2 that returns double this number. Calling this on an
        edge-weighted graph will NOT give the usual matching number.
        """
        return int(self.matching(value_only=True))

    mu = matching_number

    def independence_number(self):
        r"""
        Compute the independence number using the Sage built-in independent_set
        method. This uses the Cliquer algorithm, which does not run in
        polynomial time.

        EXAMPLES:

        ::
            sage: INPGraph(2).independence_number()
            2

        ::
            sage: INPGraph(graphs.CompleteGraph(3)).independence_number()
            1

        ::
            sage: INPGraph(graphs.PathGraph(3)).independence_number()
            2

        ::
            sage: INPGraph(graphs.StarGraph(3)).independence_number()
            3

        ::
            sage: INPGraph.KillerGraph().independence_number()
            4

        ::
            sage: INPGraph(graphs.CycleGraph(5)).independence_number()
            2

        ::  
            sage: INPGraph(graphs.PetersenGraph()).independence_number()
            4
        """
        return int(len(self.independent_set()))

    alpha = independence_number

    def bipartite_double_cover(self):
        r"""
        Return a bipartite double cover of the graph, also known as the
        bidouble.

        EXAMPLES:

        ::
            sage: b = INPGraph(2).bipartite_double_cover()
            sage: b.is_isomorphic(Graph(4))
            True

        ::
            sage: b = INPGraph(graphs.CompleteGraph(3)).bipartite_double_cover()
            sage: b.is_isomorphic(graphs.CycleGraph(6))
            True

        ::
            sage: b = INPGraph(graphs.PathGraph(3)).bipartite_double_cover()
            sage: b.is_isomorphic(Graph('EgCG'))
            True

        ::
            sage: b = INPGraph(graphs.StarGraph(3)).bipartite_double_cover()
            sage: b.is_isomorphic(Graph('Gs?GGG'))
            True

        ::
            sage: b = INPGraph('EXCO').bipartite_double_cover()
            sage: b.is_isomorphic(Graph('KXCO?C@??A_@'))
            True

        ::
            sage: b = INPGraph(graphs.CycleGraph(5)).bipartite_double_cover()
            sage: b.is_isomorphic(graphs.CycleGraph(10))
            True

        ::
            sage: b = INPGraph(graphs.PetersenGraph()).bipartite_double_cover()
            sage: b.is_isomorphic(Graph('SKC_GP@_a?O?C?G??__OO?POAI??a_@D?'))
            True
        """
        return INPGraph(self.tensor_product(graphs.CompleteGraph(2)))

    bidouble = bipartite_double_cover
    kronecker_double_cover = bipartite_double_cover
    canonical_double_cover = bipartite_double_cover

    def closed_neighborhood(self, verts):
        # TODO: Write tests
        # TODO: Write documentation
        if isinstance(verts, list):
            neighborhood = []
            for v in verts:
                neighborhood += [v] + self.neighbors(v)
            return list(set(neighborhood))
        else:
            return [verts] + self.neighbors(verts)

    def closed_neighborhood_subgraph(self, verts):
        # TODO: Write tests
        # TODO: Write documentation
        return self.subgraph(self.closed_neighborhood(verts))

    def open_neighborhood(self, verts):
        # TODO: Write tests
        # TODO: Write documentation
        if isinstance(verts, list):
            neighborhood = []
            for v in verts:
                neighborhood += self.neighbors(v)
            return list(set(neighborhood))
        else:
            return self.neighbors(verts)

    def open_neighborhood_subgraph(self, verts):
        # TODO: Write tests
        # TODO: Write documentation
        return self.subgraph(self.open_neighborhood(verts))

    def max_degree(self):
        # TODO: Write tests
        # TODO: Write documentation
        return max(self.degree())

    def min_degree(self):
        # TODO: Write tests
        # TODO: Write documentation
        return min(self.degree())

    def union_MCIS(self):
        # TODO: Write more tests
        r"""
        Return a union of maximum critical independent sets (MCIS).

        EXAMPLES:

        ::
            sage: INPGraph('Cx').union_MCIS()
            [0, 1, 3]

        ::
            sage: INPGraph(graphs.CycleGraph(4)).union_MCIS()
            [0, 1, 2, 3]
        """
        b = self.bipartite_double_cover()
        alpha = b.order() - b.matching_number()

        result = []

        for v in self.vertices():
            test = b.copy()
            test.delete_vertices(b.closed_neighborhood([(v,0), (v,1)]))
            alpha_test = test.order() - test.matching_number() + 2
            if alpha_test == alpha:
                result.append(v)

        return result

    def has_foldable_vertex(self):
        # TODO: Write tests
        # TODO: Write documentation
        # TODO: Is it better to write this using any()?
        for v in self.vertices():
            # true if N(v) contains no anti-triangles
            #if self.open_neighborhood_subgraph(v).complement().is_triangle_free():
            if self.has_foldable_vertex_at(v):
                return True
        return False

    def has_foldable_vertex_at(self, v):
        # TODO: Write tests
        # TODO: Write documentation
        return self.open_neighborhood_subgraph(v).complement().is_triangle_free()

    def fold_at(self, v):
        r"""
        Return a copy of the graph folded at `v`, as folding is defined in
        Fomin-Grandoni-Kratsch 2006.

        EXAMPLES:

        ::
            sage: G = INPGraph('EqW_')
            sage: G.fold_at(0).is_isomorphic(graphs.ClawGraph())
            True

        ::
            sage: G = INPGraph('G{O`?_')
            sage: G.fold_at(0).graph6_string()
            'E?dw'
        """
        g = self.copy()
        Nv = self.closed_neighborhood_subgraph(v)
        Nv_c = Nv.complement()
        new_nodes = []

        for (i,j) in Nv_c.edge_iterator(labels=False):
            g.add_vertex((i,j))
            g.add_edges([[(i,j), w] for w in self.open_neighborhood([i, j])])
            g.add_edges([[(i,j), w] for w in new_nodes])
            new_nodes += [(i,j)]

        g.delete_vertices(Nv.vertices())
        return g

    ###########################################################################
    # Alpha properties
    ###########################################################################

    def has_max_degree_order_minus_one(self):
        # TODO: Write tests
        # TODO: Write documentation
        return self.max_degree() == self.order() - 1
    has_max_degree_order_minus_one._is_alpha_property = True

    def is_claw_free(self):
        # TODO: Write tests
        # TODO: Write documentation
        return self.subgraph_search_count(graphs.ClawGraph()) == 0
    is_claw_free._is_alpha_property = True

    def has_pendant_vertex(self):
        # TODO: Write tests
        # TODO: Write documentation
        return 1 in self.degree()
    has_pendant_vertex._is_alpha_property = True

    def has_simplicial_vertex(self):
        # TODO: Write tests
        # TODO: Write documentation
        # TODO: Is it better to write this using any()?
        for v in self.vertices():
            if self.open_neighborhood_subgraph(v).is_clique():
                return True

        return False
    has_simplicial_vertex._is_alpha_property = True

    def is_KE(self):
        # TODO: Write tests
        # TODO: Write documentation
        c = self.union_MCIS()
        nc = []
        for v in c:
            nc.extend(self.neighbors(v))

        return list(set(c + nc)) == self.vertices()
    is_KE._is_alpha_property = True

    def is_almost_KE(self):
        # TODO: Write tests
        # TODO: Write documentation
        # TODO: Is it better to write this using any()?
        subsets = combinations_iterator(self.vertices(), self.order() - 1)
        for subset in subsets:
            if self.subgraph(subset).is_KE():
                return True

        return False
    is_almost_KE._is_alpha_property = True

    def has_nonempty_KE_part(self):
        # TODO: Write tests
        # TODO: Write documentation
        if self.union_MCIS():
            return True
        else:
            return False
    has_nonempty_KE_part._is_alpha_property = True

    def is_fold_reducible(self):
        # TODO: Write tests
        # TODO: Write documentation
        if not self.has_foldable_vertex():
            return False

        for v in self.vertices():
            if self.has_foldable_vertex_at(v):
                #if self.fold_at(v).order() < n:
                # We should be able to estimate this without actually folding
                Nv = self.closed_neighborhood_subgraph(v)
                Nv_c = Nv.complement()
                if Nv_c.size() - Nv.order() < 0:
                    return True
        return False
    is_fold_reducible._is_alpha_property = True

    ###########################################################################
    # Lower bounds
    ###########################################################################

    def matching_lower_bound(self):
        # TODO: Write more tests
        r"""
        Compute the matching number lower bound.

        EXAMPLES:

        ::

            sage: G = INPGraph(graphs.CompleteGraph(3))
            sage: G.matching_lower_bound()
            1

        """
        return self.order() - 2 * self.matching_number()
    matching_lower_bound._is_lower_bound = True

    def residue(self):
        # TODO: Write tests
        # TODO: Write documentation
        seq = self.degree_sequence()

        while seq[0] > 0:
            d = seq.pop(0)
            seq[:d] = [k-1 for k in seq[:d]]
            seq.sort(reverse=True)

        return len(seq)
    residue._is_lower_bound = True

    def average_degree_bound(self):
        # TODO: Write tests
        # TODO: Write documentation
        n = Integer(self.order())
        d = Rational(self.average_degree())
        return n / (1 + d)
    average_degree_bound._is_lower_bound = True

    def caro_wei(self):
        # TODO: Write more tests
        # TODO: Write documentation
        r"""

        EXAMPLES:

        ::

            sage: G = INPGraph(graphs.CompleteGraph(3))
            sage: G.caro_wei()
            1

        ::

            sage: G = INPGraph(graphs.PathGraph(3))
            sage: G.caro_wei()
            4/3

        """
        return sum([1/(1+Integer(d)) for d in self.degree()])
    caro_wei._is_lower_bound = True

    def wilf(self):
        # TODO: Write tests
        # TODO: Write documentation
        n = Integer(self.order())
        max_eigenvalue = max(self.adjacency_matrix().eigenvalues())
        return n / (1 + max_eigenvalue)
    wilf._is_lower_bound = True

    def hansen_zheng_lower_bound(self):
        # TODO: Write tests
        # TODO: Write documentation
        n = Integer(self.order())
        e = Integer(self.size())
        return ceil(n - (2 * e)/(1 + floor(2 * e / n)))
    hansen_zheng_lower_bound._is_lower_bound = True

    def harant(self):
        # TODO: Write tests
        # TODO: Write documentation
        n = Integer(self.order())
        e = Integer(self.size())
        term = 2 * e + n + 1
        return (1/2) * (term - sqrt(term^2 - 4*n^2))
    harant._is_lower_bound = True

    def max_even_minus_even_horizontal(self):
        r"""
        Compute `max\{e(v) - eh(v)}`, where `e(v)` is the number of vertices
        at even distance from vertex `v`, and `eh(v)` is the number of even
        horizontal edges with respect to `v`, that is, the number of edges `e`
        where both endpoints of `e` are at even distance from `v`.

        EXAMPLES:

        ::
            sage: INPGraph(2).max_even_minus_even_horizontal()
            Traceback (most recent call last):
              ...
            ValueError: This bound is not defined for disconnected graphs.

        ::
            sage: INPGraph(graphs.CompleteGraph(3)).max_even_minus_even_horizontal()
            1

        ::
            sage: INPGraph(graphs.PathGraph(3)).max_even_minus_even_horizontal()
            2

        ::
            sage: INPGraph.KillerGraph().max_even_minus_even_horizontal()
            3

        ::
            sage: INPGraph(graphs.CycleGraph(5)).max_even_minus_even_horizontal()
            2
        """
        if not self.is_connected():
            raise ValueError, "This bound is not defined for disconnected graphs."

        dist = self.distance_all_pairs()
        even = lambda v: [w for w in self.vertices() if dist[v][w] % 2 == 0]
        eh = lambda v: self.subgraph(even(v)).size()

        return max([len(even(v)) - eh(v) for v in self.vertices()])
    max_even_minus_even_horizontal._is_lower_bound = True

    ###########################################################################
    # Upper bounds
    ###########################################################################

    def matching_upper_bound(self):
        # TODO: Write more tests
        r"""
        Compute the matching number upper bound.

        EXAMPLES:

        ::
            sage: INPGraph(graphs.CompleteGraph(3)).matching_upper_bound()
            2
        """
        return self.order() - self.matching_number()
    matching_upper_bound._is_upper_bound = True

    def fractional_alpha(self):
        # TODO: Write more tests
        r"""
        Compute the fractional independence number of the graph.

        EXAMPLES:

        ::

            sage: G = INPGraph(graphs.CompleteGraph(3))
            sage: G.fractional_alpha()
            1.5

        ::

            sage: G = INPGraph(graphs.PathGraph(3))
            sage: G.fractional_alpha()
            2.0

        """
        p = MixedIntegerLinearProgram(maximization=True)
        x = p.new_variable()
        p.set_objective(sum([x[v] for v in self.vertices()]))

        for v in self.vertices():
            p.add_constraint(x[v], max=1)

        for (u,v) in self.edge_iterator(labels=False):
            p.add_constraint(x[u] + x[v], max=1)

        return p.solve()
    fractional_alpha._is_upper_bound = True

    def lovasz_theta(self):
        # TODO: There has to be a nicer way of doing this.
        r"""
        Compute the value of the Lovasz theta function of the given graph.

        EXAMPLES:

        For an empty graph `G`, `\vartheta(G) = n`::

            sage: G = INPGraph(2)
            sage: G.lovasz_theta()
            2.0

        For a complete graph `G`, `\vartheta(G) = 1`::

            sage: G = INPGraph(graphs.CompleteGraph(3))
            sage: G.lovasz_theta()
            1.0

        For a pentagon (five-cycle) graph `G`, `\vartheta(G) = \sqrt{5}`::

            sage: G = INPGraph(graphs.CycleGraph(5))
            sage: G.lovasz_theta()
            2.236

        For the Petersen graph `G`, `\vartheta(G) = 4`::

            sage: G = INPGraph(graphs.PetersenGraph())
            sage: G.lovasz_theta()
            4.0
        """
        cvxopt.solvers.options['show_progress'] = False
        cvxopt.solvers.options['abstol'] = float(1e-10)
        cvxopt.solvers.options['reltol'] = float(1e-10)

        gc = self.complement()
        n = gc.order()
        m = gc.size()

        if n == 1:
            return 1.0

        d = m + n
        c = -1 * cvxopt.base.matrix([0.0]*(n-1) + [2.0]*(d-n))
        Xrow = [i*(1+n) for i in xrange(n-1)] + [b+a*n for (a, b) in gc.edge_iterator(labels=False)]
        Xcol = range(n-1) + range(d-1)[n-1:]
        X = cvxopt.base.spmatrix(1.0, Xrow, Xcol, (n*n, d-1))

        for i in xrange(n-1):
            X[n*n-1, i] = -1.0

        sol = cvxopt.solvers.sdp(c, Gs=[-X], hs=[-cvxopt.base.matrix([0.0]*(n*n-1) + [-1.0], (n,n))])
        v = 1.0 + cvxopt.base.matrix(-c, (1, d-1)) * sol['x']

        # TODO: Rounding here is a total hack
        return round(v[0], 3)
    lovasz_theta._is_upper_bound = True

    def kwok(self):
        # TODO: Write more tests
        r"""
        Compute the upper bound `\alpha \leq n - \frac{e}{\Delta}` that is
        credited to Kwok, or possibly "folklore."

        EXAMPLES:

        ::
            sage: INPGraph(graphs.CompleteGraph(3)).kwok()
            3/2

        ::
            sage: INPGraph(graphs.PathGraph(3)).kwok()
            2
        """
        n = Integer(self.order())
        e = Integer(self.size())
        Delta = Integer(self.max_degree())

        if Delta == 0:
            raise ValueError("Kwok bound is not defined for graphs with maximum degree 0.")

        return n - e / Delta
    kwok._is_upper_bound = True

    def hansen_zheng_upper_bound(self):
        # TODO: Write more tests
        r"""
        Compute an upper bound `\frac{1}{2} + \sqrt{\frac{1/4} + n^2 - n - 2e}` 
        given by Hansen and Zheng, 1993.

        EXAMPLES:

        ::
            sage: G = INPGraph(graphs.CompleteGraph(3))
            sage: G.hansen_zheng_upper_bound()
            1

        """
        n = Integer(self.order())
        e = Integer(self.size())
        return floor(.5 + sqrt(.25 + n**2 - n - 2*e))
    hansen_zheng_upper_bound._is_upper_bound = True

    def min_degree_bound(self):
        # TODO: Write more tests
        r"""
        Compute the upper bound `\alpha \leq n - \delta`. This bound probably
        belong to "folklore."

        EXAMPLES:

        ::
            sage: G = INPGraph(graphs.CompleteGraph(3))
            sage: G.min_degree_bound()
            1

        ::
            sage: G = INPGraph(graphs.PathGraph(4))
            sage: G.min_degree_bound()
            3

        """
        return self.order() - self.min_degree()
    min_degree_bound._is_upper_bound = True

    def cvetkovic(self):
        # TODO: Write more tests
        r"""
        Compute the Cvetkovic bound `\alpha \leq p_0 + min\{p_-, p_+\}`, where
        `p_-, p_0, p_+` denote the negative, zero, and positive eigenvalues 
        of the adjacency matrix of the graph respectively.

        EXAMPLES:

        ::
            sage: G = INPGraph(graphs.PetersenGraph())
            sage: G.cvetkovic()
            4

        """
        eigenvalues = self.adjacency_matrix().eigenvalues()
        [positive, negative, zero] = [0, 0, 0]
        for e in eigenvalues:
            if e > 0:
                positive += 1
            elif e < 0:
                negative += 1
            else:
                zero += 1

        return zero + min([positive, negative])
    cvetkovic._is_upper_bound = True

    def annihilation_number(self):
        # TODO: Write more tests
        r"""
        Compute the annhilation number of the graph.

        EXAMPLES:

        ::
            sage: G = INPGraph(graphs.CompleteGraph(3))
            sage: G.annihilation_number()
            2

        ::
            sage: G = INPGraph(graphs.StarGraph(3))
            sage: G.annihilation_number()
            4

        """
        seq = sorted(self.degree())
        n = self.order()

        a = 1
        while sum(seq[:a]) <= sum(seq[a:]):
            a += 1

        return a
    annihilation_number._is_upper_bound = True

    def borg(self):
        # TODO: Write more tests
        r"""
        Compute the upper bound given by Borg.

        EXAMPLES:

        ::
            sage: INPGraph(graphs.CompleteGraph(3)).borg()
            2

        """
        n = Integer(self.order())
        Delta = Integer(self.max_degree())

        if Delta == 0:
            raise ValueError("Borg bound is not defined for graphs with maximum degree 0.")

        return n - ceil((n-1) / Delta)
    borg._is_upper_bound = True

    def cut_vertices_bound(self):
        # TODO: Write more tests
        r"""

        EXAMPLES:

        ::
            sage: G = INPGraph(graphs.PathGraph(5))
            sage: G.cut_vertices_bound()
            3

        """
        n = Integer(self.order())
        C = Integer(len(self.blocks_and_cut_vertices()[1]))
        return n - C/2 - Integer(1)/2
    cut_vertices_bound._is_upper_bound = True

    _alpha_properties = [is_claw_free, has_simplicial_vertex, is_KE, is_almost_KE, has_nonempty_KE_part, is_fold_reducible]
    _lower_bounds = [max_even_minus_even_horizontal, matching_lower_bound, residue, average_degree_bound, caro_wei, wilf, hansen_zheng_lower_bound, harant]
    _upper_bounds = [matching_upper_bound, fractional_alpha, lovasz_theta, kwok, hansen_zheng_upper_bound, min_degree_bound, cvetkovic, annihilation_number, borg, cut_vertices_bound]

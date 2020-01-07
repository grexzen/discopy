# -*- coding: utf-8 -*-

"""
Implements free monoidal categories and (dagger) monoidal functors.

We can check the axioms for dagger monoidal categories, up to interchanger.

>>> x, y, z, w = Ty('x'), Ty('y'), Ty('z'), Ty('w')
>>> f0, f1 = Box('f0', x, y), Box('f1', z, w)
>>> d = Id(x) @ f1 >> f0 @ Id(w)
>>> assert d == (f0 @ f1).interchange(0, 1)
>>> assert f0 @ f1 == d.interchange(0, 1)
>>> assert (f0 @ f1).dagger().dagger() == f0 @ f1
>>> assert (f0 @ f1).dagger().interchange(0, 1) == f0.dagger() @ f1.dagger()

We can check the Eckerman-Hilton argument, up to interchanger.

>>> s0, s1 = Box('s0', Ty(), Ty()), Box('s1', Ty(), Ty())
>>> assert s0 @ s1 == s0 >> s1 == (s1 @ s0).interchange(0, 1)
>>> assert s1 @ s0 == s1 >> s0 == (s0 @ s1).interchange(0, 1)
"""

from discopy import cat
from discopy.cat import Ob, Functor, Quiver


class Ty(Ob):
    """
    Implements a type as a list of objects, used as dom and cod of diagrams.
    Types are the free monoid on objects with product @ and unit Ty().

    Parameters
    ----------
    t : tuple
        Definition of the type as a tensor of objects
    """
    def __init__(self, *t):
        self._objects = [x if isinstance(x, Ob) else Ob(x) for x in t]
        super().__init__(str(self))

    @property
    def objects(self):
        """
        Recovers the list of objects forming a type.

        >>> Ty('x', 'y', 'z').objects
        [Ob('x'), Ob('y'), Ob('z')]
        """
        return self._objects

    def __eq__(self, other):
        """
        Types are equal when their lists of objects are.

        >>> assert Ty('x', 'y') == Ty('x') @ Ty('y')
        """
        if not isinstance(other, Ty):
            return False
        return self.objects == other.objects

    def __hash__(self):
        """
        Types are hashable whenever the name of their objects is.

        >>> {Ty('x', 'y', 'z'): 42}[Ty('x', 'y', 'z')]
        42
        """
        return hash(repr(self))

    def __repr__(self):
        return "Ty({})".format(', '.join(repr(x.name) for x in self.objects))

    def __str__(self):
        """
        When printing a type we print the tensor of the name of its objects.

        >>> print(Ty('x', 'y'))
        x @ y
        """
        return ' @ '.join(map(str, self)) or 'Ty()'

    def __len__(self):
        """
        The length of a type is the length of the list of its objects.

        >>> assert len(Ty('x', 'y')) == 2
        """
        return len(self.objects)

    def __iter__(self):
        """
        We can iterate over the objects forming a type.

        >>> list(Ty('a', 'b', 'c'))
        [Ob('a'), Ob('b'), Ob('c')]
        """
        for i in range(len(self)):
            yield self[i]

    def __getitem__(self, key):
        """
        __getitem__ may be used to slice a type seen as a list of objects.

        >>> t = Ty('x', 'y', 'z')
        >>> assert t[0] == Ob('x') != Ty('x') == t[:1]
        >>> t[1:]
        Ty('y', 'z')
        """
        if isinstance(key, slice):
            return Ty(*self.objects[key])
        return self.objects[key]

    def __matmul__(self, other):
        """
        Returns the tensor of two types, i.e. the concatenation of their lists
        of objects.

        Parameters
        ----------
        other : discopy.moncat.Ty

        Returns
        -------
        type : discopy.moncat.Ty
            such that `type.objects == self.objects + other.objects`.

        >>> Ty('x') @ Ty('y') @ Ty('x', 'z')
        Ty('x', 'y', 'x', 'z')
        """
        return Ty(*(self.objects + other.objects))

    def __add__(self, other):
        """
        __add__ may be used instead of __matmul__ for taking tensors of types.

        >>> sum([Ty('x'), Ty('y'), Ty('z')], Ty())
        Ty('x', 'y', 'z')
        """
        return self @ other

    def __pow__(self, other):
        """
        __pow__ may be used to iterate __matmul__

        >>> Ty('x') ** 3
        Ty('x', 'x', 'x')
        >>> Ty('x') ** Ty('y')  # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        ValueError: Expected int, got Ty('y') instead.
        """
        if not isinstance(other, int):
            raise ValueError(
                "Expected int, got {} instead.".format(repr(other)))
        return sum(other * (self, ), Ty())


class Diagram(cat.Diagram):
    """
    Defines a diagram given dom, cod, a list of boxes and offsets.

    >>> x, y, z, w = Ty('x'), Ty('y'), Ty('z'), Ty('w')
    >>> f0, f1, g = Box('f0', x, y), Box('f1', z, w), Box('g', y @ w, y)
    >>> d = Diagram(x @ z, y, [f0, f1, g], [0, 1, 0])
    >>> assert d == f0 @ f1 >> g

    Parameters
    ----------
    dom : discopy.moncat.Ty
        Domain of the diagram.
    cod : discopy.moncat.Ty
        Codomain of the diagram.
    boxes : list of :class:`discopy.moncat.Diagram`
        Boxes of the diagram.
    offsets : list of :class:`int`
        Offsets of each box in the diagram.

    Raises
    ------
    :class:`discopy.moncat.AxiomError`
        Whenever the boxes do not compose.
    """
    def __init__(self, dom, cod, boxes, offsets, _fast=False):
        if not isinstance(dom, Ty):
            raise ValueError("Domain of type Ty expected, got {} of type {} "
                             "instead.".format(repr(dom), type(dom)))
        if not isinstance(cod, Ty):
            raise ValueError("Codomain of type Ty expected, got {} of type {} "
                             "instead.".format(repr(cod), type(cod)))
        if len(boxes) != len(offsets):
            raise ValueError("Boxes and offsets must have the same length.")
        if not _fast:
            scan = dom
            for box, off in zip(boxes, offsets):
                if not isinstance(box, Diagram):
                    raise ValueError(
                        "Box of type Diagram expected, got {} of type {} "
                        "instead.".format(repr(box), type(box)))
                if not isinstance(off, int):
                    raise ValueError(
                        "Offset of type int expected, got {} of type {} "
                        "instead.".format(repr(off), type(off)))
                if scan[off: off + len(box.dom)] != box.dom:
                    raise AxiomError(
                        "Domain {} expected, got {} instead."
                        .format(scan[off: off + len(box.dom)], box.dom))
                scan = scan[: off] + box.cod + scan[off + len(box.dom):]
            if scan != cod:
                raise AxiomError(
                    "Codomain {} expected, got {} instead.".format(cod, scan))
        super().__init__(dom, cod, [], _fast=True)
        self._boxes, self._offsets = tuple(boxes), tuple(offsets)

    @property
    def offsets(self):
        """
        >>> Diagram(Ty('x'), Ty('x'), [], []).offsets
        []
        """
        return list(self._offsets)

    def __eq__(self, other):
        """
        >>> Diagram(Ty('x'), Ty('x'), [], []) == Ty('x')
        False
        >>> Diagram(Ty('x'), Ty('x'), [], []) == Id(Ty('x'))
        True
        """
        if not isinstance(other, Diagram):
            return False
        return all(self.__getattribute__(attr) == other.__getattribute__(attr)
                   for attr in ['dom', 'cod', 'boxes', 'offsets'])

    def __repr__(self):
        """
        >>> x, y, z, w = Ty('x'), Ty('y'), Ty('z'), Ty('w')
        >>> Diagram(x, x, [], [])
        Id(Ty('x'))
        >>> f0, f1 = Box('f0', x, y), Box('f1', z, w)
        >>> Diagram(x, y, [f0], [0])  # doctest: +ELLIPSIS
        Diagram(dom=Ty('x'), cod=Ty('y'), boxes=[Box(...)], offsets=[0])
        >>> Diagram(x @ z, y @ w, [f0, f1], [0, 1])  # doctest: +ELLIPSIS
        Diagram(dom=Ty('x', 'z'), cod=Ty('y', 'w'), boxes=..., offsets=[0, 1])
        """
        if not self.boxes:  # i.e. self is identity.
            return repr(Id(self.dom))
        return "Diagram(dom={}, cod={}, boxes={}, offsets={})".format(
            repr(self.dom), repr(self.cod),
            repr(self.boxes), repr(self.offsets))

    def __hash__(self):
        """
        >>> d = Id(Ty('x'))
        >>> assert {d: 42}[d] == 42
        """
        return hash(repr(self))

    def __str__(self):
        """
        >>> x, y, z, w = Ty('x'), Ty('y'), Ty('z'), Ty('w')
        >>> print(Diagram(x, x, [], []))
        Id(x)
        >>> f0, f1 = Box('f0', x, y), Box('f1', z, w)
        >>> print(Diagram(x, y, [f0], [0]))
        f0
        >>> print(f0 @ f1)
        f0 @ Id(z) >> Id(y) @ f1
        >>> print(f0 @ Id(z) >> Id(y) @ f1)
        f0 @ Id(z) >> Id(y) @ f1
        """
        if not self.boxes:  # i.e. self is identity.
            return str(self.id(self.dom))

        def line(scan, box, off):
            left = "{} @ ".format(self.id(scan[:off])) if scan[:off] else ""
            right = " @ {}".format(self.id(scan[off + len(box.dom):]))\
                if scan[off + len(box.dom):] else ""
            return left + str(box) + right
        box, off = self.boxes[0], self.offsets[0]
        result = line(self.dom, box, off)
        scan = self.dom[:off] + box.cod + self.dom[off + len(box.dom):]
        for box, off in zip(self.boxes[1:], self.offsets[1:]):
            result = "{} >> {}".format(result, line(scan, box, off))
            scan = scan[:off] + box.cod + scan[off + len(box.dom):]
        return result

    def tensor(self, other):
        """
        >>> x, y, z, w = Ty('x'), Ty('y'), Ty('z'), Ty('w')
        >>> f0, f1 = Box('f0', x, y), Box('f1', z, w)
        >>> assert f0.tensor(f1) == f0.tensor(Id(z)) >> Id(y).tensor(f1)
        """
        if not isinstance(other, Diagram):
            raise ValueError("Expected Diagram, got {} of type {} instead."
                             .format(repr(other), type(other)))
        dom, cod = self.dom + other.dom, self.cod + other.cod
        boxes = self.boxes + other.boxes
        offsets = self.offsets + [n + len(self.cod) for n in other.offsets]
        return Diagram(dom, cod, boxes, offsets, _fast=True)

    def __matmul__(self, other):
        """
        >>> Id(Ty('x')) @ Id(Ty('y'))
        Id(Ty('x', 'y'))
        >>> assert Id(Ty('x')) @ Id(Ty('y')) == Id(Ty('x')).tensor(Id(Ty('y')))
        """
        return self.tensor(other)

    def then(self, other):
        """
        >>> x, y, z, w = Ty('x'), Ty('y'), Ty('z'), Ty('w')
        >>> f0, f1 = Box('f0', x, y), Box('f1', z, w)
        >>> print(Id(x) @ f1 >> f0 @ Id(w))
        Id(x) @ f1 >> f0 @ Id(w)
        """
        result = super().then(other)
        return Diagram(result.dom, result.cod, result.boxes,
                       self.offsets + other.offsets, _fast=True)

    def dagger(self):
        """
        >>> x, y, z, w = Ty('x'), Ty('y'), Ty('z'), Ty('w')
        >>> d = Box('f0', x, y) @ Box('f1', z, w)
        >>> print(d.dagger())
        Id(y) @ f1.dagger() >> f0.dagger() @ Id(z)
        """
        return Diagram(self.cod, self.dom,
                       [f.dagger() for f in self.boxes[::-1]],
                       self.offsets[::-1], _fast=True)

    @staticmethod
    def id(x):
        """
        >>> assert Diagram.id(Ty('x')) == Diagram(Ty('x'), Ty('x'), [], [])
        """
        return Id(x)

    def draw(self, _test=False, _data=None):
        """
        >>> x, y, z, w = Ty('x'), Ty('y'), Ty('z'), Ty('w')
        >>> diagram = Box('f0', x, y) @ Box('f1', z, w)
        >>> graph, pos, labels = diagram.draw(_test=True)
        >>> for u, s in sorted(labels.items()): print("{} ({})".format(u, s))
        box_0 (f0)
        box_1 (f1)
        input_0 (x)
        input_1 (z)
        output_0 (y)
        output_1 (w)
        >>> for u, (i, j) in sorted(pos.items()):
        ...     print("{} {}".format(u, (i, j)))
        box_0 (-1.0, 2)
        box_1 (0.0, 1)
        input_0 (-1.0, 3)
        input_1 (0.0, 3)
        output_0 (-1.0, 0)
        output_1 (0.0, 0)
        wire_0_1 (0.0, 2)
        wire_1_0 (-1.0, 1)
        >>> for u, v in sorted(graph.edges()): print("{} -> {}".format(u, v))
        box_0 -> wire_1_0
        box_1 -> output_1
        input_0 -> box_0
        input_1 -> wire_0_1
        wire_0_1 -> box_1
        wire_1_0 -> output_0
        """
        # pylint: disable=import-outside-toplevel
        import matplotlib.pyplot as plt
        import networkx as nx

        def build_graph():
            graph, positions, labels = nx.Graph(), dict(), dict()

            def add(node, position, label):
                graph.add_node(node)
                positions.update({node: position})
                if label is not None:
                    labels.update({node: label})
            for i in range(len(self.dom)):
                position = (-.5 * len(self.dom) + i, len(self) + 1)
                add("input_{}".format(i), position, self.dom[i])
            scan = ["input_{}".format(i) for i, _ in enumerate(self.dom)]
            for i, (box, off) in enumerate(zip(self.boxes, self.offsets)):
                pad = -.5 * (len(scan) - len(box.dom) + 1)
                box_node = "box_{}".format(i)
                add(box_node, (pad + off, len(self) - i), str(box))
                graph.add_edges_from(
                    [(scan[off + j], box_node) for j, _ in enumerate(box.dom)])
                for j, _ in enumerate(scan[:off]):
                    wire_node = "wire_{}_{}".format(i, j)
                    add(wire_node, (pad + j, len(self) - i), None)
                    graph.add_edge(scan[j], wire_node)
                    scan[j] = wire_node
                for j, _ in enumerate(scan[off + len(box.dom):]):
                    wire_node = "wire_{}_{}".format(i, off + j + 1)
                    add(wire_node, (pad + off + j + 1, len(self) - i), None)
                    graph.add_edge(scan[off + len(box.dom) + j], wire_node)
                    scan[off + len(box.dom) + j] = wire_node
                scan = scan[:off] + len(box.cod) * [box_node]\
                    + scan[off + len(box.dom):]
            for i in range(len(self.cod)):
                position = (-.5 * len(scan) + i, 0)
                add("output_{}".format(i), position, self.cod[i])
                graph.add_edge(scan[i], "output_{}".format(i))
            return graph, positions, labels

        def draw_graph(graph, positions, labels):
            inputs, outputs, boxes, wires = (
                [node for node in graph.nodes if node[:len(name)] == name]
                for name in ('input', 'output', 'box', 'wire'))
            nx.draw_networkx_nodes(
                graph, positions, nodelist=inputs, node_color='#ffffff')
            nx.draw_networkx_nodes(
                graph, positions, nodelist=outputs, node_color='#ffffff')
            nx.draw_networkx_nodes(
                graph, positions, nodelist=wires, node_size=0)
            nx.draw_networkx_nodes(
                graph, positions, nodelist=boxes, node_color='#ff0000')
            nx.draw_networkx_labels(graph, positions, labels)
            nx.draw_networkx_edges(graph, positions)
            plt.axis("off")
            plt.show()
        graph, positions, labels = build_graph() if _data is None else _data
        if not _test:
            draw_graph(graph, positions, labels)
        return graph, positions, labels

    def interchange(self, i, j, left=False):
        """
        Returns a new diagram with boxes i and j interchanged.
        If there is a choice, i.e. when interchanging an effect and a state,
        then we return the right interchange move by default.

        >>> x, y = Ty('x'), Ty('y')
        >>> f = Box('f', x, y)
        >>> d = f @ f.dagger()
        >>> print(d.interchange(0, 0))
        f @ Id(y) >> Id(y) @ f.dagger()
        >>> print(d.interchange(0, 1))
        Id(x) @ f.dagger() >> f @ Id(x)
        >>> print((d >> d.dagger()).interchange(0, 2))
        Id(x) @ f.dagger() >> Id(x) @ f >> f @ Id(y) >> f.dagger() @ Id(y)
        >>> cup, cap = Box('cup', x @ x, Ty()), Box('cap', Ty(), x @ x)
        >>> print((cup >> cap).interchange(0, 1))
        cap @ Id(x @ x) >> Id(x @ x) @ cup
        >>> print((cup >> cap).interchange(0, 1, left=True))
        Id(x @ x) @ cap >> cup @ Id(x @ x)
        >>> f0, f1 = Box('f0', x, y), Box('f1', y, x)
        >>> d = f0 @ Id(y) >> f1 @ f1 >> Id(x) @ f0
        >>> d.interchange(0,2) #doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        discopy.moncat.InterchangerError: Boxes ... do not commute.
        >>> assert d.interchange(2,0) == Id(x) @ f1 >> f0 @ Id(x) >> f1 @ f0
        """
        if not 0 <= i < len(self) or not 0 <= j < len(self):
            raise IndexError("Expected indices in range({}), got {} instead."
                             .format(len(self), (i, j)))
        if i == j:
            return self
        if j < i - 1:
            result = self
            for k in range(i - j):
                result = result.interchange(i - k, i - k - 1)
            return result
        if j > i + 1:
            result = self
            for k in range(j - i):
                result = result.interchange(i + k, i + k + 1)
            return result
        if j < i:
            i, j = j, i
        box0, box1 = self.boxes[i], self.boxes[j]
        off0, off1 = self.offsets[i], self.offsets[j]
        # By default, we check if box0 is to the right first, then to the left.
        if left and off1 >= off0 + len(box0.cod):
            off1 = off1 - len(box0.cod) + len(box0.dom)
        elif off0 >= off1 + len(box1.dom):  # box0 right of box1
            off0 = off0 - len(box1.dom) + len(box1.cod)
        elif off1 >= off0 + len(box0.cod):  # box0 left of box1
            off1 = off1 - len(box0.cod) + len(box0.dom)
        else:
            raise InterchangerError("Boxes {} and {} do not commute."
                                    .format(repr(box0), repr(box1)))
        return Diagram(
            self.dom, self.cod,
            self.boxes[:i] + [box1, box0] + self.boxes[i + 2:],
            self.offsets[:i] + [off1, off0] + self.offsets[i + 2:],
            _fast=True)

    def normalize(self, left=False):
        """
        Returns a generator which yields the diagrams at each step towards
        a normal form. Never halts if the diagram is not connected.

        >>> s0, s1 = Box('s0', Ty(), Ty()), Box('s1', Ty(), Ty())
        >>> gen = (s0 @ s1).normalize()
        >>> for _ in range(3): print(next(gen))
        s1 >> s0
        s0 >> s1
        s1 >> s0
        >>> x, y = Ty('x'), Ty('y')
        >>> f0, f1 = Box('f0', x, y), Box('f1', y, x)
        >>> for d in (Id(x) @ f1 >> f0 @ Id(x)).normalize(): print(d)
        f0 @ Id(y) >> Id(y) @ f1
        >>> for d in (f0 @ f1).normalize(left=True): print(d)
        Id(x) @ f1 >> f0 @ Id(x)
        """
        diagram = self
        while True:
            before = diagram
            for i in range(len(diagram) - 1):
                box0, box1 = diagram.boxes[i], diagram.boxes[i + 1]
                off0, off1 = diagram.offsets[i], diagram.offsets[i + 1]
                if left and off1 >= off0 + len(box0.cod)\
                        or not left and off0 >= off1 + len(box1.dom):
                    try:
                        diagram = diagram.interchange(i, i + 1, left=left)
                        break
                    except InterchangerError:
                        pass
            if diagram == before:  # no more moves
                break
            yield diagram

    def normal_form(self, left=False):
        """
        Implements normalisation of connected diagrams, see arXiv:1804.07832.
        By default, we apply only right exchange moves.

        >>> assert Id(Ty()).normal_form() == Id(Ty())
        >>> assert Id(Ty('x', 'y')).normal_form() == Id(Ty('x', 'y'))
        >>> s0, s1 = Box('s0', Ty(), Ty()), Box('s1', Ty(), Ty())
        >>> (s0 >> s1).normal_form()  # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        NotImplementedError: Diagram s0 >> s1 is not connected.
        >>> x, y = Ty('x'), Ty('y')
        >>> f0, f1 = Box('f0', x, y), Box('f1', y, x)
        >>> assert f0.normal_form() == f0
        >>> assert (f0 >> f1).normal_form() == f0 >> f1
        >>> assert (Id(x) @ f1 >> f0 @ Id(x)).normal_form() == f0 @ f1
        >>> assert (f0 @ f1).normal_form(left=True) == Id(x) @ f1 >> f0 @ Id(x)
        """
        diagram, cache = self, set()
        for _diagram in self.normalize(left=left):
            if _diagram in cache:
                raise NotImplementedError(
                    "Diagram {} is not connected.".format(self))
            diagram = _diagram
            cache.add(diagram)
        return diagram

    def flatten(self):
        """
        Takes a diagram of diagrams and returns a diagram.

        >>> x, y = Ty('x'), Ty('y')
        >>> f0, f1 = Box('f0', x, y), Box('f1', y, x)
        >>> g = Box('g', x @ y, y)
        >>> d = (Id(y) @ f0 @ Id(x) >> f0.dagger() @ Id(y) @ f0 >>\\
        ...      g @ f1 >> f1 @ Id(x)).normal_form()
        >>> assert d.slice().flatten().normal_form() == d
        """
        return MonoidalFunctor(Quiver(lambda x: x), Quiver(lambda f: f))(self)

    def slice(self):
        """
        Returns a diagram with diagrams of depth 1 as boxes such that its
        flattening gives the original diagram back, up to normal form.

        >>> x, y = Ty('x'), Ty('y')
        >>> f0, f1 = Box('f0', x, y), Box('f1', y, x)
        >>> d = f0 @ Id(y) >> f0.dagger() @ f1 >> Id(x) @ f0
        >>> assert d.slice().flatten().normal_form() == d
        """
        diagram = self
        i, slices, dom, cod = 0, [], diagram.dom, diagram.dom
        while i < len(diagram):
            dom, n_boxes = cod, 0
            for j in range(i + 1, len(diagram)):
                try:
                    diagram = diagram.interchange(j, i)
                    n_boxes += 1
                except InterchangerError:
                    pass
            for j in range(i, i + n_boxes + 1):
                box, off = diagram.boxes[j], diagram.offsets[j]
                cod = cod[:off] + box.cod + cod[off + len(box.dom):]
            slices.append(Diagram(dom, cod,
                                  diagram.boxes[i: i + n_boxes + 1],
                                  diagram.offsets[i: i + n_boxes + 1],
                                  _fast=True))
            i += n_boxes + 1
        return Diagram(self.dom, self.cod, slices, len(slices) * [0],
                       _fast=True)

    def depth(self):
        """ Computes the depth of a diagram by slicing it

        >>> x, y = Ty('x'), Ty('y')
        >>> f, g = Box('f', x, y), Box('g', y, x)
        >>> assert Id(x @ y).depth() == 0
        >>> assert f.depth() == 1
        >>> assert (f @ g).depth() == 1
        >>> assert (f >> g).depth() == 2
        """
        return len(self.slice())


def _spiral(n_cups):
    """
    Implements the asymptotic worst-case for normal_form, see arXiv:1804.07832.

    >>> n = 2
    >>> spiral = _spiral(n)
    >>> unit, counit = Box('unit', Ty(), Ty('x')), Box('counit', Ty('x'), Ty())
    >>> assert spiral.boxes[0] == unit and spiral.boxes[n + 1] == counit
    >>> spiral_nf = spiral.normal_form()
    >>> assert spiral_nf.boxes[-1] == counit and spiral_nf.boxes[n] == unit
    """
    x = Ty('x')  # pylint: disable=invalid-name
    unit, counit = Box('unit', Ty(), x), Box('counit', x, Ty())
    cup, cap = Box('cup', x @ x, Ty()), Box('cap', Ty(), x @ x)
    result = unit
    for i in range(n_cups):
        result = result >> Id(x ** i) @ cap @ Id(x ** (i + 1))
    result = result >> Id(x ** n_cups) @ counit @ Id(x ** n_cups)
    for i in range(n_cups):
        result = result >>\
            Id(x ** (n_cups - i - 1)) @ cup @ Id(x ** (n_cups - i - 1))
    return result


class AxiomError(cat.AxiomError):
    """
    >>> Diagram(Ty('x'), Ty('x'), [Box('f', Ty('x'), Ty('y'))], [0])
    ... # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    discopy.moncat.AxiomError: Codomain x expected, got y instead.
    >>> Diagram(Ty('y'), Ty('y'), [Box('f', Ty('x'), Ty('y'))], [0])
    ... # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    discopy.moncat.AxiomError: Domain y expected, got x instead.
    """


class InterchangerError(AxiomError):
    """
    >>> x, y, z = Ty('x'), Ty('y'), Ty('z')
    >>> d = Box('f', x, y) >> Box('g', y, z)
    >>> d.interchange(0, 1)  # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    discopy.moncat.InterchangerError: Boxes ... do not commute.
    """


class Id(Diagram):
    """ Implements the identity diagram of a given type.

    >>> s, t = Ty('x', 'y'), Ty('z', 'w')
    >>> f = Box('f', s, t)
    >>> assert f >> Id(t) == f == Id(s) >> f
    """
    def __init__(self, x):
        """
        >>> assert Id(Ty('x')) == Diagram.id(Ty('x'))
        """
        super().__init__(x, x, [], [], _fast=True)

    def __repr__(self):
        """
        >>> Id(Ty('x'))
        Id(Ty('x'))
        """
        return "Id({})".format(repr(self.dom))

    def __str__(self):
        """
        >>> print(Id(Ty('x')))
        Id(x)
        """
        return "Id({})".format(str(self.dom))


class Box(cat.Box, Diagram):
    """ Implements a box as a diagram with a name and itself as box.

    Note that as for composition, when we tensor an empty diagram with a box,
    we get a diagram that is defined as equal to the original box.

    >>> f = Box('f', Ty('x', 'y'), Ty('z'))
    >>> Id(Ty('x', 'y')) >> f  # doctest: +ELLIPSIS
    Diagram(dom=Ty('x', 'y'), cod=Ty('z'), boxes=[Box(...)], offsets=[0])
    >>> Id(Ty()) @ f  # doctest: +ELLIPSIS
    Diagram(dom=Ty('x', 'y'), cod=Ty('z'), boxes=[Box(...)], offsets=[0])
    >>> assert Id(Ty('x', 'y')) >> f == f == f >> Id(Ty('z'))
    >>> assert Id(Ty()) @ f == f == f @ Id(Ty())
    >>> assert f == f.dagger().dagger()
    """
    def __init__(self, name, dom, cod, data=None, _dagger=False):
        """
        >>> f = Box('f', Ty('x', 'y'), Ty('z'), data=42)
        >>> print(f)
        f
        >>> f.name, f.dom, f.cod, f.data
        ('f', Ty('x', 'y'), Ty('z'), 42)
        """
        cat.Box.__init__(self, name, dom, cod, data=data, _dagger=_dagger)
        Diagram.__init__(self, dom, cod, [self], [0], _fast=True)

    def __eq__(self, other):
        """
        >>> f = Box('f', Ty('x', 'y'), Ty('z'), data=42)
        >>> assert f == Diagram(Ty('x', 'y'), Ty('z'), [f], [0])
        """
        if isinstance(other, Box):
            return repr(self) == repr(other)
        if isinstance(other, Diagram):
            return (other.boxes, other.offsets) == ([self], [0])
        return False

    def __hash__(self):
        """
        >>> f = Box('f', Ty('x', 'y'), Ty('z'), data=42)
        >>> {f: 42}[f]
        42
        """
        return hash(repr(self))


class MonoidalFunctor(Functor):
    """
    Implements a monoidal functor given its image on objects and arrows.
    One may define monoidal functors into custom categories by overriding
    the defaults ob_cls=Ty and ar_cls=Diagram.

    >>> x, y, z, w = Ty('x'), Ty('y'), Ty('z'), Ty('w')
    >>> f0, f1 = Box('f0', x, y, data=[0.1]), Box('f1', z, w, data=[1.1])
    >>> F = MonoidalFunctor({x: z, y: w, z: x, w: y}, {f0: f1, f1: f0})
    >>> assert F(f0) == f1 and F(f1) == f0
    >>> assert F(F(f0)) == f0
    >>> assert F(f0 @ f1) == f1 @ f0
    >>> assert F(f0 >> f0.dagger()) == f1 >> f1.dagger()
    """
    def __init__(self, ob, ar, ob_cls=Ty, ar_cls=Diagram):
        """
        >>> F = MonoidalFunctor({Ty('x'): Ty('y')}, {})
        >>> F(Id(Ty('x')))
        Id(Ty('y'))
        """
        super().__init__(ob, ar, ob_cls=ob_cls, ar_cls=ar_cls)

    def __repr__(self):
        """
        >>> MonoidalFunctor({Ty('x'): Ty('y')}, {})
        MonoidalFunctor(ob={Ty('x'): Ty('y')}, ar={})
        """
        return super().__repr__().replace("Functor", "MonoidalFunctor")

    def __call__(self, diagram):
        """
        >>> x, y = Ty('x'), Ty('y')
        >>> f = Box('f', x, y)
        >>> F = MonoidalFunctor({x: y, y: x}, {f: f.dagger()})
        >>> print(F(x))
        y
        >>> print(F(f))
        f.dagger()
        >>> print(F(F(f)))
        f
        >>> print(F(f >> f.dagger()))
        f.dagger() >> f
        >>> print(F(f @ f.dagger()))
        f.dagger() @ Id(x) >> Id(x) @ f
        """
        if isinstance(diagram, Ty):
            return sum([self.ob[self.ob_cls(x)] for x in diagram],
                       self.ob_cls())  # the empty type is the unit for sum.
        if isinstance(diagram, Box):
            return super().__call__(diagram)
        if isinstance(diagram, Diagram):
            scan, result = diagram.dom, self.ar_cls.id(self(diagram.dom))
            for box, off in zip(diagram.boxes, diagram.offsets):
                id_l = self.ar_cls.id(self(scan[:off]))
                id_r = self.ar_cls.id(self(scan[off + len(box.dom):]))
                result = result >> id_l @ self(box) @ id_r
                scan = scan[:off] + box.cod + scan[off + len(box.dom):]
            return result
        raise ValueError("Expected moncat.Diagram, got {} of type {} "
                         "instead.".format(repr(diagram), type(diagram)))

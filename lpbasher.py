import itertools
from rules import cell_nbrs, light_up, remaining_lightables, cell_reaches, print2D
from math import comb
from functools import cache

@cache
def binom(n,k):
    return comb(n,k)

@cache
def sumbinom(n,k):
    if k*2 > n: return 2**n - sumbinom(n,n-(k+1))
    return sum(binom(n,i) for i in range(k+1))

# Returns the restriction of all linear programming constraints in the puzzle on the set "cells". Some examples are written as comments below.
# Only the nontrivial restrictions are returned.
def computeLPRestriction(s, width, cells):
    # ((1,3),1,0,tuple()) for cells[1]+cells[3] <= 1, the whole thing was (1,3) only
    # ((2,3,4),2,1,(1,2)) for cells[2]+cells[3]+cells[4] >= 2, the whole thing was (s[1]+s[2])+(2,3,4) >= 3
    
    cellToInd = {c:i for i,c in enumerate(cells)}
    cellSet = set(cells)
    ans = []

    # Numbers
    surroundingNumberCells = {}
    for cell in cells:
        for nbr in cell_nbrs(cell, len(s)):
            if s[nbr] in "01234":
                if nbr not in surroundingNumberCells: surroundingNumberCells[nbr] = []
                surroundingNumberCells[nbr] += [cell]
    
    for numberCell, relevantCells in surroundingNumberCells.items():
        if len(relevantCells) <= 1: continue
        allRestricted = [x for x in cell_nbrs(numberCell,len(s)) if s[x] == "."]
        numRemaining = int(s[numberCell]) - sum(s[x]=="@" for x in cell_nbrs(numberCell,len(s)))

        cellIndTuple = tuple(cellToInd[cell] for cell in relevantCells)
        extraIndTuple = tuple(x for x in allRestricted if x not in cellSet)

        if numRemaining < len(cellIndTuple):
            ans += [(cellIndTuple, numRemaining, 0, extraIndTuple)]
        if numRemaining > len(extraIndTuple):
            ans += [(cellIndTuple, numRemaining-len(extraIndTuple), 1, extraIndTuple)]
    
    # Light Solve - Vertical
    blockCorrespondsTo = {}
    for i in range(len(cells)):
        curr = cells[i]
        while s[curr] not in "#01234" and curr >= 0: curr -= width
        if curr not in blockCorrespondsTo: blockCorrespondsTo[curr] = []
        blockCorrespondsTo[curr] += [i]
    
    for block in blockCorrespondsTo:
        if len(blockCorrespondsTo[block]) <= 1: continue
        extraInds = []
        curr = block+width
        while curr < len(s) and s[curr] not in "#01234":
            if curr not in cellSet and s[curr] == ".": extraInds += [curr]
            curr += width
        ans += [(tuple(blockCorrespondsTo[block]), 1, 0, tuple(extraInds))]
    
    # Light Solve - Horizontal
    blockCorrespondsTo = {}
    for i in range(len(cells)):
        curr = cells[i]
        while s[curr] not in "#01234" and curr % width != 0: curr -= 1
        if curr not in blockCorrespondsTo: blockCorrespondsTo[curr] = []
        blockCorrespondsTo[curr] += [i]
    
    for block in blockCorrespondsTo:
        if len(blockCorrespondsTo[block]) <= 1: continue
        extraInds = []
        curr = block+1 if s[block] in "#01234" else block
        while (curr % width > 0 or curr == block) and s[curr] not in "#01234":
            if curr not in cellSet and s[curr] == ".": extraInds += [curr]
            curr += 1
        ans += [(tuple(blockCorrespondsTo[block]), 1, 0, tuple(extraInds))]

    # Shadow solve
    reachSets = [set(cell_reaches(cell, s))|{cell} for cell in cells]
    reachSetsReverse = {}
    for i,reachSet in enumerate(reachSets):
        for reach in reachSet:
            if reach not in reachSetsReverse: reachSetsReverse[reach] = []
            reachSetsReverse[reach] += [i]

    for reach in reachSetsReverse:
        if len(reachSetsReverse[reach]) <= 1: continue
            
        rem = remaining_lightables(s, reach)
        if rem is not True and {*rem} == {cells[u] for u in reachSetsReverse[reach]}:
            ans += [(tuple(reachSetsReverse[reach]), 1, 1, tuple())]
    
    return ans

# By going through all 2^len(cells) possibilities, returns the puzzle after all progress has been made using the restriction of all constraints on "cells".
def lp_bash(s, width, cells):
    assert all(s[cell] == "." for cell in cells), f"LP bash only works on unknown cells! {s} {cells}"

    res = computeLPRestriction(s, width, cells)
    resProbs = []
    for lhsCells, limit, ineq, _ in res:
        llc = len(lhsCells)

        if ineq == 0: needed = limit
        else: needed = llc - limit

        prob = sumbinom(llc, needed) / (2**llc)
        resProbs += [prob]
    res = [u[1] for u in sorted(zip(resProbs,res))]

    options = []
    for option in itertools.product([0,1],repeat=len(cells)):
        bad = False
        for lhsCells, limit, ineq, extra in res:
            if ineq == 0:
                theSum = 0
                for i in lhsCells:
                    theSum += option[i]
                    if theSum > limit: break
                if theSum > limit:
                    bad = True
                    break
            else:
                lll = len(lhsCells)-limit

                theSum = 0
                for i in lhsCells:
                    theSum += 1-option[i]
                    if theSum > lll: break
                if theSum > lll:
                    bad = True
                    break
        if not bad: options += [option]
    if not options: return False

    # print(res,options,cells)

    cellFindings = []

    # Cell commonalities
    for i in range(len(cells)):
        checkIfOnly = options[0][i]
        if all(option[i] == checkIfOnly for option in options):
            cellFindings += [(cells[i], checkIfOnly)]
    
    # Saturated restrictions
    for lhsCells, limit, ineq, extra in res:
        if not extra: continue
        if all(sum(option[i] for i in lhsCells) == limit for option in options):
            for extraCell in extra:
                cellFindings += [(extraCell, ineq)]
    
    if not cellFindings: return s

    s = [*s]
    shouldLight = []
    for cell, shouldBe in cellFindings:
        if s[cell] == "-" and shouldBe == 0: continue
        s[cell] = " @"[shouldBe]
        if shouldBe: shouldLight += [cell]

    s = "".join(s)
    for lightCell in shouldLight:
        s = light_up(s, lightCell)

    return s

from itertools import combinations

# Attempts the "red blue graph" deduction strategy on the puzzle.
# Consider a graph on the the cells in the puzzle where there is a red edge drawn between two cells if they cannot both be a light,
# while there is a blue edge drawn between them if they cannot both be a non-light.
# Then a cycle of even length that alternates red and blue edges must have all relevant constraints saturated,
# while a cycle of odd length that alternates red and blue edges except at one "special vertex" where both colors are the same must have its "special vertex" determined.

# A red blue graph deduction on an even cycle may yield no information if all saturations do not give any information.
# In particular, this always happens if a red blue graph deduction was already done on this cycle.
# In this case, we should try find a different cycle that does yield information, as we are unsure if the deduction strategy works.
# Note that this does not apply to odd cycles, as odd cycles deduce one of the vertices in the graph, which is always new information.
# Define a red/blue edge to be "dark" if it being saturated gives information, and "light" otherwise.
# Then we would like an even cycle that has at least one dark edge.
# If this edge is a dark blue edge, we may start from this edge and DFS, and iterate this through every dark blue edge.
# If this edge is a dark red edge and there are no dark blue edges in the cycle, then the dark red edge must be adjacent to a light blue edge.
# Therefore, we will also iterate through all dark red edges that neighbor light blue edges.
def attempt_red_blue_graph(s, width):
    constraints = getAllConstraints(s, width)
    red = set()
    blue = set()
    dark_red = set()
    light_red = set()
    dark_blue = set()
    light_blue = set()

    nodes = [i for i in range(len(s)) if s[i] == "."]

    for lhsCells, limit, ineq in constraints:
        if ineq == 0 and limit == 1:
            to_add = {*combinations(lhsCells,2)}
            red |= to_add
            if len(lhsCells) == 2: light_red |= to_add
            else: dark_red |= to_add
        if ineq == 1 and limit == len(lhsCells)-1:
            to_add = {*combinations(lhsCells,2)}
            blue |= to_add
            if len(lhsCells) == 2: light_blue |= to_add
            else: dark_blue |= to_add

    light_red -= dark_red
    light_blue -= dark_blue

    conn_red = {u:set() for u in nodes}
    conn_blue = {u:set() for u in nodes}

    for x,y in red:
        conn_red[x].add(y)
        conn_red[y].add(x)

    for x,y in blue:
        conn_blue[x].add(y)
        conn_blue[y].add(x)
    
    even_length_start_edges = {(tuple(sorted(u)),1) for u in dark_blue}
    for light_blue_edge in light_blue:
        for node_of_incidence in light_blue_edge:
            for node_outwards in conn_red[node_of_incidence]:
                if (node_of_incidence, node_outwards) in dark_red or \
                   (node_outwards, node_of_incidence) in dark_red:
                    even_length_start_edges.add(
                        (tuple(sorted(
                            (node_of_incidence, node_outwards)
                        )),0)
                    )

    # Alternating red-blue cycle of even length
    for (start, second), beginning_color in even_length_start_edges:
        start_color = 1-beginning_color

        seen = {start}
        todo = [(second, start_color)] # (node, color it would like to receive where red=0 and blue=1)
        parents = {second: start}

        while todo:
            v,color = todo.pop()
            seen.add(v)
            friends = conn_red[v] if color == 0 else conn_blue[v]
            for w in friends:
                if w in seen: continue
                parents[w] = v
                todo += [(w,1-color)]

            if start in friends and parents[v] != start:
                # A deduction was found!
                trace_back = [v]
                while trace_back[-1] != start: trace_back += [parents[trace_back[-1]]]
                if len(trace_back) % 2 == 1: break

                cellFindings = []

                for a,b in zip(trace_back, trace_back[1:] + trace_back[:1]):
                    res = computeLPRestriction(s, width, [a,b])
                    for lhsCells, limit, ineq, extra in res:
                        assert limit == 1
                        cellFindings += [(ex, ineq) for ex in extra]

                s = [*s]
                shouldLight = []
                for cell, shouldBe in cellFindings:
                    if s[cell] == "-" and shouldBe == 0: continue
                    s[cell] = " @"[shouldBe]
                    if shouldBe: shouldLight += [cell]

                s = "".join(s)
                for lightCell in shouldLight:
                    s = light_up(s, lightCell)
                
                return s, trace_back

    # Odd cycle where 2k of the 2k+1 connections are alternating
    # Insist on letting start be the node incident to two edges of the same color
    for start in nodes:
        for start_color in 0,1:
            seen = set()
            todo = [(start,start_color)] # (node, color it would like to receive where red=0 and blue=1)
            parents = {}

            while todo:
                v,color = todo.pop()
                seen.add(v)
                friends = conn_red[v] if color == 0 else conn_blue[v]
                for w in friends:
                    if w in seen: continue
                    parents[w] = v
                    todo += [(w,1-color)]

                if start in friends and parents[v] != start:
                    # A deduction was found!
                    trace_back = [v]
                    while trace_back[-1] != start: trace_back += [parents[trace_back[-1]]]
                    assert len(trace_back) % 2

                    # "start" has been determined
                    if start_color == 0:
                        return s[:start] + " " + s[start+1:], trace_back
                    else:
                        return light_up(s, start), trace_back
    
    return s, None

# Returns a list of all constraints on a partially completed grid.
def getAllConstraints(s, width):
    cells = [i for i in range(len(s)) if s[i] == "."]
    lpr = computeLPRestriction(s, width, cells)

    ans = []
    for a,b,c,_ in lpr:
        ans += [(tuple(cells[i] for i in a),b,c)]
    return ans

# Returns a subset S of "cells" such that lp_bash on S gives the same result as lp_bash on cells, but no proper subset of S satisfies this property.
def minimalDeductionSet(s, width, cells):
    # We may prove that just checking once in order like this works.
    standard = lp_bash(s, width, cells)
    cellSet = set(cells)
    for x in cells:
        if lp_bash(s, width, [*(cellSet-{x})]) == standard: cellSet -= {x}
    return sorted(cellSet)
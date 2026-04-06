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

def attempt_red_blue_graph(s, width):
    constraints = getAllConstraints(s, width)
    red = set()
    blue = set()

    nodes = [i for i in range(len(s)) if s[i] == "."]

    for lhsCells, limit, ineq in constraints:
        if ineq == 0 and limit == 1:
            red |= {*combinations(lhsCells,2)}
        if ineq == 1 and limit == len(lhsCells)-1:
            blue |= {*combinations(lhsCells,2)}

    conn_red = {u:set() for u in nodes}
    conn_blue = {u:set() for u in nodes}

    for x,y in red:
        conn_red[x].add(y)
        conn_red[y].add(x)

    for x,y in blue:
        conn_blue[x].add(y)
        conn_blue[y].add(x)
    
    # Alternating red-blue cycle of even length, or odd length and 2k of the 2k+1 connections are alternating
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

    # For odd cycle, insist on letting start be that weird node
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
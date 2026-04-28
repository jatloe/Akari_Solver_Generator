from time import perf_counter as pc
from copy import deepcopy
from drawer import draw, make_gif
from tqdm import tqdm
import random
import itertools

from rules import cell_nbrs, cell_reaches, progress_valid, puzzle_completed, print2D, get_children_ind, set_width, light_up, remaining_lightables
from lpbasher import lp_bash, getAllConstraints, minimalDeductionSet, attempt_red_blue_graph

DEFAULT_DEDUCTION_LIMIT = 30
DEFAULT_RECURSION_LIMIT = 2
SMALL_DEDUCTION_CUTOFF = 999999
SMALL_CONSTRAINT_CUTOFF = 4
STRATEGIES = ["SC2", "SC3", "N1D"]

MAX_LP_COUNT = 4

DEFAULT_STATS = {
    "recursions": 0,
    "grids": [],
    "temp recursions": 0,
    "temp grids": 0,
    "LP deductions done": [],
    "all solutions": [],
    "used red/blue graph or recursion": False,
    "used recursion": False
}

STATS = deepcopy(DEFAULT_STATS)

# A list of cells that could theoretically have a deduction on them.
# Unfortunately, this is usually the full list of cells.
class FocusCellsList:
    def __init__(self, givenList, possibleList=None):
        if possibleList is None: possibleList = givenList[:]
        self.list = givenList[:]
        self.possibleList = possibleList

    def reset(self):
        self.list = self.possibleList[:]
    
    def is_empty(self):
        return len(self.list) == 0

    def pop(self):
        return self.list.pop()
    
    def clean(self):
        pass
    
    def shuffle(self):
        pass
    
    def copy(self):
        return FocusCellsList(self.possibleList)

def reset_stats():
    global STATS
    STATS = deepcopy(DEFAULT_STATS)

def solve(s, width, use_heuristic=False, prove=False, should_make_gif=False, verbose=True, lp_hints=None, ban_lp=False, ban_recursion=False, strategies=STRATEGIES[:], prescribed_lp_deductions=None, return_stat=("solution",)):
    st = pc()

    set_width(width)

    global prescribed_lp_deduction_ind
    prescribed_lp_deduction_ind = 0

    # Accept partially filled grids
    unfilled = "".join(x if x in "#01234" else "." for x in s)

    # Generate friends
    friends = [cell_reaches(ind, unfilled) if unfilled[ind] == "." else [] for ind in range(len(unfilled))]
    for i in range(len(unfilled)):
        if unfilled[i] in "01234":
            cn = cell_nbrs(i, len(unfilled))
            for x in cn:
                if unfilled[x] in "#01234": continue
                for y in cn:
                    if x == y: continue
                    if unfilled[y] in "#01234": continue
                    if y not in friends[x]: friends[x] += [y]

    # Checks if the cell with index focus_cell can be deduced.
    # If so, returns the updated grid. Otherwise, returns the current grid.
    # If the puzzle is impossible, returns None.
    def simpleDeductions(s, focus_cell):
        if s[focus_cell] != ".": return s

        # Shadow solve
        for cell in cell_reaches(focus_cell, s):
            if s[cell] != " ": continue
            scary = True
            for f in cell_reaches(cell, s):
                if f == focus_cell: continue
                if s[f] == ".": scary = False; break
            if scary: return light_up(s, focus_cell)
        
        scary = True
        for f in cell_reaches(focus_cell, s):
            if s[f] == ".": scary = False; break
        if scary: return light_up(s, focus_cell)

        # Numbers
        for cell in cell_nbrs(focus_cell, len(s)):
            if s[cell] not in "01234": continue
            num = int(s[cell])
            tocount = cell_nbrs(cell, len(s))
            already = sum(1 for i in tocount if s[i] == "@")
            remaining = sum(1 for i in tocount if s[i] == ".")
            if already > num: return None
            if already + remaining < num: return None
            if already == num: return s[:focus_cell] + " " + s[focus_cell+1:]
            if already + remaining == num: return light_up(s, focus_cell)

        # Light solve
        for cell in cell_reaches(focus_cell, s):
            if s[cell] == "@": raise Exception("what!"); return s[:focus_cell] + " " + s[focus_cell+1:]
        return s

    # Returns all potential LP deduction sets of cycles of 4 cells in the "shares a constraint" graph.
    def LP_deduction_candidates_helper_friends_c4(s):
        ans = []

        empty = [x for x in range(len(s)) if s[x] == "."]
        for c1 in empty: # overall_focus_cells:
            if s[c1] != ".": continue
            for c2 in friends[c1]:
                if s[c2] != ".": continue
                for c3 in friends[c2]:
                    if s[c3] != ".": continue
                    if c3 == c1: continue
                    for c4 in friends[c3]:
                        if c4 not in friends[c1]: continue
                        if s[c1] != "." or s[c2] != "." or s[c3] != "." or s[c4] != ".": continue
                        if len({c1,c2,c3,c4}) < 4: continue
                        ans += [(c1,c2,c3,c4)]
        
        return sorted(set(ans))

    def union_the_sets(sets):
        ans = set()
        for s in sets: ans |= s
        return ans

    # Returns all potential LP deduction sets of cells adjacent to one of n number clues.
    def LP_deduction_candidates_helper_n_numbers(s,n):
        numberChoices = set()

        for i in range(len(s)):
            if s[i] not in "01234": continue

            nbrSet = {nbr for nbr in cell_nbrs(i, len(s)) if s[nbr] == "."}

            numberChoices.add(tuple(sorted(nbrSet)))
        
        numberChoices = [*map(set,numberChoices)]
        ans = []

        for comb in itertools.combinations(numberChoices, r=n):
            if n == 2:
                nc1, nc2 = comb
                totsum = 0
                for i in nc1:
                    totsum += len({*friends[i]} & nc2) + (i in nc2)
                    if totsum >= 2: break
                if totsum <= 1: continue
            ans += [tuple(union_the_sets(comb))]
        
        return ans

    def LP_deduction_candidates_helper_two_numbers(s):
        return LP_deduction_candidates_helper_n_numbers(s,2)

    def LP_deduction_candidates_helper_three_numbers(s):
        return LP_deduction_candidates_helper_n_numbers(s,3)

    # Returns all potential LP deduction sets of cells orthogonally or diagonally adjacent to one number clue.
    def LP_deduction_candidates_helper_one_number_diagonal(s):
        ans = []

        for i in range(len(s)):
            if s[i] not in "01234": continue

            ans += [tuple(nbr for nbr in cell_nbrs(i, len(s), diagonal=True) if s[nbr] == ".")]
        
        return ans

    # Returns all potential LP deduction sets of cells that are the union of n small constraints (size <= 4).
    def LP_deduction_candidates_helper_n_small_constraints(s, n):
        if SMALL_CONSTRAINT_CUTOFF <= 1: return []
        
        # Find all constraints
        gac = getAllConstraints(s, width)
        smallConstraints = [set(lhsCells) for lhsCells, limit, ineq in gac if len(lhsCells) <= SMALL_CONSTRAINT_CUTOFF]
        smallConstraints = [*map(set,{tuple(sorted(x)) for x in smallConstraints})]

        # print(sorted(map(len,smallConstraints)))

        ans = []
        if n == 2:
            for comb in itertools.combinations(smallConstraints, r=n):
                nc1, nc2 = comb
                totsum = 0
                for i in nc1:
                    totsum += len({*friends[i]} & nc2) + (i in nc2)
                    if totsum >= 2: break
                if totsum <= 1: continue
                ans += [tuple(union_the_sets(comb))]
        elif n == 3:
            lsc = len(smallConstraints)
            conn = [set() for _ in range(lsc)] # Only smaller to larger
            for i in range(lsc):
                for j in range(i+1,lsc):
                    nc1 = smallConstraints[i]
                    nc2 = smallConstraints[j]

                    connected = bool(nc1 & nc2)
                    if not connected:
                        for x in nc1:
                            if {*friends[x]} & nc2:
                                connected = True
                                break

                    if connected:
                        conn[i] |= {j}
            for i in range(lsc):
                for j in conn[i]:
                    for k in conn[i] & conn[j]:
                        comb = tuple(smallConstraints[x] for x in (i,j,k))
                        ans += [tuple(union_the_sets(comb))]
        else:
            for comb in itertools.combinations(smallConstraints, r=n):
                ans += [tuple(union_the_sets(comb))]

        return ans
    
    def LP_deduction_candidates_helper_two_small_constraints(s):
        return LP_deduction_candidates_helper_n_small_constraints(s,2)
    
    def LP_deduction_candidates_helper_three_small_constraints(s):
        return LP_deduction_candidates_helper_n_small_constraints(s,3)
    
    def LP_deduction_candidates_helper_four_small_constraints(s):
        return LP_deduction_candidates_helper_n_small_constraints(s,4)

    # Returns all potential LP deduction sets of cells using the given strategies.
    def LP_deduction_candidates(s, strategies=["C4","N3","N2","SC2","SC3","N1D"]):
        ans = []
        seenans = set()

        strategyPairs = [
            ("N2", LP_deduction_candidates_helper_two_numbers),
            ("SC2", LP_deduction_candidates_helper_two_small_constraints),
            ("N3", LP_deduction_candidates_helper_three_numbers),
            ("SC3", LP_deduction_candidates_helper_three_small_constraints),
            ("SC4", LP_deduction_candidates_helper_four_small_constraints),
            ("C4", LP_deduction_candidates_helper_friends_c4),
            ("N1D", LP_deduction_candidates_helper_one_number_diagonal),
        ] # Priority is first to last

        for stratStr, stratFunc in strategyPairs:
            if stratStr in strategies:
                for cand in stratFunc(s):
                    cand = tuple(sorted(cand))
                    if cand in seenans: continue
                    ans += [cand]
                    seenans.add(cand)

        # print(ans,strategies)

        return ans

    # Usually uses simpleDeductions, sometimes uses LP deductions, and only resorts to bifurcation if completely necessary.
    # Recursion depth is the limit (goes down), depth of recursion goes up
    def solve_recurse(s, focus_cells, is_top_layer, recursion_limit, current_recursion_depth, deduction_limit):
        if not progress_valid(s): return False

        if is_top_layer and verbose: print(end=f"\r{s.count('.')} {0:05} •ᴗ•" + " "*10)
        
        prev_s = s
        possibleList = [x for x in range(len(s)) if s[x] == "."]

        if focus_cells is None:
            focus_cells = FocusCellsList(possibleList)

        focus_cells.shuffle()

        # Simple deductions
        while not focus_cells.is_empty():
            if deduction_limit <= 0 and not is_top_layer:
                if not progress_valid(s): return False
                return True

            node = focus_cells.pop()
            t = simpleDeductions(s, node)
            if t is None: return False
            if s == t: continue

            focus_cells.reset()
            s = t
            deduction_limit -= 1

            if is_top_layer:
                STATS["recursions"] += 1
                STATS["grids"] += [(s,0,tuple())]
            else:
                STATS["temp recursions"] += 1
                STATS["temp grids"] += [(s,current_recursion_depth,tuple())]
            
            if not progress_valid(s): return False

        if not progress_valid(s): return False

        if "." not in s:
            if puzzle_completed(s):
                if not prove: return s
                STATS["all solutions"] += [s]
                return False
            else: return False

        if ban_lp: return s
        if recursion_limit <= 0 and not is_top_layer: return True

        STATS["not just deductions"] = True

        # LP deductions
        if is_top_layer:
            if prescribed_lp_deductions is None:
                cands = LP_deduction_candidates(s, strategies=strategies)
                if lp_hints is not None:
                    cands = [tup for tup in lp_hints if all(s[x] == "." for x in tup)] + cands
                for cand in cands:
                    newS = lp_bash(s, width, cand)
                    if newS is False: return False
                    if s != newS:
                        newCand = minimalDeductionSet(s, width, cand)

                        STATS["recursions"] += 1
                        STATS["grids"] += [(s,0,newCand), (newS,0,newCand)]
                        STATS["LP deductions done"] += [cand]

                        s = newS
                        
                        return solve_recurse(s,
                        focus_cells = FocusCellsList(possibleList),
                        is_top_layer=is_top_layer,
                        recursion_limit=recursion_limit,
                        current_recursion_depth=current_recursion_depth,
                        deduction_limit=deduction_limit)
            else:
                # Goes through prescribed LP deductions. (See condense_lp function for explanation)
                global prescribed_lp_deduction_ind
                if prescribed_lp_deduction_ind >= len(prescribed_lp_deductions): return s

                cand = prescribed_lp_deductions[prescribed_lp_deduction_ind]

                newS = lp_bash(s, width, cand)
                if newS is False: return False
                if s == newS: return s

                prescribed_lp_deduction_ind += 1
                
                newCand = minimalDeductionSet(s, width, cand)

                STATS["recursions"] += 1
                STATS["grids"] += [(s,0,newCand), (newS,0,newCand)]
                STATS["LP deductions done"] += [cand]

                s = newS
                
                return solve_recurse(s,
                focus_cells = FocusCellsList(possibleList),
                is_top_layer=is_top_layer,
                recursion_limit=recursion_limit,
                current_recursion_depth=current_recursion_depth,
                deduction_limit=deduction_limit)

        STATS["used red/blue graph or recursion"] = True

        if ban_recursion: return s

        # RED BLUE GRAPH
        # If ever recursed then don't bother
        if is_top_layer and not STATS["used recursion"]:
            t,cand = attempt_red_blue_graph(s, width)
            if s != t:
                # WOW!
                STATS["recursions"] += 1
                STATS["grids"] += [(s,0,cand)]
                STATS["grids"] += [(t,0,cand)]
                STATS["LP deductions done"] += [cand] * (len(cand)//2) # Increase level by that much

                s = t

                return solve_recurse(s,
                focus_cells = FocusCellsList(possibleList),
                is_top_layer=is_top_layer,
                recursion_limit=recursion_limit,
                current_recursion_depth=current_recursion_depth,
                deduction_limit=deduction_limit)

        STATS["used recursion"] = True
        
        possible_caseworks = possibleList[:]

        # Bifurcation...
        for lower_recursion_limit in range(recursion_limit if not is_top_layer else DEFAULT_RECURSION_LIMIT):
            best = (10**10, None, None, 0) # (recursions, grids, other child, ind)

            for ofc_i, ind in enumerate(possible_caseworks): # original_focus_cells
                if is_top_layer and verbose: print(end=f"\r{s.count('.')} {int(possible_caseworks.index(ind)/len(possible_caseworks)*10000):05} •ᴗ•" + " "*10)
                if s[ind] != ".": continue
                children = [s[:ind]+" "+s[ind+1:], light_up(s, ind)]

                for i,child in enumerate(children):
                    if is_top_layer:
                        STATS["temp recursions"] = 0
                        STATS["temp grids"] = []
                    STATS["temp recursions"] += 1
                    STATS["temp grids"] += [(child,current_recursion_depth+1,tuple())]

                    res = solve_recurse(child, focus_cells=FocusCellsList(possibleList),
                                        is_top_layer=False,
                                        recursion_limit=lower_recursion_limit,
                                        current_recursion_depth=current_recursion_depth+1,
                                        deduction_limit=min(DEFAULT_DEDUCTION_LIMIT,best[0]))

                    if not res:
                        if STATS["temp recursions"] >= best[0]: continue
                        best = (STATS["temp recursions"], STATS["temp grids"], children[i^1], ind)
                        if best[0] < SMALL_DEDUCTION_CUTOFF: break

                if best[0] < SMALL_DEDUCTION_CUTOFF: break

            if best[1] == None: continue

            if is_top_layer:
                STATS["recursions"] += best[0]
                STATS["grids"] += best[1]

            return solve_recurse(best[2],
                focus_cells = FocusCellsList(possibleList),
                is_top_layer=is_top_layer,
                recursion_limit=recursion_limit,
                current_recursion_depth=current_recursion_depth,
                deduction_limit=deduction_limit)
        return True

    # Main driver
    size = len(s)
    solution = solve_recurse(s, focus_cells=None, is_top_layer=True, recursion_limit=0, current_recursion_depth=0, deduction_limit=len(s)*100)

    if verbose:
        print()
        if solution is True: print("Puzzle is too hard :(")
        else: print2D(solution)

    if verbose: print(f"Time taken: {pc()-st:.3f}s")
    if verbose: print("Stats:",{u:v for u,v in STATS.items() if u not in ["grids", "temp grids", "temp recursions"]})

    if should_make_gif:
        images = []
        for s,depth,lpcells in tqdm(STATS["grids"]):
            images += [draw(s, width, depth, lpcells)]
        make_gif(images)

    if "solution" not in STATS: STATS["solution"] = solution
    STATS["total recursion layer"] = sum(x[1] for x in STATS["grids"])
    
    if not return_stat:
        reset_stats()
        return solution
    elif len(return_stat) == 1:
        to_return = STATS[return_stat[0]]
        reset_stats()
        return to_return
    else:
        to_return = {}
        for u in return_stat:
            to_return[u] = STATS[u]
        reset_stats()
        return to_return

# Condenses the ordered list of LP deductions done by finding a subsequence of the deductions that reaches the same progress such that no proper subsequence of it has this property.
def condense_lp(s, width, lp_used, return_stat=0, prove_for_all_sols=False, supposed_to_be_solved=True, only_care_about_lights=False):
    # Stuff to return: [just the length, the deductions themselves, full solve path][return_stat]
    progression = [solve(s, width, verbose=False, prescribed_lp_deductions=[])]
    for lpd in lp_used:
        progression += [solve(progression[-1], width, verbose=False, prescribed_lp_deductions=[lpd])]

    bestProgress = progression[-1]
    if supposed_to_be_solved: assert puzzle_completed(bestProgress)

    new_lp_used = []

    for i in range(len(lp_used)):
        if progression[i] == progression[i+1]: continue
        new_prog = progression[:]
        new_prog[i+1] = new_prog[i]
        caught_up = False
        for j in range(i+1,len(lp_used)):
            new_prog[j+1] = solve(new_prog[j], width, verbose=False, prescribed_lp_deductions=[lp_used[j]])
            if new_prog[j+1] == progression[j+1]:
                progression = new_prog
                caught_up = True
                break
        if caught_up: continue
        if only_care_about_lights and new_prog[-1].count("@") == bestProgress.count("@"):
            progression = new_prog
            continue
        new_lp_used += [lp_used[i]]

    # print(bestProgress)
    # print(len(lp_used))

    curr_lpd = new_lp_used[:]

    if return_stat == 0: return len(curr_lpd)
    elif return_stat == 1: return curr_lpd
    elif type(return_stat) is tuple: return solve(s, width, prove=prove_for_all_sols, verbose=False, prescribed_lp_deductions=curr_lpd, return_stat=return_stat)
    else: raise Exception("Invalid return stat for condense_lp!")
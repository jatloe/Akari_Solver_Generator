import math
import random

from rules import set_width, cell_nbrs, light_up, print2D, decode_puzzle, encode_puzzle, l2_squared_dist
from solver import solve, condense_lp, STRATEGIES

MIN_LP_RATE = 2 # Requires >= n LP deductions at MIN_LP_RATE*n clues
BAILOUT_RATE = 500 # Bails out with 1/(BAILOUT_RATE+1) chance when reaches max depth
MAX_CLUE_MULTIPLIER = 1.1 # Max depth is sqrt(size) * MAX_CLUE_MULTIPLIER
REQUIRED_PROGRESS_PROPORTION = 1.1 # If proportion of deduced unknowns is less than REQUIRED_PROGRESS_PROPORTION times the proportion of clues placed, bail out
FILTER_RANDOM_CLUES = True
DEPTH_RESTRICTION_START = 2

def required_progress(depth, depthLimit):
    # Interpolation: quadratic through (0,0) and (1,1), derivative at 0 is REQUIRED_PROGRESS_PROPORTION
    if depth < DEPTH_RESTRICTION_START: return 0
    depth -= DEPTH_RESTRICTION_START
    depthLimit -= DEPTH_RESTRICTION_START
    propThrough = depth / depthLimit
    c = REQUIRED_PROGRESS_PROPORTION-1
    return propThrough * (c + 1 - c*propThrough)
    return min(propThrough * REQUIRED_PROGRESS_PROPORTION, 1-(propThrough-1)**2)

class BailoutSignal:
    def __init__(self, turns):
        self.turns = turns
    
    def dec(self):
        self.turns -= 1
        if self.turns <= 0: return False
        return self

# random.seed(1434)

# specifiedList = [0, 11, 16, 30, 39, 44, 58, 62, 65, 66, 77, 78, 81, 85, 99, 104, 113, 127, 132, 143]

def fill_random_clue(s, width, easy=False, curr_progress=None):
    clueCells = [i for i in range(len(s)) if s[i] in "#01234"]
    emptyInds = [x for x in range(len(s)) if s[x] == "."]
    if curr_progress and FILTER_RANDOM_CLUES:
        # u = len(emptyInds)
        emptyInds = [x for x in emptyInds if any(curr_progress[i] == "." for i in cell_nbrs(x, len(s))+[x])]
        # print(u,len(emptyInds))

    if not clueCells: weights = [1]*len(emptyInds)
    else:
        weights = [1/sum(
            math.exp(-math.sqrt(l2_squared_dist(emptyInd,clueNum)))
        for clueNum in clueCells) for emptyInd in emptyInds]

    toChooseFrom = "4"
    if not curr_progress or curr_progress.count(".") / len(curr_progress) > 0.1:
        ind = random.choices(emptyInds, weights=weights)[0]
        toChooseFrom = "#11122233" if not easy else "#011112222334"
    else:
        if curr_progress and random.randint(1,3) == 1:
            actuallyValidIndinds = [i for i,x in enumerate(emptyInds) if curr_progress[x] == "."]
            actualEmptyInds = [emptyInds[i] for i in actuallyValidIndinds]
            actualWeights = [weights[i] for i in actuallyValidIndinds]
            ind = random.choices(actualEmptyInds, weights=actualWeights)[0]
            toChooseFrom = "#"
        else:
            ind = random.choices(emptyInds, weights=weights)[0]
            toChooseFrom = "#001112"
    
    possible = len([x for x in cell_nbrs(ind,len(s)) if s[x] == "."])
    for k in [2,3]:
        if possible <= k: toChooseFrom = toChooseFrom.replace(str(k),"")

    if curr_progress:
        counted = len([x for x in cell_nbrs(ind,len(s)) if curr_progress[x] == "@"])
        for k in [0,1,2]:
            if counted > k: toChooseFrom = toChooseFrom.replace(str(k),"")

    return s[:ind] + random.choice(toChooseFrom) + s[ind+1:]

def random_return():
    if random.randint(1,BAILOUT_RATE) != BAILOUT_RATE: return False
    return BailoutSignal(1000)
    return BailoutSignal(int(-math.log(random.random()))+1)

# False means no puzzle, None means kill the branch
def generate_puzzle_recursive(s, width, depth, depth_limit, prev_prop=0, lp_hints=None, strategies=STRATEGIES[:], verbose=True):
    # if solve(s, width, verbose=False) == False: return False
    if depth >= depth_limit: return random_return()

    returned = solve(s, width, verbose=False, lp_hints=lp_hints, strategies=strategies, ban_recursion=True, return_stat=("LP deductions done","solution"))
    currProgress = returned["solution"]

    if currProgress is False: return False

    lpDeductions = condense_lp(s, width, returned["LP deductions done"], return_stat=1, supposed_to_be_solved=False, only_care_about_lights=True)

    completed = "." not in currProgress

    if strategies and len(lpDeductions) < depth // MIN_LP_RATE - int(completed): # Allow one slack for completed puzzles
        return random_return() # Bails out more often now
    solvedProp = 1 - currProgress.count(".") / s.count(".")
    if solvedProp < prev_prop: return random_return()
    if solvedProp < required_progress(depth, depth_limit): return random_return()

    if completed:
        return s
        # if not {*solve(s, width, verbose=False, ban_lp=True)} <= {*".#01234"}:
        #     # Bad breakin
        #     # print("OH NO!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        #     # print(encode_puzzle(s,width))
        #     # exit()
        #     # return None
        #     return s
        # else:
        #     return s

    if verbose:
        print(end=f"\r{depth}     {random.randint(1000,9999)}     {len(lpDeductions)}     {currProgress.count('.')/len(s):.3f}          ")
        # if solvedProp > 0.9: print2D(currProgress)
        if solvedProp > 0.95:
            # print()
            # print2D(currProgress)
            # exit()
            pass

    # currMissing = currProgress.count(".")
    # tries = 20 if currMissing >= 5 else len(s)*3

    for i in range(20+int(1/(1-solvedProp))):
        newS = fill_random_clue(s, width, easy=not bool(strategies), curr_progress=currProgress)
        recurred = generate_puzzle_recursive(newS, width, depth+1, prev_prop=solvedProp, depth_limit=depth_limit, strategies=strategies, lp_hints=lpDeductions[:], verbose=verbose)
        if type(recurred) is BailoutSignal: return recurred.dec()
        if recurred: return recurred
        if recurred is None: return None
    
    return random_return()

def generate_puzzle(size, width, seed=None, strategies=STRATEGIES[:], verbose=True):
    set_width(width)

    assert seed is None or len(seed) == size
    
    for topLevelLoopInd in range(10000):
        # Top level, put in some random clues to begin with
        s = "."*size if seed is None else seed
        pzl = generate_puzzle_recursive(s, width, depth=0,
                                        depth_limit=int((len(s)**.5) * MAX_CLUE_MULTIPLIER), strategies=strategies, verbose=verbose)
        if pzl and type(pzl) is not BailoutSignal:
            if verbose: print()
            return pzl
    
    raise Exception("Unlucky")
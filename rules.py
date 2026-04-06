"""
# is filled square with no number
01234 is filled square with number
. is empty square
(space) is known empty square
- is square that is lit but not a light
@ is light
"""

import math

width = 0
bigstr = "0123456789abcdefghijklmnopqrstuvwxyz"

# Sets the width of the puzzle, which affects the rest of the rules.
def set_width(w):
    global width
    
    width = w

# Input: "run", which is the contents of an entire row or column
# Separates "run" into continuous regions separated by blocks.
# Then, if there are at least two lights in any region, returns False.
# Otherwise, returns all cells in "run" that were lit up by something in "run".
def check_run(run):
    lit_up = set()

    # Figure out the block-separated regions
    lastStart = 0
    regions = []
    for i in range(len(run)):
        if run[i] in "#01234":
            if i != lastStart:
                regions += [(lastStart,i-1)]
            lastStart = i+1
    i = len(run)
    if i != lastStart:
        regions += [(lastStart,i-1)]
    
    # Check the regions
    for l,r in regions:
        regionString = run[l:r+1]
        ct = regionString.count("@")
        if ct >= 2: return False
        if ct == 0: continue
        # There is one light, so all of l-r is lit up
        lit_up |= {*range(l,r+1)}
    
    return lit_up

# Returns the (up to) four orthogonal neighbors of the cell with index i.
# If diagonal is True, then also returns the (up to) four diagonal neighbors for (up to) eight total.
def cell_nbrs(i,size,diagonal=False):
    imw = i % width
    if not diagonal:
        ans = []
        if i >= width: ans.append(i-width)
        if imw != 0: ans.append(i-1)
        if imw != width-1: ans.append(i+1)
        if i < size-width: ans.append(i+width)
        return ans
    conds = [i >= width, imw != 0, imw != width-1, i < size-width]
    return [i-width]*conds[0] + [i-1]*conds[1] + [i+1]*conds[2] + [i+width]*conds[3] + [i-width-1]*conds[0]*conds[1] + [i-width+1]*conds[0]*conds[2] + [i+width-1]*conds[1]*conds[3] + [i+width+1]*conds[2]*conds[3]

# Returns all cells that the cell with index "ind" can see.
def cell_reaches(ind,s):
    assert s[ind] not in "#01234"
    
    ans = []

    i = ind
    while i>=0 and s[i] not in "#01234":
        ans += [i]
        i -= width
    i = ind
    while s[i] not in "#01234":
        ans += [i]
        if i%width == 0: break
        i -= 1
    i = ind
    while s[i] not in "#01234":
        ans += [i]
        if i%width == width-1: break
        i += 1
    i = ind
    while i<len(s) and s[i] not in "#01234":
        ans += [i]
        i += width
    return sorted({*ans}-{ind})

# If s[ind] is not currently lit, returns the remaining cells that could still light it up.
# Otherwise, returns True.
def remaining_lightables(s,ind):
    
    if s[ind] in "-@": return True

    ans = []
    for u in cell_reaches(ind,s):
        if s[u] == "@": return True
        if s[u] == ".": ans += [u]

    if s[ind] == ".": ans += [ind]
    return ans

# Returns True if "s" is a correctly completed puzzle, and False otherwise.
def puzzle_completed(s):
    if "." in s: return False

    # Check that every number constraint is satisfied
    for i,c in enumerate(s):
        if c not in "01234": continue
        num_lit = 0
        for j in cell_nbrs(i,len(s)):
            num_lit += (s[j] == "@")
        if num_lit != int(c): return False

    # Check that every cell is lit up
    lit_up = set()
    for rs in range(0, len(s), width):
        check = check_run(s[rs:rs+width])
        if check == False: return False
        for cell in check:
            lit_up.add(rs+cell)
    for cs in range(width):
        check = check_run(s[cs::width])
        if check == False: return False
        for cell in check:
            lit_up.add(cs+width*cell)
    
    to_light = {i for i in range(len(s)) if s[i] not in "#01234"}
    
    if to_light != lit_up: return False

    return True

# Returns True if the current progress "s" on a puzzle is valid, and False otherwise.
def progress_valid(s):
    # Check that every number constraint is satisfied
    for i,c in enumerate(s):
        if c not in "01234": continue
        num_lit = 0
        total_possible = 0
        check = True
        for j in cell_nbrs(i,len(s)):
            num_lit += (s[j] == "@")
            total_possible += (s[j] in "@.")
            if s[j] == ".": check = False
        if num_lit > int(c): return False
        if check and num_lit != int(c): return False
        if total_possible < int(c): return False

    # Check that no run has two lights
    for rs in range(0, len(s), width):
        if check_run(s[rs:rs+width]) == False: return False
    for cs in range(width):
        if check_run(s[cs::width]) == False: return False

    # Probably also check that every unlit cell can possibly be lit
    for i in range(len(s)):
        if s[i] != " ": continue
        if all(s[j] not in ".@" for j in cell_reaches(i,s)): return False
    
    return True

# Returns s, but with ind replaced with a light and the corresponding cells lit up.
def light_up(s, ind):
    s = [*s]
    s[ind] = "@"
    for i in cell_reaches(ind, s):
        if s[i] in ". ": s[i] = "-"
    return "".join(s)

# Returns both possible states after caseworking on index ind on puzzle s.
def get_children_ind(s,ind):
    return [light_up(s,ind), s[:ind]+" "+s[ind+1:]]

# Prints the puzzle string "s" in 2D.
def print2D(s):
    print("+"+"-"*width+"+")
    print("\n".join("|"+s[rs:rs+width].replace("-"," ")+"|" for rs in range(0,len(s),width)))
    print("+"+"-"*width+"+")
    print()

# Takes a link from puzz.link and returns the tuple (grid string, width).
def decode_puzzle(s):
    while s[-1] == "/": s = s[:-1]
    width,height,s = s[s.index("akari/")+6:].split("/")
    width = int(width)
    height = int(height)

    grid = ["."]*(width*height)
    i = 0
    for c in s:
        if c == ".":
            grid[i] = "#"
        elif c in "0123456789abcde":
            k = int(c,16)
            grid[i] = str(k%5)
            i += k//5
        else:
            i += int(c,36)-16
        i += 1

    grid = "".join(grid)

    set_width(width)

    return (grid,width)

# Takes a grid string and a width and returns the corresponding link for puzz.link.
def encode_puzzle(s,width):
    height = len(s)//width

    ans = f"https://puzz.link/p?akari/{width}/{height}/"

    count = 0
    i = 0
    while i < len(s):
        pstr = ""
        if s[i] in "01234":
            if i+1 < len(s) and s[i+1] != ".":
                pstr = bigstr[int(s[i])]
            elif i+2 < len(s) and s[i+2] != ".":
                pstr = bigstr[(int(s[i]))+5]
                i += 1
            else:
                pstr = bigstr[(int(s[i]))+10]
                i += 2
        elif s[i] == "#": pstr = "."
        else: count += 1

        if count == 0: ans += pstr
        elif pstr or count == 20:
            ans += bigstr[count+15]+pstr
            count = 0
        i += 1
    if count: ans += bigstr[count+15]

    return ans+"/"

# Returns the squared Euclidean distance between the grid positions of indices a and b.
def l2_squared_dist(a,b):
    r1,c1 = divmod(a,width)
    r2,c2 = divmod(b,width)
    return (r1-r2)**2 + (c1-c2)**2
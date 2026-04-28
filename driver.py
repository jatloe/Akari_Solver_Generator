import time

from rules import set_width, cell_nbrs, light_up, print2D, decode_puzzle, encode_puzzle
from solver import solve, condense_lp, reset_stats, STATS
from time import perf_counter as pc

# Tests the solver on all puzzles in the puzz.link database.
def test_all_puzzles():
    start_time = pc()
    all_puzzles = open("puzzle_bank.txt","r",encoding="utf16").readlines()
    skipped = 0
    total_recursions = 0
    total_trl = 0
    for ind,s in enumerate(all_puzzles):
        puzzle, width = decode_puzzle(s.strip())
        set_width(width)
        try:
            solved = solve(puzzle, width, verbose=0, return_stat=["solution", "recursions", "total recursion layer"])
            sol, rec, trl = map(solved.get, ["solution","recursions","total recursion layer"])
            if sol in [True, False]: raise Exception("Couldn't solve the puzzle! Puzzle: {s}, Solution: {sol}")
            total_recursions += rec
            total_trl += trl
        except KeyboardInterrupt:
            print(f"\r{s.strip()}")
            skipped += 1
            time.sleep(0.5)
        ind += 1
        print(end=f"\r{ind:04}/{len(all_puzzles)}, skipped: {skipped:03}, recursions: {total_recursions}, total recursion layer: {total_trl}, time: {pc()-start_time:.3f}s •ᴗ•")

    exit()

# Tests the solver on a specific puzzle.
def test_puzzle(link):
    puzzle,width = decode_puzzle(link)
    set_width(width)
    size = len(puzzle)

    lpd = solve(puzzle, width, should_make_gif=0, return_stat=("LP deductions done",))
    # clpl = condense_lp(puzzle, width, lpd, return_stat=0)
    print(len(lpd))
    # print(clpl)

    exit()

# test_puzzle("https://puzz.link/p?akari/10/10/pb.ich5.h.g.zbgbq1.i6.h.a2.pa.../")
test_puzzle("https://puzz.link/p?akari/17/17/bsbh.g.g5.g.zybi1..kbyb.i.hbh.laj.h.s.ha.g6.g6.hahb6.gbbzzs6.g.ha.g.gbi0..i1..jbsb")
# test_all_puzzles()

from generator import generate_puzzle
size = 225
width = 15
set_width(width)
print(encode_puzzle(generate_puzzle(size,width),width))
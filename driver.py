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

test_puzzle("https://puzz.link/p?akari/25/20/l.6bhbo1ag.k.i.i5ag.g.h16bg.g.iaga.gckaccgch..p.g.iagaj6.g.h.i.h.5ahbodo.g.i...hbgbh.j...i.i.g.g.g.gag.h6bg.b.g.g5.i.g.h.g.k.g.g.g5.l.o.g.g.g.g.g.l5ag..icgbh5b5at.obqbkbk.gbai7ck.gcn.m0..bgba.h.l7.g.g.gcj.j.61bragbj")
# test_puzzle("https://puzz.link/p?akari/41/41/qbk7.mbq0.h0bkbmbk..h1ag.l.g.g.h.g..g.g0.ga.g6bj.j1.qak.q..kb66.gb1.i7.i1.h6.g.gb.i.xcvb.hc..h.k.g.g.g.k.h..hc.ibg.h.h666bg.g.g.gbb.i.h.jbk.h.g.i.gbbkchb.g.i2.kag6ag.k1.i.g.ic.l...j.i.j1.bj.h.i.h.gcbg.g.i.i.g.i.h.gb.i.l.icb.icbcgbj.i6.b6.i.g.h.g.h.g.i5.h..gbl.j1..k.gbi...jbjcg.h.nb.gb.nb.i6..i.g1a1bg.bg..i.c2.g.i..ldi.hcoc.k.l.h.l.i.agbg..ibj.hbg.g.h5.h.k.ibi.h6b.g.hbdh.j.g0.ibg15chbhcc.g.h.g.hbicgbi.h.g.h.g.i.h.lbg.bg.i..i.l.h.lci.hdobbibj0.i.g2c..i.bg1.i0.h.5.i..g.ic.nb.gb.nbcgbj.j...k.gai..bh.n61.h7bg.g.h.g.h6bg.gb1.g.i.l.iccdgd.h.i.ldg.h.g.h.i.g.ibg.gbg.h8.h.ibbj...j.i.j.0.l.h.i.gag.bibg.g.ibi..i.g.h.j.md.gag.g.hbk.jbbg.h.h.g.g.g.i.g.g6.hdbg.i.hb.a.k7.g.g.kb..hc.h.xcv.ib.g.g.ga..i.g.i.c.g.g.g.h.k..qakbo1ah.l76c.g.66..g.h.g.g.l.i0.h0.m.ock.b1aq.m.g.mbo")
# test_all_puzzles()

from generator import generate_puzzle
size = 225
width = 15
set_width(width)
print(encode_puzzle(generate_puzzle(size,width),width))
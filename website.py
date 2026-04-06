from flask import Flask, request, make_response, render_template, redirect, url_for
from solver import solve, condense_lp
from rules import decode_puzzle, encode_puzzle, set_width
from drawer import draw_and_save
from generator import generate_puzzle

app = Flask(__name__)

@app.route('/')
def home():
    return render_template("base.html")

@app.route('/api/solve_puzzle', methods=['GET', 'POST'])
def solve_puzzle():
    puzzle,width = decode_puzzle(request.form.get("puzzle_link"))
    hard = request.form.get("use_hard_lp")
    set_width(width)

    strats = ["SC2","N1D"]+["SC3"]*bool(hard)

    returned = solve(puzzle, width, use_heuristic=True, prove=True, strategies=strats,
                     return_stat=("LP deductions done","grids","all solutions","used red/blue graph or recursion"), verbose=False)

    print(returned)
    # If no recursion, condense LP
    if not returned["used red/blue graph or recursion"]:
        lpd = returned["LP deductions done"]
        returned = condense_lp(puzzle, width, lpd, prove_for_all_sols=True, return_stat=("grids", "all solutions", "LP deductions done","used red/blue graph or recursion"))

    ans = returned["all solutions"]
    allgrids = returned["grids"]
    numlp = len(returned["LP deductions done"])
    if returned["used red/blue graph or recursion"]: numlp = "∞"

    proof = [draw_and_save(info, width).split("/")[1] for info in allgrids]

    return render_template("solved.html", numsols=len(ans), proof=proof, numlp=numlp)

@app.route('/generator')
def generator():
    return render_template("generator.html")

@app.route('/generate_puzzle', methods=['GET', 'POST'])
def generate_puzzle_for_website():
    try:
        height = int(request.form.get("height"))
        width = int(request.form.get("width"))
        difficulty = int(request.form.get("difficulty"))
        seed = request.form.get("seed")
        if not seed: seed = None
        else:
            seed, decoded_width = decode_puzzle(seed)
            assert decoded_width == width
            assert len(seed) == height*width
        assert height >= 1 <= width
        assert 1 <= difficulty <= 3
    except:
        return "Invalid parameters!", 400
    set_width(width)
    strategies = ["SC2", "N1D"] * (difficulty >= 2) + ["SC3"] * (difficulty >= 3)
    puzzle = generate_puzzle(height*width, width, seed=seed if seed else None, strategies=strategies, verbose=False)
    return redirect(encode_puzzle(puzzle,width))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
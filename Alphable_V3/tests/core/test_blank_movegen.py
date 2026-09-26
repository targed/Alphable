import pytest
from alphable.core import structure, simulator

@pytest.fixture(scope="module")
def gaddag():
    # Use CSW24 or mini dictionary
    dict_path = "resources/CSW24.txt"
    return structure.Gaddag.load(dict_path)

def test_cross_checks_adjacent_to_lowercase_blank(gaddag):
    gen = structure.MoveGenerator(gaddag)
    board = simulator.create_empty_board()
    
    # Place a blank 'e' on board at row 7, col 7
    board[7][7] = 'e'
    
    # Check that cross_checks for (6, 7) or (8, 7) (vertical checks above/below blank for Across plays) are non-empty
    cross_checks = {}
    gen._compute_cross_checks(board, cross_checks)
    
    # (6, 7) is immediately above 'e' at (7,7).
    # Letters like 'D', 'H', 'M', 'N', 'W', 'Y' form 'De', 'He', 'Me', 'Ne', 'We', 'Ye'
    assert (6, 7) in cross_checks, "Square adjacent vertically to blank must have cross-checks computed"
    valid_chars = cross_checks[(6, 7)]
    assert len(valid_chars) > 0, "Square adjacent to blank must not have empty cross-checks"
    assert 'H' in valid_chars or 'M' in valid_chars or 'B' in valid_chars

def test_moves_hooking_onto_blank_tile(gaddag):
    gen = structure.MoveGenerator(gaddag)
    board = simulator.create_empty_board()
    
    # Place 'eTHANOL' with blank 'e' at C7 (Down: row 6, col 2)
    word = "eTHANOL"
    for idx, char in enumerate(word):
        board[6 + idx][2] = char
        
    # Also place connecting OURIE at row 7, col 3
    for idx, char in enumerate("OURIE"):
        board[7][3 + idx] = char
        
    # Generate moves with rack AEIINRT
    moves = gen.generate(board, list("AEIINRT"))
    
    # Verify INERTIA at row 0, col 1 Down is generated (hooks to 'e')
    down_bingos = [
        m for m in moves
        if m['dir'] == 'Down' and m['col'] == 1 and m['word'] == 'INERTIA'
    ]
    assert len(down_bingos) == 1, "Must generate INERTIA hooking onto the blank 'e' of eTHANOL"
    m = down_bingos[0]
    assert m['row'] == 0
    assert m['col'] == 1
    
    # Verify simulate_move scores 69 points
    _, pts, nr = simulator.simulate_move(board, m, list("AEIINRT"))
    assert pts == 69
    assert len(nr) == 0

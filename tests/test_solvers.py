from agent.solvers import NUMERIC_CONCEPTS, SOLVER_SPECS, SOLVERS, program_for


def test_solvers():
    assert SOLVERS["floor_div"](19, 4) == 4
    assert SOLVERS["modulo"](17, 5) == 2
    assert SOLVERS["power_of"](2, 3) == 8
    assert SOLVERS["range_sum"](1, 4) == 6
    assert SOLVERS["nested_count"](2, 3) == 6
    assert SOLVERS["list_total"](2, 3, 5) == 10


def test_numeric_concepts_only_name_known_solvers():
    assert set(NUMERIC_CONCEPTS) == {"arithmetic_operators", "running_total", "nested_loops", "list_traversal"}
    for functions in NUMERIC_CONCEPTS.values():
        assert set(functions) <= set(SOLVERS)


def test_every_solver_declares_a_spec():
    assert set(SOLVER_SPECS) == set(SOLVERS)


def test_program_for_writes_the_arguments_into_the_code():
    assert program_for("floor_div", [19, 4]) == "print(19 // 4)"
    assert program_for("list_total", [2, 3, 5]).startswith("marks = [2, 3, 5]\n")
    assert "for i in range(1, 4):\n    total = total + i" in program_for("range_sum", [1, 4])


def test_programs_match_what_the_solvers_compute():
    # Runs only the fixed templates in agent/solvers.py, never anything from the LLM.
    arguments = {
        "floor_div": [19, 4],
        "modulo": [17, 5],
        "power_of": [2, 3],
        "range_sum": [1, 4],
        "nested_count": [2, 3],
        "list_total": [2, 3, 5],
    }
    assert set(arguments) == set(SOLVERS)
    for function, args in arguments.items():
        printed = []
        exec(program_for(function, args), {"print": printed.append})
        expected = SOLVERS[function](*args)
        assert (len(printed) if function == "nested_count" else printed[-1]) == expected, function

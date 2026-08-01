"""Deterministic templates for EAG Engineering Benchmarks."""

from eag.chief.runtime.models import Plan, PlanStep


def get_benchmark_plan(benchmark_id: str) -> Plan:
    """Returns a deterministic plan for a given benchmark ID."""

    steps: list[PlanStep] = []

    # Common Step 1: Git Init
    steps.append(
        PlanStep(
            step_id="step_1_git_init",
            name="Initialize Git Repository",
            capability_id="repository",
            metadata={"operation": "init"},
        )
    )

    if benchmark_id == "EBS-001":
        steps.append(
            PlanStep(
                step_id="step_2_files",
                name="Generate Calculator Files",
                capability_id="workspace",
                dependencies=("step_1_git_init",),
                metadata={
                    "operation": "write",
                    "path": "calculator.py",
                    "content": "import sys\n\ndef add(a, b): return a + b\ndef subtract(a, b): return a - b\ndef multiply(a, b): return a * b\ndef divide(a, b): return a / b if b != 0 else float('inf')\n\ndef main():\n    op = sys.argv[1]\n    a = float(sys.argv[2])\n    b = float(sys.argv[3])\n    if op == 'add': print(add(a, b))\n    elif op == 'sub': print(subtract(a, b))\n    elif op == 'mul': print(multiply(a, b))\n    elif op == 'div': print(divide(a, b))\n\nif __name__ == '__main__':\n    main()\n",
                },
            )
        )
        steps.append(
            PlanStep(
                step_id="step_3_tests",
                name="Generate Calculator Tests",
                capability_id="workspace",
                dependencies=("step_2_files",),
                metadata={
                    "operation": "write",
                    "path": "test_calculator.py",
                    "content": "from calculator import add, subtract, multiply, divide\n\ndef test_add():\n    assert add(2, 3) == 5\n\ndef test_subtract():\n    assert subtract(5, 2) == 3\n\ndef test_divide():\n    assert divide(6, 3) == 2.0\n",
                },
            )
        )
        steps.append(
            PlanStep(
                step_id="step_4_readme",
                name="Create README.md",
                capability_id="workspace",
                dependencies=("step_3_tests",),
                metadata={
                    "operation": "write",
                    "path": "README.md",
                    "content": "# Calculator\n\nA simple Python CLI calculator.\n\n## Usage\n\n```bash\ncalc add 5 3\n```\n",
                },
            )
        )
        steps.append(
            PlanStep(
                step_id="step_5_pyproject",
                name="Create pyproject.toml",
                capability_id="workspace",
                dependencies=("step_4_readme",),
                metadata={
                    "operation": "write",
                    "path": "pyproject.toml",
                    "content": '[project]\nname = "calculator"\nversion = "0.1.0"\ndependencies = []\n\n[project.scripts]\ncalc = "calculator:main"\n',
                },
            )
        )

    elif benchmark_id == "EBS-002":
        steps.append(
            PlanStep(
                step_id="step_2_files",
                name="Generate File Organizer",
                capability_id="workspace",
                dependencies=("step_1_git_init",),
                metadata={
                    "operation": "write",
                    "path": "organizer.py",
                    "content": "import os\nimport shutil\n\ndef organize(directory):\n    for filename in os.listdir(directory):\n        file_path = os.path.join(directory, filename)\n        if os.path.isfile(file_path):\n            ext = filename.split('.')[-1] if '.' in filename else 'misc'\n            target_dir = os.path.join(directory, ext)\n            os.makedirs(target_dir, exist_ok=True)\n            shutil.move(file_path, os.path.join(target_dir, filename))\n\nif __name__ == '__main__':\n    import sys\n    if len(sys.argv) > 1:\n        organize(sys.argv[1])\n",
                },
            )
        )
        steps.append(
            PlanStep(
                step_id="step_3_tests",
                name="Generate Organizer Tests",
                capability_id="workspace",
                dependencies=("step_2_files",),
                metadata={
                    "operation": "write",
                    "path": "test_organizer.py",
                    "content": "import os\nimport tempfile\nfrom organizer import organize\n\ndef test_organize():\n    with tempfile.TemporaryDirectory() as tmpdir:\n        open(os.path.join(tmpdir, 'file1.txt'), 'w').close()\n        open(os.path.join(tmpdir, 'file2.jpg'), 'w').close()\n        organize(tmpdir)\n        assert os.path.exists(os.path.join(tmpdir, 'txt', 'file1.txt'))\n        assert os.path.exists(os.path.join(tmpdir, 'jpg', 'file2.jpg'))\n",
                },
            )
        )
        steps.append(
            PlanStep(
                step_id="step_4_readme",
                name="Create README.md",
                capability_id="workspace",
                dependencies=("step_3_tests",),
                metadata={
                    "operation": "write",
                    "path": "README.md",
                    "content": "# File Organizer\n\nOrganizes files into extension-based subdirectories.\n\n## Usage\n```bash\npython organizer.py /path/to/dir\n```\n",
                },
            )
        )
        steps.append(
            PlanStep(
                step_id="step_5_pyproject",
                name="Create pyproject.toml",
                capability_id="workspace",
                dependencies=("step_4_readme",),
                metadata={
                    "operation": "write",
                    "path": "pyproject.toml",
                    "content": '[project]\nname = "file-organizer"\nversion = "0.1.0"\ndependencies = []\n',
                },
            )
        )

    elif benchmark_id == "EBS-003":
        steps.append(
            PlanStep(
                step_id="step_2_files",
                name="Generate Notes CLI",
                capability_id="workspace",
                dependencies=("step_1_git_init",),
                metadata={
                    "operation": "write",
                    "path": "notes.py",
                    "content": "import json\nimport os\n\nNOTES_FILE = 'notes.json'\n\ndef load_notes(filepath=NOTES_FILE):\n    if os.path.exists(filepath):\n        with open(filepath, 'r') as f:\n            return json.load(f)\n    return []\n\ndef save_notes(notes, filepath=NOTES_FILE):\n    with open(filepath, 'w') as f:\n        json.dump(notes, f)\n\ndef add_note(text, filepath=NOTES_FILE):\n    notes = load_notes(filepath)\n    notes.append(text)\n    save_notes(notes, filepath)\n    return notes\n\ndef list_notes(filepath=NOTES_FILE):\n    return load_notes(filepath)\n",
                },
            )
        )
        steps.append(
            PlanStep(
                step_id="step_3_tests",
                name="Generate Notes Tests",
                capability_id="workspace",
                dependencies=("step_2_files",),
                metadata={
                    "operation": "write",
                    "path": "test_notes.py",
                    "content": "import os\nimport tempfile\nfrom notes import add_note, list_notes\n\ndef test_add_and_list_notes():\n    with tempfile.NamedTemporaryFile(delete=False) as tmp:\n        filepath = tmp.name\n    try:\n        add_note('Test note 1', filepath)\n        notes = list_notes(filepath)\n        assert 'Test note 1' in notes\n    finally:\n        if os.path.exists(filepath):\n            os.remove(filepath)\n",
                },
            )
        )
        steps.append(
            PlanStep(
                step_id="step_4_readme",
                name="Create README.md",
                capability_id="workspace",
                dependencies=("step_3_tests",),
                metadata={
                    "operation": "write",
                    "path": "README.md",
                    "content": "# Notes CLI\n\nA simple JSON-backed note-taking CLI tool.\n",
                },
            )
        )
        steps.append(
            PlanStep(
                step_id="step_5_pyproject",
                name="Create pyproject.toml",
                capability_id="workspace",
                dependencies=("step_4_readme",),
                metadata={
                    "operation": "write",
                    "path": "pyproject.toml",
                    "content": '[project]\nname = "notes-cli"\nversion = "0.1.0"\ndependencies = []\n',
                },
            )
        )

    elif benchmark_id == "EBS-004":
        steps.append(
            PlanStep(
                step_id="step_2_files",
                name="Generate FastAPI App",
                capability_id="workspace",
                dependencies=("step_1_git_init",),
                metadata={
                    "operation": "write",
                    "path": "main.py",
                    "content": "from fastapi import FastAPI\n\napp = FastAPI()\nitems_db = []\n\n@app.get('/items/')\nasync def read_items():\n    return items_db\n\n@app.post('/items/')\nasync def create_item(item: dict):\n    items_db.append(item)\n    return item\n",
                },
            )
        )
        steps.append(
            PlanStep(
                step_id="step_3_tests",
                name="Generate FastAPI Tests",
                capability_id="workspace",
                dependencies=("step_2_files",),
                metadata={
                    "operation": "write",
                    "path": "test_main.py",
                    "content": "from fastapi.testclient import TestClient\nfrom main import app\n\nclient = TestClient(app)\n\ndef test_read_items():\n    response = client.get('/items/')\n    assert response.status_code == 200\n    assert isinstance(response.json(), list)\n",
                },
            )
        )
        steps.append(
            PlanStep(
                step_id="step_4_readme",
                name="Create README.md",
                capability_id="workspace",
                dependencies=("step_3_tests",),
                metadata={
                    "operation": "write",
                    "path": "README.md",
                    "content": "# FastAPI CRUD\n\nA basic FastAPI REST service with CRUD endpoints.\n",
                },
            )
        )
        steps.append(
            PlanStep(
                step_id="step_5_pyproject",
                name="Create pyproject.toml",
                capability_id="workspace",
                dependencies=("step_4_readme",),
                metadata={
                    "operation": "write",
                    "path": "pyproject.toml",
                    "content": '[project]\nname = "fastapi-crud"\nversion = "0.1.0"\ndependencies = ["fastapi", "uvicorn"]\n',
                },
            )
        )

    elif benchmark_id == "EBS-005":
        steps.append(
            PlanStep(
                step_id="step_2_files",
                name="Generate TODO App",
                capability_id="workspace",
                dependencies=("step_1_git_init",),
                metadata={
                    "operation": "write",
                    "path": "app.py",
                    "content": "TODOS = {}\n\ndef add_todo(task: str) -> int:\n    idx = len(TODOS) + 1\n    TODOS[idx] = task\n    return idx\n\ndef list_todos() -> dict:\n    return TODOS\n\ndef clear_todos():\n    TODOS.clear()\n",
                },
            )
        )
        steps.append(
            PlanStep(
                step_id="step_3_tests",
                name="Generate TODO App Tests",
                capability_id="workspace",
                dependencies=("step_2_files",),
                metadata={
                    "operation": "write",
                    "path": "test_app.py",
                    "content": "from app import add_todo, list_todos, clear_todos\n\ndef test_todo_operations():\n    clear_todos()\n    idx = add_todo('Buy milk')\n    todos = list_todos()\n    assert todos[idx] == 'Buy milk'\n",
                },
            )
        )
        steps.append(
            PlanStep(
                step_id="step_4_readme",
                name="Create README.md",
                capability_id="workspace",
                dependencies=("step_3_tests",),
                metadata={
                    "operation": "write",
                    "path": "README.md",
                    "content": "# TODO App\n\nIn-memory task manager.\n",
                },
            )
        )
        steps.append(
            PlanStep(
                step_id="step_5_pyproject",
                name="Create pyproject.toml",
                capability_id="workspace",
                dependencies=("step_4_readme",),
                metadata={
                    "operation": "write",
                    "path": "pyproject.toml",
                    "content": '[project]\nname = "todo-app"\nversion = "0.1.0"\ndependencies = []\n',
                },
            )
        )

    # Common Final Step: Git Commit
    steps.append(
        PlanStep(
            step_id="step_final_commit",
            name="Commit Implementation",
            capability_id="repository",
            dependencies=(steps[-1].step_id,),
            metadata={"operation": "commit", "message": f"feat: implement {benchmark_id}"},
        )
    )

    return Plan(steps=tuple(steps))

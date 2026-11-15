Requirements
-----------

Installing Swappy Bird requires [Git](https://git-scm.com) and [uv](https://docs.astral.sh/uv). For Git installation instructions, see https://git-scm.com/install. For uv installation instructions, see https://docs.astral.sh/uv/getting-started/installation/.

PowerShell
----------

1. Clone the Git repository for Swappy Bird: `git clone https://github.com/python-processing-unit/Swappy-Bird`.
2. Set the repo as your cwd: `Set-Location Swappy-Bird`.
3. Install dependencies with uv: `uv sync --locked`.
4. (optional) Build the executable with `./build.ps1`

Bash
----

1. Clone the Git repository for Swappy Bird: `git clone https://github.com/python-processing-unit/Swappy-Bird`.
2. Set the repo as your cwd: `cd Swappy-Bird`.
3. Install dependencies with uv: `uv sync --locked`.
4. (optional) Build the executable with `pwsh ./build.ps1`

Post-install
------------

You can run Swappy Bird from the installation directory with `uv run swappy-bird`, or (if you completed step 4) by invoking `swappy_bird.exe`.
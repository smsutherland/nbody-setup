nbody-setup
-----------

`nbody-setup` is a tool for setting up one or many N-body cosmological
simulations. If you encounter any problems using `nbody-setup`, please file an
issue on github. If you use `nbody-setup` to generate data for a publication, I
ask that you please note this in an acknowledgments section.

`nbody-setup` attempts to be as neutral as possible to the environment or the
codes used. As a result, it passes much of the complexity on to the user, which
they may opt in to if needed. Unfortunately, the current CLI implementation
using Python's [argparse](https://docs.python.org/3/library/argparse.html) can't
completely generate proper help pages. See [Usage](#usage) for greater details
on how to use `nbody-setup`.

### Quick Navigation
  * [Installation](#installation)
  * [Usage](#usage)
    * [New](#new)
    * [Ensemble](#ensemble)
    * [Generate Table](#generate-table)

### Installation
Installation can be achieved via pip:

```bash
pip install 'git+https://github.com/smsutherland/nbody-setup'
```

Or via uv:

```bash
uv tool install 'git+https://github.com/smsutherland/nbody-setup'
```

Or via pipx:

```bash
pipx install 'git+https://github.com/smsutherland/nbody-setup'
```

### Usage

`nbody-setup` currently has 3 subcommands: `new`, `ensemble`, and
`generate-table`.

#### New
```bash
nbody-setup new [options] [target]
```
`new` only has one positional option (`target`) which gives a path in which to
set up a simulation. If `target` is not given, a simulation will be prepared in
the current directory. A simulation will be prepared at the target. The job.sh
script generated in the target directory will, if run, prepare initial
conditions and run the simulation. The script also has an sbatch header prepared
for submission to slurm. If you want to submit the job to slurm, I recommend
checking the sbatch parameters set, and add/change parameters as needed.

The following options specify the cosmology of the run created:
```
--Om Ω_m      Cosmic matter density parameter     default: 0.3
--Ob Ω_b      Cosmic baryon desnity parameter     default: 0.049
--sigma8 σ_8  Matter clustering at 8 Mpc/h scales default: 0.8
--ns n_s      Spectral index                      default: 0.9624
--h h         Reduced hubble constant             default: 0.6711
```

The following options specify less physical aspects about the simulation:
```
--seed S     Random seed for initial conditions             default: 12
--boxsize L  Simulations have co-moving side length L Mpc/h default: 25
--N N        Simulations have N^3 particles                 default: 256
```

The following are options for `nbody-setup` itself:
```
-h, --help        Display a help message and immediately exit
-y, --no-confirm  Skip asking for confirmation before making a simulation
--gadget PATH     Path to a Gadget-III executable
--ics {2lpt}      What initial condition code to use
```

Currently `--ics` only has one option: 2lpt. More options are planned, and pull
requests adding more are welcome. Additionally, I intend to add a similar option
to change simulation code, rather than requiring use of Gadget. Each initial
conditions code may specify its own options.

If `--ics` is 2lpt, the following options are added:
```
--2lpt PATH   Path to a 2LPTic executable
--glass PATH  Path to a glass file to use
```
If `2LPTic` is present on your PATH, then `--2lpt` may be omitted and the 2LPTic
on your PATH will be used instead. if `--2lpt` is specified, it will be used
instead of a PATH located executable. `--glass` is always required.

#### Ensemble
```bash
nbody-setup ensemble [optinos] basename table
```

The ensemble command will create an ensemble of N-body simulations, each with
different parameters. The parameters of an ensemble are determined by a
[table](#generate-table). The number of rows in the table determines the number
of simulations prepared. Simulations are simply numbered from 0 to (N-1)

```
# EXAMPLE TABLE
Om      Ob      sigma8  ns      h       seed    boxsize N
0.2     0.049   0.8     0.9624  0.6711  11      25      256
0.3     0.049   0.8     0.9624  0.6711  12      25      256
0.4     0.049   0.8     0.9624  0.6711  13      25      256
```

Any column in the table may be omitted, in which case all simulations will have
a default value for that parameter. Default values are as follows:
| Name    | Default Value |
|---------|---------------|
| Om      | 0.3           |
| Ob      | 0.049         |
| sigma8  | 0.8           |
| ns      | 0.9624        |
| h       | 0.6711        |
| seed    | 12            |
| boxsize | 25            |
| N       | 256           |

Note for CAMELS users: the table used is similar in concept to, but distinct from,
the cosmo-astro-seed tables we use.

`ensemble` requires two positional options: basename and table.
Basename gives the base name for prepared simulations.
For example, CV results in simulation directories named CV_0, CV_1, ...
Table is a path to the parameter table.

`ensemble` also accepts the following options:
```
-h, --help            Display a help message and immediately exit
-y, --no-confirm      Skip asking for confirmation before making a simulation
--gadget PATH         Path to a Gadget-III executable
--ics {2lpt}          What initial condition code to use
--engine {none,array} Which execution engine (if any) to prepare
```

`--gadget` and `--ics` keep their meanings from the [new subcommand](#new)
(including the options that exist as a result of the `--ics` value). `--engine`,
if set, will prepare an execution engine to run all the generated simulations.
`--engine=none` will forgo the preparation of such an engine. `--engine=array`
prepares a slurm job array to run the simulations, submittable from the
generated job.sh script. Double check all slurm parameters present in job.sh,
and change/add parameters as necessary.

#### Generate Table
`nbody-setup generate-table > table.txt`

`generate-table` prepares a table will all columns present, ready to be filled
in for [ensemble](#ensemble). The table is printed to standard out, so
redirecting it to the desired file is recommended. Currently, `generate-table`
accepts no command-line options.
```
# This is all the columns suppored by nbody-setup ensemble.
# Columns may be safely removed.
# Removed columns will be replaced by a suitable default for all runs.
# Om      | float | Ω_m total matter density
# Ob      | float | Ω_b baryonic matter density
# sigma8  | float | σ_8 8 Mpc/h matter clustering
# ns      | float | Spectral index of initial power spectra
# h       | float | Reducede hubble constant H_0 / (100 km/s/Mpc)
# seed    | int   | Random seed for initial conditions
# boxsize | float | Box side length in Mpc/h
# N       | int   | cube root of the number of particles
Om      Ob      sigma8  ns      h       seed    boxsize N
```

### To-Dos
- [x] Generic over IC code
- [ ] Generic over simulation code
  - [ ] Glue between different IC formats
- [ ] Configurable output times
  - [ ] Output in a format accepted by the generic simulation code
- [ ] Support for MonofonIC ICs
- [ ] Support for SWIFT N-body runs
- [ ] Support for disBatch engine
- [ ] Don't use slurm commands if they're not present
- [ ] Migrate this todo list to github issues
- [ ] Proper and complete help command
- [ ] Make ensemble expand one-row columns to the whole set
- [ ] Generate shell completions
- [ ] Don't assume glass files are 64x64x64. Either that or document that they
      must be such.
- [ ] Generate tables with values from a latin hypercube or sobol sequence
- [ ] Initial conditions mode to simply link to a specific file(s) for ICs
- [ ] Define a cosmology class to use

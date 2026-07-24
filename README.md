nbody-setup
-----------

`nbody-setup` is a tool for setting up one or many N-body cosmological
simulations. If you encounter any problems using `nbody-setup`, please file an
issue on github. If you use `nbody-setup` to generate data for a publication, I
ask that you please note this in an acknowledgments section.

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

### To-Dos
- [x] Generic over IC code
- [ ] Generic over simulation code
  - [ ] Glue between different IC formats
- [ ] Configurable output times
  - [ ] Output in a format accepted by the generic simulation code
- [ ] Support for MonofonIC ICs
- [ ] Support for SWIFT N-body runs
- [ ] Support for disBatch engine
- [ ] Don't use slurm commands if they're not present.

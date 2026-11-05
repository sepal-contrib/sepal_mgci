# Domain and lifecycle tests

Run from the repository root:

```sh
python -S -m unittest discover -s tests_offline -v
```

These tests use only the standard library and the `mgci` package. `-S` disables
site initialization, so pysepal, widgets, Earth Engine and the network are not
needed. The legacy `tests/conftest.py` is not collected.

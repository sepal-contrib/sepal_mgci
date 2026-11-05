# Local dependency and render checks

Run from the repository root with the app environment:

```sh
python tests_local/run.py
```

The runner forbids socket connections and persistent Earth Engine credentials
before test discovery. Earth Engine graph tests use the installed client's static
algorithms; file and session boundaries use in-memory doubles. Solara tests render
actual widgets. No export or authenticated request is submitted.

These checks do not cover browser appearance, real asset access, remote workspace
behavior or numerical equivalence over live regions.

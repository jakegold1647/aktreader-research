# Reproducibility notes

AKT Reader is designed to make a local run inspectable rather than opaque. A complete study should record:

1. The repository release and commit SHA.
2. The supplied scan or crop identifier and SHA-256 hash.
3. The model, runtime, prompt, schema, and decoding configuration.
4. The configured privacy policy and any manual review decisions.
5. The resulting evidence JSON, including uncertainty and source spans.

The repository includes schemas, validators, and tests. It does not ship model weights, model executables, or archive scans. The documented local baseline for historical handwriting has not yet been run; no benchmark performance should be inferred from the presence of tests or example configurations.

For a fresh environment, install the development dependencies, run `python -m pytest`, and then run `aktreader doctor`. Supply only local paths to a model runtime and artifacts that you are authorized to use.
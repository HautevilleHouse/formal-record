# Upstream Sources

Records uses upstream projects as attributed source routes.

## OpenConjecture

- Steward: `davisrbr/openconjecture`
- Dataset: https://huggingface.co/datasets/davisrbr/openconjecture
- Pipeline: https://github.com/davisrbr/conjectures-arxiv
- Dataset card license field: `other`
- Publication policy: record-level text publication and withholding fields described by the dataset card
- Records policy: metadata only; no conjecture or statement bodies are emitted by the importer

## DeepMind Formal Conjectures

- Steward: Google DeepMind
- Repository: https://github.com/google-deepmind/formal-conjectures
- License: Apache-2.0
- Records policy: Git tree metadata only by default; paths, blob identities, and sizes remain attributed to the upstream repository

## arXiv

- Steward: arXiv
- Route: versioned abstract pages such as `https://arxiv.org/abs/2606.26786v1`
- Records policy: source identity and links; source text remains governed by each paper's license and arXiv's terms

## Commentary

- Steward: HautevilleHouse
- Repository: https://github.com/HautevilleHouse/commentary
- Records policy: generated record metadata links to the complete public packet and binds the public identity file by SHA-256

## Commentary history note

The public [`commentary`](https://github.com/HautevilleHouse/commentary) shelf was republished as a single-commit public history. Catalog `source_revision` values pin the live public tip. Older multi-commit history is retained off the public surface and is not part of this catalog's provenance pins.

Attribution and metadata links do not imply endorsement by any upstream steward.

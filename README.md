# CircuitCLI – Image‑to‑Simulation Tool

## 1  Purpose & Vision

CircuitCLI turns a **photographed or hand‑drawn electrical circuit** into a fully solvable digital twin.  In a single command‑line workflow the tool will:

1. **Detect** every component, junction, and text label in the image.
2. **Build** a graph or SPICE netlist that captures node connectivity and component values.
3. **Simulate** the circuit (DC, AC, transient) via ngspice/PySpice.

The goal is a reproducible pipeline that shortens idea‑to‑analysis time for engineers, educators, and hobbyists.

---

## 2  Problem Statement

Today users manually redraw schematics in EDA suites before they can run analyses—slow, error‑prone, and inaccessible on the go. CircuitCLI removes that bottleneck by *automating* the translation from pixels to equations.

---

## 3  Scope

| In‑scope                                            | Out‑of‑scope                          |
| --------------------------------------------------- | ------------------------------------- |
| Hand‑drawn & printed schematics (single page)       | Multi‑sheet or hierarchical designs   |
| 45 symbol classes (+ junction, crossover, terminal) | Complex IC footprints like BGA or QFP |
| DC, AC, transient analyses                          | RF, Monte‑Carlo, temperature sweeps   |
| CLI & Docker delivery                               | Full GUI editor                       |

---

## 4  High‑Level Architecture

```
      +-------------+     bboxes/json      +-------------+
 image→| Detector &  | ───────────────▶ | Wire/Graph   |
       |  OCR (DL)  |                    |  Assembly    |
      +-------------+                    +------+------+
                                                | graph/netlist
                                                ▼
                                +--------------+-------------+
                                |  Simulation (ngspice)     |
                                +--------------+-------------+
                                                | waveforms/CSV/PNG
                                                ▼
                                         User / CI pipeline
```

**Data flow**: raw image → ML inference (YOLOv8‑seg + OCR) → skeleton tracing → NetworkX graph → SPICE netlist → PySpice simulation.

---

## 5  Core Components

| Layer                      | Responsibilities                                      | Key Tech                          |
| -------------------------- | ----------------------------------------------------- | --------------------------------- |
| **Dataset & Augmentation** | Store raw and synthetic images, split, augment        | DVC, Albumentations               |
| **Detection & OCR**        | Detect symbols, text, junctions; classify orientation | PyTorch/YOLOv8‑seg, EasyOCR/TrOCR |
| **Graph Builder**          | Extract skeleton, construct connectivity graph        | OpenCV, NetworkX                  |
| **Netlist Generator**      | Map graph to SPICE primitives                         | Custom YAML mapping               |
| **Simulation Engine**      | Run DC/AC/transient analyses                          | PySpice (ngspice backend)         |
| **CLI & Packaging**        | Expose features, progress bars, installation          | click, rich/tqdm, Poetry + pipx   |
| **CI/CD & DevOps**         | Lint, test, Docker, model caching                     | GitHub Actions, Ruff, mypy        |

---

## 6  Project Phases (Epics)

1. **Dataset Audit & Preparation** – Version raw data, create COCO JSON, synthesize printed schematics.
2. **Detection & OCR Models** – Train YOLOv8‑seg, export ONNX, integrate OCR & orientation.
3. **Wire Detection & Graph Assembly** – Skeletonise image, build NetworkX graph, visualise.
4. **Netlist Generation** – YAML mapping, writer, user overrides.
5. **Simulation Integration** – Docker with ngspice, wrapper for DC/AC/transient, plotting helper.
6. **CLI Packaging & UX** – click multi‑command app, progress bars, pipx/Docker release.
7. **Quality Engineering & CI/CD** – Actions for lint/tests, artefact caching, CODEOWNERS.
8. **Validation, Docs & Release** – Benchmark, user guide, GitHub Release v0.1.0.

---

## 7  Technology Stack

* **Languages**: Python 3.12, (bash for helpers)
* **ML Frameworks**: PyTorch 2.x, Ultralytics YOLOv8, ONNX Runtime
* **Vision & Graph**: OpenCV, Albumentations, NetworkX, Graphviz
* **Simulation**: ngspice 36+, PySpice 1.5+
* **CLI & UX**: click, rich, tqdm, matplotlib
* **DevOps**: Docker, GitHub Actions, DVC, Poetry

---

## 8  Key Deliverables

1. **`circuitcli` CLI package** (pipx & Docker)
2. Pre‑trained **ONNX model** (≈20 MB) for offline inference
3. **Documentation site** (MkDocs / GitHub Pages) with a worked tutorial
4. **Benchmark report** covering detection mAP, graph accuracy, simulation fidelity
5. **v0.1.0 GitHub Release** with changelog and usage examples

---

## 9  Success Metrics

| Metric                                     | Target                      |
| ------------------------------------------ | --------------------------- |
| Detection mAP‑50                           | ≥ 0.60 on validation set    |
| Graph connectivity accuracy                | ≥ 95 % junction correctness |
| OCR component‑value accuracy               | ≥ 90 %                      |
| Simulation match (RMS error vs golden)     | ≤ 5 %                       |
| End‑to‑end CLI runtime (1080 × 1920 image) | ≤ 8 s on laptop CPU         |

---

## 10  Timeline Snapshot (12 weeks)

* **Wk 1–2** Dataset & augments
* **Wk 3–5** Detector/ocr training
* **Wk 6–7** Graph assembly
* **Wk 8** Netlist
* **Wk 9** Simulation
* **Wk 10** CLI & CI
* **Wk 11–12** Benchmarks, docs, release

---

## 11  Stakeholders & Roles

| Role                  | Responsibility                            |
| --------------------- | ----------------------------------------- |
| **ML Engineer** (you) | Model training, integration, benchmarking |
| Software Engineer     | Graph, netlist, CLI implementation        |
| DevOps                | Docker, CI/CD, release automation         |
| Tech Writer           | Documentation, tutorials                  |
| Product Lead          | Scope alignment, success criteria         |

---

## 12  Glossary

| Term                | Definition                                                                            |
| ------------------- | ------------------------------------------------------------------------------------- |
| **SPICE**           | Simulation Program with Integrated Circuit Emphasis, de‑facto standard netlist format |
| **COCO JSON**       | Common object‑detection annotation schema                                             |
| **Skeletonisation** | Morphological thinning of binary image to 1‑pixel‑wide lines                          |
| **Netlist**         | Text description of circuit components and node connections                           |

---

### TL;DR

CircuitCLI is an open‑source **image‑to‑simulation pipeline**. Snap a photo of a schematic, run a single command, and get solved waveforms—powered by YOLO, OCR, graph analysis, and ngspice.

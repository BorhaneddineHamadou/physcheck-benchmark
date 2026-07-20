| Corpus (real data) | Files | Tool false positives | Specificity | Conversion-artifact findings¹ | Seeded mutants | Detected | Sensitivity |
|---|---|---|---|---|---|---|---|
| corner_case_ndd | 25 | 0 | 100.0% | 0 | 76 | 76 | 100.0% |
| dlr_ht | 1 | 0 | 100.0% | 0 | — | — | — |
| dlr_ut | 4 | 0 | 100.0% | 0 | — | — | — |
| sctrans_real | 1079 | 0 | 100.0% | 1079 files | 1545 | 1545 | 100.0% |

¹ Error findings manually verified as TRUE defects of the corpus's conversion pipeline (template metadata, converted-map under-coverage), not tool mistakes — triage evidence in the benchmark repo.

*physcheck 0.2.0; protocol, corpora provenance and per-finding triage: see the [benchmark repo](https://github.com/BorhaneddineHamadou/physcheck-benchmark).*

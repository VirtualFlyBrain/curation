# NEVER LOADED

**Nothing in this directory has ever been loaded into the VFB KB.** It is kept only in case
it is useful; it is not a queue, and the checker (`src/run_peevish.py`) does not read it.
Do not move these into `to_submit/` without regenerating or re-checking them first.

Contrast `records/archive/`, which holds records that *were* loaded.

Moved here by Alex McLachlan on 2026-10-16, as part of handing over.

| directory | what | why it never loaded |
|---|---|---|
| `gen1_mcfo_260306/` | Gen1 MCFO image records for Dionne2018, Jenett2012, Jovanic2019, Tirian2017 (~43k rows), from 6 March 2026 | The image load pipeline was the bottleneck at the time, so the curation work was dropped. That bottleneck has since been removed. **Regenerate rather than load these**: the FlyLight Split-GAL4 curation repo produces them, and the source JSON will have moved on. |
| `Kuan2020_problem_rows/` | 3 rows split out of `anat_Kuan2020_230227` (VNC leg images, `vnc_harvard_catmaid_api`) | They failed the load in 2023. The rest of that file loaded and is in `records/archive/`. Probably not worth fixing. |
| `SplitMeissner2024_mismatches/` | 22 rows of `split_SplitMeissner2024_241216` flagged as mismatches to fix (larval L3 CNS splits) | Never fixed. A few of these lines appear in later Meissner2024 split loads in `records/archive/`; most do not. Check against the KB before reusing any row. |

Also removed from the branch on the same day, because they were not unloaded data:
`Hold/anat_McKellar2020_230707.*` (byte-identical to the copy in `records/archive/`, which
was loaded) and `id test/anat_SplitSterne2021_221202.*` (a 2023 test of loading with a set
id, `VFB_alexalex`, never meant to load).

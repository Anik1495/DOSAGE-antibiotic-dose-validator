# Data folder

The app loads four CSV files from this folder at startup. Place them here
before running `main.py` (this file should be saved as `data/README.md` in
your repo).

The dataset itself is published separately on Figshare — see `SOURCE.md` in
this folder for the download link and citation. Once downloaded, the files
need to match the filenames/columns below.

| File                | Source table    | Required columns (used by main.py)                                                                                          |
|----------------------|------------------|-------------------------------------------------------------------------------------------------------------------------------|
| `normal_dose.csv`    | disease-specific dosing | `generic`, `disease`, `administration`, `min_age_Y/M/D`, `max_age_Y/M/D`, `min_weight`, `max_weight`, `min_dose_dw_mg`, `max_dose_dw_mg`, `min_dose_dd_mg`, `max_dose_dd_mg`, `min_dose_dw_UNIT`, `max_dose_dw_UNIT`, `min_dose_dd_UNIT`, `max_dose_dd_UNIT` |
| `standard_dose.csv`  | non-disease-specific dosing | same columns as `normal_dose.csv`, minus `disease`                                                                    |
| `pregnancy.csv`      | pregnancy risk category | `generic`, `pregnancy_risk`                                                                                              |
| `renal_dose.csv`     | renal (CrCl) adjustments | `generic`, `disease`, `administration`, `min_crcl`, `max_crcl`, `min_weight`, `max_weight`, `recommendation_flag`, `max_dose_dd_mg`, `max_dose_dw_mg`, `max_dose_dd_UNIT`, `max_dose_dw_UNIT` |

## Where to get these files

Download the dataset from the Figshare link in `SOURCE.md`. Its published
files (`d_dose.csv`, `s_dose.csv`, `r_dose.csv`, `preg_risk.csv`) use shorter
column names for the data descriptor (e.g. `min_dd_mg`) that don't line up
1:1 with this app's internal schema. Rename/remap columns to match the table
above, save under the filenames listed (`normal_dose.csv`, `standard_dose.csv`,
`pregnancy.csv`, `renal_dose.csv`), and place them in this folder.

If you still have access to the original Supabase project, exporting each
table directly (Table Editor → select table → Export → CSV) is the safest
route since it guarantees the columns already match.

These CSVs are meant to be committed alongside the code so the demo works
out of the box for anyone who clones the repo — or you can leave them out
and just point people to `SOURCE.md` if you'd rather not duplicate the data.

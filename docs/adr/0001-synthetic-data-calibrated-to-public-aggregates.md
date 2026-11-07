# 1. Synthetic student data, compared with public CDE aggregates

Status: accepted

## Context
Real student records are protected by FERPA and California law, and a public portfolio cannot hold them. Fake data with no tie to reality would make the reports meaningless.

## Decision
Generate every student record from a fixed seed, and label it as generated in the files, the manifest and every dashboard page. Compare the generated rates with CDE's public chronic absenteeism file using `k12att calibrate`.

## Consequences
- The generator's target rates are placeholders until the calibration is run against a real CDE file. That has not been done yet: the build environment could not reach cde.ca.gov.
- Because the generator also writes the defect manifest, the validation rules have an exact test oracle.

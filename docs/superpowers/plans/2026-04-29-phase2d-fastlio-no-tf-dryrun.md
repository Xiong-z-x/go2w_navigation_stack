# Phase 2D FAST-LIO2 No-TF Runtime Dry-Run Plan

## Scope

Implement the approved Phase 2D automation boundary with repository-local
scripts and evidence documents only. External FAST_LIO_ROS2 source remains in
`/tmp`.

## Steps

1. Add a preparation script that reuses or acquires FAST_LIO_ROS2, restores the
   `ikd-Tree` submodule source, applies the Phase 2C patch, audits the result,
   and builds `fast_lio` with `FAST_LIO_ENABLE_LIVOX=OFF`.
2. Add a no-TF runtime dry-run script that launches the accepted headless
   simulator, starts patched FAST-LIO with a temporary no-TF config, samples
   output topics, samples TF, and cleans up.
3. Add a Phase 2D verification record with the exact command boundary and
   observed result.
4. Update `README.md` and `docs/architecture/architecture_state.md` so the
   operator-facing summary and state file point to the new Phase 2D gate.
5. Run syntax checks, external preparation, dry-run evidence collection,
   whitespace check, and scoped build/regression commands.
6. Commit and push the single Phase 2D automation change set to `main`.

## Review Points

- The scripts must not vendor FAST_LIO_ROS2 into this repository.
- The scripts must not enable FAST-LIO TF publication.
- The scripts must not claim `odom -> base_link`.
- Any missing FAST-LIO output topic must be recorded as evidence, not hidden.

## Commands

```bash
bash -n tools/prepare_phase2d_fastlio_external.sh
bash -n tools/verify_phase2d_fastlio_no_tf_dryrun.sh
GO2W_FASTLIO_REBUILD=1 ./tools/prepare_phase2d_fastlio_external.sh
./tools/verify_phase2d_fastlio_no_tf_dryrun.sh
git diff --check
```

UV ?= uv
REPORT_PYTHON ?= python3.11
.PHONY: setup report report-test report-check notebook-check paper paper-check
setup:
	$(UV) sync --frozen --python 3.11
report:
	$(REPORT_PYTHON) scripts/public_release.py build
report-test:
	PYTHONPATH=. $(REPORT_PYTHON) -m pytest -q tests/test_g5_reporting.py tests/test_public_notebook.py tests/test_working_paper.py -k "not protected_originals_and_archive_exceptions and not presentation_traceability_and_scope and not headline_dimensions_and_summary and not check_entrypoint and not correction_keeps_registry_and_archives_immutable and not full_results_only_renderer_with_no_private_inputs and not research_pipeline_not_in_report_build"
report-check:
	$(REPORT_PYTHON) scripts/public_release.py check
notebook-check:
	$(REPORT_PYTHON) scripts/execute_notebook.py
paper:
	$(REPORT_PYTHON) scripts/working_paper.py build
paper-check:
	$(REPORT_PYTHON) scripts/working_paper.py check

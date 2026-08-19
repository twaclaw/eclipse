# Earth, Moon and Sun - development and publishing.
#
# The site is a pile of static files, but it is not self-contained: the pages
# fetch a Python runtime, some wheels, three.js and the planet maps from public
# CDNs at view time. Anything that can serve files will host it; nothing will
# make it work offline.

.DEFAULT_GOAL := help
.PHONY: help install test edit site serve check deploy clean

PORT ?= 8080

help:  ## Show this help
	@grep -hE '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk -F':.*?## ' '{printf "  \033[1m%-10s\033[0m %s\n", $$1, $$2}'

install:  ## Set up the virtualenv, including the site tooling
	uv sync --all-groups
	uv run --group site playwright install chromium

test:  ## Run the test suite
	uv run pytest -q

edit:  ## Open the notebooks in marimo
	uv run marimo edit notebooks/

site:  ## Build the static site into site/
	uv run --group dev python scripts/build_site.py

serve: site  ## Build and serve the site locally
	@echo "http://localhost:$(PORT)"
	python3 -m http.server $(PORT) --directory site

check:  ## Load every built page in a real browser and check it runs
	uv run --group site python scripts/check_site.py

deploy:  ## Explain how publishing works (it is not done from here)
	@echo "The site is published by .github/workflows/pages.yml on every push"
	@echo "to main: it runs the tests, builds, checks every page in a browser,"
	@echo "and deploys through the Pages artifact."
	@echo
	@echo "Set the repository's Pages source to 'GitHub Actions'."
	@echo
	@echo "Nothing is committed, which is the point: the built site is 28 MB"
	@echo "against 592 kB of source, and a gh-pages branch would be pulled by"
	@echo "every clone forever."

clean:  ## Remove the built site
	rm -rf site

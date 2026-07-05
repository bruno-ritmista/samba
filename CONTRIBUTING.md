# Contributing

Thanks for your interest in this project!

## Issues

You are very welcome — and encouraged — to open an issue if you:

- Found a bug
- Have a feature idea
- Think something could work better
- Have questions about how to use the tools

Issues are the best way to help improve this project, and all feedback is appreciated.

## Code Contributions

This is my first personal public project, so I'm still learning how to navigate contribution from others. If you'd like to contribute code, please **reach out to me ** — open an issue or contact me to discuss. I'm happy to collaborate when there's a good fit.

## Tool conventions

Every tool folder (e.g. `sheets_to_banana/`, `banana_to_pdf/`) must support both:

- **Direct run, no install**: a top-level `__main__.py` shim so `python <tool_dir> <args>` works straight from a checkout.
- **Installed CLI**: a `[project.scripts]` entry in `pyproject.toml` so `python -m <tool_dir> <args>` works after `pip install`.

CI auto-discovers any folder containing a `pyproject.toml` and runs both usage modes against it, so new tools get covered automatically — no workflow changes needed.

## Contact

You can reach me via GitHub issues.
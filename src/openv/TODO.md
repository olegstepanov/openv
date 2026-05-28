- Check if prerequisites are missing before installing
- Move topological sort and pm detectio to install_tools
- Add short docstrings to modules and functions
- Put equivalent return path under else
- Create separate method for extracting dependencies from tool
- Put dependencies into ToolInfo
- Centralize information about special files (installation scripts, manifest)
- Find tasks that are marked as implemented, but for which code is missing. Check if these tasks really need to be implemented.
? How to organize global Claude settings to put Python-specific preferences in a separate file to be looked up only for Python projects?
- PYTHON: Prefer relative imports for local modules

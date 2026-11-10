# Releasing tapetum to PyPI

Once this is set up, a release is one command, and `uvx tapetum` works for everyone without the `git+https://` part.

## One-time setup (done on 2026-11-10)

1. **Make a PyPI account** at <https://pypi.org/account/register/>. Confirm your email and turn on two-factor auth, which PyPI requires before you can publish.
2. **Tell PyPI to trust this repo.** Go to <https://pypi.org/manage/account/publishing/> and add a *pending publisher*:
   - PyPI project name: `tapetum`
   - Owner: `Nadercr7`
   - Repository name: `tapetum`
   - Workflow name: `release.yml`
   - Environment name: `pypi`

   This is "trusted publishing". GitHub proves to PyPI that the upload really comes from this repo's workflow, so no password or token ever lives in the repo or in a chat.
3. **Create the environment on GitHub.** Repo → Settings → Environments → New environment → name it `pypi`. Leave the rest as is.

## Every release

Bump `version` in `pyproject.toml`, `src/tapetum/__init__.py` and `.claude-plugin/plugin.json`, commit, then tag and push:

```bash
git tag v0.2.1
git push origin v0.2.1
```

The `release` workflow builds the package and uploads it. Watch it under the repo's Actions tab. A couple of minutes later it's live at <https://pypi.org/project/tapetum/>, and anyone can run:

```bash
uvx tapetum "https://youtu.be/jNQXAC9IVRw"
```

If the upload fails with "invalid-publisher", one of the five fields in step 2 doesn't match exactly.

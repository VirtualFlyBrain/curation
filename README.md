# Curation [![Build Status](https://secure.travis-ci.org/VirtualFlyBrain/curation.png)](https://travis-ci.org/VirtualFlyBrain/curation)

A repository of records specifying curation into the VFB Knowledge Base and code that parses and checks them.

## Curation manual
To  learn about curation, please see our [Curation manual](https://github.com/VirtualFlyBrain/curation/wiki/Curation--Manual-Wiki) and the links to spec files within it.

## Git workflow 

**To curate:** please checkout a branch with your name.  Make sure to register this branch name on the Jenkins submission job.  ***Do not*** merge this branch back into master.  Keep working content in the working directories.  Move content to the submission directory in order to test load it to the KB.  Make sure to keep code in this branch up-to-date using "git merge master".

**To work on checking/parsing code:** please check out a new branch. ***Do not*** merge back to master until all tests have passed and merge is safe.  Please use pull requests to document/review merges.

**Running an update:** Updates are run on a private Jenkins server: the Test job checks records against the KB, the Run job loads them into the writable KB. Rows that fail are skipped and reported, and fail the run. Loading order is `new_metadata`, then `newmeta_deletions` (edges to remove; see [its README](records/newmeta_deletions/README.md)), then `new_splits`, `new_eps` (expression pattern classes of single drivers, with no image; see [its README](records/new_eps/README.md)), `new_images` and `new_xrefs`.

**Archiving:** nothing moves files automatically. After a successful Run, move the loaded files to `records/archive` on your branch with `python src/archive_submitted.py` (`--dry-run` to preview), then commit and push.


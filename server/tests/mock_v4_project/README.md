This is needed for the migration testing. One inconvenience that warrants the template fill-in with absolute paths is that such were used in the settings and image paths in the repo for v4.

In `original/` there should be the original repo created with pamet v4 (kept only locally).
From it the `template/` is created with `python prepare.py anonymize`

The last working v4 commit is `be8be4ce0dd07527e86f4f524257ffec09d17369`; clone it with `git clone https://github.com/v-ko/pamet` and `git checkout be8be4ce0dd07527e86f4f524257ffec09d17369`.

Opening the original repo should happen with a v4 of pamet and
```
pamet --config-path ./original/app_data/settings.json
```

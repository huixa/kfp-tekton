# Third Party dependency -- Argo

This folder holds resources for KFP to redistribute <https://argoproj.github.io/projects/argo>
container images.

There's no code change. KFP only makes sure the images comply with licenses of all its dependencies
and transitive dependencies by redistributing license notices and source code (when required by
license) inside a `/NOTICES` folder inside the container.

## Upgrade Argo image

NOTE: the following steps will push argo images to gcr.io/ml-pipeline.

Prerequisites:

* Be an admin to gcr.io/ml-pipeline.
* Install go-licenses/v2 from [Bobgy's current release](https://github.com/Bobgy/go-licenses/releases/tag/v0.0.0-2021-06-23). Make sure the tool is available in PATH.

Instructions:

1. Set version of argo you want to upgrade to, for example:

    ```bash
    ARGO_TAG=v3.1.6
    ```

1. ```bash
    echo "${ARGO_TAG}" > VERSION
    ./release.sh
    ```

    or run separate steps, so you can quickly fix issues

    ```bash
    echo "${ARGO_TAG}" > VERSION
    # Ensure there are no errors. If there are any issues, update go-licenses.yaml and retry.
    # Also, we need to check licenses-argoexec.csv and licenses-workflow-controller.csv
    # manually. Verify all the entries look sane and examine specific modules for license if sth
    # is weird.
    ./imp-1-update-notices.sh
    # gcloud auth login first, so that you can use docker push to push to gcr.io/ml-pipeline.
    ./imp-2-build-push-images.sh
    ```

    The `release.sh` script does a few things:

    * Use [github.com/Bobgy/go-licenses/v2](https://github.com/Bobgy/go-licenses/tree/main/v2) to prepare NOTICES folder for argo images.
    * Build license compliant argo images.
    * Push them to `gcr.io/ml-pipeline/argoexec:${ARGO_TAG}-license-compliance` and
    `gcr.io/ml-pipeline/workflow-controller:${ARGO_TAG}-license-compliance`.

1. Update [manifests](../../manifests) and other places in the code base that still uses the old argo image tag.

1. Commit these changes to a PR.

1. Fix any other issues caused by the upgrade.

## TODOs

Ideas to improve this process:

* Write a script that auto updates all occurrences of old argo image
tag to the new one.
* Reduce occurrences of argo image tag version, and let them use `./VERSION` programmatically when possible.

"""Builds the API's zip: server/ as committed, with its packages installed for App Service.

Azure runs the zip as it is and builds nothing (SCM_DO_BUILD_DURING_DEPLOYMENT is false), so
production runs the packages built here, not a second install on the App Service plan. pip takes
Linux wheels for the API's Python whatever machine runs this, so it works the same on Windows.

    python -m dev.package api.zip --version v1.4.0      (from server/)
"""
import argparse
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

# The App Service runtime; ci.yml and deploy/azure/provision.ps1 name the same
PYTHON = "3.15"
# Wheels built for glibc 2.34 or older: Azure's Python images (Debian bookworm, Ubuntu noble) are newer.
# pip doesn't widen one --platform to the older ones, so each is listed
PLATFORMS = ("manylinux_2_34_x86_64", "manylinux_2_28_x86_64", "manylinux_2_17_x86_64", "manylinux2014_x86_64")
# Where the packages go in the zip; the API's PYTHONPATH names it (deploy/azure, deploy.yml)
PACKAGES = ".python_packages"

REPO = Path(__file__).resolve().parents[2]


def git(*args: str) -> bytes:
    return subprocess.run(["git", "-C", str(REPO), *args], check=True, capture_output=True).stdout


def pip(*args: str) -> None:
    subprocess.run([sys.executable, "-m", "pip", *args, "--quiet", "--disable-pip-version-check"], check=True)


def install_packages(requirements: Path, target: Path, scratch: Path) -> None:
    """Installs the requirements as wheels for App Service: a package that would compile here could not run there.

    A package published only as source (langdetect) gets a wheel built here first. Only the pure-Python
    ones are kept, which run anywhere; one that compiles has no wheel to offer and stops the build.
    """
    built, pure = scratch / "built", scratch / "pure"
    pip("wheel", "-r", str(requirements), "--wheel-dir", str(built))
    pure.mkdir()
    for wheel in built.glob("*-none-any.whl"):
        wheel.rename(pure / wheel.name)
    platforms = [f"--platform={platform}" for platform in PLATFORMS]
    pip("install", "--no-compile", "--only-binary=:all:", "--implementation=cp", f"--python-version={PYTHON}",
        *platforms, "--find-links", str(pure), "--target", str(target), "-r", str(requirements))


def build(out: Path, version: str) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        # The committed requirements, like the committed code: what's deployed is what's in git
        requirements = Path(tmp) / "requirements.txt"
        requirements.write_bytes(git("show", "HEAD:server/requirements.txt"))
        packages = Path(tmp) / PACKAGES
        install_packages(requirements, packages, Path(tmp))

        # Only committed files, so no .env, data or virtual environment, plus the version for /health
        git("archive", "--format=zip", "-o", str(out), f"--add-virtual-file=version.txt:{version}", "HEAD:server")
        with zipfile.ZipFile(out, "a", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(packages.rglob("*")):
                if path.is_file():
                    archive.write(path, f"{PACKAGES}/{path.relative_to(packages).as_posix()}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the API's zip for App Service.")
    parser.add_argument("out", type=Path, help="the zip to write")
    parser.add_argument("--version", required=True, help="shown by /health, e.g. v1.4.0")
    args = parser.parse_args()
    build(args.out.resolve(), args.version)
    print(f"Wrote {args.out} ({args.out.stat().st_size // 1_000_000} MB)")


if __name__ == "__main__":
    main()

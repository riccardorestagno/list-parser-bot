"""dev/package.py: the API's zip holds the committed server/ and its packages, built for App Service."""
import zipfile
from pathlib import Path

from dev import package


def stub_pip(monkeypatch, wheels: tuple[str, ...] = ()) -> list[tuple[str, ...]]:
    """pip without the network: `wheel` leaves the given wheel files, `install` one package."""
    calls: list[tuple[str, ...]] = []

    def pip(*args: str) -> None:
        calls.append(args)
        if args[0] == "wheel":
            built = Path(args[args.index("--wheel-dir") + 1])
            built.mkdir()
            for name in wheels:
                (built / name).write_bytes(b"")
        if args[0] == "install":
            target = Path(args[args.index("--target") + 1])
            (target / "fastapi").mkdir(parents=True)
            (target / "fastapi" / "__init__.py").write_text("")

    monkeypatch.setattr(package, "pip", pip)
    return calls


def test_the_zip_holds_the_committed_server_its_packages_and_the_version(tmp_path, monkeypatch):
    stub_pip(monkeypatch)
    out = tmp_path / "api.zip"
    package.build(out, "v9.9.9")

    with zipfile.ZipFile(out) as archive:
        names = archive.namelist()
        assert archive.read("version.txt") == b"v9.9.9"
    assert "main.py" in names and "requirements.txt" in names
    assert f"{package.PACKAGES}/fastapi/__init__.py" in names
    assert not any(name.startswith(("server/", "venv/", "data/")) or name == ".env" for name in names)


def test_packages_are_wheels_for_the_apis_linux_and_python(tmp_path, monkeypatch):
    calls = stub_pip(monkeypatch)
    package.build(tmp_path / "api.zip", "v9.9.9")

    install = next(call for call in calls if call[0] == "install")
    assert "--only-binary=:all:" in install
    assert f"--python-version={package.PYTHON}" in install
    assert {f"--platform={platform}" for platform in package.PLATFORMS} <= set(install)


def test_only_pure_python_wheels_built_here_are_offered(tmp_path, monkeypatch):
    calls = stub_pip(monkeypatch, wheels=("langdetect-1.0.9-py3-none-any.whl",
                                          "native-1.0-cp315-cp315-win_amd64.whl"))
    offered: list[str] = []
    real_pip = package.pip

    def pip(*args: str) -> None:
        if args[0] == "install":
            offered.extend(path.name for path in Path(args[args.index("--find-links") + 1]).iterdir())
        real_pip(*args)

    monkeypatch.setattr(package, "pip", pip)
    package.build(tmp_path / "api.zip", "v9.9.9")

    assert offered == ["langdetect-1.0.9-py3-none-any.whl"]
    assert any(call[0] == "install" for call in calls)

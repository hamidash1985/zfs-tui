import argparse
import subprocess
import sys
from pathlib import Path


def build_native(project_root: Path):
    spec_file = project_root / "zfs-tui.spec"
    dist_dir = project_root / "dist"
    work_dir = project_root / "build" / "pyinstaller"

    if not spec_file.exists():
        print(f"Spec file not found: {spec_file}", file=sys.stderr)
        sys.exit(1)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        str(spec_file),
        "--distpath", str(dist_dir),
        "--workpath", str(work_dir),
        "--noconfirm",
    ]

    print(f"Building native executable...")
    print(f"Spec: {spec_file}")
    print(f"Output: {dist_dir}")
    print()

    result = subprocess.run(cmd, cwd=project_root)
    sys.exit(result.returncode)


def build_linux_docker(project_root: Path):
    dockerfile = project_root / "Dockerfile.build"
    dist_dir = project_root / "dist"

    if not dockerfile.exists():
        print(f"Dockerfile not found: {dockerfile}", file=sys.stderr)
        sys.exit(1)

    image_tag = "zfs-tui-builder"

    print("==> Building Docker image: zfs-tui-builder")
    subprocess.run(
        ["docker", "build", "-t", image_tag, "-f", str(dockerfile), str(project_root)],
        check=True,
    )

    print()
    print("==> Building Linux executable via Docker...")
    dist_dir.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        [
            "docker", "run", "--rm",
            "-v", f"{project_root}:/project",
            "-v", f"{dist_dir}:/output",
            image_tag,
        ],
        check=True,
    )

    linux_bin = dist_dir / "zfs-tui"
    print()
    if linux_bin.exists():
        print(f"Done! Linux executable at: {linux_bin}")
        size = linux_bin.stat().st_size
        print(f"Size: {size / 1024 / 1024:.1f} MiB")
    else:
        print("Build completed but executable not found — check for errors above.")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Build zfs-tui standalone executable")
    parser.add_argument(
        "--linux", action="store_true",
        help="Build Linux executable via Docker (cross-compile from any host)",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent.parent

    if args.linux:
        build_linux_docker(project_root)
    else:
        build_native(project_root)


if __name__ == "__main__":
    main()

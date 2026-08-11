from pathlib import Path
import tarfile
import tempfile
import unittest

from idion.registry import Registry
from idion.rootfs import build_kobo_root


REPOSITORY = Path(__file__).resolve().parents[1]


class RootPackageTests(unittest.TestCase):
    def test_installs_key_at_the_account_home_resolved_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            public_key = root / "operator.pub"
            public_key.write_text(
                "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAICNQ3xB3D2eNLGcWb+70Kp1VvSoE3o22F8C4YV4QYJ5F test\n"
            )
            tool = root / "tool"
            tool.write_text("#!/bin/sh\nexit 0\n")
            tool.chmod(0o755)
            output = root / "output"
            device = Registry(REPOSITORY / "adapters").get("kobo-clara-bw")

            result = build_kobo_root(
                device=device,
                adapter_rootfs=REPOSITORY / "adapters" / "_kobo-common" / "rootfs",
                authorized_key=public_key,
                scp_binary=tool,
                sftp_server_binary=tool,
                rsync_binary=tool,
                output_directory=output,
            )

            with tarfile.open(result["installer"], "r:gz") as archive:
                names = set(archive.getnames())
                self.assertIn("./.ssh/authorized_keys", names)
                self.assertNotIn("./root/.ssh/authorized_keys", names)
                key = archive.extractfile("./.ssh/authorized_keys")
                self.assertIsNotNone(key)
                self.assertEqual(key.read(), public_key.read_bytes())  # type: ignore[union-attr]
                sshd = archive.extractfile("./etc/ssh/sshd_config")
                self.assertIsNotNone(sshd)
                self.assertIn(b"AuthorizedKeysFile\t/.ssh/authorized_keys", sshd.read())  # type: ignore[union-attr]

            self.assertEqual(len(result["installer_sha256"]), 64)
            self.assertTrue(Path(result["host_public_key"]).is_file())

    def test_builds_minimal_nickelmenu_package_without_root_ssh(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package_tree = root / "nickelmenu"
            library = package_tree / "usr/local/Kobo/imageformats/libnm.so"
            library.parent.mkdir(parents=True)
            library.write_bytes(b"nickelmenu")
            documentation = package_tree / "mnt/onboard/.adds/nm/doc"
            documentation.parent.mkdir(parents=True)
            documentation.write_text("NickelMenu\n")
            package = root / "NickelMenu.tgz"
            with tarfile.open(package, "w:gz") as archive:
                archive.add(package_tree, arcname=".")
            output = root / "output"
            device = Registry(REPOSITORY / "adapters").get("kobo-clara-bw")

            result = build_kobo_root(
                device=device,
                adapter_rootfs=REPOSITORY / "adapters" / "_kobo-common" / "rootfs",
                output_directory=output,
                launch_mode="nickelmenu",
                nickelmenu_package=package,
            )

            with tarfile.open(result["installer"], "r:gz") as archive:
                names = set(archive.getnames())
                self.assertIn("./usr/local/Kobo/imageformats/libnm.so", names)
                self.assertIn("./etc/hosts", names)
                self.assertNotIn("./etc/init.d/on-animator.sh", names)
                self.assertNotIn("./etc/init.d/ssh", names)
                hosts = archive.extractfile("./etc/hosts")
                self.assertIsNotNone(hosts)
                self.assertIn(b"api.kobobooks.com", hosts.read())  # type: ignore[union-attr]

            self.assertEqual(result["host_public_key"], "not-applicable")


if __name__ == "__main__":
    unittest.main()

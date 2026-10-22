import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path

spec = importlib.util.spec_from_file_location('archive', Path(__file__).parents[1] / 'merifield_sync/archive.py')
archive = importlib.util.module_from_spec(spec)
spec.loader.exec_module(archive)


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.folder = self.root / 'terrain'
        (self.folder / 'DCIM').mkdir(parents=True)
        (self.folder / 'test.qgs').write_text('<qgis/>')
        (self.folder / 'DCIM/signature.png').write_bytes(b'png-test')

    def test_relative_paths_and_attachments(self):
        destination = self.root / 'terrain.zip'
        self.assertEqual(2, archive.create_zip(self.folder, destination))
        with zipfile.ZipFile(destination) as z:
            self.assertEqual({'terrain/test.qgs', 'terrain/DCIM/signature.png'}, set(z.namelist()))
            self.assertEqual(b'png-test', z.read('terrain/DCIM/signature.png'))

    def test_rejects_output_inside_source_and_preserves_existing_zip(self):
        output = self.folder / 'terrain.zip'
        output.write_bytes(b'existing')
        with self.assertRaises(ValueError):
            archive.create_zip(self.folder, output)
        self.assertEqual(b'existing', output.read_bytes())

    def test_rejects_symlink_outside_package(self):
        secret = self.root / 'outside.txt'
        secret.write_text('not-in-package')
        (self.folder / 'linked').symlink_to(secret)
        with self.assertRaises(ValueError):
            archive.create_zip(self.folder, self.root / 'terrain.zip')

    def test_requires_project(self):
        (self.folder / 'test.qgs').unlink()
        with self.assertRaises(ValueError):
            archive.create_zip(self.folder, self.root / 'terrain.zip')

    def test_copy_failure_leaves_previous_archive_intact(self):
        from unittest.mock import patch
        destination = self.root / 'terrain.zip'
        destination.write_bytes(b'previous')
        with patch.object(zipfile.ZipFile, 'write', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                archive.create_zip(self.folder, destination)
        self.assertEqual(b'previous', destination.read_bytes())
        self.assertEqual([destination], list(self.root.glob('*.zip')))


if __name__ == '__main__':
    unittest.main()

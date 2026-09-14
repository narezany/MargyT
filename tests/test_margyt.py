"""The build's own tests.

    python3 -m unittest discover tests

No toolchain and no network: everything runs against tests/data/fixture.apk, a
seven-kilobyte apk built by aapt2 from tests/fixture/ and checked in. It has
what the real one has -- a label from a string resource, an adaptive icon whose
layers are vectors, the icon at two densities, a launcher entry that is an
alias -- and nothing else.
"""

import os
import shutil
import struct
import tempfile
import unittest

import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from margyt import (accent as accent_module, artwork, dexpatch, icon as icon_module,
                    manifest as manifest_module, palette, png, vector)
from margyt.apkzip import Apk, STORED
from margyt.arsc import Arsc, ArscError
from margyt.axml import Axml, TYPE_REFERENCE, TYPE_STRING

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FIXTURE = os.path.join(HERE, "data", "fixture.apk")


def fixture() -> Apk:
    return Apk(FIXTURE)


class AxmlTest(unittest.TestCase):
    def setUp(self):
        self.apk = fixture()
        self.raw = self.apk.read("AndroidManifest.xml")

    def tearDown(self):
        self.apk.close()

    def test_round_trip_is_byte_for_byte(self):
        self.assertEqual(Axml.parse(self.raw).build(), self.raw)

    def test_reading_the_manifest(self):
        axml = Axml.parse(self.raw)
        self.assertEqual(manifest_module.package_name(axml), "cat.narezany.fixture")
        self.assertEqual(manifest_module.application_class(axml), "cat.narezany.fixture.App")
        self.assertEqual(len(manifest_module.icon_ids(axml)), 1)  # icon and roundIcon agree

    def test_min_sdk_comes_from_the_manifest(self):
        self.assertEqual(manifest_module.min_sdk(Axml.parse(self.raw)), 24)

    def test_the_launcher_entry_is_found_through_the_alias(self):
        axml = Axml.parse(self.raw)
        found = manifest_module.launcher_elements(axml)
        self.assertEqual(len(found), 1)
        self.assertEqual(axml.attr_string(found[0], "name"), "cat.narezany.fixture.Splash")

    def test_label_becomes_an_inline_string(self):
        axml = Axml.parse(self.raw)
        manifest_module.set_label(axml, "MargyT")
        again = Axml.parse(axml.build())
        application = manifest_module.application(again)
        attr = again.attr(application, "label")
        self.assertEqual(attr.kind, TYPE_STRING)
        self.assertEqual(again.pool.get(attr.data), "MargyT")

    def test_added_activity_survives_a_rebuild(self):
        """The mod's screen: declared, exported, and off the home screen.

        It is opened from the row in TikTok's own settings, so it has no
        launcher entry -- and therefore no task of its own either, which is
        what lets the back button return to the settings it was opened from.
        """
        axml = Axml.parse(self.raw)
        manifest_module.set_label(axml, "MargyT")
        manifest_module.add_activity(axml, "cat.narezany.margyt.SettingsActivity",
                                     "MargyT settings", 0x0103012C)
        again = Axml.parse(axml.build())

        names = [again.attr_string(node, "name") for node in again.elements("activity")]
        self.assertIn("cat.narezany.margyt.SettingsActivity", names)
        self.assertIn("cat.narezany.fixture.MainActivity", names)

        added = [n for n in again.elements("activity")
                 if again.attr_string(n, "name") == "cat.narezany.margyt.SettingsActivity"][0]
        self.assertEqual(again.attr_string(added, "label"), "MargyT settings")
        self.assertEqual(again.attr(added, "theme").data, 0x0103012C)
        self.assertEqual(again.attr(added, "exported").data, 0xFFFFFFFF)
        self.assertIsNone(again.attr(added, "taskAffinity"))
        self.assertIsNone(again.attr(added, "launchMode"))

        # the app's own launcher entry is untouched, and ours is not one
        launchers = [again.attr_string(n, "name") for n in manifest_module.launcher_elements(again)]
        self.assertNotIn("cat.narezany.margyt.SettingsActivity", launchers)
        self.assertIn("cat.narezany.fixture.Splash", launchers)

    def test_a_launcher_activity_gets_a_task_of_its_own(self):
        """Asked for an entry on the home screen, it comes with what that needs."""
        axml = Axml.parse(self.raw)
        manifest_module.add_activity(axml, "cat.narezany.margyt.SettingsActivity",
                                     "MargyT settings", 0x0103012C, "cat.narezany.margyt",
                                     launcher=True)
        again = Axml.parse(axml.build())

        added = [n for n in again.elements("activity")
                 if again.attr_string(n, "name") == "cat.narezany.margyt.SettingsActivity"][0]
        self.assertEqual(again.attr_string(added, "taskAffinity"), "cat.narezany.margyt")
        self.assertEqual(again.attr(added, "launchMode").data,
                         manifest_module.LAUNCH_SINGLE_TASK)
        launchers = [again.attr_string(n, "name") for n in manifest_module.launcher_elements(again)]
        self.assertIn("cat.narezany.margyt.SettingsActivity", launchers)
        self.assertIn("cat.narezany.fixture.Splash", launchers)

    def test_a_provider_can_be_declared(self):
        axml = Axml.parse(self.raw)
        manifest_module.add_provider(axml, "cat.narezany.margyt.MargyProvider",
                                     "cat.narezany.fixture.margyt")
        again = Axml.parse(axml.build())
        providers = {again.attr_string(n, "name"): n for n in again.elements("provider")}
        self.assertIn("cat.narezany.margyt.MargyProvider", providers)
        added = providers["cat.narezany.margyt.MargyProvider"]
        self.assertEqual(again.attr_string(added, "authorities"), "cat.narezany.fixture.margyt")
        self.assertEqual(again.attr(added, "exported").data, 0)
        self.assertIn("cat.narezany.fixture.P", providers)  # the ones already there stay

    def test_the_screen_the_row_goes_on_is_the_one_the_mod_looks_for(self):
        """The build refuses an apk whose settings screen has been renamed."""
        from margyt.build import TIKTOK_SETTINGS
        source = os.path.join(ROOT, "inject", "java", "cat", "narezany", "margyt",
                              "SettingsRow.java")
        with open(source, encoding="utf-8") as handle:
            self.assertIn('"%s"' % TIKTOK_SETTINGS, handle.read())
        self.assertFalse(manifest_module.has_activity(Axml.parse(self.raw), TIKTOK_SETTINGS))
        self.assertTrue(manifest_module.has_activity(Axml.parse(self.raw),
                                                     "cat.narezany.fixture.MainActivity"))
        # an alias counts too: the launcher entry of the real apk is one
        self.assertTrue(manifest_module.has_activity(Axml.parse(self.raw),
                                                     "cat.narezany.fixture.Splash"))

    def test_only_the_authorities_the_package_does_not_cover_move(self):
        axml = Axml.parse(self.raw)
        package = manifest_module.package_name(axml)
        shared = manifest_module.shared_authorities(axml, package)
        self.assertEqual(shared, ["com.example.shared.provider1233"])

        renames = {old: old + ".margyt" for old in shared}
        manifest_module.rename_authorities(axml, renames)
        again = Axml.parse(axml.build())

        authorities = [again.attr_string(n, "authorities") for n in again.elements("provider")]
        self.assertIn("com.example.shared.provider1233.margyt", authorities)
        self.assertIn("cat.narezany.fixture.p", authorities)  # named after the package, untouched
        self.assertEqual(manifest_module.shared_authorities(again, package),
                         ["com.example.shared.provider1233.margyt"])

    def test_inserting_a_string_moves_every_index_that_follows(self):
        """The bug this test exists for: a pool insert renumbers the pool.

        Adding an attribute the file has never used puts its name in the middle
        of the pool, where the resource map ends. Every index above it moves --
        including the ones in elements that have been made but not inserted yet,
        which is how an <activity> once came out as an <action>.
        """
        axml = Axml.parse(self.raw)
        before = [axml.pool.get(node.name) for node in axml.nodes if node.kind == 0x0102]
        activity = axml.make_element("activity")
        axml.set_attr(activity, "configChanges", 0x10, 0xFFF)  # never used by the fixture
        after = [axml.pool.get(node.name) for node in axml.nodes if node.kind == 0x0102]
        self.assertEqual(before, after)
        self.assertEqual(axml.pool.get(activity.name), "activity")

    def test_an_adaptive_icon_reads_back(self):
        axml = Axml.parse(self.apk.read("res/mipmap-anydpi-v26/ic_app.xml"))
        layers = {}
        for layer in ("background", "foreground"):
            node = axml.elements(layer)[0]
            attr = axml.attr(node, "drawable")
            self.assertEqual(attr.kind, TYPE_REFERENCE)
            layers[layer] = attr.data
        self.assertNotEqual(layers["background"], layers["foreground"])


class ArscTest(unittest.TestCase):
    def setUp(self):
        self.apk = fixture()
        self.arsc = Arsc(self.apk.read("resources.arsc"))
        self.manifest = Axml.parse(self.apk.read("AndroidManifest.xml"))

    def tearDown(self):
        self.apk.close()

    def test_the_icon_resolves_to_files_in_the_apk(self):
        res_id = manifest_module.icon_ids(self.manifest)[0]
        paths = [self.arsc.file_path(v) for v in self.arsc.values(res_id)]
        self.assertIn("res/mipmap-mdpi-v4/ic_app.png", paths)
        self.assertIn("res/mipmap-hdpi-v4/ic_app.png", paths)
        self.assertIn("res/mipmap-anydpi-v26/ic_app.xml", paths)
        for path in paths:
            self.assertTrue(self.apk.has(path), path)

    def test_densities_come_out_of_the_config(self):
        res_id = manifest_module.icon_ids(self.manifest)[0]
        densities = sorted(v.density for v in self.arsc.values(res_id))
        self.assertEqual(densities, [160, 240, 0xFFFE])

    def test_a_same_length_string_can_be_swapped_in_place(self):
        res_id = manifest_module.icon_ids(self.manifest)[0]
        value = [v for v in self.arsc.values(res_id) if v.density == 160][0]
        size = len(self.arsc.data)
        self.arsc.replace_string(value.data, "res/mipmap-mdpi-v4/ic_zzz.png")
        self.assertEqual(len(self.arsc.data), size)
        self.assertEqual(self.arsc.strings.get(value.data), "res/mipmap-mdpi-v4/ic_zzz.png")

    def test_a_different_length_string_is_refused(self):
        res_id = manifest_module.icon_ids(self.manifest)[0]
        value = self.arsc.values(res_id)[0]
        with self.assertRaises(ArscError):
            self.arsc.replace_string(value.data, "res/short.png")

    def test_a_value_can_be_repainted_without_moving_a_byte(self):
        colour = self.find_colour()
        size = len(self.arsc.data)
        self.arsc.set_value(colour, colour.kind, artwork.MINT)
        self.assertEqual(len(self.arsc.data), size)
        again = Arsc(self.arsc.build())
        repainted = [v for v in again.values(self.colour_id) if v.offset == colour.offset][0]
        self.assertEqual(repainted.data, artwork.MINT)

    def find_colour(self):
        for package in self.arsc.packages:
            for type_id in package.types:
                name = package.type_names.get(type_id - 1)
                if name != "color":
                    continue
                for entry in range(4):
                    res_id = (package.id << 24) | (type_id << 16) | entry
                    values = self.arsc.values(res_id)
                    if values:
                        self.colour_id = res_id
                        return values[0]
        self.fail("the fixture has no colour resource")


class ApkZipTest(unittest.TestCase):
    def setUp(self):
        self.room = tempfile.mkdtemp()
        self.copy = os.path.join(self.room, "fixture.apk")
        shutil.copy(FIXTURE, self.copy)

    def tearDown(self):
        shutil.rmtree(self.room, ignore_errors=True)

    def test_a_rewrite_keeps_every_entry(self):
        source = fixture()
        original = {name: source.read(name) for name in source.names()}
        out = os.path.join(self.room, "out.apk")
        source.write(out)
        source.close()

        written = Apk(out)
        self.assertEqual(sorted(written.names()), sorted(original))
        for name, data in original.items():
            self.assertEqual(written.read(name), data, name)
        written.close()

    def test_edits_land_and_stored_entries_stay_aligned(self):
        apk = Apk(self.copy)
        apk.replace("resources.arsc", apk.read("resources.arsc"), STORED)
        apk.add("classes2.dex", b"not really a dex, but it is only bytes here")
        apk.remove("res/drawable/ic_back.xml")
        out = os.path.join(self.room, "out.apk")
        apk.write(out)
        apk.close()

        written = Apk(out)
        self.assertTrue(written.has("classes2.dex"))
        self.assertFalse(written.has("res/drawable/ic_back.xml"))
        self.assertEqual(written.index["resources.arsc"].method, STORED)
        for entry, offset in self.data_offsets(out, written):
            if entry.method == STORED:
                self.assertEqual(offset % 4, 0, entry.name)
        written.close()

    def test_the_old_signature_is_dropped(self):
        apk = Apk(self.copy)
        apk.add("META-INF/CERT.SF", b"x")
        apk.add("META-INF/CERT.RSA", b"x")
        apk.add("META-INF/MANIFEST.MF", b"x")
        apk.add("META-INF/services/keep.me", b"x")
        gone = apk.drop_signature()
        self.assertEqual(len(gone), 3)
        self.assertTrue(apk.has("META-INF/services/keep.me"))
        apk.close()

    @staticmethod
    def data_offsets(path, apk):
        with open(path, "rb") as handle:
            for entry in apk.entries:
                handle.seek(entry.source_offset)
                head = struct.unpack("<IHHHHHIIIHH", handle.read(30))
                yield entry, entry.source_offset + 30 + head[9] + head[10]


class PngTest(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(ROOT, artwork.MASTER_PNG), "rb") as handle:
            self.master = png.decode(handle.read())

    def test_the_master_is_what_it_claims(self):
        self.assertEqual((self.master.width, self.master.height), (512, 512))

    def test_resizing_keeps_the_corner_mint(self):
        for size in (48, 56, 192):
            small = self.master.resized(size)
            self.assertEqual(small.width, size)
            corner = tuple(small.pixels[:4])
            self.assertEqual(corner, (0x8D, 0xD1, 0xB0, 0xFF))

    def test_encode_decode_is_lossless(self):
        small = self.master.resized(32)
        again = png.decode(png.encode(small))
        self.assertEqual(again.width, 32)
        self.assertEqual(bytes(again.pixels), bytes(small.pixels))

    def test_size_without_decoding(self):
        data = png.encode(self.master.resized(64))
        self.assertEqual(png.size_of(data), (64, 64))


class VectorTest(unittest.TestCase):
    def test_a_generated_vector_parses_as_one(self):
        data = vector.build(artwork.VIEWPORT, artwork.COMBINED)
        axml = Axml.parse(data)
        self.assertEqual(axml.build(), data)

        root = axml.elements("vector")[0]
        self.assertEqual(axml.attr(root, "width").data, (108 << 8) | 1)  # 108dp
        self.assertEqual(axml.attr(root, "viewportWidth").data, vector.float_bits(108.0))

        paths = axml.elements("path")
        self.assertEqual(len(paths), len(artwork.COMBINED))
        colours = [axml.attr(p, "fillColor").data for p in paths]
        self.assertEqual(colours, [colour for colour, _data in artwork.COMBINED])
        for element, (_colour, data_string) in zip(paths, artwork.COMBINED):
            self.assertEqual(axml.pool.get(axml.attr(element, "pathData").data), data_string)

    def test_the_attribute_ids_are_the_ones_the_platform_uses(self):
        # read back out of the fixture, which aapt2 compiled from real source
        apk = fixture()
        axml = Axml.parse(apk.read("res/drawable/ic_back.xml"))
        apk.close()
        by_name = dict(zip([axml.pool.get(i) for i in range(len(axml.resource_map))],
                           axml.resource_map))
        for name, expected in zip(vector.ATTR_NAMES, vector.ATTR_IDS):
            if name in by_name:
                self.assertEqual(by_name[name], expected, name)


class IconTest(unittest.TestCase):
    def setUp(self):
        self.room = tempfile.mkdtemp()
        self.apk = fixture()
        self.arsc = Arsc(self.apk.read("resources.arsc"))
        self.manifest = Axml.parse(self.apk.read("AndroidManifest.xml"))
        with open(os.path.join(ROOT, artwork.MASTER_PNG), "rb") as handle:
            self.master = handle.read()

    def tearDown(self):
        self.apk.close()
        shutil.rmtree(self.room, ignore_errors=True)

    def test_every_file_behind_the_icon_is_replaced(self):
        sizes_before = {
            path: png.size_of(self.apk.read(path))
            for path in ("res/mipmap-mdpi-v4/ic_app.png", "res/mipmap-hdpi-v4/ic_app.png")
        }
        icon_module.replace_everywhere(self.apk, self.arsc, self.manifest, self.master)

        for path, size in sizes_before.items():
            self.assertEqual(png.size_of(self.apk.read(path)), size)
            image = png.decode(self.apk.read(path))
            self.assertEqual(tuple(image.pixels[:4]), (0x8D, 0xD1, 0xB0, 0xFF))

        # the adaptive icon still points where it did; its layers are ours now
        adaptive = Axml.parse(self.apk.read("res/mipmap-anydpi-v26/ic_app.xml"))
        self.assertEqual(len(adaptive.elements("adaptive-icon")), 1)
        for path, expected in (("res/drawable/ic_back.xml", artwork.BACKGROUND),
                               ("res/drawable/ic_front.xml", artwork.GLYPH)):
            layer = Axml.parse(self.apk.read(path))
            colours = [layer.attr(p, "fillColor").data for p in layer.elements("path")]
            self.assertEqual(colours, [colour for colour, _d in expected])

    def test_the_resource_table_is_not_disturbed(self):
        before = bytes(self.arsc.data)
        icon_module.replace_everywhere(self.apk, self.arsc, self.manifest, self.master)
        self.assertEqual(bytes(self.arsc.data), before)
        self.assertFalse(self.arsc.dirty)


class AccentTest(unittest.TestCase):
    """The fixture's colour is #FF0050, and its vector is filled with #161823."""

    PINK = 0xFFFF0050
    INK = 0xFF161823
    MINT = 0xFF8DD1B0

    def setUp(self):
        self.room = tempfile.mkdtemp()
        self.copy = os.path.join(self.room, "fixture.apk")
        shutil.copy(FIXTURE, self.copy)
        self.apk = Apk(self.copy)
        self.arsc = Arsc(self.apk.read("resources.arsc"))

    def tearDown(self):
        self.apk.close()
        shutil.rmtree(self.room, ignore_errors=True)

    def test_a_colour_resource_is_repainted_where_it_lies(self):
        size = len(self.arsc.data)
        report = accent_module.bake(self.apk, self.arsc, self.PINK, self.MINT)
        self.assertEqual(len(self.arsc.data), size)
        self.assertIn("resource entries: 1", report)

        again = Arsc(self.arsc.build())
        values = [v for v in self.values_of_every_colour(again)]
        self.assertIn(self.MINT, values)
        self.assertNotIn(self.PINK, values)

    def test_a_vector_fill_is_repainted_too(self):
        accent_module.bake(self.apk, self.arsc, self.INK, self.MINT)
        vector_xml = Axml.parse(self.apk.read("res/drawable/ic_back.xml"))
        fills = [vector_xml.attr(p, "fillColor").data for p in vector_xml.elements("path")]
        self.assertEqual(fills, [self.MINT])

    def test_nothing_happens_when_the_colour_is_already_the_one(self):
        before = bytes(self.arsc.data)
        report = accent_module.bake(self.apk, self.arsc, self.PINK, self.PINK)
        self.assertEqual(bytes(self.arsc.data), before)
        # nothing is written, but the build still has to say what it left alone:
        # those places are exactly the ones the runtime palette cannot reach
        self.assertIn("nothing to bake", report[0])
        self.assertTrue(any("stay as they are" in line for line in report))
        self.assertTrue(any("--accent" in line for line in report))

    def values_of_every_colour(self, arsc):
        for package in arsc.packages:
            for type_id in package.types:
                if package.type_names.get(type_id - 1) != "color":
                    continue
                for entry in range(8):
                    res_id = (package.id << 24) | (type_id << 16) | entry
                    for value in arsc.values(res_id):
                        yield value.data


class DexPatchTest(unittest.TestCase):
    SAMPLE = """\
.method public static a(Landroid/content/Context;)Ljava/lang/String;
    .locals 2
    invoke-virtual {v0}, Landroid/telephony/TelephonyManager;->getSimCountryIso()Ljava/lang/String;
    move-result-object v1
    invoke-virtual {v5, v0}, Landroid/telephony/TelephonyManager;->getSimState(I)I
    invoke-virtual/range {v10 .. v10}, Landroid/telephony/TelephonyManager;->hasIccCard()Z
    invoke-virtual {v0}, Landroid/telephony/TelephonyManager;->getDataNetworkType()I
    invoke-virtual {v0}, Lcom/example/Other;->getSimCountryIso()Ljava/lang/String;
    return-object v1
.end method
"""

    def rewrite(self, text):
        for _label, pattern, target in dexpatch.rules():
            text = pattern.sub(target, text)
        return text

    def test_the_calls_that_should_move_move(self):
        out = self.rewrite(self.SAMPLE)
        self.assertIn(
            "invoke-static {v0}, Lcat/narezany/margyt/Region;->"
            "getSimCountryIso(Landroid/telephony/TelephonyManager;)Ljava/lang/String;", out)
        self.assertIn(
            "invoke-static {v5, v0}, Lcat/narezany/margyt/Region;->"
            "getSimState(Landroid/telephony/TelephonyManager;I)I", out)
        self.assertIn(
            "invoke-static/range {v10 .. v10}, Lcat/narezany/margyt/Region;->"
            "hasIccCard(Landroid/telephony/TelephonyManager;)Z", out)

    def test_the_calls_that_should_not_move_stay(self):
        out = self.rewrite(self.SAMPLE)
        self.assertIn(
            "invoke-virtual {v0}, Landroid/telephony/TelephonyManager;->getDataNetworkType()I", out)
        self.assertIn(
            "invoke-virtual {v0}, Lcom/example/Other;->getSimCountryIso()Ljava/lang/String;", out)

    def test_every_target_has_a_method_to_land_in(self):
        source = os.path.join(ROOT, "inject", "java", "cat", "narezany", "margyt", "Region.java")
        with open(source, encoding="utf-8") as handle:
            java = handle.read()
        for name, _original, _replacement in dexpatch.TARGETS:
            self.assertIn(name + "(TelephonyManager tm", java, name)

    def test_a_renamed_authority_moves_in_the_bytecode_too(self):
        import tempfile as tf
        room = tf.mkdtemp()
        try:
            with open(os.path.join(room, "a.smali"), "w", encoding="utf-8") as handle:
                handle.write(
                    '    const-string v0, "com.example.shared.provider1233"\n'
                    '    const-string v1, "com.example.shared.provider1233.suffix"\n'
                    '    const-string v2, "untouched"\n'
                )
            counts = dexpatch.rewrite_literals(
                room, {"com.example.shared.provider1233": "com.example.shared.provider1233.margyt"})
            self.assertEqual(counts, {"com.example.shared.provider1233": 1})
            with open(os.path.join(room, "a.smali"), encoding="utf-8") as handle:
                out = handle.read()
            self.assertIn('"com.example.shared.provider1233.margyt"', out)
            # a longer string that merely starts the same is not a match
            self.assertIn('"com.example.shared.provider1233.suffix"', out)
            self.assertIn('"untouched"', out)
        finally:
            shutil.rmtree(room, ignore_errors=True)

    def test_a_dex_holding_a_renamed_authority_is_taken_apart(self):
        self.assertFalse(dexpatch.interesting(b"nothing", {"com.example.p": "x"}))
        self.assertTrue(dexpatch.interesting(b"...com.example.p...", {"com.example.p": "x"}))

    def test_a_forced_method_keeps_its_modifiers_and_loses_its_body(self):
        import tempfile as tf
        room = tf.mkdtemp()
        try:
            class_name, signature = dexpatch.FORCED_FALSE[0]
            path = os.path.join(room, *class_name.split("/")) + ".smali"
            os.makedirs(os.path.dirname(path))
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(
                    ".class public L%s;\n" % class_name
                    + ".method public final %s\n" % signature
                    + "    .registers 4\n\n"
                    + "    invoke-static {}, Lsomething/Expensive;->check()Z\n\n"
                    + "    move-result v0\n\n    return v0\n.end method\n"
                    + ".method public final other()V\n    return-void\n.end method\n"
                )
            counts = dexpatch.force_false(room)
            self.assertEqual(sum(counts.values()), 1)
            with open(path, encoding="utf-8") as handle:
                out = handle.read()
            self.assertIn(".method public final %s\n    .registers 1" % signature, out)
            self.assertNotIn("Expensive", out)
            self.assertIn("other()V", out)  # nothing else touched
        finally:
            shutil.rmtree(room, ignore_errors=True)

    def test_a_forced_method_that_moved_stops_the_build(self):
        import tempfile as tf
        room = tf.mkdtemp()
        try:
            class_name, _signature = dexpatch.FORCED_FALSE[0]
            path = os.path.join(room, *class_name.split("/")) + ".smali"
            os.makedirs(os.path.dirname(path))
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(".class public L%s;\n" % class_name)
            with self.assertRaises(RuntimeError):
                dexpatch.force_false(room)
        finally:
            shutil.rmtree(room, ignore_errors=True)

    def test_the_dex_holding_a_forced_class_is_taken_apart(self):
        class_name = dexpatch.FORCED_FALSE[0][0]
        self.assertTrue(dexpatch.interesting(("L%s;" % class_name).encode()))
        self.assertFalse(dexpatch.interesting(b"some other app entirely"))

    def test_the_accent_constant_becomes_a_call(self):
        text = ("    const v1, -0x1d3ab\n\n"
                "    invoke-virtual {v2, v1}, Landroid/graphics/Paint;->setColor(I)V\n\n"
                "    const v4, -0x1d3ac\n")
        for _label, pattern, target in dexpatch.accent_rules():
            text = pattern.sub(target, text)
        # accent(), not colour(): the constants go through the plugins and the
        # mod's own screen does not
        self.assertIn("invoke-static {}, Lcat/narezany/margyt/Accent;->accent()I", text)
        self.assertIn("move-result v1", text)
        self.assertIn("const v4, -0x1d3ac", text)  # a colour that is not the accent

    def test_the_save_button_is_pointed_at_the_clean_address(self):
        """Both names are TikTok's own, and both return the same type."""
        text = ("    invoke-virtual {v3}, Lcom/ss/android/ugc/aweme/feed/model/Video;"
                "->getDownloadAddr()Lcom/ss/android/ugc/aweme/base/model/UrlModel;\n"
                "    invoke-virtual {v3}, Lcom/example/Other;"
                "->getDownloadAddr()Lcom/ss/android/ugc/aweme/base/model/UrlModel;\n")
        for _label, pattern, target in dexpatch.model_rules():
            text = pattern.sub(target, text)
        self.assertIn("invoke-static {v3}, Lcat/narezany/margyt/Download;->getDownloadAddr("
                      "Lcom/ss/android/ugc/aweme/feed/model/Video;)"
                      "Lcom/ss/android/ugc/aweme/base/model/UrlModel;", text)
        # somebody else's method of the same name is not ours to move
        self.assertIn("Lcom/example/Other;->getDownloadAddr()", text)

    def test_a_dex_without_the_model_is_left_alone(self):
        self.assertFalse(dexpatch.touches_a_model(b"nothing here"))
        self.assertFalse(dexpatch.touches_a_model(
            b"Lcom/ss/android/ugc/aweme/feed/model/Video;\x00getPlayAddr"))
        self.assertTrue(dexpatch.touches_a_model(
            b"Lcom/ss/android/ugc/aweme/feed/model/Video;\x00getDownloadAddr"))
        self.assertTrue(dexpatch.touches_a_model(
            b"Lcom/ss/android/ugc/aweme/feed/model/FeedItemList;\x00getItems"))

    def test_the_feed_page_comes_through_the_mod(self):
        """The ads are dropped where the page is read, not hidden per screen."""
        text = ("    invoke-virtual {v3}, Lcom/ss/android/ugc/aweme/feed/model/"
                "FeedItemList;->getItems()Ljava/util/List;\n")
        for _label, pattern, target in dexpatch.model_rules():
            text = pattern.sub(target, text)
        self.assertIn("Lcat/narezany/margyt/Feed;->getItems("
                      "Lcom/ss/android/ugc/aweme/feed/model/FeedItemList;)"
                      "Ljava/util/List;", text)

    def test_comment_pages_are_filtered_before_tiktok_reads_them(self):
        text = ("    invoke-virtual {v3}, Lcom/example/CommentPage;->getComments()"
                "Ljava/util/List;\n")
        for _label, pattern, target in dexpatch.model_rules():
            text = pattern.sub(target, text)
        self.assertIn("Lcat/narezany/margyt/CommentFilter;->getComments("
                      "Ljava/lang/Object;)Ljava/util/List;", text)

    def test_comment_filter_source_is_defensive(self):
        path = os.path.join(ROOT, "inject", "java", "cat", "narezany", "margyt",
                            "CommentFilter.java")
        with open(path, encoding="utf-8") as source:
            text = source.read()
        self.assertIn("https://tiktokyou.yzewe.ru/api/v1/badges", text)
        self.assertIn("new JSONArray", text)
        self.assertIn("keeping the last list", text)
        self.assertIn('"roblox russia".equals(plain)', text)

    def test_a_field_read_becomes_a_call_and_a_move(self):
        """allowDownload is a field, so one instruction has to become two."""
        text = ("    iget-object v2, v5, Lcom/ss/android/ugc/aweme/feed/model/"
                "VideoControl;->allowDownload:Ljava/lang/Boolean;\n")
        for _label, pattern, target in dexpatch.model_rules():
            text = pattern.sub(target, text)
        self.assertIn("invoke-static {v5}, Lcat/narezany/margyt/Download;->allowDownload("
                      "Lcom/ss/android/ugc/aweme/feed/model/VideoControl;)"
                      "Ljava/lang/Boolean;", text)
        self.assertIn("move-result-object v2", text)
        # the receiver is read into the call, the result lands in the original
        self.assertLess(text.index("invoke-static"), text.index("move-result-object"))

    def test_a_colour_being_applied_is_redirected_too(self):
        """Reading a colour is half of it; the other half is using one."""
        text = ("    invoke-virtual {v2, v1}, Landroid/graphics/Paint;->setColor(I)V\n"
                "    invoke-virtual {v3, v1}, Landroid/widget/TextView;->setTextColor(I)V\n"
                "    invoke-static {v1}, Landroid/content/res/ColorStateList;"
                "->valueOf(I)Landroid/content/res/ColorStateList;\n"
                "    invoke-virtual {v4, v1}, Lcom/example/Own;->setColor(I)V\n")
        for _label, pattern, target in dexpatch.accent_rules():
            text = pattern.sub(target, text)
        self.assertIn("Lcat/narezany/margyt/Accent;->setColor(Landroid/graphics/Paint;I)V", text)
        self.assertIn("Lcat/narezany/margyt/Accent;->setTextColor("
                      "Landroid/widget/TextView;I)V", text)
        # a static keeps its shape exactly: no receiver to move
        self.assertIn("invoke-static {v1}, Lcat/narezany/margyt/Accent;->valueOf(I)"
                      "Landroid/content/res/ColorStateList;", text)
        self.assertIn("Lcom/example/Own;->setColor(I)V", text)  # not ours to touch

    def test_the_stamp_is_only_dropped_in_the_class_that_draws_it(self):
        """Every drawBitmap in the apk is not ours to touch -- one of them is."""
        call = ("    invoke-virtual {v6, v3, v0, v0, v5}, Landroid/graphics/Canvas;"
                "->drawBitmap(Landroid/graphics/Bitmap;FFLandroid/graphics/Paint;)V\n")

        marked = '    const-string v1, "[tiktok_logo]"\n' + call
        other = "    const-string v1, \"something else\"\n" + call
        for anchor, _label, pattern, target in dexpatch.anchored_rules():
            if anchor in marked:
                marked = pattern.sub(target, marked)
            if anchor in other:
                other = pattern.sub(target, other)

        self.assertIn("Lcat/narezany/margyt/Watermark;->drawBitmap("
                      "Landroid/graphics/Canvas;Landroid/graphics/Bitmap;FF"
                      "Landroid/graphics/Paint;)V", marked)
        self.assertIn("invoke-static {v6, v3, v0, v0, v5}", marked)  # same registers
        self.assertNotIn("margyt", other)  # a class without the marker is left alone

    def test_a_dex_without_the_marker_is_left_alone(self):
        self.assertTrue(dexpatch.carries_an_anchor(b"...[tiktok_logo]..."))
        self.assertFalse(dexpatch.carries_an_anchor(b"nothing of the sort"))

    def test_a_colour_asked_of_the_framework_is_redirected(self):
        text = ("    invoke-virtual {v0, v1}, Landroid/content/res/Resources;->getColor(I)I\n"
                "    invoke-virtual {v0, v1}, Lcom/example/Own;->getColor(I)I\n")
        for _label, pattern, target in dexpatch.accent_rules():
            text = pattern.sub(target, text)
        self.assertIn("invoke-static {v0, v1}, Lcat/narezany/margyt/Accent;->"
                      "getColor(Landroid/content/res/Resources;I)I", text)
        self.assertIn("Lcom/example/Own;->getColor(I)I", text)  # someone else's method

    def test_the_pink_is_looked_for_as_an_instruction(self):
        import struct
        colour = struct.pack("<I", dexpatch.TIKTOK_PINK)
        self.assertTrue(dexpatch.holds_the_pink(b"\x14\x02" + colour))   # const v2, pink
        self.assertFalse(dexpatch.holds_the_pink(b"some string " + colour))

    def test_the_dex_format_is_read_off_the_header(self):
        self.assertEqual(dexpatch.dex_format(b"dex\n035\x00rest"), "035")
        self.assertEqual(dexpatch.dex_format(b"dex\n039\x00rest"), "039")

    def test_the_new_dex_continues_the_run(self):
        self.assertEqual(dexpatch.next_dex_name(["classes.dex", "AndroidManifest.xml"]),
                         "classes2.dex")
        self.assertEqual(
            dexpatch.next_dex_name(["classes.dex", "classes2.dex", "classes3.dex"]),
            "classes4.dex")

    def test_a_dex_without_telephony_is_left_alone(self):
        self.assertFalse(dexpatch.interesting(b"nothing to see here"))
        self.assertFalse(dexpatch.interesting(b"Landroid/telephony/TelephonyManager;getDataState"))
        self.assertTrue(
            dexpatch.interesting(b"Landroid/telephony/TelephonyManager;\x00getSimCountryIso"))


class PaletteTest(unittest.TestCase):
    """The zone the accent takes over, and the step it moves it by."""

    PINK = 0xFFFE2C55
    MINT = 0xFF8DD1B0
    CYAN = 0xFF25F4EE  # TikTok's other brand colour, and it has to stay put

    def test_the_reference_lands_exactly_on_the_accent(self):
        self.assertEqual(palette.map_colour(self.PINK, self.PINK, self.MINT), self.MINT)

    def test_alpha_is_kept_and_the_rest_follows(self):
        """Half-transparent pink is the same pink: the first build missed all of it."""
        for alpha in (0x00, 0x1A, 0x80, 0xD9):
            faded = (alpha << 24) | (self.PINK & 0xFFFFFF)
            moved = palette.map_colour(faded, self.PINK, self.MINT)
            self.assertEqual(moved >> 24 & 0xFF, alpha)
            self.assertEqual(moved & 0xFFFFFF, self.MINT & 0xFFFFFF)

    def test_the_neighbours_of_the_family_come_along(self):
        # the shades the apk actually holds, counted off 46.9.42
        for neighbour in (0xFFFF1764, 0xFFED3495, 0xFFF43F5E, 0xFFFF3B5C, 0xFFFB1E70):
            self.assertTrue(palette.captures(neighbour, self.PINK))
            self.assertNotEqual(palette.map_colour(neighbour, self.PINK, self.MINT),
                                neighbour)

    def test_what_is_not_the_family_is_not_touched(self):
        for other in (self.CYAN, 0xFF000000, 0xFFFFFFFF, 0xFF808080,
                      0xFF4C8DFF, 0xFF35C759, 0xFF1C2C24):
            self.assertFalse(palette.captures(other, self.PINK))
            self.assertEqual(palette.map_colour(other, self.PINK, self.MINT), other)

    def test_a_lighter_member_stays_lighter(self):
        """Gradients have two ends, and they have to still have two."""
        light = palette.map_colour(0xFFFF96B8, self.PINK, self.MINT)
        dark = palette.map_colour(0xFF801D35, self.PINK, self.MINT)
        self.assertGreater(palette._split(light)[3], palette._split(dark)[3])

    def test_asking_for_the_colour_it_already_is_changes_nothing(self):
        for colour in (self.PINK, 0xFFFF1764, self.CYAN):
            self.assertEqual(palette.map_colour(colour, self.PINK, self.PINK), colour)

    def test_the_java_side_was_given_the_same_numbers(self):
        """Two implementations of one formula, and a seam if they disagree."""
        source = os.path.join(ROOT, "inject", "java", "cat", "narezany", "margyt",
                              "Palette.java")
        with open(source, encoding="utf-8") as handle:
            java = handle.read()
        self.assertIn("HUE = %gf" % palette.HUE, java)
        self.assertIn("MIN_SATURATION = %gf" % palette.MIN_SATURATION, java)
        self.assertIn("MIN_VALUE = %gf" % palette.MIN_VALUE, java)


if __name__ == "__main__":
    unittest.main()

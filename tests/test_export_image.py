from component.widget import export_dialog


class FakeImage:
    def __init__(self, bands):
        self.bands = bands
        self.properties = {}

    def rename(self, name):
        return FakeImage([name])

    def clip(self, _aoi):
        return self

    def mask(self):
        return "source mask"

    def updateMask(self, mask):
        assert mask == "source mask"
        return self

    def addBands(self, other):
        return FakeImage(self.bands + other.bands)

    def set(self, properties):
        self.properties = properties
        return self


def test_export_image_includes_belt_band_and_class_metadata(monkeypatch):
    monkeypatch.setattr(export_dialog.ee, "Image", lambda _asset: FakeImage(["belts"]))

    image = export_dialog.prepare_export_image(
        FakeImage(["final_degradation"]), "aoi", export_dialog.DEGRADATION_CLASSES
    )

    assert image.bands == ["final_degradation", "bioclimatic_belt"]
    assert image.properties["mgci_bioclimatic_belt_classes"] == (
        "1=Nival; 2=Alpine; 3=Montane; 4=Remaining mountain area"
    )
    assert "0=Unclassified" in image.properties["mgci_pixel_classes"]
